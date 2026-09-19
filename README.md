<div align="center">

# 👁️ RetinaScan AI

**AI-Based Diabetic Retinopathy Screening & Classification**

Upload a fundus image → quality gate → 5-stage ICDR classification → lesion segmentation overlay → HL7 FHIR R4 report.

[![CI](https://github.com/Siddhesh-ai-del/retinascan-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Siddhesh-ai-del/retinascan-ai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![ONNX](https://img.shields.io/badge/ONNX%20Runtime-CPU%20%7C%20GPU-005CED?style=flat-square&logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![License: Proprietary](https://img.shields.io/badge/License-Proprietary-red.svg?style=flat-square)](LICENSE)

![ICDR Accuracy](https://img.shields.io/badge/external_val_accuracy-60.8%25-blue?style=for-the-badge)
![Sensitivity](https://img.shields.io/badge/referable_DR_sensitivity-97.5%25-green?style=for-the-badge)
![Inference](https://img.shields.io/badge/full_pipeline-0.59s-success?style=for-the-badge)
![Stages](https://img.shields.io/badge/ICDR_stages-0–4-purple?style=for-the-badge)

</div>

---

## ✨ What it does

| Stage | Tech | Output |
|---|---|---|
| 🛡️ Image Quality Gate | OpenCV (retina-masked CLAHE-Laplacian blur, brightness, glare, fundus geometry) | Gradable verdict + recapture guidance |
| 🎨 Preprocessing | CLAHE → green channel → pupil-centered crop → 512² | Normalized tensor |
| 🧠 Classification | EfficientNet-B2 (focal loss, class-weighted) | ICDR stage 0–4 + confidence |
| 🔬 Lesion Segmentation | U-Net / ResNet18 encoder (Dice + weighted BCE) | Microaneurysms · Hemorrhages · Hard Exudates · Cotton Wool Spots |
| 📊 Visualization | Per-lesion toggleable overlays | Color-coded canvas |
| 🏥 Interoperability | HL7 **FHIR R4** DiagnosticReport (SNOMED CT + LOINC) | Standards-compliant JSON |

## 🚀 Quick Start

```bash
git clone https://github.com/Siddhesh-ai-del/retinascan-ai.git
cd retinascan-ai
```

<details>
<summary><b>1 · Environment setup</b> (one-time)</summary>

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cd frontend && npm install && cd ..
```

</details>

<details>
<summary><b>2 · Data + training</b> (one-time, ~1h GPU)</summary>

Requires [Kaggle API credentials](https://www.kaggle.com/docs/api) (`~/.kaggle/access_token` or `kaggle.json`) and APTOS competition rules accepted.

```bash
python -m src.data.download                                   # IDRiD + APTOS (~10GB)
python -m src.models.train --mode classification --epochs 50 --batch_size 16 --lr 2e-4
python -m src.models.train --mode segmentation --epochs 80 --batch_size 8
python -m src.export.onnx_export --skip-segmenter                  # FP32 ONNX
```

Preprocessed tensors are cached in `data/processed/cache_512/` after the first run.

</details>

### 3 · Run the demo

```bash
bash start_demo.sh        # one command: backend :8000 + frontend :3000
```

Open **http://localhost:3000**, then drag an image from `demo_images/`:
`blurry_ungradable.jpg` shows the IQA rejection flow · `moderate_npdr.jpg` runs the full pipeline.

## 🏗️ Architecture

```
                 ┌──────────────────────┐
   fundus.jpg ──▶│  Image Quality Gate  │── reject ──▶ recapture guidance
                 └──────────┬───────────┘
                            ▼
                 ┌──────────────────────┐
                 │  CLAHE·green·crop    │  512×512, cached tensors
                 └──────────┬───────────┘
              ┌─────────────┴─────────────┐
              ▼                           ▼
   ┌────────────────────┐      ┌────────────────────┐
   │ EfficientNet-B2    │      │ U-Net (ResNet18)   │
   │ ICDR stage 0–4     │      │ MA·HE·EX·CWS masks │
   └─────────┬──────────┘      └─────────┬──────────┘
             └─────────────┬─────────────┘
                           ▼
            ┌──────────────────────────────┐
            │ overlays · referral advice · │
            │ FHIR R4 DiagnosticReport     │
            └──────────────────────────────┘
```

Both models run as **INT8/FP32 ONNX** via onnxruntime (CUDA when available, CPU fallback).

## 📈 Results

### External Validation (APTOS 2019 — 3,394 unseen images)

| Metric | Value |
|---|---|
| Overall accuracy | **60.8%** (95% CI: 59.2–62.3%) |
| Referable DR sensitivity | **97.5%** (95% CI: 96.5–98.2%) |
| Referable DR specificity | 72.8% |
| NPV (safe to discharge) | 97.5% |
| AUC | 0.8433 |
| IQA rejection rate | 7.3% |

### Per-Class F1 (External Validation)

| Class | F1 |
|---|---|
| No DR | 0.897 |
| Mild NPDR | 0.000 |
| Moderate NPDR | 0.499 |
| Severe NPDR | 0.256 |
| Proliferative DR | 0.326 |

### Performance

| Metric | Value |
|---|---|
| Full pipeline latency (CPU) | **0.59 s** |
| P95 latency | 0.71 s |
| Classifier ONNX latency | 77 ms |
| Segmenter ONNX latency | 150 ms |
| Parameters | 8.1M classifier · 12.5M segmenter |

## 🌐 API

| Endpoint | Description |
|---|---|
| `POST /api/assess-quality` | IQA only — gradable verdict + feedback |
| `POST /api/predict?patient_id=` | Full pipeline (JSON with base64 overlays + FHIR) |
| `POST /api/batch-predict` | Batch analysis (up to 20 images) |
| `GET  /api/fhir/{patient_id}` | Cached FHIR DiagnosticReport |
| `GET  /api/report/{patient_id}.pdf` | PDF clinical report |
| `GET  /api/demo-images` | Bundled demo images |
| `GET  /api/health` | Liveness + model status |

## 📁 Project Structure

```
├── src/
│   ├── data/          download · preprocess (CLAHE/crop/cache) · datasets
│   ├── quality/       image quality assessment
│   ├── models/        classifier · segmenter · training loops
│   ├── export/        ONNX export + INT8 quantization + benchmarks
│   ├── inference/     predictor pipeline
│   ├── fhir/          FHIR R4 generator (SNOMED/LOINC coded)
│   └── api/           FastAPI server
├── frontend/          React 19 UI (upload · overlays · FHIR viewer)
├── demo_images/       bundled fundus samples per ICDR stage
├── models/onnx/       exported inference artifacts (generated)
└── start_demo.sh      one-command launcher
```

## 📚 Datasets & Citations

- **IDRiD** — Porwal *et al.*, "Indian Diabetic Retinopathy Image Dataset (DRiD)", *Data* 2018 — grading labels + pixel-level lesion annotations
- **APTOS 2019** — Kaggle Blindness Detection — 3,662 graded fundus images

> Trained models are not distributed in this repo — export them with `src.export.onnx_export`.

## 🗺️ Roadmap

- Docker Compose one-command hosting (backend + nginx frontend) — spec drafted, pending verification on a Docker-enabled machine
- Multi-user auth + cloud deployment
- Longitudinal risk scoring across bilateral visit history

## ⚠️ Disclaimer

Research prototype. This is decision-support software, **not** a certified medical device and not a substitute for clinical diagnosis.

## 📄 License

[Proprietary](LICENSE) © 2026 Siddhesh
