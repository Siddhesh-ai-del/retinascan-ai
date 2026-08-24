import hashlib
from pathlib import Path

import cv2
import numpy as np

DEFAULT_SIZE = 512

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

CACHE_DIR_NAME = "cache_512"


def get_project_root():
    return Path(__file__).resolve().parents[2]


def apply_clahe(img, clip_limit=2.0, grid_size=8):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    lab[..., 0] = clahe.apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def extract_green_channel(img):
    return img[..., 1]


def crop_box_for(gray_blurred, shape, keep_fraction=0.8):
    h, w = shape[:2]
    (_, _, min_loc, _) = cv2.minMaxLoc(gray_blurred)
    cx, cy = min_loc
    side = int(min(h, w) * keep_fraction)
    x0 = max(0, min(cx - side // 2, w - side))
    y0 = max(0, min(cy - side // 2, h - side))
    return x0, y0, side


def crop_pupil_center(img, keep_fraction=0.8):
    h, w = img.shape[:2]
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (51, 51), 0)
    x0, y0, side = crop_box_for(blurred, (h, w), keep_fraction)
    return img[y0 : y0 + side, x0 : x0 + side]


def resize_image(img, target_size=DEFAULT_SIZE):
    return cv2.resize(img, (target_size, target_size), interpolation=cv2.INTER_LANCZOS4)


def preprocess_pipeline(image_path, target_size=DEFAULT_SIZE):
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    img = apply_clahe(img)
    green = extract_green_channel(img)
    green = crop_pupil_center(green)
    green = resize_image(green, target_size)
    normalized = green.astype(np.float32) / 255.0
    return normalized


def preprocess_pipeline_3ch(image_path, target_size=DEFAULT_SIZE):
    single = preprocess_pipeline(image_path, target_size)
    stacked = np.stack([single, single, single], axis=0)
    return stacked


def _cache_key(image_path) -> str:
    stat = Path(image_path).stat()
    raw = f"{Path(image_path).name}_{stat.st_size}_{int(stat.st_mtime)}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def get_cached_uint8(image_path, cache_root=None, target_size=DEFAULT_SIZE):
    if cache_root is None:
        cache_root = get_project_root() / "data" / "processed" / CACHE_DIR_NAME
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)

    key = _cache_key(image_path)
    cache_file = cache_root / f"{key}.npy"
    box_file = cache_root / f"{key}.box.npy"
    if cache_file.exists() and box_file.exists():
        arr = np.load(cache_file)
        if arr.shape == (target_size, target_size):
            return arr

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")
    img = apply_clahe(img)
    green = extract_green_channel(img)
    gray_blurred = cv2.GaussianBlur(green, (51, 51), 0)
    x0, y0, side = crop_box_for(gray_blurred, green.shape[:2])
    green = green[y0 : y0 + side, x0 : x0 + side]
    green = resize_image(green, target_size)
    arr = green.astype(np.uint8)
    np.save(cache_file, arr)
    np.save(box_file, np.array([x0, y0, side, img.shape[0], img.shape[1]], dtype=np.int32))
    return arr


def load_mask_aligned(mask_path, image_path, cache_root=None, target_size=DEFAULT_SIZE):
    if cache_root is None:
        cache_root = get_project_root() / "data" / "processed" / CACHE_DIR_NAME
    key = _cache_key(image_path)
    box_file = Path(cache_root) / f"{key}.box.npy"
    if not box_file.exists():
        get_cached_uint8(image_path, cache_root, target_size)
    x0, y0, side, oh, ow = np.load(box_file)

    m = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
    if m is None:
        return np.zeros((target_size, target_size), dtype=np.uint8)
    scale_y, scale_x = oh / m.shape[0], ow / m.shape[1]
    if abs(scale_y - 1) > 1e-3 or abs(scale_x - 1) > 1e-3:
        m = cv2.resize(m, (ow, oh), interpolation=cv2.INTER_NEAREST)
    m = m[y0 : y0 + side, x0 : x0 + side]
    return resize_image(m, target_size)


def _cache_worker(args):
    path, cache_root = args
    return get_cached_uint8(path, cache_root)


def build_cache(image_paths, cache_root=None, workers=8):
    from concurrent.futures import ProcessPoolExecutor
    from tqdm import tqdm

    jobs = [(p, str(cache_root) if cache_root else None) for p in image_paths]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        list(tqdm(ex.map(_cache_worker, jobs), total=len(jobs), desc="Caching"))
