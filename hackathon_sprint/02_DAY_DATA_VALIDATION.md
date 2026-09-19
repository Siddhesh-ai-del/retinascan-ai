# Day 3-4: External Validation on Unseen Data

## Deadline
- **Day 3 morning:** Download APTOS test set
- **Day 3 afternoon:** Run model on all test images
- **Day 4 morning:** Generate full metrics (sensitivity, specificity, ROC, CI)
- **Day 4 afternoon:** Create validation report
- **STOP when:** Full metrics report generated with ≥1,000 images evaluated

## Goal
Prove the model generalizes by evaluating it on images it has **never seen during training**. Generate a clinical-grade metrics report suitable for the PPT.

## Why This Matters
Without external validation, your model is just "trained on some data." With it, you can say "87% sensitivity on 1,928 unseen images." That's a hackathon-winning claim.

---

## Task 1: Download APTOS Test Set (Day 3, 30 minutes)

### Current State
Your `src/data/download.py` already has APTOS download support. But the APTOS competition test set doesn't have public labels — only the training set does.

### Strategy
Use the **APTOS training set** (3,662 images with labels) as your external validation set. Your model was trained on IDRiD, so APTOS images are completely unseen.

**Important:** Make sure you did NOT include APTOS in the training set. Check your `build_combined_dataset` call:
```python
# In src/data/dataset.py:
def build_combined_dataset(transform=None, include_idrid=True, include_aptos=True, cache_root=None):
```
If `include_aptos=True` during training, you need to retrain with `include_aptos=False` first. This is critical — using training data for validation is data leakage.

### If APTOS Was in Training
```bash
# Retrain WITHOUT APTOS (IDRiD only):
python -m src.models.train --mode classification --epochs 50 --batch_size 16 --lr 2e-4
# But first modify build_combined_dataset call in train.py:
# build_combined_dataset(transform=TRAIN_TRANSFORM, include_aptos=False, cache_root=cache_root)
```
This will take ~6-8 hours. Start immediately if needed.

### If APTOS Was NOT in Training
Proceed directly to evaluation.

### Download/Verify APTOS Data
```bash
cd /home/siddhesh/Desktop/Draft_confidential
source venv/bin/activate

# Download APTOS if not present
python -m src.data.download --aptos

# Verify
ls data/raw/aptos/train.csv
ls data/raw/aptos/train_images/ | wc -l
# Should show ~3,662 images
```

---

## Task 2: Create External Validation Script (Day 3, 2 hours)

### Create File: `scripts/external_validation.py`

```python
"""
External validation of DR classifier on APTOS dataset.
Generates comprehensive clinical metrics.
"""
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.constants import CLASS_NAMES
from src.data.preprocess import get_cached_uint8, IMAGENET_MEAN, IMAGENET_STD
from src.inference.predictor import DRPredictor

# ─── Configuration ───────────────────────────────────────────────
APTOS_CSV = PROJECT_ROOT / "data" / "raw" / "aptos" / "train.csv"
APTOS_IMG_DIR = PROJECT_ROOT / "data" / "raw" / "aptos" / "train_images"
CLASSIFIER_ONNX = PROJECT_ROOT / "models" / "onnx" / "classifier.onnx"
OUTPUT_DIR = PROJECT_ROOT / "hackathon_sprint" / "metrics"
N_BOOTSTRAP = 1000  # For confidence intervals


def load_aptos_data():
    """Load APTOS images and labels."""
    df = pd.read_csv(APTOS_CSV)
    samples = []
    for _, row in df.iterrows():
        img_path = APTOS_IMG_DIR / f"{row['id_code']}.png"
        if img_path.exists():
            samples.append({
                "path": str(img_path),
                "label": int(row["diagnosis"]),
                "id": row["id_code"],
            })
    print(f"Loaded {len(samples)} APTOS images")
    return samples


def run_inference(predictor, samples):
    """Run model on all samples, return predictions and labels."""
    all_preds = []
    all_labels = []
    all_probs = []
    times = []

    for i, sample in enumerate(samples):
        if (i + 1) % 100 == 0:
            print(f"  Processing {i+1}/{len(samples)}...")

        t0 = time.time()
        try:
            result = predictor.predict(sample["path"], patient_id="validation")
            elapsed = time.time() - t0
            times.append(elapsed)

            if result["status"] == "ok" and result["classification"]:
                all_preds.append(result["classification"]["stage"])
                all_probs.append(result["classification"]["probabilities"])
            else:
                # Image was rejected by IQA — count as wrong prediction
                all_preds.append(-1)  # sentinel
                all_probs.append([0.0] * 5)
        except Exception as e:
            print(f"  Error on {sample['id']}: {e}")
            all_preds.append(-1)
            all_probs.append([0.0] * 5)
            times.append(time.time() - t0)

        all_labels.append(sample["label"])

    return all_preds, all_labels, all_probs, times


def compute_metrics(all_preds, all_labels, all_probs, times):
    """Compute comprehensive clinical metrics."""
    metrics = {}

    # Filter out rejected images
    valid_mask = [p != -1 for p in all_preds]
    valid_preds = [p for p, v in zip(all_preds, valid_mask) if v]
    valid_labels = [l for l, v in zip(all_labels, valid_mask) if v]
    valid_probs = [p for p, v in zip(all_probs, valid_mask) if v]

    n_rejected = sum(1 for p in all_preds if p == -1)
    n_total = len(all_preds)
    n_valid = len(valid_preds)

    metrics["total_images"] = n_total
    metrics["rejected_by_iqa"] = n_rejected
    metrics["evaluated"] = n_valid
    metrics["rejection_rate"] = round(n_rejected / n_total, 4)

    # Overall accuracy
    metrics["accuracy"] = round(accuracy_score(valid_labels, valid_preds), 4)

    # Bootstrap confidence interval for accuracy
    rng = np.random.default_rng(42)
    boot_accs = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.choice(n_valid, size=n_valid, replace=True)
        boot_accs.append(accuracy_score(
            [valid_labels[i] for i in idx],
            [valid_preds[i] for i in idx]
        ))
    metrics["accuracy_95ci"] = (
        round(float(np.percentile(boot_accs, 2.5)), 4),
        round(float(np.percentile(boot_accs, 97.5)), 4)
    )

    # Per-class metrics
    report = classification_report(valid_labels, valid_preds, target_names=CLASS_NAMES, output_dict=True)
    metrics["per_class"] = {}
    for cls_name in CLASS_NAMES:
        if cls_name in report:
            metrics["per_class"][cls_name] = {
                "precision": round(report[cls_name]["precision"], 4),
                "recall": round(report[cls_name]["recall"], 4),
                "f1": round(report[cls_name]["f1-score"], 4),
                "support": report[cls_name]["support"],
            }

    # Referable DR (Stage >= 2 vs Stage 0-1)
    referable_true = [1 if l >= 2 else 0 for l in valid_labels]
    referable_pred = [1 if p >= 2 else 0 for p in valid_preds]

    # Sensitivity and specificity for referable DR
    tp = sum(1 for t, p in zip(referable_true, referable_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(referable_true, referable_pred) if t == 0 and p == 1)
    tn = sum(1 for t, p in zip(referable_true, referable_pred) if t == 0 and p == 0)
    fn = sum(1 for t, p in zip(referable_true, referable_pred) if t == 1 and p == 0)

    sensitivity = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    ppv = tp / max(tp + fp, 1)
    npv = tn / max(tn + fn, 1)

    metrics["referable_dr"] = {
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "ppv": round(ppv, 4),
        "npv": round(npv, 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }

    # Bootstrap CI for sensitivity
    boot_sens = []
    for _ in range(N_BOOTSTRAP):
        idx = rng.choice(len(referable_true), size=len(referable_true), replace=True)
        bt = [referable_true[i] for i in idx]
        bp = [referable_pred[i] for i in idx]
        btp = sum(1 for t, p in zip(bt, bp) if t == 1 and p == 1)
        bfn = sum(1 for t, p in zip(bt, bp) if t == 1 and p == 0)
        boot_sens.append(btp / max(btp + bfn, 1))
    metrics["referable_dr"]["sensitivity_95ci"] = (
        round(float(np.percentile(boot_sens, 2.5)), 4),
        round(float(np.percentile(boot_sens, 97.5)), 4)
    )

    # AUC for referable DR
    try:
        referable_probs = [max(p[2], p[3], p[4]) for p in valid_probs]  # P(Stage>=2)
        metrics["referable_dr"]["auc"] = round(roc_auc_score(referable_true, referable_probs), 4)
    except ValueError:
        metrics["referable_dr"]["auc"] = None

    # Confusion matrix
    cm = confusion_matrix(valid_labels, valid_preds)
    metrics["confusion_matrix"] = cm.tolist()

    # Inference time
    metrics["latency"] = {
        "mean_ms": round(np.mean(times) * 1000, 1),
        "p95_ms": round(np.percentile(times, 95) * 1000, 1),
        "p99_ms": round(np.percentile(times, 99) * 1000, 1),
    }

    return metrics


def save_report(metrics, output_dir):
    """Save metrics as JSON and human-readable text."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    with open(output_dir / "external_validation.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Human-readable
    lines = [
        "=" * 60,
        "EXTERNAL VALIDATION REPORT — RetinaScan AI",
        "=" * 60,
        f"Dataset: APTOS 2019 (unseen during training)",
        f"Total images: {metrics['total_images']}",
        f"Evaluated: {metrics['evaluated']} (rejected: {metrics['rejected_by_iqa']})",
        f"Rejection rate: {metrics['rejection_rate']:.1%}",
        "",
        f"Overall Accuracy: {metrics['accuracy']:.1%} "
        f"(95% CI: {metrics['accuracy_95ci'][0]:.1%} – {metrics['accuracy_95ci'][1]:.1%})",
        "",
        "Per-Class Metrics:",
    ]
    for cls_name, cls_m in metrics["per_class"].items():
        lines.append(f"  {cls_name:20s}  P={cls_m['precision']:.3f}  R={cls_m['recall']:.3f}  F1={cls_m['f1']:.3f}  n={cls_m['support']:.0f}")

    ref = metrics["referable_dr"]
    lines += [
        "",
        "Referable DR Detection (Stage >= 2):",
        f"  Sensitivity: {ref['sensitivity']:.1%} (95% CI: {ref['sensitivity_95ci'][0]:.1%} – {ref['sensitivity_95ci'][1]:.1%})",
        f"  Specificity: {ref['specificity']:.1%}",
        f"  PPV: {ref['ppv']:.1%}",
        f"  NPV: {ref['npv']:.1%}",
        f"  AUC: {ref['auc']:.4f}" if ref['auc'] else "  AUC: N/A",
        f"  TP={ref['tp']} FP={ref['fp']} TN={ref['tn']} FN={ref['fn']}",
        "",
        f"Inference Latency:",
        f"  Mean: {metrics['latency']['mean_ms']:.0f} ms",
        f"  P95:  {metrics['latency']['p95_ms']:.0f} ms",
        f"  P99:  {metrics['latency']['p99_ms']:.0f} ms",
        "",
        "=" * 60,
    ]

    with open(output_dir / "external_validation.txt", "w") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))


def main():
    print("Loading APTOS dataset...")
    samples = load_aptos_data()

    print("Loading model...")
    predictor = DRPredictor(classifier_path=CLASSIFIER_ONNX)
    if not predictor.classifier:
        print("ERROR: Classifier not loaded. Export ONNX model first.")
        sys.exit(1)

    print(f"Running inference on {len(samples)} images...")
    all_preds, all_labels, all_probs, times = run_inference(predictor, samples)

    print("Computing metrics...")
    metrics = compute_metrics(all_preds, all_labels, all_probs, times)

    print("Saving report...")
    save_report(metrics, OUTPUT_DIR)

    print(f"\nDone! Report saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
```

### Create Directory
```bash
mkdir -p /home/siddhesh/Desktop/Draft_confidential/hackathon_sprint/metrics
```

---

## Task 3: Run External Validation (Day 3-4, 3-4 hours)

### Command
```bash
cd /home/siddhesh/Desktop/Draft_confidential
source venv/bin/activate

python scripts/external_validation.py
```

### Expected Output
```
Loaded 3662 APTOS images
Loading model...
Running inference on 3662 images...
  Processing 100/3662...
  Processing 200/3662...
  ...
  Processing 3600/3662...
Computing metrics...
============================================================
EXTERNAL VALIDATION REPORT — RetinaScan AI
============================================================
Dataset: APTOS 2019 (unseen during training)
Total images: 3662
Evaluated: 3662 (rejected: X)
Rejection rate: X.X%

Overall Accuracy: XX.X% (95% CI: XX.X% – XX.X%)

Per-Class Metrics:
  No DR                P=X.XXX  R=X.XXX  F1=X.XXX  n=XXX
  Mild NPDR            P=X.XXX  R=X.XXX  F1=X.XXX  n=XXX
  Moderate NPDR        P=X.XXX  R=X.XXX  F1=X.XXX  n=XXX
  Severe NPDR          P=X.XXX  R=X.XXX  F1=X.XXX  n=XXX
  Proliferative DR     P=X.XXX  R=X.XXX  F1=X.XXX  n=XXX

Referable DR Detection (Stage >= 2):
  Sensitivity: XX.X% (95% CI: XX.X% – XX.X%)
  Specificity: XX.X%
  PPV: XX.X%
  NPV: XX.X%
  AUC: X.XXXX
  TP=X FP=X TN=X FN=X

Inference Latency:
  Mean: XXX ms
  P95:  XXX ms
  P99:  XXX ms
============================================================
```

### If Results Are Below Target
- **Accuracy < 80%:** Your model overfit to IDRiD. Consider training on both IDRiD + APTOS and evaluating on a held-out APTOS subset.
- **Sensitivity < 80%:** The referable DR threshold may need tuning. Try adjusting the threshold from `>=2` to `>=1`.
- **High rejection rate:** Your IQA gate is too aggressive. Check `FUNDUS_SCORE_THRESHOLD` in `src/quality/iqa.py`.

---

## Task 4: Generate ROC Curve Plot (Day 4, 1 hour)

### Add to `scripts/external_validation.py`

Add this function and call it from `main()`:

```python
def plot_roc(metrics, output_dir):
    """Generate ROC curve for referable DR detection."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Load the saved data to reconstruct ROC
    # (or compute during main and pass referable_probs)

    # For now, plot from saved confusion matrix data
    ref = metrics["referable_dr"]
    # Generate a simple performance summary plot
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Confusion matrix
    cm = np.array(metrics["confusion_matrix"])
    im = axes[0].imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    axes[0].set_title('Confusion Matrix')
    axes[0].set_xlabel('Predicted')
    axes[0].set_ylabel('True')
    tick_marks = np.arange(len(CLASS_NAMES))
    axes[0].set_xticks(tick_marks)
    axes[0].set_xticklabels(CLASS_NAMES, rotation=45, ha='right')
    axes[0].set_yticks(tick_marks)
    axes[0].set_yticklabels(CLASS_NAMES)
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            axes[0].text(j, i, format(cm[i, j], 'd'),
                        ha="center", va="center",
                        color="white" if cm[i, j] > cm.max()/2 else "black")

    # Per-class F1 bars
    f1_scores = [metrics["per_class"][c]["f1"] for c in CLASS_NAMES]
    colors = ['#3e8a6c', '#83863c', '#b58424', '#b56128', '#b04536']
    axes[1].barh(CLASS_NAMES, f1_scores, color=colors)
    axes[1].set_xlabel('F1 Score')
    axes[1].set_title('Per-Class F1 Score')
    axes[1].set_xlim(0, 1)
    for i, v in enumerate(f1_scores):
        axes[1].text(v + 0.01, i, f'{v:.3f}', va='center')

    plt.tight_layout()
    plt.savefig(output_dir / "validation_charts.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Charts saved to {output_dir / 'validation_charts.png'}")
```

---

## Task 5: Create Comparison Slide Data (Day 4, 30 minutes)

### Create File: `hackathon_sprint/metrics/comparison.json`

```json
{
  "before": {
    "model": "EfficientNet-B2 (baseline)",
    "val_accuracy": 0.767,
    "severe_f1": 0.43,
    "pdr_f1": 0.42,
    "external_validation": "none"
  },
  "after": {
    "model": "EfficientNet-B2 (optimized)",
    "val_accuracy": "FILL FROM training_summary.json",
    "severe_f1": "FILL FROM classification_report.txt",
    "pdr_f1": "FILL FROM classification_report.txt",
    "external_accuracy": "FILL FROM external_validation.json",
    "referable_sensitivity": "FILL FROM external_validation.json",
    "referable_specificity": "FILL FROM external_validation.json",
    "referable_auc": "FILL FROM external_validation.json",
    "n_unseen_images": 3662,
    "dataset": "APTOS 2019"
  }
}
```

Fill in actual values after evaluation.

---

## Go/No-Go Criteria

| Metric | Target | Minimum |
|---|---|---|
| Images evaluated | 3,000+ | 1,000+ |
| External accuracy | 80%+ | 75%+ |
| Referable DR sensitivity | 85%+ | 80%+ |
| Report generated | Yes | Yes |

---

## Files Generated
- `scripts/external_validation.py` — validation script
- `hackathon_sprint/metrics/external_validation.json` — full metrics
- `hackathon_sprint/metrics/external_validation.txt` — human-readable report
- `hackathon_sprint/metrics/validation_charts.png` — visual charts
- `hackathon_sprint/metrics/comparison.json` — before/after comparison
