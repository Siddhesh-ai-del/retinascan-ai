import argparse
import json
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from onnxruntime.quantization import quantize_dynamic, QuantType

from src.models.classifier import DRClassifier, DRClassifierConvNeXt
from src.models.segmenter import LesionSegmenter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ONNX_DIR = PROJECT_ROOT / "models" / "onnx"


def load_classifier(device="cpu"):
    ckpt_path = PROJECT_ROOT / "models" / "classification" / "best_classifier.pth"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"{ckpt_path} not found. Train the classifier first.")
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=False)
    backbone = ckpt.get("backbone", "efficientnet")
    if backbone == "convnext_tiny":
        model = DRClassifierConvNeXt(num_classes=5, pretrained=False)
    else:
        model = DRClassifier(num_classes=5, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    print(f"Loaded {backbone} model (val_acc={ckpt.get('val_acc', 'N/A')})")
    return model


def load_segmenter(device="cpu"):
    ckpt_path = PROJECT_ROOT / "models" / "segmentation" / "best_segmenter.pth"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"{ckpt_path} not found. Train the segmenter first.")
    model = LesionSegmenter(num_classes=4, pretrained=False)
    ckpt = torch.load(ckpt_path, map_location=device, weights_only=True)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()
    return model


def export_onnx(model, save_path, input_name="input", opset=17):
    dummy = torch.randn(1, 3, 512, 512)
    torch.onnx.export(
        model,
        dummy,
        str(save_path),
        export_params=True,
        opset_version=opset,
        do_constant_folding=True,
        input_names=[input_name],
        output_names=["output"],
        dynamic_axes={input_name: {0: "batch_size"}, "output": {0: "batch_size"}},
    )
    print(f"Exported: {save_path} ({save_path.stat().st_size / 1e6:.1f} MB)")


def quantize_onnx(onnx_path, quantized_path):
    quantize_dynamic(str(onnx_path), str(quantized_path), weight_type=QuantType.QInt8)
    print(f"Quantized: {quantized_path} ({quantized_path.stat().st_size / 1e6:.1f} MB)")


def benchmark(model_path, runs=50):
    sess_options = ort.SessionOptions()
    available = ort.get_available_providers()
    providers = (
        ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if "CUDAExecutionProvider" in available
        else ["CPUExecutionProvider"]
    )
    try:
        sess = ort.InferenceSession(str(model_path), sess_options, providers=providers)
    except Exception:
        providers = ["CPUExecutionProvider"]
        sess = ort.InferenceSession(str(model_path), sess_options, providers=providers)

    input_name = sess.get_inputs()[0].name
    dummy = np.random.randn(1, 3, 512, 512).astype(np.float32)
    for _ in range(5):
        sess.run(None, {input_name: dummy})
    start = time.time()
    for _ in range(runs):
        sess.run(None, {input_name: dummy})
    avg_ms = (time.time() - start) / runs * 1000
    used = sess.get_providers()[0]
    print(f"{model_path.name}: {avg_ms:.1f} ms/inference [{used}]")
    return {"path": str(model_path.name), "avg_ms": round(avg_ms, 2), "provider": used}


def main():
    parser = argparse.ArgumentParser(description="Export trained models to ONNX and quantize")
    parser.add_argument("--skip-classifier", action="store_true")
    parser.add_argument("--skip-segmenter", action="store_true")
    parser.add_argument("--skip-quantize", action="store_true",
                        help="Skip INT8 quantization (may degrade small models)")
    args = parser.parse_args()

    if not ONNX_DIR.exists():
        raise SystemExit(f"Directory missing: {ONNX_DIR}")

    results = {}
    if not args.skip_classifier:
        cls_model = load_classifier()
        cls_onnx = ONNX_DIR / "classifier.onnx"
        export_onnx(cls_model, cls_onnx)
        cls_results = [benchmark(cls_onnx)]
        if not args.skip_quantize:
            quantize_onnx(cls_onnx, ONNX_DIR / "classifier_int8.onnx")
            cls_results.append(benchmark(ONNX_DIR / "classifier_int8.onnx"))
        results["classifier"] = cls_results

    if not args.skip_segmenter:
        seg_model = load_segmenter()
        seg_onnx = ONNX_DIR / "segmenter.onnx"
        export_onnx(seg_model, seg_onnx)
        seg_results = [benchmark(seg_onnx)]
        if not args.skip_quantize:
            # NOTE: INT8 quantization degrades the U-Net segmenter (13x slower
            # in benchmarks). Skip by default; pass --skip-quantize=false to
            # force it for comparison.
            quantize_onnx(seg_onnx, ONNX_DIR / "segmenter_int8.onnx")
            seg_results.append(benchmark(ONNX_DIR / "segmenter_int8.onnx"))
        results["segmenter"] = seg_results

    (ONNX_DIR / "benchmark_results.json").write_text(json.dumps(results, indent=2))
    print("All exports complete.")


if __name__ == "__main__":
    main()
