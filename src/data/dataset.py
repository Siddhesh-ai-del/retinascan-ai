from pathlib import Path

import albumentations as A
import cv2
import numpy as np
import pandas as pd
import torch
from albumentations.pytorch import ToTensorV2
from torch.utils.data import Dataset

from src.data.preprocess import (
    DEFAULT_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    get_cached_uint8,
    get_project_root,
    load_mask_aligned,
)

LESION_CHANNELS = ["microaneurysms", "hemorrhages", "hard_exudates", "cotton_wool_spots"]
NUM_LESIONS = 4
NUM_CLASSES = 5

TRAIN_TRANSFORM = A.Compose(
    [
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=15, border_mode=cv2.BORDER_REFLECT_101, p=0.7),
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.5),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ]
)

SEG_TRAIN_TRANSFORM = A.Compose(
    [
        A.HorizontalFlip(p=0.5),
        A.Rotate(limit=15, border_mode=cv2.BORDER_REFLECT_101, p=0.7),
        A.ElasticTransform(alpha=30, sigma=5, p=0.3),
        A.RandomBrightnessContrast(brightness_limit=0.15, contrast_limit=0.15, p=0.5),
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ]
)

EVAL_TRANSFORM = A.Compose(
    [
        A.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ToTensorV2(),
    ]
)


def find_idrid_paths():
    root = get_project_root() / "data" / "raw" / "idrid"
    if not root.exists():
        raise FileNotFoundError(f"IDRiD not found at {root}. Run python -m src.data.download first.")

    grading_csvs = [p for p in root.rglob("*.csv") if "grading" in p.name.lower()]
    train_csv = next((p for p in grading_csvs if "training" in p.stem.lower()), None)
    test_csv = next((p for p in grading_csvs if "test" in p.stem.lower()), None)
    if train_csv is None:
        train_csv = grading_csvs[0]

    sets = {"seg_train": None, "seg_test": None, "cls_train": None, "cls_test": None}
    for d in sorted(root.rglob("*")):
        if d.is_dir() and "original images" in d.parent.name.lower():
            section = d.parent.parent.name.lower()
            key = "seg" if section.startswith("a") else ("cls" if section.startswith("b") else None)
            if key is None:
                continue
            name = d.name.lower()
            if "training" in name or name.startswith("a."):
                sets[f"{key}_train"] = d
            elif "testing" in name or name.startswith("b."):
                sets[f"{key}_test"] = d

    seg_gt_root = next((d for d in root.rglob("*") if d.is_dir() and "segmentation groundtruth" in d.name.lower()), None)

    return {
        "train_csv": train_csv,
        "test_csv": test_csv,
        "cls_train_dir": sets["cls_train"],
        "cls_test_dir": sets["cls_test"],
        "seg_train_dir": sets["seg_train"],
        "seg_test_dir": sets["seg_test"],
        "seg_gt_root": seg_gt_root,
    }


def _find_mask_dirs(seg_root):
    dirs = {"MA": None, "HE": None, "EX": None, "SE": None}
    if seg_root is None:
        return dirs
    lesion_keywords = {
        "MA": ["microaneurysm"],
        "HE": ["haemorrhage", "hemorrhage"],
        "EX": ["hard exudate"],
        "SE": ["soft exudate", "cotton wool"],
    }
    all_dirs = [d for d in seg_root.rglob("*") if d.is_dir()]
    for key, keywords in lesion_keywords.items():
        candidates = [d for d in all_dirs if any(k in d.name.lower() for k in keywords)]
        if candidates:
            dirs[key] = sorted(candidates)[0]
    return dirs


class IDRiDDataset(Dataset):
    def __init__(self, task="classification", transform=None, split="train", cache_root=None):
        paths = find_idrid_paths()
        self.transform = transform or TRAIN_TRANSFORM
        self.cache_root = cache_root
        self.task = task
        self.samples = []

        if task == "classification":
            csv_path = paths["train_csv"] if split == "train" else (paths["test_csv"] or paths["train_csv"])
            df = pd.read_csv(csv_path)
            label_col = df.columns[1]
            img_dir = paths["cls_train_dir"] if split == "train" else (paths["cls_test_dir"] or paths["cls_train_dir"])
            self.mask_dirs = {k: None for k in ("MA", "HE", "EX", "SE")}
            for _, row in df.iterrows():
                img_id = str(row.iloc[0]).strip()
                matches = list(img_dir.glob(f"{img_id}.jpg")) + list(img_dir.glob(f"{img_id}.png")) if img_dir else []
                if matches:
                    self.samples.append({"path": matches[0], "label": int(row[label_col]), "id": img_id})
        else:
            img_dir = paths["seg_train_dir"] if split == "train" else (paths["seg_test_dir"] or paths["seg_train_dir"])
            gt_split_dir = None
            if paths["seg_gt_root"] is not None:
                subs = [d for d in paths["seg_gt_root"].rglob("*") if d.is_dir() and (("training" in d.name.lower() and split == "train") or ("testing" in d.name.lower() and split != "train"))]
                gt_split_dir = sorted(subs)[0] if subs else paths["seg_gt_root"]
            self.mask_dirs = _find_mask_dirs(gt_split_dir)

            grade_lookup = {}
            try:
                gdf = pd.read_csv(paths["train_csv"])
                grade_lookup = {str(r.iloc[0]).strip(): int(r[gdf.columns[1]]) for _, r in gdf.iterrows()}
            except Exception:
                pass

            anchor = self.mask_dirs["MA"] or self.mask_dirs["HE"] or self.mask_dirs["EX"] or self.mask_dirs["SE"]
            ids = []
            if anchor is not None:
                for f in sorted(anchor.iterdir()):
                    stem = f.stem.rsplit("_", 1)[0]
                    if stem not in ids:
                        ids.append(stem)
            for img_id in ids:
                matches = list(img_dir.glob(f"{img_id}.jpg")) + list(img_dir.glob(f"{img_id}.tif")) if img_dir else []
                if matches:
                    self.samples.append({"path": matches[0], "label": grade_lookup.get(img_id, 0), "id": img_id})

    def __len__(self):
        return len(self.samples)

    def _load_mask(self, mask_dir, img_id, image_path=None):
        if mask_dir is None:
            return np.zeros((DEFAULT_SIZE, DEFAULT_SIZE), dtype=np.float32)
        candidates = sorted(mask_dir.glob(f"{img_id}_*"))
        if not candidates:
            return np.zeros((DEFAULT_SIZE, DEFAULT_SIZE), dtype=np.float32)
        m = load_mask_aligned(candidates[0], image_path or self.samples[0]["path"], self.cache_root)
        return (m > 0).astype(np.float32)

    def __getitem__(self, idx):
        s = self.samples[idx]
        base = get_cached_uint8(s["path"], self.cache_root)
        image = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB) if base.ndim == 2 else base

        masks = np.stack(
            [self._load_mask(self.mask_dirs[k], s["id"], s["path"]) for k in ("MA", "HE", "EX", "SE")],
            axis=-1,
        )

        augmented = self.transform(image=image, masks=[masks[..., i] for i in range(NUM_LESIONS)])
        img_t = augmented["image"]
        mask_t = torch.stack([torch.from_numpy(np.ascontiguousarray(m)).float() for m in augmented["masks"]], dim=0)
        label_t = torch.tensor(s["label"], dtype=torch.long)
        return img_t, label_t, mask_t


class APTOSDataset(Dataset):
    def __init__(self, transform=None, cache_root=None):
        root = get_project_root() / "data" / "raw" / "aptos"
        img_dir = root / "train_images"
        csv_path = root / "train.csv"
        if not csv_path.exists() or not img_dir.exists():
            raise FileNotFoundError(f"APTOS not found at {root}. Run python -m src.data.download first.")

        df = pd.read_csv(csv_path)
        self.transform = transform or TRAIN_TRANSFORM
        self.cache_root = cache_root
        self.samples = []
        for _, row in df.iterrows():
            src = img_dir / f"{row['id_code']}.png"
            if src.exists():
                self.samples.append({"path": src, "label": int(row["diagnosis"]), "id": row["id_code"]})

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        base = get_cached_uint8(s["path"], self.cache_root)
        image = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB)
        zeros = np.zeros((DEFAULT_SIZE, DEFAULT_SIZE), dtype=np.float32)
        augmented = self.transform(image=image, masks=[zeros] * NUM_LESIONS)
        img_t = augmented["image"]
        mask_t = torch.stack([torch.from_numpy(np.ascontiguousarray(m)).float() for m in augmented["masks"]], dim=0)
        label_t = torch.tensor(s["label"], dtype=torch.long)
        return img_t, label_t, mask_t


class CombinedDataset(Dataset):
    def __init__(self, datasets, transform=None):
        self.datasets = datasets
        self.lengths = [len(d) for d in datasets]
        self.offsets = np.cumsum([0] + self.lengths)

    def __len__(self):
        return int(self.offsets[-1])

    def __getitem__(self, idx):
        ds_idx = int(np.searchsorted(self.offsets, idx, side="right") - 1)
        return self.datasets[ds_idx][idx - self.offsets[ds_idx]]

    @property
    def labels(self):
        all_labels = []
        for d in self.datasets:
            all_labels.extend([s["label"] for s in d.samples])
        return np.array(all_labels)


def build_combined_dataset(transform=None, include_idrid=True, include_aptos=True, cache_root=None):
    datasets = []
    if include_idrid:
        datasets.append(IDRiDDataset(task="classification", transform=transform, split="train", cache_root=cache_root))
    if include_aptos:
        datasets.append(APTOSDataset(transform=transform, cache_root=cache_root))
    if not datasets:
        raise RuntimeError("No datasets available. Download data first.")
    return CombinedDataset(datasets)
