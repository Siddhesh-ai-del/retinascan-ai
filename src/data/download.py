import argparse
import shutil
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DEMO_DIR = PROJECT_ROOT / "demo_images"

IDRID_KAGGLE_DATASETS = [
    "aaryapatel98/indian-diabetic-retinopathy-image-dataset",
    "abdullahshafi315/indian-diabetic-retinopathy-image-datasetidrid",
    "gyanpr02/indian-diabetic-retinopathy-image-datasetidrid",
]
APTOS_COMPETITION = "aptos2019-blindness-detection"

STAGE_NAMES = {
    0: "healthy",
    1: "mild_npdr",
    2: "moderate_npdr",
    3: "severe_npdr",
    4: "proliferative_dr",
}


def check_kaggle_credentials() -> bool:
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    access_token = Path.home() / ".kaggle" / "access_token"
    if kaggle_json.exists() or access_token.exists():
        return True
    print(
        "Kaggle credentials not found.\n"
        "Option A: create ~/.kaggle/access_token containing your Kaggle API token\n"
        "          (kaggle.com -> Settings -> API -> Create New Token)\n"
        "Option B: save the classic kaggle.json to " + str(kaggle_json) + "\n"
        "Alternatively download the datasets manually via browser and unzip into:\n"
        f"  IDRiD -> {DATA_RAW / 'idrid'}\n"
        f"  APTOS -> {DATA_RAW / 'aptos'}"
    )
    return False


def _unzip_all(folder: Path):
    for z in sorted(folder.glob("**/*.zip")):
        target = z.parent / z.stem
        if not target.exists():
            print(f"Extracting {z.name} ...")
            with zipfile.ZipFile(z) as zf:
                zf.extractall(z.parent)
        try:
            z.unlink()
        except OSError:
            pass


def download_idrid():
    out = DATA_RAW / "idrid"
    out.mkdir(parents=True, exist_ok=True)
    if any(out.iterdir()):
        print(f"IDRiD folder not empty, skipping download ({out})")
        return
    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    errors = []
    for ref in IDRID_KAGGLE_DATASETS:
        try:
            print(f"Downloading IDRiD mirror {ref} ...")
            api.dataset_download_files(ref, path=out, unzip=True)
            _unzip_all(out)
            n_imgs = len(list(out.rglob("*.jpg"))) + len(list(out.rglob("*.png")))
            if n_imgs == 0:
                raise RuntimeError("no images found after extraction")
            print(f"OK: {n_imgs} images -> {out}")
            return
        except Exception as e:
            print(f"  mirror failed: {e}")
            errors.append(f"{ref}: {e}")
    raise RuntimeError("All IDRiD mirrors failed:\n" + "\n".join(errors))


def _zip_valid(path: Path) -> bool:
    import zipfile

    try:
        with zipfile.ZipFile(path) as zf:
            return zf.testzip() is None
    except Exception:
        return False


def download_aptos(retries=5):
    out = DATA_RAW / "aptos"
    out.mkdir(parents=True, exist_ok=True)
    if (out / "train.csv").exists() and (out / "train_images").exists():
        print(f"APTOS already present ({out})")
        return

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            print(f"Downloading APTOS 2019 (attempt {attempt}/{retries})...")
            api.competition_download_files(APTOS_COMPETITION, path=out)
            zpath = next(out.glob("*.zip"))
            if not _zip_valid(zpath):
                raise RuntimeError("downloaded zip failed integrity check")
            _unzip_all(out)
            if not ((out / "train.csv").exists()):
                raise RuntimeError("train.csv missing after extraction")
            print(f"APTOS stored in {out}")
            return
        except Exception as e:
            last_err = e
            print(f"  attempt {attempt} failed: {e}")
            for junk in list(out.glob("*.zip")) + list(out.glob("*.kaggle-partial")):
                try:
                    junk.unlink()
                except OSError:
                    pass
    raise RuntimeError(f"APTOS download failed after {retries} attempts: {last_err}")


def prepare_demo_images(num_per_stage: int = 1):
    import cv2
    import pandas as pd

    aptos_img_dir = DATA_RAW / "aptos" / "train_images"
    csv_path = DATA_RAW / "aptos" / "train.csv"
    idrid_csv_candidates = list((DATA_RAW / "idrid").rglob("*Disease*Grading*Labels*.csv")) + list(
        (DATA_RAW / "idrid").rglob("*groundtruth*.csv")
    )

    DEMO_DIR.mkdir(parents=True, exist_ok=True)

    def _save(src: Path, stage: int):
        dst = DEMO_DIR / f"{STAGE_NAMES[stage]}.jpg"
        img = cv2.imread(str(src))
        if img is None:
            return False
        h, w = img.shape[:2]
        scale = 1024 / max(h, w)
        if scale < 1:
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(dst), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(f"  {dst.name} <- {src.name}")
        return True

    if csv_path.exists() and aptos_img_dir.exists():
        df = pd.read_csv(csv_path)
        for stage in range(5):
            saved = 0
            subset = df[df["diagnosis"] == stage]
            for _, row in subset.iterrows():
                src = aptos_img_dir / f"{row['id_code']}.png"
                if src.exists() and _save(src, stage):
                    saved += 1
                    break
            if saved == 0:
                print(f"  WARNING: no APTOS image found for stage {stage}")

    blurry_src = DEMO_DIR / "healthy.jpg"
    if blurry_src.exists():
        img = cv2.imread(str(blurry_src))
        h, w = img.shape[:2]
        blurred = cv2.GaussianBlur(img, (0, 0), sigmaX=min(h, w) / 40)
        small = cv2.resize(blurred, (w // 6, h // 6), interpolation=cv2.INTER_AREA)
        degraded = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
        dst = DEMO_DIR / "blurry_ungradable.jpg"
        cv2.imwrite(str(dst), degraded, [cv2.IMWRITE_JPEG_QUALITY, 35])
        print(f"  {dst.name} <- synthetic blur of healthy.jpg")
    else:
        print("  NOTE: healthy.jpg missing; cannot synthesize blurry demo image")

    print(f"Demo images ready in {DEMO_DIR}")


def main():
    parser = argparse.ArgumentParser(description="Download IDRiD + APTOS datasets and prepare demo images")
    parser.add_argument("--idrid", action="store_true", help="Download IDRiD only")
    parser.add_argument("--aptos", action="store_true", help="Download APTOS only")
    parser.add_argument("--demo", action="store_true", help="Prepare demo images from downloaded data")
    args = parser.parse_args()

    do_all = not (args.idrid or args.aptos or args.demo)

    if (do_all or args.idrid or args.aptos) and not check_kaggle_credentials():
        raise SystemExit(1)
    if do_all or args.idrid:
        download_idrid()
    if do_all or args.aptos:
        download_aptos()
    if do_all or args.demo:
        prepare_demo_images()


if __name__ == "__main__":
    main()
