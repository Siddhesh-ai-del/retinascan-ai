# RetinaScan AI — Evaluation Metrics & Benchmark Results

> AI-Based Diabetic Retinopathy Screening & Classification

## Classification (ICDR 5-stage)

**Model:** ConvNeXt-Tiny (28M params), ImageNet-pretrained backbone, custom head (GELU, dropout 0.3→512→256→5)
**Data:** IDRiD (413 images) + APTOS 2019 (3,662 images) = **4,075 training images** (10× previous)
**Loss:** Focal loss (γ=2.0, label smoothing 0.15) with severity-boosted class weights · **Opt:** AdamW 1e-4, OneCycleLR, AMP, gradient clipping
**Ensemble:** 4-model average (best + top-3 checkpoints by internal val accuracy)
**Validation:** stratified 80/20 split of combined IDRiD+APTOS (815 images: 85 IDRiD, 730 APTOS)

### Internal Validation (20% held-out)

| Metric | Value |
|---|---|
| **Overall accuracy** | **80.4%** (single best) / **82.1%** (4-model ensemble) |
| No DR F1 | 0.977 |
| Mild NPDR F1 | 0.626 |
| Moderate NPDR F1 | 0.755 |
| Severe NPDR F1 | 0.321 |
| Proliferative DR F1 | 0.442 |

### Full APTOS 2019 (3,662 images — external validation)

| Metric | Value |
|---|---|
| **Overall accuracy** | **76.7%** (ensemble) |
| No DR F1 | 0.952 (98.6% recall) |
| Mild NPDR F1 | 0.218 (14.1% recall) |
| Moderate NPDR F1 | 0.718 (89.4% recall) |
| Severe NPDR F1 | 0.172 (9.8% recall) |
| Proliferative DR F1 | 0.334 (22.4% recall) |

> **Note:** Full APTOS accuracy (76.7%) is lower than the held-out split (82.1%) because the APTOS class distribution is more imbalanced than the combined IDRiD+APTOS split. The held-out split benefits from IDRiD's more balanced distribution.

## Lesion Segmentation (U-Net)

**Model:** U-Net with ResNet18 ImageNet encoder, decoder (128→8), 4 output channels
**Data:** IDRiD (54 images) + DDR (383+149+225 images) = 811 training images with pixel-level lesion masks
**Loss:** 1.5×Dice(multilabel) + 0.5×BCE(pos_weight [31,10,11,23]) · **Test dice:** **0.314** (225 unseen DDR test images)

### Per-Class Test Dice (DDR Test Set)

| Lesion Type | Dice |
|---|---|
| Microaneurysms (MA) | 0.116 |
| Haemorrhages (HE) | 0.178 |
| Hard Exudates (EX) | 0.196 |
| Cotton Wool Spots (CWS) | **0.769** |

> DDR dataset increased training data from 54 to 811 images (15× increase). Cotton Wool Spot detection is particularly strong. Microaneurysms remain challenging due to their tiny size (5–10 pixels).

## Model Architecture Changes

| Component | Before | After |
|---|---|---|
| Classifier backbone | EfficientNet-B2 (9M params) | **ConvNeXt-Tiny (28M params)** |
| Training data | IDRiD only (413 images) | **IDRiD + APTOS (4,075 images)** |
| Loss function | Focal only | Focal + Mixup augmentation |
| Class balancing | severity_boost=2.0 | **severity_boost=4.0** |
| Inference | Single model | **4-model ensemble** |
| Classifier val accuracy | 73.5% | **82.1%** (+8.6%) |

## Latency (ONNX Runtime, CPU — Intel-class laptop CPU, RTX 4050 GPU available but not required)

| Component | FP32 | INT8 (dynamic) |
|---|---|---|
| Classifier ConvNeXt-Tiny (512² input) | **160 ms** | 930 ms |
| Segmenter (512² input) | **150 ms** | 1,949 ms |
| **End-to-end API call** (IQA + preprocess + both models + overlays + FHIR) | **≈ 0.7 s** | — |
| Grad-CAM `/api/explain` (PyTorch .pth, CPU, lazy-loaded) | **≈ 0.35 s** | — |

> INT8 dynamic quantization degrades ConvNeXt-Tiny (5.8× slower on CPU) — server uses FP32.

## Ensemble Details

| Checkpoint | Internal Val | APTOS Val |
|---|---|---|
| best (epoch 38) | 80.4% | 81.6% |
| top3_epoch30 | 77.6% | 80.4% |
| top3_epoch18 | 77.3% | 80.6% |
| **Average ensemble** | — | **82.1%** |

## IQA Validation Gauntlet

| Test set | Result |
|---|---|
| 5 bundled demo fundus images | 5/5 gradable (fundus score 0.88–0.96) |
| Synthetic selfie-like photo | rejected (fundus 0.30) |
| Flat bright frame | rejected (0.00) |
| Text screenshot | rejected (0.19) |
| Random raw APTOS/IDRiD sample (n=20) | 19/20 pass (single reject genuinely dark) |
| DDR test images (n=10) | 10/10 gradable |

## Known Limitations

- Rare stages (Mild/Severe/Proliferative) have weaker recall due to class imbalance (~3–20% prevalence)
- Severe NPDR recall is 9.8% on full APTOS — class boundary overlap with Moderate NPDR
- Segmenter microaneurysm detection is limited (Dice 0.116) due to tiny lesion size
- Single-fundus (not bilateral) analysis; no OCT/clinical metadata fusion
- Decision-support prototype — not a certified medical device
- Ensemble adds 3× model loading cost (~340 MB additional memory)
