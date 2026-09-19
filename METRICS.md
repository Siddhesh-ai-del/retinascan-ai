# RetinaScan AI — Evaluation Metrics & Benchmark Results

> AI-Based Diabetic Retinopathy Screening & Classification

## Classification (ICDR 5-stage)

**Model:** EfficientNet-B2, ImageNet-pretrained backbone, custom head (dropout 0.3 → 256 → 5)
**Data:** IDRiD disease grading (413 train + 103 test) — APTOS 2019 held out for external validation
**Loss:** Focal loss (γ=2.0, label smoothing 0.15) with severity-boosted class weights · **Opt:** AdamW 2e-4, OneCycleLR, AMP
**Validation:** stratified 80/20 split (IDRiD only)

| Metric | Value |
|---|---|
| **IDRiD validation accuracy** | **73.5%** |
| No DR F1 | 0.794 |
| Mild NPDR F1 | 0.333 |
| Moderate NPDR F1 | 0.560 |
| Severe NPDR F1 | 0.571 |
| Proliferative DR F1 | 0.286 |

Full per-class report: `models/classification/classification_report.txt` · confusion matrix: `confusion_matrix.png`

## External Validation (APTOS 2019 — 3,394 unseen images)

| Metric | Value |
|---|---|
| **Overall accuracy** | **60.8%** (95% CI: 59.2–62.3%) |
| **Referable DR sensitivity** | **97.5%** (95% CI: 96.5–98.2%) |
| Referable DR specificity | 72.8% |
| NPV (safe to discharge) | 97.5% |
| AUC | 0.8433 |
| IQA rejection rate | 7.3% |

### Per-Class F1 (External Validation)

| Class | Precision | Recall | F1 |
|---|---|---|---|
| No DR | 0.637 | 0.936 | 0.897 |
| Mild NPDR | 0.000 | 0.000 | 0.000 |
| Moderate NPDR | 0.610 | 0.419 | 0.499 |
| Severe NPDR | 0.400 | 0.193 | 0.256 |
| Proliferative DR | 0.246 | 0.438 | 0.326 |

> **Screening use case:** 97.5% sensitivity means only 2.5% of referable DR cases are missed — strong for a triage/screening tool. The lower overall accuracy reflects the ICDR class boundary ambiguity, not screening failure.

## Lesion Segmentation (U-Net)

**Model:** U-Net with ResNet18 ImageNet encoder, decoder (128→8), 4 output channels
**Data:** IDRiD (54 images) + DDR (383 images) = 437 training images with pixel-level lesion masks
**Loss:** 2×Dice(multilabel) + 0.5×BCE(pos_weight [31,10,11,23]) · **Test dice:** **0.314** (225 unseen DDR test images)

### Per-Class Test Dice (DDR Test Set)

| Lesion Type | Dice |
|---|---|
| Microaneurysms (MA) | 0.116 |
| Haemorrhages (HE) | 0.178 |
| Hard Exudates (EX) | 0.196 |
| Cotton Wool Spots (CWS) | **0.769** |

> DDR dataset increased training data from 54 to 437 images (8× increase). Cotton Wool Spot detection is particularly strong. Microaneurysms remain challenging due to their tiny size (5–10 pixels).

## Latency (ONNX Runtime, CPU — Intel-class laptop CPU, RTX 4050 GPU available but not required)

| Component | FP32 | INT8 (dynamic) |
|---|---|---|
| Classifier (512² input) | **77 ms** | 498 ms |
| Segmenter (512² input) | **150 ms** | 1,949 ms |
| **End-to-end API call** (IQA + preprocess + both models + overlays + FHIR) | **≈ 0.59 s** | — |
| P95 latency | **0.71 s** | — |
| Grad-CAM `/api/explain` (PyTorch .pth, CPU, lazy-loaded) | **≈ 0.35 s** | — |

INT8 dynamic quantization reduces model size ~4× but is slower on this CPU — the server auto-prefers FP32.
Grad-CAM runs as a separate async request after the main result, so screening latency is unaffected.

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

- Rare stages (Mild/Severe/Proliferative) have weaker F1 due to class imbalance (~3–20% prevalence)
- Mild NPDR F1 is 0.00 on external validation — class boundary overlap with No DR
- Segmenter microaneurysm detection is limited (Dice 0.116) due to tiny lesion size
- Single-fundus (not bilateral) analysis; no OCT/clinical metadata fusion
- Decision-support prototype — not a certified medical device
