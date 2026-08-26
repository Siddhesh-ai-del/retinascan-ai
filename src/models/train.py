import argparse
import json
import random
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Subset
from tqdm import tqdm

import segmentation_models_pytorch as smp

from src.data.dataset import (
    EVAL_TRANSFORM,
    TRAIN_TRANSFORM,
    CombinedDataset,
    IDRiDDataset,
    NUM_CLASSES,
    build_combined_dataset,
)
from src.constants import CLASS_NAMES
from src.models.classifier import DRClassifier
from src.models.segmenter import LesionSegmenter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SEED = 42


def set_seed(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, logits, targets):
        ce = F.cross_entropy(logits, targets, weight=self.alpha, reduction="none")
        pt = torch.exp(-ce)
        focal = (1 - pt) ** self.gamma * ce
        return focal.mean()


def compute_class_weights(labels):
    counts = np.bincount(labels, minlength=NUM_CLASSES).astype(np.float64)
    weights = len(labels) / (NUM_CLASSES * np.maximum(counts, 1))
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32)


def make_loaders(args):
    cache_root = PROJECT_ROOT / "data" / "processed"

    if args.mode == "classification":
        train_ds = build_combined_dataset(transform=TRAIN_TRANSFORM, cache_root=cache_root)
        val_ds = build_combined_dataset(transform=EVAL_TRANSFORM, cache_root=cache_root)
        labels = train_ds.labels
        train_idx, val_idx = train_test_split(
            np.arange(len(train_ds)), test_size=0.2, stratify=labels, random_state=SEED
        )
        train_subset, val_subset = Subset(train_ds, train_idx.tolist()), Subset(val_ds, val_idx.tolist())
        class_weights = compute_class_weights(labels[train_idx])
        print(f"Train: {len(train_subset)} | Val: {len(val_subset)} | Class weights: {class_weights.numpy().round(3)}")
        return (
            DataLoader(train_subset, batch_size=args.batch_size, shuffle=True, num_workers=4, pin_memory=True, drop_last=True),
            DataLoader(val_subset, batch_size=args.batch_size, shuffle=False, num_workers=4, pin_memory=True),
            class_weights,
            None,
        )

    idrid_train = IDRiDDataset(task="segmentation", transform=TRAIN_TRANSFORM, split="train", cache_root=cache_root)
    idrid_test = IDRiDDataset(task="segmentation", transform=TRAIN_TRANSFORM, split="test", cache_root=cache_root)
    idrid_val = IDRiDDataset(task="segmentation", transform=EVAL_TRANSFORM, split="train", cache_root=cache_root)
    idrid_val_test = IDRiDDataset(task="segmentation", transform=EVAL_TRANSFORM, split="test", cache_root=cache_root)

    pool_train = torch.utils.data.ConcatDataset([idrid_train, idrid_test])
    pool_val = torch.utils.data.ConcatDataset([idrid_val, idrid_val_test])
    idx = np.arange(len(pool_train))
    train_idx, val_idx = train_test_split(idx, test_size=0.2, random_state=SEED)
    train_subset = Subset(pool_train, train_idx.tolist())
    val_subset = Subset(pool_val, val_idx.tolist())
    print(f"Seg Train: {len(train_subset)} | Seg Val: {len(val_subset)}")
    return (
        DataLoader(train_subset, batch_size=args.batch_size, shuffle=True, num_workers=4, pin_memory=True, drop_last=True),
        DataLoader(val_subset, batch_size=args.batch_size, shuffle=False, num_workers=4, pin_memory=True),
        None,
        None,
    )


@torch.no_grad()
def evaluate_classifier(model, loader, device):
    model.eval()
    all_preds, all_targets = [], []
    for imgs, labels, _ in loader:
        imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        with torch.autocast("cuda"):
            outputs = model(imgs)
        all_preds.extend(outputs.argmax(1).cpu().numpy())
        all_targets.extend(labels.cpu().numpy())
    acc = float(np.mean(np.array(all_preds) == np.array(all_targets)))
    return acc, np.array(all_preds), np.array(all_targets)


@torch.no_grad()
def evaluate_segmenter(model, loader, device):
    model.eval()
    eps = 1e-7
    dices = []
    for imgs, _, masks in tqdm(loader, desc="Validating", leave=False):
        imgs = imgs.to(device, non_blocking=True)
        with torch.autocast("cuda"):
            outputs = model(imgs)
        probs = (torch.sigmoid(outputs.float()) > 0.5).cpu().numpy()
        gts = masks.numpy()
        for b in range(probs.shape[0]):
            batch_dices = []
            for c in range(probs.shape[1]):
                pred, gt = probs[b, c].astype(bool), gts[b, c].astype(bool)
                inter = np.logical_and(pred, gt).sum()
                denom = pred.sum() + gt.sum()
                batch_dices.append(1.0 if denom == 0 else 2 * inter / (denom + eps))
            dices.append(batch_dices)
    dices = np.array(dices)
    per_class = dices.mean(axis=0)
    return float(per_class[per_class > 0.01].mean()) if (per_class > 0.01).any() else float(per_class.mean()), per_class


def train_classification(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, class_weights, _ = make_loaders(args)

    model = DRClassifier(num_classes=NUM_CLASSES, pretrained=True).to(device)
    criterion = FocalLoss(alpha=class_weights.to(device), gamma=2.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda")

    out_dir = PROJECT_ROOT / "models" / "classification"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_acc = 0.0
    ckpt_path = out_dir / "best_classifier.pth"

    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        pbar = tqdm(train_loader, desc=f"[Cls] Epoch {epoch + 1}/{args.epochs}")
        for imgs, labels, _ in pbar:
            imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda"):
                outputs = model(imgs)
                loss = criterion(outputs, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_loss += loss.item()
            pbar.set_postfix(loss=f"{loss.item():.4f}")
        scheduler.step()

        acc, preds, targets = evaluate_classifier(model, val_loader, device)
        print(f"Epoch {epoch + 1}: train_loss={running_loss / max(len(train_loader), 1):.4f} val_acc={acc:.4f}")
        if acc > best_acc:
            best_acc = acc
            torch.save(
                {"model_state_dict": model.state_dict(), "val_acc": acc, "epoch": epoch + 1},
                ckpt_path,
            )
            print(f"  Saved new best ({ckpt_path.name}, acc={acc:.4f})")

    report = classification_report(targets, preds, target_names=CLASS_NAMES, digits=4)
    (out_dir / "classification_report.txt").write_text(report)
    cm = confusion_matrix(targets, preds)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.ylabel("True"), plt.xlabel("Predicted"), plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig(out_dir / "confusion_matrix.png", dpi=120)
    plt.close()

    (out_dir / "training_summary.json").write_text(
        json.dumps({"best_val_accuracy": best_acc, "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr}, indent=2)
    )
    print(f"DONE. Best val accuracy: {best_acc:.4f}. Artifacts in {out_dir}")


def train_segmentation(args):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader, val_loader, _, _ = make_loaders(args)

    model = LesionSegmenter(num_classes=4, pretrained=True).to(device)
    dice_loss = smp.losses.DiceLoss(mode="multilabel", from_logits=True)
    pos_weight = torch.tensor([31.0, 10.0, 11.0, 23.0], device=device).view(1, 4, 1, 1)
    bce_loss = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.amp.GradScaler("cuda")

    out_dir = PROJECT_ROOT / "models" / "segmentation"
    out_dir.mkdir(parents=True, exist_ok=True)
    best_dice = 0.0
    ckpt_path = out_dir / "best_segmenter.pth"

    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        pbar = tqdm(train_loader, desc=f"[Seg] Epoch {epoch + 1}/{args.epochs}")
        for imgs, _, masks in pbar:
            imgs, masks = imgs.to(device, non_blocking=True), masks.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cuda"):
                outputs = model(imgs)
                loss = 2.0 * dice_loss(outputs, masks) + 0.5 * bce_loss(outputs, masks)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_loss += loss.item()
            pbar.set_postfix(loss=f"{loss.item():.4f}")
        scheduler.step()

        mean_dice, per_class = evaluate_segmenter(model, val_loader, device)
        print(
            f"Epoch {epoch + 1}: train_loss={running_loss / max(len(train_loader), 1):.4f} "
            f"val_dice={mean_dice:.4f} | MA={per_class[0]:.3f} HE={per_class[1]:.3f} EX={per_class[2]:.3f} CWS={per_class[3]:.3f}"
        )
        if mean_dice > best_dice:
            best_dice = mean_dice
            torch.save({"model_state_dict": model.state_dict(), "val_dice": mean_dice, "epoch": epoch + 1}, ckpt_path)
            print(f"  Saved new best ({ckpt_path.name}, dice={mean_dice:.4f})")

    (out_dir / "training_summary.json").write_text(
        json.dumps({"best_val_dice": best_dice, "epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr}, indent=2)
    )
    print(f"DONE. Best val dice: {best_dice:.4f}. Artifacts in {out_dir}")


def main():
    parser = argparse.ArgumentParser(description="Train DR classifier and/or lesion segmenter")
    parser.add_argument("--mode", choices=["classification", "segmentation"], required=True)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    args = parser.parse_args()

    if args.mode == "classification":
        args.epochs = args.epochs or 30
        args.batch_size = args.batch_size or 16
        args.lr = args.lr or 1e-4
        set_seed()
        train_classification(args)
    else:
        args.epochs = args.epochs or 50
        args.batch_size = args.batch_size or 8
        args.lr = args.lr or 1e-4
        set_seed()
        train_segmentation(args)


if __name__ == "__main__":
    main()
