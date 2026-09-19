import base64

import cv2
import numpy as np
import onnxruntime as ort

from src.constants import CLASS_NAMES
from src.data.preprocess import IMAGENET_MEAN, IMAGENET_STD, get_cached_uint8
from src.fhir.generator import generate_fhir_report
from src.quality.iqa import ImageQualityAssessor

LESION_NAMES = ["Microaneurysms", "Hemorrhages", "Hard Exudates", "Cotton Wool Spots"]
LESION_KEYS = ["microaneurysms", "hemorrhages", "hard_exudates", "cotton_wool_spots"]
LESION_COLORS_RGB = [
    (255, 69, 58),
    (255, 149, 0),
    (255, 214, 10),
    (50, 215, 75),
]

REFERRAL_MAP = {
    0: {"recommended": False, "urgency": "none — routine annual screening"},
    1: {"recommended": False, "urgency": "repeat screening in 12 months"},
    2: {"recommended": True, "urgency": "within 4 weeks"},
    3: {"recommended": True, "urgency": "within 2 weeks"},
    4: {"recommended": True, "urgency": "immediate — within 24 hours"},
}

SEG_VIS_THRESHOLD = 0.30  # Was 0.40 — more sensitive detection
OVERLAY_ALPHA = 0.75  # Was 0.65 — more visible overlays
LESION_PIXEL_THRESHOLD = 25

# Abstention: below this confidence (or in the fundus-score borderline band)
# the case is flagged for human review instead of being trusted outright.
CONF_ABSTAIN_THRESHOLD = 0.55
FUNDUS_REVIEW_BAND = 0.6
MANUAL_REVIEW_URGENCY = "manual review recommended before clinical decision"


def make_session(model_path):
    available = ort.get_available_providers()
    providers = (
        ["CUDAExecutionProvider", "CPUExecutionProvider"]
        if "CUDAExecutionProvider" in available
        else ["CPUExecutionProvider"]
    )
    try:
        return ort.InferenceSession(str(model_path), providers=providers)
    except Exception as e:
        print(f"WARNING: failed to load {model_path} ({e}). Model endpoints will be unavailable until trained.")
        return None


class DRPredictor:
    def __init__(self, classifier_path=None, segmenter_path=None, patient_id="unknown",
                 ensemble_paths=None):
        self.classifier = make_session(classifier_path) if classifier_path else None
        self.segmenter = make_session(segmenter_path) if segmenter_path else None
        self.ensemble = []
        if ensemble_paths:
            for p in ensemble_paths:
                sess = make_session(p)
                if sess is not None:
                    self.ensemble.append(sess)
            if self.ensemble:
                print(f"Loaded {len(self.ensemble)} ensemble models")
        self.iqa = ImageQualityAssessor()
        self.patient_id = patient_id

    def is_ready(self):
        return self.classifier is not None and self.segmenter is not None

    def _preprocess(self, image_path):
        base = get_cached_uint8(image_path)
        rgb = cv2.cvtColor(base, cv2.COLOR_GRAY2RGB).astype(np.float32) / 255.0
        rgb = (rgb - np.array(IMAGENET_MEAN, dtype=np.float32)) / np.array(IMAGENET_STD, dtype=np.float32)
        chw = rgb.transpose(2, 0, 1)[np.newaxis, ...]
        return base, chw.astype(np.float32)

    def _classify(self, input_tensor):
        logits = self.classifier.run(None, {self.classifier.get_inputs()[0].name: input_tensor})[0][0]
        probs = np.exp(logits - logits.max())
        probs = probs / probs.sum()
        stage = int(np.argmax(probs))
        return {
            "stage": stage,
            "label": CLASS_NAMES[stage],
            "confidence": round(float(probs[stage]), 4),
            "probabilities": [round(float(p), 4) for p in probs],
        }

    def _classify_tta(self, input_tensor, n_augments=4):
        """Average predictions over augmented versions of the input."""
        base = input_tensor[0]  # (3, 512, 512) CHW

        # Generate augmented versions
        augmented_tensors = [input_tensor]  # original

        # Horizontal flip
        flipped = np.flip(base, axis=2).copy()  # flip W
        augmented_tensors.append(flipped[np.newaxis, ...])

        # Vertical flip
        vflipped = np.flip(base, axis=1).copy()  # flip H
        augmented_tensors.append(vflipped[np.newaxis, ...])

        # Both flips
        both = np.flip(base, axis=(1, 2)).copy()
        augmented_tensors.append(both[np.newaxis, ...])

        # Collect all predictions
        all_probs = []
        for aug_tensor in augmented_tensors:
            aug_tensor = aug_tensor.astype(np.float32)
            logits = self.classifier.run(None, {self.classifier.get_inputs()[0].name: aug_tensor})[0][0]
            probs = np.exp(logits - logits.max())
            probs = probs / probs.sum()
            all_probs.append(probs)

        # Average probabilities
        mean_probs = np.mean(all_probs, axis=0)
        stage = int(np.argmax(mean_probs))
        return {
            "stage": stage,
            "label": CLASS_NAMES[stage],
            "confidence": round(float(mean_probs[stage]), 4),
            "probabilities": [round(float(p), 4) for p in mean_probs],
        }

    def _classify_ensemble(self, input_tensor):
        """Ensemble prediction: average probabilities across multiple models."""
        if not self.ensemble:
            return self._classify_tta(input_tensor)

        all_probs = []
        for sess in self.ensemble:
            logits = sess.run(None, {sess.get_inputs()[0].name: input_tensor})[0][0]
            probs = np.exp(logits - logits.max())
            probs = probs / probs.sum()
            all_probs.append(probs)

        mean_probs = np.mean(all_probs, axis=0)
        stage = int(np.argmax(mean_probs))
        return {
            "stage": stage,
            "label": CLASS_NAMES[stage],
            "confidence": round(float(mean_probs[stage]), 4),
            "probabilities": [round(float(p), 4) for p in mean_probs],
        }

    def _segment(self, input_tensor):
        logits = self.segmenter.run(None, {self.segmenter.get_inputs()[0].name: input_tensor})[0][0]
        raw = (1 / (1 + np.exp(-logits)) > SEG_VIS_THRESHOLD).astype(np.uint8)

        # Morphological cleanup — remove small isolated pixels
        kernel = np.ones((3, 3), np.uint8)
        cleaned = np.zeros_like(raw)
        for i in range(raw.shape[0]):
            # Remove small noise
            cleaned[i] = cv2.morphologyEx(raw[i], cv2.MORPH_OPEN, kernel)
            # Fill small holes
            cleaned[i] = cv2.morphologyEx(cleaned[i], cv2.MORPH_CLOSE, kernel)
        return cleaned

    def _encode_png(self, img):
        ok, buf = cv2.imencode(".png", img)
        return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None

    def _make_overlays(self, base_gray, masks):
        original_b64 = self._encode_png(cv2.cvtColor(base_gray, cv2.COLOR_GRAY2BGR))
        overlays = {}
        h, w = base_gray.shape[:2]

        for i, mask in enumerate(masks):
            layer = np.zeros((h, w, 4), dtype=np.uint8)
            if mask.any():
                r, g, b = LESION_COLORS_RGB[i]
                region = mask.astype(bool)
                layer[region, 0] = b
                layer[region, 1] = g
                layer[region, 2] = r
                layer[region, 3] = int(255 * OVERLAY_ALPHA)
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                cv2.drawContours(layer, contours, -1, (b, g, r, 255), 2)  # Thicker contours
            key = LESION_KEYS[i]
            overlays[key] = self._encode_png(layer)

        combined = np.zeros((h, w, 4), dtype=np.uint8)
        alpha_acc = np.zeros((h, w), dtype=np.float32)
        color_acc = np.zeros((h, w, 3), dtype=np.float32)
        for i, mask in enumerate(masks):
            region = mask.astype(bool)
            r, g, b = LESION_COLORS_RGB[i]
            a = OVERLAY_ALPHA
            m = region.astype(np.float32) * a
            newly = np.clip(a - alpha_acc, 0, 1) * region
            color_acc += np.stack([np.full((h, w), b), np.full((h, w), g), np.full((h, w), r)], axis=-1) * newly[..., None]
            alpha_acc = np.maximum(alpha_acc, m)
        vis_alpha = alpha_acc > 0
        combined[..., :3][vis_alpha] = color_acc[vis_alpha].astype(np.uint8)
        combined[..., 3][vis_alpha] = (alpha_acc[vis_alpha] * 255).clip(0, 255).astype(np.uint8)

        return {
            "original": original_b64,
            "overlays": overlays,
            "combined_overlay": self._encode_png(combined),
        }

    def predict(self, image_path, patient_id=None):
        patient_id = patient_id or self.patient_id
        quality = self.iqa.assess(image_path)
        if not quality["gradable"]:
            return {
                "status": "rejected",
                "quality": quality,
                "classification": None,
                "segmentation": None,
                "referral": None,
                "fhir": None,
            }

        base, input_tensor = self._preprocess(image_path)
        classification = self._classify_ensemble(input_tensor) if self.classifier else None
        masks = self._segment(input_tensor) if self.segmenter else None

        overlay_pack = self._make_overlays(base, masks) if masks is not None else None

        lesion_summary = {}
        if masks is not None:
            total_pixels = masks.shape[1] * masks.shape[2]
            for i, (key, name) in enumerate(zip(LESION_KEYS, LESION_NAMES)):
                count = int(masks[i].sum())
                area_pct = round(count / total_pixels * 100, 2)
                lesion_summary[key] = {
                    "detected": bool(count > LESION_PIXEL_THRESHOLD),
                    "pixels": count,
                    "area_percent": area_pct,
                    "name": name,
                }

        overlay_b64 = overlay_pack["combined_overlay"] if overlay_pack else None

        referral = REFERRAL_MAP.get(classification["stage"], {"recommended": True, "urgency": "refer to ophthalmologist — unrecognised stage"}) if classification else None

        needs_review = False
        review_reasons = []
        if classification:
            low_conf = classification["confidence"] < CONF_ABSTAIN_THRESHOLD
            borderline_fundus = quality["fundus_score"] < FUNDUS_REVIEW_BAND
            needs_review = bool(low_conf or borderline_fundus)
            if low_conf:
                review_reasons.append("low_confidence")
            if borderline_fundus:
                review_reasons.append("borderline_fundus_quality")
            if needs_review and referral is not None:
                referral = {
                    **referral,
                    "recommended": True,
                    "urgency": MANUAL_REVIEW_URGENCY,
                    "overridden_by": "abstention",
                }

        fhir = generate_fhir_report(patient_id, classification, lesion_summary) if classification else None

        return {
            "status": "ok",
            "needs_human_review": needs_review,
            "review_reasons": review_reasons,
            "quality": quality,
            "classification": classification,
            "segmentation": {
                "lesions": lesion_summary,
                "original": overlay_pack["original"] if overlay_pack else None,
                "overlays": overlay_pack["overlays"] if overlay_pack else None,
                "overlay": overlay_b64,
                "legend": [
                    {"key": k, "name": n, "color": "#%02X%02X%02X" % c}
                    for k, n, c in zip(LESION_KEYS, LESION_NAMES, LESION_COLORS_RGB)
                ],
            },
            "referral": referral,
            "fhir": fhir,
        }
