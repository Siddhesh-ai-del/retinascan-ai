"""
Capture real model evidence for the deck: predictions, lesion overlays and
Grad-CAM attention heatmaps, straight out of the running FastAPI service.

Outputs -> scripts/deck_assets/out/
    hero_cam.png          Grad-CAM overlay (proliferative demo image)
    hero_cam_healthy.png  Grad-CAM overlay (healthy demo image)
    lesion_overlay.png    combined 4-lesion segmentation overlay
    evidence.json         real classification + quality numbers for the deck

Run:  ./venv/bin/python scripts/deck_assets/capture_evidence.py
Falls back gracefully: on any failure it writes evidence.json with
{"fallback": true} so the deck builder can switch to illustrative art.
"""

from __future__ import annotations

import base64
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8011
BASE = f"http://127.0.0.1:{PORT}"
PY = ROOT / "venv" / "bin" / "python"


def log(msg: str) -> None:
    print(f"[evidence] {msg}", flush=True)


def wait_health(proc, timeout: float = 180.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited early (rc={proc.returncode})")
        try:
            with urllib.request.urlopen(f"{BASE}/api/health", timeout=3) as r:
                payload = json.loads(r.read())
                if payload.get("models_loaded"):
                    return payload
        except Exception:
            pass
        time.sleep(1.5)
    raise TimeoutError("backend never became healthy")


def multipart(path: Path, extra: dict[str, str] | None = None) -> bytes:
    boundary = "----deckassetboundary"
    parts = []
    for key, val in (extra or {}).items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode()
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{path.name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode()
        + path.read_bytes()
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts)


def post(path: Path, endpoint: str, extra: dict[str, str] | None = None) -> dict:
    req = urllib.request.Request(
        f"{BASE}{endpoint}",
        data=multipart(path, extra),
        headers={"Content-Type": "multipart/form-data; boundary=----deckassetboundary"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read())


def save_b64(data: str, name: str) -> None:
    (OUT / name).write_bytes(base64.b64decode(data))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [
            str(PY),
            "-m",
            "uvicorn",
            "src.api.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
        ],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    evidence: dict = {"fallback": True, "errors": []}
    try:
        health = wait_health(proc)
        log(f"healthy: {health}")

        # --- prediction + segmentation overlay ---------------------------------
        img = ROOT / "demo_images" / "proliferative_dr.jpg"
        pred = post(img, "/api/predict", {"patient_id": "deck-hero"})
        log(f"predict status={pred.get('status')} cls={pred.get('classification')}")
        seg = pred.get("segmentation") or {}
        if seg.get("overlay"):
            save_b64(seg["overlay"], "lesion_overlay.png")
        if seg.get("original"):
            save_b64(seg["original"], "lesion_original.png")

        # --- Grad-CAM (real, from the .pth checkpoint) -------------------------
        cams = {}
        for fname, out_name in [
            ("proliferative_dr.jpg", "hero_cam.png"),
            ("moderate_npdr.jpg", "hero_cam_mod.png"),
            ("healthy.jpg", "hero_cam_healthy.png"),
        ]:
            try:
                cam = post(
                    ROOT / "demo_images" / fname,
                    "/api/explain",
                    {"patient_id": "deck-hero"},
                )
                if cam.get("heatmap"):
                    save_b64(cam["heatmap"], out_name)
                    cams[fname] = cam.get("label")
                    log(f"grad-cam {fname} -> {out_name} ({cam.get('label')})")
            except Exception as e:  # noqa: BLE001
                evidence["errors"].append(f"explain {fname}: {e}")
                log(f"grad-cam FAILED {fname}: {e}")

        # --- IQA rejection evidence (blurry demo frame) -------------------------
        try:
            rej = post(ROOT / "demo_images" / "blurry_ungradable.jpg", "/api/predict")
            evidence["rejected"] = {
                "status": rej.get("status"),
                "quality": rej.get("quality"),
            }
            log(f"rejection demo status={rej.get('status')}")
        except Exception as e:  # noqa: BLE001
            evidence["errors"].append(f"reject: {e}")

        cls = pred.get("classification") or {}
        evidence.update(
            {
                "fallback": not cams,
                "stage": cls.get("label"),
                "confidence": cls.get("confidence"),
                "probabilities": cls.get("probabilities"),
                "quality": pred.get("quality"),
                "needs_human_review": pred.get("needs_human_review"),
                "lesions": {k: v for k, v in (seg.get("lesions") or {}).items()},
                "gradcam": cams,
                "referral": pred.get("referral"),
            }
        )
    except Exception as e:  # noqa: BLE001
        evidence["errors"].append(f"fatal: {e}")
        log(f"FAILED: {e}")
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:  # noqa: BLE001
            proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:  # noqa: BLE001
            proc.kill()
    (OUT / "evidence.json").write_text(json.dumps(evidence, indent=1))
    log(
        f"evidence.json fallback={evidence.get('fallback')} errors={evidence.get('errors')}"
    )
    return 0 if not evidence.get("fallback") else 1


if __name__ == "__main__":
    sys.exit(main())
