import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.inference.predictor import DRPredictor

PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "data" / "uploads"
DEMO_DIR = PROJECT_ROOT / "demo_images"
CLASSIFIER_FP32 = PROJECT_ROOT / "models" / "onnx" / "classifier.onnx"
CLASSIFIER_INT8 = PROJECT_ROOT / "models" / "onnx" / "classifier_int8.onnx"
SEGMENTER_FP32 = PROJECT_ROOT / "models" / "onnx" / "segmenter.onnx"
SEGMENTER_INT8 = PROJECT_ROOT / "models" / "onnx" / "segmenter_int8.onnx"


def _pick(fp32, int8):
    if fp32.exists():
        return fp32
    return int8 if int8.exists() else None

predictor: Optional[DRPredictor] = None
fhir_cache: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global predictor
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    predictor = DRPredictor(_pick(CLASSIFIER_FP32, CLASSIFIER_INT8), _pick(SEGMENTER_FP32, SEGMENTER_INT8))
    print(f"Models loaded. Ready: {predictor.is_ready()} (classifier={predictor.classifier is not None}, segmenter={predictor.segmenter is not None})")
    yield


app = FastAPI(title="RetinaScan AI - DR Screening", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload(file: UploadFile) -> Path:
    suffix = Path(file.filename or "image.jpg").suffix or ".jpg"
    path = UPLOAD_DIR / f"{int(time.time())}_{uuid.uuid4().hex[:8]}{suffix}"
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    return path


@app.get("/api/health")
async def health():
    return {"status": "ok", "models_loaded": bool(predictor and predictor.is_ready())}


@app.post("/api/assess-quality")
async def assess_quality(file: UploadFile = File(...)):
    path = _save_upload(file)
    result = predictor.iqa.assess(path)
    return result


@app.post("/api/predict")
async def predict(file: UploadFile = File(...), patient_id: str = ""):
    if predictor is None or not predictor.is_ready():
        raise HTTPException(status_code=503, detail="Models not loaded yet. Train models and run ONNX export first.")
    path = _save_upload(file)
    try:
        result = predictor.predict(path, patient_id=patient_id or "anonymous")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")
    finally:
        path.unlink(missing_ok=True)

    if result.get("fhir"):
        pid = patient_id or "anonymous"
        fhir_cache[pid] = result["fhir"]
    return result


@app.get("/api/fhir/{patient_id}")
async def get_fhir_report(patient_id: str):
    report = fhir_cache.get(patient_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"No FHIR report cached for patient '{patient_id}'. Run a prediction first.")
    return report


@app.get("/api/demo-images")
async def list_demo_images():
    images = []
    if DEMO_DIR.exists():
        for p in sorted(DEMO_DIR.glob("*.jpg")) + sorted(DEMO_DIR.glob("*.png")):
            images.append({"name": p.name, "url": p.name})
    return {"images": images}


@app.get("/api/demo-image/{name}")
async def get_demo_image(name: str):
    if "/" in name or ".." in name or "\\" in name:
        raise HTTPException(status_code=400, detail="Invalid image name")
    path = DEMO_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Demo image not found")
    from fastapi.responses import FileResponse

    return FileResponse(path)
