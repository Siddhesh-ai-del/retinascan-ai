import logging
import os
import shutil
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import anyio
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from src.constants import CLASS_NAMES
from src.inference.explain import explain_preprocessed
from src.inference.predictor import DRPredictor
from src.report.pdf import generate_pdf_report

logger = logging.getLogger("retinascan.api")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
DEMO_DIR = PROJECT_ROOT / "demo_images"
CLASSIFIER_FP32 = PROJECT_ROOT / "models" / "onnx" / "classifier.onnx"
CLASSIFIER_INT8 = PROJECT_ROOT / "models" / "onnx" / "classifier_int8.onnx"
SEGMENTER_FP32 = PROJECT_ROOT / "models" / "onnx" / "segmenter.onnx"
SEGMENTER_INT8 = PROJECT_ROOT / "models" / "onnx" / "segmenter_int8.onnx"
CLASSIFIER_PTH = PROJECT_ROOT / "models" / "classification" / "best_classifier.pth"
CAM_ENABLED = CLASSIFIER_PTH.exists()

# --- configuration (env-overridable; defaults keep the local demo friction-free) ---
API_KEY = os.environ.get("RETINASCAN_API_KEY", "").strip()  # unset => auth disabled
MAX_UPLOAD_MB = float(os.environ.get("RETINASCAN_MAX_UPLOAD_MB", "10"))
RATE_LIMIT_PER_MIN = int(os.environ.get("RETINASCAN_RATE_LIMIT_PER_MIN", "30"))
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get("RETINASCAN_ALLOWED_ORIGINS", "*").split(",") if o.strip()
] or ["*"]
FHIR_CACHE_MAX = 256
UPLOAD_CHUNK = 1024 * 1024

predictor: Optional[DRPredictor] = None
# Full predict payloads per patient (FHIR doc, images, review flag, attention heatmap).
results_cache: "OrderedDict[str, dict]" = OrderedDict()
_rate_bucket: dict = defaultdict(deque)


def _pick(fp32: Path, int8: Path) -> Optional[Path]:
    if fp32.exists():
        return fp32
    return int8 if int8.exists() else None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global predictor
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    classifier_path = _pick(CLASSIFIER_FP32, CLASSIFIER_INT8)
    segmenter_path = _pick(SEGMENTER_FP32, SEGMENTER_INT8)
    predictor = DRPredictor(classifier_path, segmenter_path)
    logger.info(
        "Models loaded. Ready: %s (classifier=%s, segmenter=%s)",
        predictor.is_ready(),
        classifier_path is not None,
        segmenter_path is not None,
    )
    yield


app = FastAPI(title="RetinaScan AI - DR Screening", version="1.0.0", lifespan=lifespan)
# allow_credentials stays False: the SPA uses no cookies, and False keeps "*" origins spec-safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _check_auth(request: Request) -> None:
    """No-op unless RETINASCAN_API_KEY is configured."""
    if not API_KEY:
        return
    if request.headers.get("X-API-Key") != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing X-API-Key header")


def _check_rate_limit(request: Request) -> None:
    now = time.monotonic()
    bucket = _rate_bucket[request.client.host if request.client else "unknown"]
    while bucket and now - bucket[0] > 60:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_PER_MIN:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again shortly.")
    bucket.append(now)


def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    path = UPLOAD_DIR / f"{int(time.time())}_{uuid.uuid4().hex[:8]}{suffix}"
    limit_bytes = MAX_UPLOAD_MB * 1024 * 1024
    written = 0
    try:
        with path.open("wb") as f:
            while chunk := file.file.read(UPLOAD_CHUNK):
                written += len(chunk)
                if written > limit_bytes:
                    raise HTTPException(status_code=413, detail=f"Upload exceeds {MAX_UPLOAD_MB:g} MB limit")
                f.write(chunk)
    except HTTPException:
        path.unlink(missing_ok=True)
        raise
    except OSError as e:
        path.unlink(missing_ok=True)
        logger.error("Failed writing upload: %s", e)
        raise HTTPException(status_code=500, detail="Could not store uploaded file") from e
    finally:
        file.file.close()
    return path


def _cache_result(patient_id: str, payload: dict) -> None:
    results_cache.pop(patient_id, None)
    results_cache[patient_id] = payload
    while len(results_cache) > FHIR_CACHE_MAX:
        results_cache.popitem(last=False)


@app.get("/api/health")
async def health():
    return {"status": "ok", "models_loaded": bool(predictor and predictor.is_ready())}


@app.post("/api/assess-quality")
async def assess_quality(request: Request, file: UploadFile = File(...)):
    _check_auth(request)
    _check_rate_limit(request)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Models not loaded yet.")
    path = await _save_and_keep(file)
    try:
        return predictor.iqa.assess(path)
    except Exception as e:
        logger.exception("Quality assessment failed")
        raise HTTPException(status_code=500, detail="Quality assessment failed for this image") from e
    finally:
        path.unlink(missing_ok=True)


async def _save_and_keep(file: UploadFile) -> Path:
    """Blocking disk IO in a worker thread so the event loop is never stalled."""
    return await anyio.to_thread.run_sync(_save_upload, file)


@app.post("/api/predict")
async def predict(request: Request, file: UploadFile = File(...), patient_id: str = ""):
    _check_auth(request)
    _check_rate_limit(request)
    if predictor is None or not predictor.is_ready():
        raise HTTPException(status_code=503, detail="Models not loaded yet. Train models and run ONNX export first.")
    pid = patient_id or "anonymous"
    path = await _save_and_keep(file)
    try:
        result = await anyio.to_thread.run_sync(predictor.predict, path, pid)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Inference failed for patient '%s'", pid)
        raise HTTPException(status_code=500, detail="Inference failed. Check server logs for details.") from e
    finally:
        path.unlink(missing_ok=True)

    if result.get("fhir"):
        _cache_result(pid, {**result, "patient_id": pid})
    return result


@app.post("/api/explain")
async def explain(request: Request, file: UploadFile = File(...), patient_id: str = ""):
    """Grad-CAM attention heatmap for the predicted ICDR stage."""
    _check_auth(request)
    _check_rate_limit(request)
    if predictor is None or not predictor.is_ready():
        raise HTTPException(status_code=503, detail="Models not loaded yet. Train models and run ONNX export first.")
    if not CAM_ENABLED:
        raise HTTPException(status_code=503, detail="Grad-CAM unavailable: classifier checkpoint (.pth) not found.")
    path = await _save_and_keep(file)
    try:
        base, input_tensor = predictor._preprocess(path)

        def _run_cam():
            return explain_preprocessed(CLASSIFIER_PTH, base, input_tensor)

        heatmap_b64, stage = await anyio.to_thread.run_sync(_run_cam)
        label = CLASS_NAMES[stage] if 0 <= stage < len(CLASS_NAMES) else f"Stage {stage}"
        if patient_id and heatmap_b64:
            cached = results_cache.get(patient_id)
            if cached is not None:
                cached["attention"] = heatmap_b64
        return {"heatmap": heatmap_b64, "stage": stage, "label": label}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Explain failed")
        raise HTTPException(status_code=500, detail="Could not compute attention heatmap") from e
    finally:
        path.unlink(missing_ok=True)


@app.get("/api/fhir/{patient_id}")
async def get_fhir_report(request: Request, patient_id: str):
    _check_auth(request)
    report = (results_cache.get(patient_id) or {}).get("fhir")
    if report is None:
        raise HTTPException(status_code=404, detail=f"No FHIR report cached for patient '{patient_id}'. Run a prediction first.")
    return report


@app.get("/api/report/{patient_id}.pdf")
async def get_pdf_report(request: Request, patient_id: str):
    _check_auth(request)
    payload = results_cache.get(patient_id)
    if not payload:
        raise HTTPException(status_code=404, detail=f"No prediction cached for patient '{patient_id}'. Run a prediction first.")
    try:

        def _build():
            return generate_pdf_report(payload)

        pdf_bytes = await anyio.to_thread.run_sync(_build)
    except Exception as e:
        logger.exception("PDF generation failed for patient '%s'", patient_id)
        raise HTTPException(status_code=500, detail="Could not generate PDF report") from e
    filename = f'RetinaScanAI_{patient_id}_{payload.get("_generated_ts", "report")}.pdf'
    from urllib.parse import quote

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"},
    )


@app.get("/api/demo-images")
async def list_demo_images():
    images = []
    if DEMO_DIR.exists():
        for pattern in ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp"):
            images.extend({"name": p.name, "url": p.name} for p in sorted(DEMO_DIR.glob(pattern)))
    return {"images": images}


@app.get("/api/demo-image/{name}")
async def get_demo_image(name: str):
    if "/" in name or ".." in name or "\\" in name or "\x00" in name:
        raise HTTPException(status_code=400, detail="Invalid image name")
    path = DEMO_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Demo image not found")
    return FileResponse(path)
