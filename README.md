<div align="center">

# 👁️ RetinaScan AI

**AI-Based Diabetic Retinopathy Screening & Classification — SIH 2026 · SIH26038**

Upload a fundus image → quality gate → 5-stage ICDR classification → lesion segmentation overlay → HL7 FHIR R4 report.

[![CI](https://github.com/Siddhesh-ai-del/retinascan-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/Siddhesh-ai-del/retinascan-ai/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.6-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![ONNX](https://img.shields.io/badge/ONNX%20Runtime-CPU%20%7C%20GPU-005CED?style=flat-square&logo=onnx&logoColor=white)](https://onnxruntime.ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

![ICDR Accuracy](https://img.shields.io/badge/ICDR_val_accuracy-76.7%25-blue?style=for-the-badge)
![Inference](https://img.shields.io/badge/full_pipeline-0.39s-success?style=for-the-badge)
![Stages](https://img.shields.io/badge/ICDR_stages-0–4-purple?style=for-the-badge)
![Lesions](https://img.shields.io/badge/lesion_classes-4-orange?style=for-the-badge)

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
python -m src.models.train --mode classification --epochs 30 --batch_size 16
python -m src.models.train --mode segmentation --epochs 80 --batch_size 8
python -m src.export.onnx_export                              # FP32 + INT8 + benchmark
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

| Metric | Value |
|---|---|
| Classifier val accuracy (IDRiD + APTOS) | **76.7%** |
| No DR class F1 | 0.97 |
| Full pipeline latency (CPU) | **0.39 s** |
| Classifier ONNX latency | 77 ms |
| Segmenter ONNX latency | 150 ms |
| Demo-set screening accuracy | **5/5 stages correct** |
| Parameters | 8.1M classifier · 12.5M segmenter |

## 🌐 API

| Endpoint | Description |
|---|---|
| `POST /api/assess-quality` | IQA only — gradable verdict + feedback |
| `POST /api/predict?patient_id=` | Full pipeline (JSON with base64 overlays + FHIR) |
| `GET  /api/fhir/{patient_id}` | Cached FHIR DiagnosticReport |
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

## ⚠️ Disclaimer

Research prototype built for **Smart India Hackathon 2026**. This is decision-support software, **not** a certified medical device and not a substitute for clinical diagnosis.

## 📄 License

[MIT](LICENSE) © 2026 Siddhesh
