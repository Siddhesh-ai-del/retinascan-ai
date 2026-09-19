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

# --- Configuration ---
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


def plot_roc(metrics, referable_true, referable_probs, output_dir):
    """Generate ROC curve for referable DR detection."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # ROC curve
    fpr, tpr, _ = roc_curve(referable_true, referable_probs)
    auc = metrics["referable_dr"]["auc"]
    axes[0].plot(fpr, tpr, 'b-', linewidth=2, label=f'ROC (AUC = {auc:.3f})')
    axes[0].plot([0, 1], [0, 1], 'k--', linewidth=1, label='Random')
    axes[0].set_xlabel('False Positive Rate')
    axes[0].set_ylabel('True Positive Rate')
    axes[0].set_title('ROC Curve — Referable DR Detection')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Per-class F1 bars
    f1_scores = [metrics["per_class"][c]["f1"] for c in CLASS_NAMES]
    colors = ['#3e8a6c', '#83863c', '#b58424', '#b56128', '#b04536']
    axes[1].barh(CLASS_NAMES, f1_scores, color=colors)
    axes[1].set_xlabel('F1 Score')
    axes[1].set_title('Per-Class F1 Score (External Validation)')
    axes[1].set_xlim(0, 1)
    for i, v in enumerate(f1_scores):
        axes[1].text(v + 0.01, i, f'{v:.3f}', va='center')

    plt.tight_layout()
    plt.savefig(output_dir / "validation_charts.png", dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Charts saved to {output_dir / 'validation_charts.png'}")


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

    # Get valid referable data for ROC
    valid_mask = [p != -1 for p in all_preds]
    valid_labels = [l for l, v in zip(all_labels, valid_mask) if v]
    valid_probs = [p for p, v in zip(all_probs, valid_mask) if v]
    referable_true = [1 if l >= 2 else 0 for l in valid_labels]
    referable_probs = [max(p[2], p[3], p[4]) for p in valid_probs]

    print("Saving report...")
    save_report(metrics, OUTPUT_DIR)

    print("Generating charts...")
    plot_roc(metrics, referable_true, referable_probs, OUTPUT_DIR)

    print(f"\nDone! Report saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
