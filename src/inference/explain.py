import base64
import threading

import cv2
import numpy as np
import torch

from src.models.classifier import DRClassifier

CAM_BLEND_ALPHA = 0.5

_cam_model = None
_cam_lock = threading.Lock()


def get_cam_model(checkpoint_path, device="cpu"):
    """Lazy singleton PyTorch classifier for Grad-CAM (ONNX serving untouched)."""
    global _cam_model
    if _cam_model is not None:
        return _cam_model
    with _cam_lock:
        if _cam_model is None:
            model = DRClassifier(num_classes=5, pretrained=False)
            ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
            model.load_state_dict(ckpt["model_state_dict"])
            model.eval().to(device)
            _cam_model = model
    return _cam_model


class _GradCAM:
    """Manual Grad-CAM: forward hook captures last-conv activations, backward
    hook captures their gradients; channel weights are GAP of gradients."""

    def __init__(self, model):
        self.model = model
        self.activations = None
        self.gradients = None
        block = model.backbone.features[-1]
        block.register_forward_hook(self._save_activation)
        block.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, _module, _inputs, output):
        self.activations = output.detach()

    def _save_gradient(self, _module, _grad_inputs, grad_output):
        self.gradients = grad_output[0].detach()

    def heatmap(self, input_tensor, class_idx=None):
        with torch.enable_grad():
            self.model.zero_grad(set_to_none=True)
            logits = self.model(input_tensor.requires_grad_(False))
            if class_idx is None:
                class_idx = int(logits.argmax(dim=1).item())
            score = logits[0, class_idx]
            score.backward()
        weights = self.gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * self.activations).sum(dim=1)).squeeze(0).cpu().numpy()
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
    model = get_cam_model(checkpoint_path)
    cam, stage = _GradCAM(model).heatmap(torch.from_numpy(chw_tensor))
    return make_heatmap_overlay(base_gray_u8, cam), stage
