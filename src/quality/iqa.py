import cv2
import numpy as np

BLUR_THRESHOLD = 20.0
DARK_THRESHOLD = 40.0
OVEREXPOSED_THRESHOLD = 220.0
GLARE_PIXEL_THRESHOLD = 250
GLARE_RATIO_THRESHOLD = 0.05
MIN_RETINA_COVERAGE = 0.25


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

        _, rmask = cv2.threshold(g, 12, 255, cv2.THRESH_BINARY)
        rmask = cv2.morphologyEx(rmask, cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
        coverage = float((rmask > 0).mean())

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

        if coverage < MIN_RETINA_COVERAGE:
            issues.append("no_fundus_detected")

        if min(h, w) < 224:
            issues.append("low_resolution")

        gradable = len(issues) == 0
        feedback = self._build_feedback(issues) if not gradable else None

        return {
            "gradable": bool(gradable),
            "blur_score": round(blur_score, 3),
            "brightness": round(brightness, 2),
            "quality_issues": issues,
            "feedback": feedback,
        }

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
        if "no_fundus_detected" in issues:
            parts.append("this does not look like a fundus image — capture the retina centered in frame")
        return "Please recapture: " + "; ".join(parts) + "."
