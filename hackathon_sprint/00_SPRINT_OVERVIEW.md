# RetinaScan AI — 10-Day Hackathon Sprint

## Deadline
- **Start:** Day 1 (Monday)
- **End:** Day 10 (Wednesday)
- **Submission:** Day 10 afternoon

## What We're Building
An AI-powered Diabetic Retinopathy screening system that:
1. Accepts retinal fundus photographs
2. Classifies DR severity (ICDR 5-stage)
3. Segments lesions (microaneurysms, hemorrhages, exudates, cotton wool spots)
4. Generates HL7 FHIR R4 clinical reports
5. Provides referral urgency guidance

## Current State (Pre-Sprint)

### Model Performance
| Model | Metric | Current Value | Target |
|---|---|---|---|
| Classifier (EfficientNet-B2) | Val accuracy | 76.7% | 82-85% |
| Classifier | Severe NPDR F1 | 0.43 | 0.60+ |
| Classifier | Proliferative DR F1 | 0.42 | 0.60+ |
| Classifier | Referable DR sensitivity | Unknown | 85%+ |
| Segmenter (U-Net ResNet18) | Val Dice | 0.21 | Polish visuals, skip retraining |

### Infrastructure
- Backend: FastAPI (single process, `src/api/server.py`)
- Frontend: React 19 SPA (`frontend/`)
- Models: ONNX format, served via onnxruntime
- Database: SQLite for visit history
- Launch: `bash start_demo.sh`

### Datasets
- IDRiD (Indian Diabetic Retinopathy Image Dataset) — downloaded via `src/data/download.py`
- APTOS 2019 — downloaded via `src/data/download.py`
- Total: ~4,500 images
- **No external validation performed**

## Sprint Goals (Ranked by Priority)

### P0 — Must Complete
1. **Model accuracy: 76.7% → 82-85%** (Days 1-2)
2. **External validation on unseen data** (Days 3-4)
3. **Clinical metrics report** (Day 7)

### P1 — Should Complete
4. Segmenter visual polish (Day 5)
5. Batch triage demo feature (Day 6)

### P2 — Nice to Have
6. PPT + presentation (Day 8)
7. Demo video recording (Day 8)
8. Final polish (Day 9)

## File Structure
```
hackathon_sprint/
├── 00_SPRINT_OVERVIEW.md          ← You are here
├── 01_DAY_MODEL_TRAINING.md       ← Days 1-2: Model accuracy blitz
├── 02_DAY_DATA_VALIDATION.md      ← Days 3-4: External validation
├── 03_DAY_SEGMENTER.md            ← Day 5: Segmenter triage
├── 04_DAY_DEMO_FEATURE.md         ← Day 6: Killer demo feature
├── 05_DAY_CLINICAL_REPORT.md      ← Day 7: Clinical validation report
├── 06_DAY_PPT.md                  ← Day 8: Presentation
├── 07_DAY_POLISH.md               ← Day 9: Polish everything
├── 08_DAY_SUBMIT.md               ← Day 10: Rehearse + submit
├── 09_DAY_BUFFER.md               ← Buffer day if behind schedule
└── metrics/                       ← Generated metrics go here
```

## Key Commands Reference
```bash
# Activate environment
source venv/bin/activate

# Train classifier
python -m src.models.train --mode classification --epochs 50 --batch_size 16 --lr 1e-4

# Train segmenter
python -m src.models.train --mode segmentation --epochs 100 --batch_size 8 --lr 1e-4

# Export to ONNX
python -m src.export.onnx_export

# Run CI tests
python scripts/ci_checks.py

# Start demo
bash start_demo.sh

# Download datasets
python -m src.data.download --aptos
python -m src.data.download --idrid
```

## Success Criteria
The sprint is DONE when:
- [ ] Classifier accuracy ≥ 82% on validation set
- [ ] External validation completed on ≥1,000 unseen images
- [ ] Sensitivity/specificity report generated
- [ ] Demo runs cleanly end-to-end
- [ ] PPT is ready for submission
- [ ] Demo video recorded (backup for live demo failures)
