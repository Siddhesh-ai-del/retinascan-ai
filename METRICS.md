# RetinaScan AI — Evaluation Metrics & Benchmark Results

> SIH 2026 · Problem Statement SIH26038 · AI-Based Diabetic Retinopathy Screening & Classification

## Classification (ICDR 5-stage)

**Model:** EfficientNet-B2, ImageNet-pretrained backbone, custom head (dropout 0.3 → 256 → 5)
**Data:** IDRiD disease grading (413 train + 103 test) + APTOS 2019 (3,662) = 4,178 images
**Loss:** Focal loss (γ=2.0) with inverse-frequency class weights · **Opt:** AdamW 1e-4, cosine annealing, AMP
**Validation:** stratified 80/20 split

| Metric | Value |
|---|---|
| **Best validation accuracy** | **76.7%** |
| No DR — precision / recall / F1 | 0.984 / 0.961 / **0.973** |
| Mild NPDR F1 | 0.541 |
| Moderate NPDR F1 | 0.673 |
| Severe NPDR F1 | 0.429 |
| Proliferative DR F1 | 0.425 |
| Macro F1 | 0.608 |
| Weighted F1 | 0.766 |

Full per-class report: `models/classification/classification_report.txt` · confusion matrix: `confusion_matrix.png`

## Lesion Segmentation (U-Net)

**Model:** U-Net with ResNet18 ImageNet encoder, decoder (128→8), 4 output channels
**Data:** IDRiD pixel-level lesion annotations — Microaneurysms, Haemorrhages, Hard Exudates, Soft Exudates
**Loss:** 2×Dice(multilabel) + 0.5×BCE(pos_weight [31,10,11,23]) · **Val dice:** **0.2066** (100 epochs)

> Honest note: only 81 annotated images exist in IDRiD's segmentation subset; dice is computed at threshold 0.5 on an 80/20 split. Exudates and hemorrhages localize reliably; microaneurysms and cotton-wool spots remain sparse. Visualization runs at threshold 0.40 for overlay recall.

## Latency (ONNX Runtime, CPU — Intel-class laptop CPU, RTX 4050 GPU available but not required)

| Component | FP32 | INT8 (dynamic) |
|---|---|---|
| Classifier (512² input) | **77 ms** | 498 ms |
| Segmenter (512² input) | **157 ms** | 2,037 ms |
| **End-to-end API call** (IQA + preprocess + both models + overlays + FHIR) | **≈ 0.39 s** | — |

INT8 dynamic quantization reduces model size ~4× but is slower on this CPU — the server auto-prefers FP32.

## IQA Validation Gauntlet

| Test set | Result |
|---|---|
| 5 bundled demo fundus images | 5/5 gradable (fundus score 0.88–0.96) |
| Synthetic selfie-like photo | rejected (fundus 0.30) |
| Flat bright frame | rejected (0.00) |
| Text screenshot | rejected (0.19) |
| Random raw APTOS/IDRiD sample (n=20) | 19/20 pass (single reject genuinely dark) |

## Demo-set Screening Accuracy (bundled `demo_images/`, one per ICDR stage)

| Ground truth | Predicted | Confidence |
|---|---|---|
| Stage 0 — No DR | ✅ Stage 0 | 91% |
| Stage 1 — Mild NPDR | ✅ Stage 1 | 69% |
| Stage 2 — Moderate NPDR | ✅ Stage 2 | 85% |
| Stage 3 — Severe NPDR | ✅ Stage 3 | 94% |
| Stage 4 — Proliferative DR | ✅ Stage 4 | 87% |

## Known Limitations

- Rare stages (Mild/Severe/Proliferative) have weaker F1 due to class imbalance (~3–20% prevalence)
- Segmenter trained on a small annotated subset; MA/CWS masks under-represented
- Single-fundus (not bilateral) analysis; no OCT/clinical metadata fusion
- Decision-support prototype — not a certified medical device
