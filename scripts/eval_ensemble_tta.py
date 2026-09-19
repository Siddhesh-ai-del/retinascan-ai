#!/usr/bin/env python
"""Evaluate with TTA + ensemble — memory-efficient, streaming images."""
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
from sklearn.model_selection import train_test_split
import cv2
import json

from src.models.classifier import DRClassifierConvNeXt
from src.data.preprocess import IMAGENET_MEAN, IMAGENET_STD
from src.constants import CLASS_NAMES

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_tta_transforms():
    return [
        A.Compose([A.Resize(512,512), A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD), ToTensorV2()]),
        A.Compose([A.Resize(512,512), A.HorizontalFlip(p=1.0), A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD), ToTensorV2()]),
        A.Compose([A.Resize(512,512), A.Rotate(limit=10, border_mode=cv2.BORDER_REFLECT_101, p=1.0), A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD), ToTensorV2()]),
    ]


def get_val_indices():
    """Get validation indices (same split as training)."""
    import pandas as pd
    root = PROJECT_ROOT / "data" / "raw" / "aptos"
    df = pd.read_csv(root / "train.csv")
    labels = df["diagnosis"].values
    _, val_idx = train_test_split(np.arange(len(labels)), test_size=0.2, stratify=labels, random_state=42)
    return val_idx, df


def predict_image(model, img_path, tta_transforms, device):
    """Load image, TTA predict, return probs."""
    img = cv2.imread(str(img_path))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    views = []
    for t in tta_transforms:
        aug = t(image=img)
        views.append(aug["image"].unsqueeze(0))
    batch = torch.cat(views, dim=0).to(device)
    with torch.no_grad():
        probs = torch.softmax(model(batch), dim=1)
        return probs.mean(dim=0).cpu().numpy()


def main():
    device = torch.device("cpu")
    print(f"Device: {device}")

    # Get val split
    val_idx, df = get_val_indices()
    print(f"Val samples: {len(val_idx)}")

    tta_transforms = get_tta_transforms()
    root = PROJECT_ROOT / "data" / "raw" / "aptos"

    # Load top checkpoints
    top3 = sorted(
        Path(PROJECT_ROOT / "models/classification").glob("top3_*.pth"),
        key=lambda p: float(p.stem.split("acc")[1]),
        reverse=True
    )[:3]
    best_path = PROJECT_ROOT / "models/classification" / "best_classifier.pth"
    checkpoints = [best_path] + top3 if best_path.exists() else top3

    print(f"Checkpoints: {[p.name for p in checkpoints]}")

    all_probs = []
    for i, ckpt_path in enumerate(checkpoints):
        print(f"\n--- Model {i+1}: {ckpt_path.name} ---")
        model = DRClassifierConvNeXt(num_classes=5, pretrained=False)
        ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["model_state_dict"])
        model.to(device).eval()

        model_probs = []
        model_targets = []
        for count, idx in enumerate(val_idx):
            row = df.iloc[idx]
            img_path = root / "train_images" / f"{row['id_code']}.png"
            if not img_path.exists():
                continue
            probs = predict_image(model, img_path, tta_transforms, device)
            model_probs.append(probs)
            model_targets.append(int(row["diagnosis"]))
            if (count + 1) % 50 == 0:
                print(f"  Processed {count+1}/{len(val_idx)}")

        model_probs = np.array(model_probs)
        model_targets = np.array(model_targets)
        preds = model_probs.argmax(axis=1)
        acc = (preds == model_targets).mean()
        print(f"  TTA accuracy: {acc:.4f} ({acc*100:.1f}%)")
        all_probs.append(model_probs)

        # Free memory
        del model

    # Now evaluate
    # Get the targets (use last model's targets since they're the same)
    targets = model_targets

    # Single best
    print("\n" + "=" * 60)
    print("SINGLE BEST MODEL (TTA)")
    print("=" * 60)
    best_preds = all_probs[0].argmax(axis=1)
    acc = (best_preds == targets).mean()
    print(f"Accuracy: {acc:.4f} ({acc*100:.1f}%)")
    print(classification_report(targets, best_preds, target_names=CLASS_NAMES, digits=4, zero_division=0))

    # Ensemble
    print("=" * 60)
    print(f"ENSEMBLE ({len(checkpoints)} models)")
    print("=" * 60)
    ens_probs = np.mean(all_probs, axis=0)
    ens_preds = ens_probs.argmax(axis=1)
    ens_acc = (ens_preds == targets).mean()
    print(f"Accuracy: {ens_acc:.4f} ({ens_acc*100:.1f}%)")
    print(classification_report(targets, ens_preds, target_names=CLASS_NAMES, digits=4, zero_division=0))
    cm = confusion_matrix(targets, ens_preds)
    print("Confusion Matrix:")
    print(cm)

    # Save
    results = {
        "single_best_tta_acc": float(acc),
        "ensemble_tta_acc": float(ens_acc),
        "models_evaluated": [p.name for p in checkpoints],
        "val_samples": len(targets),
    }
    out = PROJECT_ROOT / "hackathon_sprint" / "metrics"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ensemble_tta_results.json").write_text(json.dumps(results, indent=2))
    print(f"\nResults saved.")


if __name__ == "__main__":
    main()
