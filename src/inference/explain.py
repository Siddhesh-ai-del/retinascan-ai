import base64
import threading

import cv2
import numpy as np

# torch and src.models.classifier are imported lazily inside the functions
# that need them: the API (and CI smoke tests, which run without torch) must
# be able to import this module. Only /api/explain actually requires PyTorch.

CAM_BLEND_ALPHA = 0.5

_cam_model = None
_cam_key = None
_cam_lock = threading.Lock()  # guards checkpoint load / singleton publish
_cam_compute_lock = threading.Lock()  # serializes Grad-CAM on the shared model


def is_convnext_checkpoint(ckpt):
    """True if checkpoint metadata declares a ConvNeXt backbone.

    Legacy checkpoints have no "backbone" key and are EfficientNet-B2.
    Torch-free so CI smoke tests can cover the selection logic.
    """
    return "convnext" in str(ckpt.get("backbone", "efficientnet")).lower()


def _load_cam_checkpoint(checkpoint_path, device):
    """Load a .pth checkpoint with weights_only=True (trusted types only).

    Training saves scalar metadata (val_acc) as np.float64, which the strict
    weights-only unpickler rejects by default — allowlist exactly that path.
    """
    import torch

    scalar = (
        np._core.multiarray.scalar
        if hasattr(np, "_core")
        else np.core.multiarray.scalar
    )
    safe = [scalar, np.dtype]
    float64_dtype = getattr(getattr(np, "dtypes", None), "Float64DType", None)
    if float64_dtype is not None:
        safe.append(float64_dtype)
    with torch.serialization.safe_globals(safe):
        return torch.load(checkpoint_path, map_location=device, weights_only=True)


def get_cam_model(checkpoint_path, device="cpu"):
    """Lazy singleton PyTorch classifier for Grad-CAM (ONNX serving untouched).

    Reads ckpt["backbone"] to build the matching architecture — newer
    checkpoints are ConvNeXt-Tiny, older ones EfficientNet-B2. Cached per
    (checkpoint_path, device) so a changed path cannot return the wrong arch.
    """
    global _cam_model, _cam_key
    key = (str(checkpoint_path), str(device))
    if _cam_model is not None and _cam_key == key:
        return _cam_model
    with _cam_lock:
        if _cam_model is None or _cam_key != key:
            ckpt = _load_cam_checkpoint(checkpoint_path, device)
            from src.models.classifier import DRClassifier, DRClassifierConvNeXt

            cls = DRClassifierConvNeXt if is_convnext_checkpoint(ckpt) else DRClassifier
            model = cls(num_classes=5, pretrained=False)
            try:
                model.load_state_dict(ckpt["model_state_dict"])
            except (KeyError, RuntimeError) as e:
                raise RuntimeError(
                    f"Checkpoint {checkpoint_path} does not match detected backbone "
                    f"'{ckpt.get('backbone', 'efficientnet')}' ({cls.__name__})"
                ) from e
            model.eval().to(device)
            _cam_model = model
            _cam_key = key
    return _cam_model


class _GradCAM:
    """Manual Grad-CAM: forward hook captures last-conv activations, backward
    hook captures their gradients; channel weights are GAP of gradients."""

    def __init__(self, model):
        self.model = model
        self.activations = None
        self.gradients = None
        block = model.backbone.features[-1]
        self._hooks = [
            block.register_forward_hook(self._save_activation),
            block.register_full_backward_hook(self._save_gradient),
        ]

    def close(self):
        """Remove hooks — must be called after heatmap() to avoid leaking
        hooks (and their captured tensors) on the shared singleton model."""
        for handle in self._hooks:
            handle.remove()
        self._hooks = []

    def _save_activation(self, _module, _inputs, output):
        self.activations = output.detach()

    def _save_gradient(self, _module, _grad_inputs, grad_output):
        self.gradients = grad_output[0].detach()

    def heatmap(self, input_tensor, class_idx=None):
        import torch

        with torch.enable_grad():
            self.model.zero_grad(set_to_none=True)
            logits = self.model(input_tensor.requires_grad_(False))
            if class_idx is None:
                class_idx = int(logits.argmax(dim=1).item())
            score = logits[0, class_idx]
            score.backward()
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = (
            torch.relu((weights * self.activations).sum(dim=1)).squeeze(0).cpu().numpy()
        )
        cam = (cam - cam.min()) / max(cam.max() - cam.min(), 1e-8)
        return cam, class_idx


def make_heatmap_overlay(base_gray_u8, cam, alpha=CAM_BLEND_ALPHA):
    """Jet heatmap blended over the preprocessed fundus image."""
    h, w = base_gray_u8.shape[:2]
    cam_resized = cv2.resize(cam, (w, h), interpolation=cv2.INTER_CUBIC)
    cam_u8 = np.clip(cam_resized * 255.0, 0, 255).astype(np.uint8)
    jet = cv2.applyColorMap(cam_u8, cv2.COLORMAP_JET)
    base_bgr = cv2.cvtColor(base_gray_u8, cv2.COLOR_GRAY2BGR)
    blend = cv2.addWeighted(jet, alpha, base_bgr, 1.0 - alpha, 0)
    ok, buf = cv2.imencode(".png", blend)
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None


def explain_preprocessed(checkpoint_path, base_gray_u8, chw_tensor):
    """Full explain step for an already-preprocessed image.

    Returns (heatmap_b64, stage_idx). Runs on CPU; loads the .pth lazily.
    """
    import torch

    model = get_cam_model(checkpoint_path)
    # Serialize CAM on the shared model: concurrent runs would cross-talk via
    # the hooks (wrong heatmap) and leak hooks on the singleton.
    with _cam_compute_lock:
        cam_obj = _GradCAM(model)
        try:
            cam, stage = cam_obj.heatmap(torch.from_numpy(chw_tensor))
        finally:
            cam_obj.close()
    return make_heatmap_overlay(base_gray_u8, cam), stage
