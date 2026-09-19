# RetinaScan AI — Hackathon Submission

## Quick Start
1. `bash start_demo.sh`
2. Open http://localhost:3000
3. Upload a fundus image and click "Analyze"

## What's Included
- AI-powered DR screening (5-stage ICDR classification)
- Lesion segmentation overlay
- HL7 FHIR R4 clinical reports
- Batch screening mode
- Clinical validation report

## Model Performance

### External Validation (APTOS 2019 — 3,394 unseen images)

| Metric | Value |
|---|---|
| Overall accuracy | 60.8% (95% CI: 59.2–62.3%) |
| **Referable DR sensitivity** | **97.5%** (95% CI: 96.5–98.2%) |
| Specificity | 72.8% |
| NPV | 97.5% |
| AUC | 0.8433 |
| Inference latency | 590ms mean, 710ms P95 |

### Clinical Story
This is a **screening** tool, not a diagnostic tool. High sensitivity (97.5%) catches nearly all referable DR cases. NPV of 97.5% means if the model says "no referral," patients are almost certainly safe.

## Files
- `hackathon_sprint/clinical_validation_report.pdf` — Clinical metrics report
- `hackathon_sprint/RetinaScanAI_Presentation.pptx` — 12-slide presentation
- `hackathon_sprint/metrics/` — Raw metrics data
- `hackathon_sprint/metrics/validation_charts.png` — ROC + F1 charts

## API Endpoints
- `POST /api/predict` — Single image analysis
- `POST /api/batch-predict` — Batch analysis (up to 20 images)
- `GET /api/fhir/{patient_id}` — FHIR DiagnosticReport
- `GET /api/report/{patient_id}.pdf` — PDF clinical report
- `GET /api/health` — Health check

## Demo Images
- `healthy.jpg` → Stage 0 (No DR)
- `mild_npdr.jpg` → Stage 1 (Mild NPDR)
- `moderate_npdr.jpg` → Stage 2 (Moderate NPDR)
- `severe_npdr.jpg` → Stage 3 (Severe NPDR)
- `proliferative_dr.jpg` → Stage 4 (PDR)
- `blurry_ungradable.jpg` → IQA rejection
