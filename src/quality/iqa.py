import cv2
import numpy as np

BLUR_THRESHOLD = 20.0
DARK_THRESHOLD = 40.0
OVEREXPOSED_THRESHOLD = 220.0
GLARE_PIXEL_THRESHOLD = 250
GLARE_RATIO_THRESHOLD = 0.05
FUNDUS_SCORE_THRESHOLD = 0.5


class ImageQualityAssessor:
    def assess(self, image_path) -> dict:
        img = cv2.imread(str(image_path))
        if img is None:
            return {
                "gradable": False,
                "blur_score": 0.0,
                "brightness": 0.0,
                "quality_issues": ["unreadable"],
                "feedback": "Image could not be read. Please upload a valid image file.",
            }

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape[:2]
        s = 1024
        g = cv2.resize(gray, (s, max(1, int(s * h / w))))
        color = cv2.resize(img, (g.shape[1], g.shape[0]))

        rmask, geometry_term, centroid_offset = self._retina_geometry(g)
        ys, xs = np.where(rmask > 0)
        if len(xs) > 100:
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            center = g[(y0 + y1) // 4 : (3 * y0 + 3 * y1) // 4, (x0 + x1) // 4 : (3 * x0 + 3 * x1) // 4]
        else:
            center = g

        issues = []

        blur_score = self._check_blur(center)
        if blur_score < 1.0:
            issues.append("blur")

        brightness = float(np.mean(gray))
        if brightness < DARK_THRESHOLD:
            issues.append("dark")
        if brightness > OVEREXPOSED_THRESHOLD:
            issues.append("overexposed")

        if self._check_glare(img):
            issues.append("glare")

        fundus_score = self._fundus_score(color, rmask, geometry_term)
        if fundus_score < FUNDUS_SCORE_THRESHOLD:
            issues.append("no_fundus_detected")

        if min(h, w) < 224:
            issues.append("low_resolution")

        gradable = len(issues) == 0
        feedback = self._build_feedback(issues) if not gradable else None

        return {
            "gradable": bool(gradable),
            "blur_score": round(blur_score, 3),
            "brightness": round(brightness, 2),
            "fundus_score": round(fundus_score, 3),
            "quality_issues": issues,
            "feedback": feedback,
        }

    def _retina_geometry(self, g):
        _, mask = cv2.threshold(g, 12, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((25, 25), np.uint8))

        ys, xs = np.where(mask > 0)
        if len(xs) < 100:
            return mask, 1.0, 1.0
        coverage = float((mask > 0).mean())
        if coverage > 0.97 or coverage < 0.2:
            return mask, 1.0, 1.0

        bw, bh = xs.max() - xs.min(), ys.max() - ys.min()
        aspect = bw / max(bh, 1)
        aspect_penalty = min(abs(np.log(max(aspect, 1e-6)) / np.log(2.5)), 1.0)

        cx, cy = xs.mean() / g.shape[1], ys.mean() / g.shape[0]
        offset = float(np.hypot(cx - 0.5, cy - 0.5) * 2)

        geometry_term = 0.0 if (aspect_penalty < 0.85 and offset < 0.55) else min(1.0, aspect_penalty + offset)
        return mask, geometry_term, offset

    def _fundus_score(self, color_bgr, rmask, geometry_term):
        hsv = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2HSV)
        retina = rmask > 0
        px = int(retina.sum())
        if px < 500:
            return 0.0

        h_, s_, v_ = hsv[..., 0].astype(int), hsv[..., 1].astype(int), hsv[..., 2].astype(int)
        warm_hue = ((h_ <= 35) | (h_ >= 160)) & (s_ > 40) & (v_ > 30)
        warmth = float((warm_hue & retina).sum()) / max(px, 1)

        gray_in = cv2.cvtColor(color_bgr, cv2.COLOR_BGR2GRAY)[retina]
        structure = min(float(gray_in.std()) / 25.0, 1.0)

        b_mean = float(color_bgr[..., 0][retina].mean())
        g_mean = float(color_bgr[..., 1][retina].mean())
        r_mean = float(color_bgr[..., 2][retina].mean())
        channel_ok = r_mean >= g_mean >= b_mean or (g_mean >= max(r_mean, b_mean) and r_mean >= b_mean)

        score = 0.45 * min(warmth / 0.60, 1.0) + 0.35 * (geometry_term == 0.0) + 0.20 * structure
        if not channel_ok:
            score -= 0.15

        return float(min(max(score, 0.0), 1.0))

    def _check_blur(self, center_region):
        clahe = cv2.createCLAHE(2.0, (8, 8)).apply(center_region)
        lap_var = cv2.Laplacian(clahe, cv2.CV_64F).var()
        return float(min(lap_var / BLUR_THRESHOLD, 10.0))

    def _check_brightness(self, gray):
        return float(np.mean(gray))

    def _check_glare(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bright = cv2.threshold(gray, GLARE_PIXEL_THRESHOLD, 255, cv2.THRESH_BINARY)
        ratio = float(np.count_nonzero(bright)) / bright.size
        return ratio > GLARE_RATIO_THRESHOLD

    def _build_feedback(self, issues):
        parts = []
        if "no_fundus_detected" in issues:
            parts.append(
                "this does not appear to be a retinal fundus image — please upload a fundus photograph centered on the retina"
            )
        if "blur" in issues:
            parts.append("image is blurry — hold the camera steady and refocus")
        if "dark" in issues:
            parts.append("image is too dark — increase illumination")
        if "overexposed" in issues:
            parts.append("image is overexposed — reduce exposure")
        if "glare" in issues:
            parts.append("specular glare detected — adjust the flash angle")
        if "low_resolution" in issues:
            parts.append("image resolution too low — recapture at higher quality")
        return "Please recapture: " + "; ".join(parts) + "."
