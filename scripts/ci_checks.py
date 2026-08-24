"""CI smoke tests that run without torch or trained models."""
import json
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.fhir.generator import generate_fhir_report  # noqa: E402
from src.quality.iqa import ImageQualityAssessor  # noqa: E402


def synthetic_fundus():
    img = np.zeros((600, 600, 3), dtype=np.uint8)
    cv2.circle(img, (300, 300), 260, (30, 90, 60), -1)
    for _ in range(3000):
        x, y = np.random.randint(80, 520, 2)
        cv2.line(
            img,
            (x, y),
            (x + np.random.randint(-25, 25), y + np.random.randint(-25, 25)),
            (40 + int(np.random.randint(0, 60)), 120, 60),
            1,
        )
    return img


def test_iqa_gradable(tmp):
    p = str(tmp / "fundus.png")
    cv2.imwrite(p, synthetic_fundus())
    r = ImageQualityAssessor().assess(p)
    assert r["gradable"], f"expected gradable, got {r}"
    print("PASS iqa gradable:", r["blur_score"])


def test_iqa_blur_rejected(tmp):
    p = str(tmp / "blur.jpg")
    blurred = cv2.GaussianBlur(synthetic_fundus(), (0, 0), sigmaX=18)
    small = cv2.resize(blurred, (100, 100))
    degraded = cv2.resize(small, (600, 600), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(p, degraded, [cv2.IMWRITE_JPEG_QUALITY, 35])
    r = ImageQualityAssessor().assess(p)
    assert not r["gradable"], f"expected rejection, got {r}"
    assert "blur" in r["quality_issues"]
    print("PASS iqa blur rejected:", r["quality_issues"])


def test_fhir_report():
    report = generate_fhir_report(
        "ci-patient",
        {"stage": 3, "label": "Severe NPDR", "confidence": 0.9},
        {"microaneurysms": {"detected": True}, "hemorrhages": {"detected": False}},
    )
    assert report["resourceType"] == "DiagnosticReport"
    assert report["result"][0]["valueInteger"] == 3
    json.dumps(report)
    print("PASS fhir report:", report["conclusionCode"]["coding"][0]["display"])


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_iqa_gradable(Path(tmp))
        test_iqa_blur_rejected(Path(tmp))
    test_fhir_report()
    print("ALL CI CHECKS PASSED")
