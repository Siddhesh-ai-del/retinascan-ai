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
    cv2.circle(img, (300, 300), 260, (25, 85, 140), -1)
    rng = np.random.default_rng(42)
    for _ in range(3500):
        x, y = int(rng.integers(90, 510)), int(rng.integers(90, 510))
        dx, dy = int(rng.integers(-25, 25)), int(rng.integers(-25, 25))
        color = (30 + int(rng.integers(0, 50)), 70 + int(rng.integers(0, 60)), 110 + int(rng.integers(0, 80)))
        cv2.line(img, (x, y), (x + dx, y + dy), color, 1)
    return img


def random_photo():
    rng = np.random.default_rng(7)
    img = rng.integers(80, 220, (600, 600, 3), dtype=np.uint8)
    cv2.circle(img, (360, 300), 120, (150, 130, 180), -1)
    cv2.rectangle(img, (100, 500), (620, 690), (60, 50, 70), -1)
    return img


def test_iqa_gradable(tmp):
    p = str(tmp / "fundus.png")
    cv2.imwrite(p, synthetic_fundus())
    r = ImageQualityAssessor().assess(p)
    assert r["gradable"], f"expected gradable, got {r}"
    assert r["fundus_score"] >= 0.5, f"synthetic fundus failed gate: {r}"
    print("PASS iqa gradable:", r["blur_score"], "fundus_score:", r["fundus_score"])


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


def test_random_photo_rejected(tmp):
    p = str(tmp / "photo.jpg")
    cv2.imwrite(p, random_photo())
    r = ImageQualityAssessor().assess(p)
    assert not r["gradable"], f"expected rejection of non-fundus image, got {r}"
    assert "no_fundus_detected" in r["quality_issues"], r["quality_issues"]
    print("PASS non-fundus rejected:", r["quality_issues"], "fundus_score:", r["fundus_score"])


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


def test_api_health():
    """Boot the FastAPI app with TestClient and verify the health endpoint."""
    from fastapi.testclient import TestClient

    from src.api.server import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/health")
    assert resp.status_code == 200, f"health check failed: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body["status"] == "ok", f"unexpected status: {body}"
    print(f"PASS api health: models_loaded={body['models_loaded']}")


def test_api_file_type_validation():
    """Reject non-image uploads with 415 Unsupported Media Type."""
    from fastapi.testclient import TestClient

    from src.api.server import app

    client = TestClient(app, raise_server_exceptions=False)
    # Send a .txt file — should be rejected
    resp = client.post(
        "/api/predict",
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 415, f"expected 415, got {resp.status_code}: {resp.text}"
    print("PASS api file type validation: rejected .txt upload")


def test_api_demo_images():
    """Verify the demo-images endpoint returns a list."""
    from fastapi.testclient import TestClient

    from src.api.server import app

    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/api/demo-images")
    assert resp.status_code == 200, f"demo-images failed: {resp.status_code}"
    body = resp.json()
    assert "images" in body, f"unexpected response: {body}"
    print(f"PASS api demo-images: {len(body['images'])} images listed")


def test_fhir_robustness():
    """FHIR generator handles edge cases without crashing."""
    # Empty lesion summary
    report = generate_fhir_report(
        "edge-patient",
        {"stage": 0, "label": "No DR", "confidence": 0.99},
        {},
    )
    assert report["resourceType"] == "DiagnosticReport"
    # None lesion summary
    report2 = generate_fhir_report(
        "edge-patient-2",
        {"stage": 1, "label": "Mild NPDR", "confidence": 0.7},
        None,
    )
    assert report2["conclusionCode"]["coding"][0]["code"] == "714812005"
    print("PASS fhir robustness: edge cases handled")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_iqa_gradable(Path(tmp))
        test_iqa_blur_rejected(Path(tmp))
        test_random_photo_rejected(Path(tmp))
    test_fhir_report()
    test_fhir_robustness()
    test_api_health()
    test_api_file_type_validation()
    test_api_demo_images()
    print("ALL CI CHECKS PASSED")
