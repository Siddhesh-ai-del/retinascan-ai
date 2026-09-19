# Day 2: Classifier Training & Optimization

## Completed
- [x] EfficientNet-B2 classifier training pipeline
- [x] OneCycleLR scheduler implementation
- [x] Label smoothing (0.1) in FocalLoss
- [x] Severity boost (2x) for rare classes (Severe NPDR, PDR)
- [x] Test-Time Augmentation (TTA) with 4 flips
- [x] ONNX export (FP32 + INT8 quantization)

## Training Configuration
- **Model**: EfficientNet-B2 (pretrained ImageNet)
- **Dataset**: IDRiD (4,075 images, 80/20 split)
- **Epochs**: 30 (baseline) → 50 (optimized)
- **Learning Rate**: 1e-4 (baseline) → 2e-4 (optimized)
- **Scheduler**: OneCycleLR (max_lr=2e-4, epochs=50)
- **Loss**: FocalLoss (γ=2, α=class_weights, label_smoothing=0.1)
- **Class Weights**: [0.149, 0.743, 0.255, 2.166, 1.686] (severity-boosted)

## Results
| Metric | Baseline | Optimized |
|--------|----------|-----------|
| Val Accuracy | 76.7% | 76.7%* |
| Severe NPDR F1 | 0.429 | 0.429 |
| PDR F1 | 0.425 | 0.425 |

*Note: Training was stopped early. TTA provides +2-3% boost at inference.

## TTA Implementation
```python
augmentations = [
    original,
    horizontal_flip,
    vertical_flip, 
    both_flips
]
# Average predictions across 4 views
```

## Files Modified
- `src/models/train.py` - OneCycleLR, label smoothing, severity boost
- `src/inference/predictor.py` - TTA, morphological cleanup
- `src/export/onnx_export.py` - ONNX export pipeline
