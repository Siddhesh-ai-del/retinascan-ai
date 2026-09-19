# RetinaScan AI — Sprint Progress

## Last Updated: 2026-09-19

---

## Current Status: Day 9 COMPLETE — Ready for Submission

We have completed Days 1-9 of the 10-day hackathon sprint. All core deliverables are ready and tested.

---

## What Was Done

### Days 1-2: Model Training

**Problem found:** APTOS data was included in training (data leakage). Retrained on IDRiD only.

**Training run 1 (combined IDRiD+APTOS):**
- Best val accuracy: 80.5% (target: 82%)
- Attempted severity_boost=2.0, label_smoothing=0.1
- Attempted severity_boost=3.0, label_smoothing=0.15
- Did not reach 82% target, but improved from 76.7% baseline

**Training run 2 (IDRiD only — clean):**
- Best val accuracy: 73.5%
- Only 413 IDRiD images (small dataset trade-off)
- Model exported to ONNX: `models/onnx/classifier.onnx` (32.2 MB)

**Code changes in `src/models/train.py`:**
- `FocalLoss` with label_smoothing=0.15
- `compute_class_weights` with severity_boost=3.0
- `OneCycleLR` scheduler (replaces CosineAnnealing)
- scheduler.step() inside batch loop
- Default: epochs=50, lr=2e-4, batch_size=16
- `build_combined_dataset` now uses `include_aptos=False` (clean validation)

**Code changes in `src/inference/predictor.py`:**
- `_classify_tta` method (4 augmentations: original + h-flip + v-flip + both)
- `predict()` calls `_classify_tta` instead of `_classify`

### Days 3-4: External Validation

**Dataset:** APTOS 2019 (3,662 images, completely unseen during training)

**Results:**
- Evaluated: 3,394 images (268 rejected by IQA = 7.3%)
- **Overall accuracy: 60.8%** (95% CI: 59.2–62.3%)
- **Referable DR sensitivity: 97.5%** (95% CI: 96.5–98.2%) ✅
- **Specificity: 72.8%**
- **NPV: 97.5%**
- **AUC: 0.8433**
- Inference latency: 350ms mean, 445ms P95

**Per-class F1:**
- No DR: 0.897
- Mild NPDR: 0.000 (model never predicts this class)
- Moderate NPDR: 0.499
- Severe NPDR: 0.256
- Proliferative DR: 0.326

**Files generated:**
- `hackathon_sprint/metrics/external_validation.json` — full metrics
- `hackathon_sprint/metrics/external_validation.txt` — human-readable report
- `hackathon_sprint/metrics/validation_charts.png` — ROC + F1 charts
- `hackathon_sprint/metrics/comparison.json` — before/after comparison

### Day 5: Segmenter Visual Polish ✅

**Completed tasks:**
- [x] Morphological cleanup (opening + closing) in `src/inference/predictor.py`
- [x] Lower segmentation threshold (0.40 → 0.30) for more sensitive detection
- [x] Higher overlay alpha (0.65 → 0.75) for better visibility
- [x] Thicker contours (2px) for easier viewing in screenshots
- [x] Lesion area percentage calculation in `predict()` return
- [x] Frontend lesion summary card in `Results.jsx`
- [x] Area percentage display in `LesionOverlay.jsx` legend
- [x] CSS styling for `.lesion-summary`, `.lesion-row`, `.lesion-status`

### Day 6: Batch Triage Demo Feature ✅

**Completed tasks:**
- [x] `/api/batch-predict` endpoint (up to 20 images) in `src/api/server.py`
- [x] Severity-sorted results (highest urgency first)
- [x] Frontend batch upload UI in `BatchScreening.jsx`
- [x] Progress bar with per-image status
- [x] Summary cards (total/screened/urgent/review/rejected)
- [x] Sortable results table with severity coloring
- [x] CSV export button
- [x] "View" button for individual results

### Day 7: Frontend Polish ✅

**Completed tasks:**
- [x] Clean, professional UI design (Japanese editorial theme)
- [x] Responsive layout (desktop + tablet)
- [x] Dark mode support
- [x] Loading states & error handling
- [x] Accessibility (ARIA labels, keyboard nav)
- [x] Image upload with drag-and-drop
- [x] Results display with confidence bars
- [x] Lesion overlay with colored contours
- [x] Referral urgency indicator
- [x] FHIR JSON viewer
- [x] PDF report download

### Day 8: API & Backend Polish ✅

**Completed tasks:**
- [x] FastAPI endpoints with auto-docs
- [x] Batch prediction endpoint
- [x] Visit history with SQLite
- [x] Error handling & validation
- [x] Rate limiting & CORS
- [x] API key authentication (optional)
- [x] Grad-CAM attention heatmap endpoint
- [x] PDF report generation endpoint

### Day 8: Presentation & Reports ✅

**Completed tasks:**
- [x] Clinical validation report PDF (`hackathon_sprint/clinical_validation_report.pdf`)
- [x] Presentation slides (`hackathon_sprint/RetinaScanAI_Presentation.pptx`) — 12 slides with real metrics
- [x] All metric files generated and validated

---

### Day 9: Final Polish ✅

**Completed tasks:**
- [x] Full system test — all 5 demo images produce valid results
- [x] IQA rejection working (blurry image correctly rejected)
- [x] Invalid file type rejection working (415 error)
- [x] FHIR report generation and caching working
- [x] PDF report generation working (271KB)
- [x] Demo images list endpoint working (6 images)
- [x] **Bug fix:** `patient_id` form field missing `Form()` annotation in `/api/predict` and `/api/batch-predict` — was silently defaulting to "anonymous", breaking FHIR caching
- [x] hackathon_sprint/README.md created
- [x] PROGRESS.md updated with all sprint details

---

## Remaining Sprint Days

| Day | Task | Status |
|-----|------|--------|
| 1-2 | Model accuracy blitz | ✅ Complete |
| 3-4 | External validation | ✅ Complete |
| 5 | Segmenter visual polish | ✅ Complete |
| 6 | Batch triage demo feature | ✅ Complete |
| 7 | Clinical metrics report | ✅ Complete |
| 8 | PPT + presentation | ✅ Complete |
| 9 | Final polish | ✅ Complete |
| 10 | Rehearse + submit | ⏳ Pending |

---

## Key Commands

```bash
# Activate environment
source venv/bin/activate

# Train classifier (IDRiD only — clean)
python -m src.models.train --mode classification --epochs 50 --batch_size 16 --lr 2e-4

# Export to ONNX
python -m src.export.onnx_export --skip-segmenter

# Run external validation
python scripts/external_validation.py

# Generate clinical report PDF
python scripts/generate_clinical_report.py

# Generate presentation
python scripts/create_ppt.py

# Start demo
bash start_demo.sh
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/models/train.py` | Training code (modified: label smoothing, severity boost, OneCycleLR) |
| `src/inference/predictor.py` | Inference code (modified: TTA, morphological cleanup, lesion stats) |
| `src/api/server.py` | API endpoints (batch predict, FHIR, Grad-CAM, PDF) — fixed `patient_id` Form() bug |
| `scripts/external_validation.py` | External validation script |
| `scripts/generate_clinical_report.py` | Clinical report PDF generator |
| `scripts/create_ppt.py` | Presentation generator |
| `models/onnx/classifier.onnx` | Exported ONNX model |
| `models/classification/best_classifier.pth` | PyTorch checkpoint |
| `hackathon_sprint/metrics/` | All validation metrics and charts |
| `hackathon_sprint/clinical_validation_report.pdf` | Clinical report PDF |
| `hackathon_sprint/RetinaScanAI_Presentation.pptx` | Presentation slides |
| `frontend/src/components/` | React UI components |

---

## Honest Assessment

**Strengths:**
- 97.5% sensitivity for referable DR — clinically strong
- AUC 0.84 — solid discrimination
- TTA implemented for better predictions
- Clean external validation on 3,394 unseen images
- Complete end-to-end pipeline: upload → quality gate → classify → segment → FHIR report
- Batch triage mode for clinical workflow
- Professional UI with lesion overlays and area percentages
- Clinical validation report PDF ready for presentation

**Weaknesses:**
- Overall accuracy 60.8% (below 75% target)
- Mild NPDR class has 0% F1
- Model struggles with fine-grained classification
- IDRiD-only training (413 images) limits performance
- No demo video recorded yet

**Story for hackathon:**
This is a *screening* tool, not a *diagnostic* tool. High sensitivity (97.5%) catches nearly all referable cases. The model is safe — NPV of 97.5% means if it says "no referral," patients are almost certainly safe.

---

## Demo Checklist

- [x] Start demo server (`bash start_demo.sh`)
- [x] Open frontend (http://localhost:3000)
- [x] Upload single image → see results
- [x] Show lesion overlays with area percentages
- [x] Upload batch → see sorted results table
- [x] Export CSV from batch results
- [x] Download PDF report
- [x] Show FHIR JSON output
- [x] FHIR caching fixed and working
- [x] All smoke tests passing
- [ ] Record demo video (manual — requires screen recording)
- [ ] Final rehearsal (manual — requires presentation practice)
