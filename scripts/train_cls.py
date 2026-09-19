#!/usr/bin/env python
"""Train ConvNeXt-Tiny classifier with proper GPU support."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, Subset
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from tqdm import tqdm
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from src.data.dataset import (
    EVAL_TRANSFORM, TRAIN_TRANSFORM, IDRiDDataset, APTOSDataset,
    CombinedDataset, NUM_CLASSES,
)
from src.models.classifier import DRClassifierConvNeXt
from src.constants import CLASS_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SEED = 42
NUM_WORKERS = 4


def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0, label_smoothing=0.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.label_smoothing = label_smoothing

    def forward(self, logits, targets):
        num_classes = logits.size(-1)
        if self.label_smoothing > 0:
            with torch.no_grad():
                smooth = torch.full_like(logits, self.label_smoothing / (num_classes - 1))
                smooth.scatter_(1, targets.unsqueeze(1), 1.0 - self.label_smoothing)
            log_probs = F.log_softmax(logits, dim=-1)
            loss = -(smooth * log_probs).sum(dim=-1)
            pt = torch.exp(-loss)
            focal = (1 - pt) ** self.gamma * loss
        else:
            ce = F.cross_entropy(logits, targets, weight=self.alpha, reduction="none")
            pt = torch.exp(-ce)
            focal = (1 - pt) ** self.gamma * ce
        return focal.mean()


def mixup_data(x, y, alpha=0.2):
    if alpha > 0:
        lam = np.random.beta(alpha, alpha)
    else:
        lam = 1.0
    batch_size = x.size(0)
    index = torch.randperm(batch_size, device=x.device)
    mixed_x = lam * x + (1 - lam) * x[index]
    return mixed_x, y, y[index], lam


def mixup_criterion(criterion, pred, y_a, y_b, lam):
    return lam * criterion(pred, y_a) + (1 - lam) * criterion(pred, y_b)


def compute_class_weights(labels, severity_boost=3.0):
    counts = np.bincount(labels, minlength=NUM_CLASSES).astype(np.float64)
    weights = len(labels) / (NUM_CLASSES * np.maximum(counts, 1))
    weights = weights / weights.mean()
    boost = np.ones(NUM_CLASSES, dtype=np.float64)
    boost[3] = severity_boost
    boost[4] = severity_boost
    weights = weights * boost
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32)


def evaluate_classifier(model, loader, device):
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for imgs, labels, _ in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            outputs = model(imgs)
            preds = outputs.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_targets.extend(labels.cpu().numpy())
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    acc = (all_preds == all_targets).mean()
    return acc, all_preds, all_targets


def main():
    set_seed()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    if device.type == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

    # Hyperparameters — V3 config that got 81.7% on APTOS
    EPOCHS = 80
    BATCH_SIZE = 16
    LR = 1e-4
    WEIGHT_DECAY = 5e-4
    PATIENCE = 25
    MIXUP_PROB = 0.3
    MIXUP_ALPHA = 0.2
    LABEL_SMOOTHING = 0.15
    SEVERITY_BOOST = 4.0

    cache_root = PROJECT_ROOT / "data" / "processed"

    # Load IDRiD + APTOS
    idrid_ds = IDRiDDataset(task="classification", transform=TRAIN_TRANSFORM, split="train", cache_root=cache_root)
    aptos_ds = APTOSDataset(transform=TRAIN_TRANSFORM, cache_root=cache_root)
    print(f"IDRiD: {len(idrid_ds)} | APTOS: {len(aptos_ds)} | Total: {len(idrid_ds) + len(aptos_ds)}")

    all_labels = np.array(
        [s["label"] for s in idrid_ds.samples] + [s["label"] for s in aptos_ds.samples]
    )
    all_indices = np.arange(len(all_labels))

    # Stratified split: 80% train, 20% val
    train_idx, val_idx = train_test_split(all_indices, test_size=0.2, stratify=all_labels, random_state=SEED)

    combined = CombinedDataset([idrid_ds, aptos_ds])
    train_subset = Subset(combined, train_idx.tolist())
    val_subset = Subset(combined, val_idx.tolist())

    class_weights = compute_class_weights(all_labels[train_idx], severity_boost=SEVERITY_BOOST)
    print(f"Train: {len(train_subset)} | Val: {len(val_subset)}")
    print(f"Class weights: {class_weights.numpy().round(3)}")

    # Print class distribution
    train_labels = all_labels[train_idx]
    val_labels = all_labels[val_idx]
    for c in range(NUM_CLASSES):
        print(f"  Class {c}: train={np.sum(train_labels == c)}, val={np.sum(val_labels == c)}")

    train_loader = DataLoader(train_subset, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=NUM_WORKERS, pin_memory=True, drop_last=True)
    val_loader = DataLoader(val_subset, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=NUM_WORKERS, pin_memory=True)

    # Model
    model = DRClassifierConvNeXt(num_classes=NUM_CLASSES, pretrained=True).to(device)
    params = sum(p.numel() for p in model.parameters()) / 1e6
    print(f"ConvNeXt-Tiny: {params:.1f}M params")

    # Training setup
    criterion = FocalLoss(alpha=class_weights.to(device), gamma=2.0, label_smoothing=LABEL_SMOOTHING)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    scheduler = torch.optim.lr_scheduler.OneCycleLR(
        optimizer, max_lr=LR * 5, epochs=EPOCHS,
        steps_per_epoch=len(train_loader), pct_start=0.3
    )
    scaler = torch.amp.GradScaler("cuda")

    out_dir = PROJECT_ROOT / "models" / "classification"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0
    patience_counter = 0
    ckpt_path = out_dir / "best_classifier.pth"
    # Keep top 3 checkpoints for ensemble
    top_checkpoints = []  # (acc, epoch, path)

    print(f"\nStarting training: {EPOCHS} epochs, batch_size={BATCH_SIZE}, lr={LR}")
    print(f"Mixup prob={MIXUP_PROB}, label_smoothing={LABEL_SMOOTHING}, severity_boost={SEVERITY_BOOST}")
    print(f"Early stopping patience={PATIENCE}")
    print("=" * 60)

    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{EPOCHS}")

        for imgs, labels, _ in pbar:
            imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)

            use_mixup = np.random.random() < MIXUP_PROB
            if use_mixup:
                imgs, y_a, y_b, lam = mixup_data(imgs, labels, alpha=MIXUP_ALPHA)

            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda"):
                outputs = model(imgs)
                if use_mixup:
                    loss = mixup_criterion(criterion, outputs, y_a, y_b, lam)
                else:
                    loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            running_loss += loss.item()
            pbar.set_postfix(loss=f"{loss.item():.4f}")

        # Validate
        acc, preds, targets = evaluate_classifier(model, val_loader, device)
        avg_loss = running_loss / max(len(train_loader), 1)
        print(f"Epoch {epoch + 1}: loss={avg_loss:.4f} val_acc={acc:.4f} ({acc*100:.1f}%)")

        if acc > best_acc:
            best_acc = acc
            patience_counter = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_acc": acc,
                "epoch": epoch + 1,
                "backbone": "convnext_tiny",
                "class_weights": class_weights.numpy().tolist(),
                "hyperparams": {
                    "lr": LR, "batch_size": BATCH_SIZE, "epochs": EPOCHS,
                    "mixup_prob": MIXUP_PROB, "label_smoothing": LABEL_SMOOTHING,
                    "severity_boost": SEVERITY_BOOST, "weight_decay": WEIGHT_DECAY,
                }
            }, ckpt_path)
            print(f"  >> New best: {acc:.4f} ({acc*100:.1f}%) saved to {ckpt_path}")

            # Save top-3 checkpoints for ensemble
            top_ckpt_path = out_dir / f"top3_epoch{epoch+1}_acc{acc:.4f}.pth"
            torch.save({
                "model_state_dict": model.state_dict(),
                "val_acc": acc,
                "epoch": epoch + 1,
                "backbone": "convnext_tiny",
            }, top_ckpt_path)
            top_checkpoints.append((acc, epoch + 1, str(top_ckpt_path)))
            top_checkpoints.sort(reverse=True)
            if len(top_checkpoints) > 3:
                # Remove worst checkpoint file
                worst_acc, worst_epoch, worst_path = top_checkpoints.pop()
                Path(worst_path).unlink(missing_ok=True)

            # Print per-class performance
            from sklearn.metrics import precision_recall_fscore_support
            p, r, f1, _ = precision_recall_fscore_support(targets, preds, average=None, labels=range(NUM_CLASSES))
            for c in range(NUM_CLASSES):
                print(f"     Class {c} ({CLASS_NAMES[c]}): P={p[c]:.3f} R={r[c]:.3f} F1={f1[c]:.3f}")
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                print(f"Early stopping at epoch {epoch + 1}")
                break

    print(f"\n{'=' * 60}")
    print(f"Best validation accuracy: {best_acc:.4f} ({best_acc*100:.1f}%)")

    # Final evaluation with best model
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    acc, preds, targets = evaluate_classifier(model, val_loader, device)
    print(f"Final val accuracy (best checkpoint): {acc:.4f}")

    # Save report
    report = classification_report(targets, preds, target_names=CLASS_NAMES, digits=4)
    (out_dir / "classification_report.txt").write_text(report)
    print(report)

    # Confusion matrix
    cm = confusion_matrix(targets, preds)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.ylabel("True"), plt.xlabel("Predicted"), plt.title("Confusion Matrix (ConvNeXt-Tiny)")
    plt.tight_layout()
    plt.savefig(out_dir / "confusion_matrix.png", dpi=120)
    plt.close()

    # Save summary
    summary = {
        "best_val_accuracy": float(best_acc),
        "epochs_completed": epoch + 1,
        "backbone": "convnext_tiny",
        "params_M": round(params, 1),
        "dataset": "IDRiD + APTOS (4075 images)",
        "hyperparams": {
            "lr": LR, "batch_size": BATCH_SIZE, "epochs": EPOCHS,
            "mixup_prob": MIXUP_PROB, "label_smoothing": LABEL_SMOOTHING,
            "severity_boost": SEVERITY_BOOST, "weight_decay": WEIGHT_DECAY,
        }
    }
    (out_dir / "training_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nDone. All artifacts saved to {out_dir}")


if __name__ == "__main__":
    main()
