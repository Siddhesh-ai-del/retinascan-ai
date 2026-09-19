#!/usr/bin/env python
"""Evaluate classifier with Test-Time Augmentation (TTA) on APTOS validation set."""
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import albumentations as A
from albumentations.pytorch import ToTensorV2
from pathlib import Path
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, Dataset
import cv2

from src.models.classifier import DRClassifierConvNeXt
from src.data.preprocess import IMAGENET_MEAN, IMAGENET_STD, get_cached_uint8
from src.constants import CLASS_NAMES
from src.data.dataset import APTOSDataset, EVAL_TRANSFORM
from torch.utils.data import Subset
from sklearn.model_selection import train_test_split

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class APTOSImageDataset(Dataset):
    """Lightweight APTOS dataset that returns raw images (no transform)."""
    def __init__(self, cache_root=None):
        import pandas as pd
        root = PROJECT_ROOT / "data" / "raw" / "aptos"
        self.samples = []
        df = pd.read_csv(root / "train.csv")
        for _, row in df.iterrows():
            img_path = root / "train_images" / f"{row['id_code']}.png"
            if img_path.exists():
                self.samples.append({"path": str(img_path), "label": int(row["diagnosis"])})

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        img = cv2.imread(s["path"])
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return img, s["label"]


def tta_evaluate(model, dataset, device, n_tta=5):
    """Evaluate with TTA: original + n augmented views."""
    model.eval()

    # TTA transforms
    tta_transforms = [
        # Original
        A.Compose([
            A.Resize(512, 512),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]),
        # Horizontal flip
        A.Compose([
            A.Resize(512, 512),
            A.HorizontalFlip(p=1.0),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]),
        # Slight rotation + brightness
        A.Compose([
            A.Resize(512, 512),
            A.Rotate(limit=10, border_mode=cv2.BORDER_REFLECT_101, p=1.0),
            A.RandomBrightnessContrast(brightness_limit=0.1, contrast_limit=0.1, p=1.0),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]),
        # Center crop + resize back
        A.Compose([
            A.Resize(560, 560),
            A.CenterCrop(480, 480),
            A.Resize(512, 512),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]),
        # Color jitter + slight rotation
        A.Compose([
            A.Resize(512, 512),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=15, val_shift_limit=10, p=1.0),
            A.Rotate(limit=5, border_mode=cv2.BORDER_REFLECT_101, p=1.0),
            A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ToTensorV2(),
        ]),
    ][:n_tta]

    all_preds = []
    all_targets = []
    all_probs = []

    for img_raw, label in dataset:
        # Stack all TTA views
        views = []
        for t in tta_transforms:
            augmented = t(image=img_raw)
            views.append(augmented["image"].unsqueeze(0))
        batch = torch.cat(views, dim=0).to(device)

        with torch.no_grad():
            logits = model(batch)
            probs = torch.softmax(logits, dim=1)
            avg_probs = probs.mean(dim=0)
            pred = avg_probs.argmax().item()

        all_preds.append(pred)
        all_targets.append(label)
        all_probs.append(avg_probs.cpu().numpy())

    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    all_probs = np.array(all_probs)

    acc = (all_preds == all_targets).mean()
    return acc, all_preds, all_targets, all_probs


def evaluate_standard(model, dataset, device):
    """Standard evaluation without TTA."""
    model.eval()
    transform = EVAL_TRANSFORM
    all_preds, all_targets = [], []
    for img_raw, label in dataset:
        augmented = transform(image=img_raw)
        imgs = augmented["image"].unsqueeze(0).to(device)
        with torch.no_grad():
            pred = model(imgs).argmax(dim=1).item()
        all_preds.append(pred)
        all_targets.append(label)
    return (np.array(all_preds) == np.array(all_targets)).mean(), np.array(all_preds), np.array(all_targets)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Load model
    model = DRClassifierConvNeXt(num_classes=5, pretrained=False)
    ckpt = torch.load(PROJECT_ROOT / "models/classification/best_classifier.pth",
                      map_location=device, weights_only=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    print(f"Model: val_acc={ckpt['val_acc']:.4f}, epoch={ckpt['epoch']}")

    # Load APTOS dataset (raw images)
    aptos_raw = APTOSImageDataset(cache_root=PROJECT_ROOT / "data" / "processed")
    labels = np.array([s["label"] for s in aptos_raw.samples])
    _, val_idx = train_test_split(np.arange(len(labels)), test_size=0.2, stratify=labels, random_state=42)
    val_subset = Subset(aptos_raw, val_idx.tolist())
    print(f"APTOS validation: {len(val_subset)} images")

    # Standard evaluation
    print("\n" + "=" * 60)
    print("STANDARD EVALUATION (no TTA)")
    print("=" * 60)
    acc, preds, targets = evaluate_standard(model, val_subset, device)
    print(f"Accuracy: {acc:.4f} ({acc*100:.1f}%)")
    print(classification_report(targets, preds, target_names=CLASS_NAMES, digits=4))

    # TTA evaluation
    for n_tta in [3, 5]:
        print(f"\n{'=' * 60}")
        print(f"TTA EVALUATION ({n_tta} views)")
        print("=" * 60)
        tta_acc, tta_preds, tta_targets, probs = tta_evaluate(model, val_subset, device, n_tta=n_tta)
        print(f"TTA Accuracy: {tta_acc:.4f} ({tta_acc*100:.1f}%)")
        print(f"Improvement over standard: +{(tta_acc - acc)*100:.1f}%")
        print(classification_report(tta_targets, tta_preds, target_names=CLASS_NAMES, digits=4))
        cm = confusion_matrix(tta_targets, tta_preds)
        print("Confusion Matrix:")
        print(cm)

        # Show confidence distribution
        confidences = probs.max(axis=1)
        print(f"\nConfidence: mean={confidences.mean():.3f}, min={confidences.min():.3f}")

        # Per-class accuracy
        for c in range(5):
            mask = tta_targets == c
            if mask.sum() > 0:
                cls_acc = (tta_preds[mask] == c).mean()
                print(f"  {CLASS_NAMES[c]}: {cls_acc:.3f} ({mask.sum()} samples)")

    # Save results
    import json
    results = {
        "standard_acc": float(acc),
        "tta_3_acc": None,
        "tta_5_acc": None,
        "model_epoch": int(ckpt["epoch"]),
        "model_val_acc": float(ckpt["val_acc"]),
    }
    (PROJECT_ROOT / "hackathon_sprint" / "metrics" / "tta_results.json").write_text(
        json.dumps(results, indent=2))
    print("\nResults saved.")


if __name__ == "__main__":
    main()
