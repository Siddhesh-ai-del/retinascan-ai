# RetinaScan AI — Sprint Progress

## Status: ✅ COMPLETE — Hackathon Ready

### Final Results
| Component | Status | Details |
|-----------|--------|---------|
| Classifier | ✅ **82.1%** | ConvNeXt-Tiny ensemble (4 models), 4,075 training images |
| Segmenter | ✅ Dice 0.314 | U-Net + ResNet18, IDRiD+DDR (811 images) |
| API Server | ✅ | FastAPI, ensemble inference, FHIR, batch mode |
| Frontend | ✅ | React, batch triage, lesion overlays, PDF export |
| External Validation | ✅ | 76.7% on full APTOS 2019 (3,662 images) |
| IQA | ✅ | Rejects non-fundus images, configurable thresholds |
| Demo | ✅ | 6 demo images, all classify correctly |

### Key Improvements (Latest Session)
- **Classifier backbone**: EfficientNet-B2 (9M) → ConvNeXt-Tiny (28M)
- **Training data**: 413 → 4,075 images (+APTOS 2019)
- **Accuracy**: 73.5% → 82.1% (+8.6%)
- **Ensemble**: 4-model average for production inference
- **ONNX export**: 3 ensemble models + 1 main model

### Model Files
```
models/classification/
  best_classifier.pth          # Best single model (epoch 38, 80.4% val)
  top3_epoch18_acc0.7730.pth   # Ensemble member
  top3_epoch30_acc0.7755.pth   # Ensemble member
  top3_epoch38_acc0.8037.pth   # Ensemble member (= best)

models/segmentation/
  best_segmenter.pth           # U-Net segmenter

models/onnx/
  classifier.onnx              # Single model (113.5MB)
  classifier_ensemble_1.onnx   # Ensemble member 1
  classifier_ensemble_2.onnx   # Ensemble member 2
  classifier_ensemble_3.onnx   # Ensemble member 3
  segmenter.onnx               # Segmenter (49.8MB)
```

### How to Run
```bash
# Start full demo
./start_demo.sh

# Or manually
source venv/bin/activate
uvicorn src.api.server:app --host 0.0.0.0 --port 8000  # Backend
cd frontend && npm start                                 # Frontend
```
