# Day 5: Segmenter Triage

## Deadline
- **Day 5 full day:** Polish segmenter visuals OR quick retraining
- **STOP when:** Demo-quality overlays working AND no visual artifacts

## Goal
Make the lesion segmentation look impressive in the demo. The Dice score (0.21) isn't the priority — the visual output is.

## Decision Point: Fix or Polish?

### Option A: Quick Retraining (if Dice < 0.25 and you have time)
### Option B: Visual Polish Only (recommended for hackathon)

**Recommendation: Option B.** The segmenter's job in the demo is to show colored overlays on the fundus image. Even with low Dice, the overlays can look convincing if you tune the thresholds and colors.

---

## Option A: Quick Segmenter Retraining (3-4 hours)

### Changes to `src/models/train.py`

#### 1. Better Loss Combination
```python
# In train_segmentation(), replace the loss:
# OLD:
# loss = 2.0 * dice_loss(outputs, masks) + 0.5 * bce_loss(outputs, masks)

# NEW:
dice_loss = smp.losses.DiceLoss(mode="multilabel", from_logits=True, smooth=0.1)
focal_loss = smp.losses.FocalLoss(mode="multilabel", alpha=0.75, gamma=2.0)
# ...
loss = 1.0 * dice_loss(outputs, masks) + 1.0 * focal_loss(outputs, masks)
```

#### 2. Add Deep Supervision
Add auxiliary loss at decoder stage 3:

```python
# In LesionSegmenter forward(), return intermediate features
# This requires modifying the model to output multi-scale

# Alternative: simpler approach — just use TTA for segmentation
```

#### 3. Train
```bash
python -m src.models.train --mode segmentation --epochs 80 --batch_size 8 --lr 1e-4
```

Target: Dice ≥ 0.28

---

## Option B: Visual Polish (Recommended, 3-4 hours)

### Task 1: Tune Segmentation Threshold (30 min)

File: `src/inference/predictor.py`

The current threshold is `SEG_VIS_THRESHOLD = 0.40`. For better visual results:

```python
# Try lowering to 0.30 for more sensitive detection
SEG_VIS_THRESHOLD = 0.30  # Was 0.40
```

Also add **morphological cleanup** to reduce noise:

```python
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
```

### Task 2: Improve Overlay Colors and Alpha (30 min)

File: `src/inference/predictor.py`

```python
# Current colors are fine, but increase overlay alpha for visibility:
OVERLAY_ALPHA = 0.75  # Was 0.65 — more visible overlays

# Also add contour thickness for better visibility:
# In _make_overlays():
cv2.drawContours(layer, contours, -1, (b, g, r, 255), 2)  # Was 1 — thicker contours
```

### Task 3: Add Lesion Statistics to Output (1 hour)

File: `src/inference/predictor.py`

Add to the `predict()` return, inside the segmentation block:

```python
lesion_stats = {}
if masks is not None:
    total_pixels = masks.shape[1] * masks.shape[2]
    for i, (key, name) in enumerate(zip(LESION_KEYS, LESION_NAMES)):
        count = int(masks[i].sum())
        area_pct = round(count / total_pixels * 100, 2)
        lesion_stats[key] = {
            "detected": bool(count > LESION_PIXEL_THRESHOLD),
            "pixels": count,
            "area_percent": area_pct,
            "name": name,
        }
```

And add to the return dict:
```python
"segmentation": {
    "lesions": lesion_stats,
    # ... rest unchanged
}
```

### Task 4: Frontend Lesion Stats Display (1 hour)

File: `frontend/src/components/LesionOverlay.jsx`

Add area percentage to the legend:

```jsx
{legend.map((l) => {
    const info = lesions[l.key] || {};
    return (
        <label key={l.key} className={`legend-item ${active[l.key] ? '' : 'off'}`}>
            <input type="checkbox" checked={active[l.key]} onChange={() => toggle(l.key)} />
            <span className="dot" style={{ background: l.color }} />
            <span className="legend-name">{l.name}</span>
            <span className="legend-status">
                {info.detected ? `${info.area_percent}%` : '—'}
            </span>
        </label>
    );
})}
```

### Task 5: Add Combined Lesion Summary Card (1 hour)

File: `frontend/src/components/Results.jsx`

After the grade card, add a lesion summary:

```jsx
{segmentation?.lesions && (
    <div className="card">
        <h3>Lesion Detection</h3>
        <div className="lesion-summary">
            {Object.entries(segmentation.lesions).map(([key, info]) => (
                <div key={key} className="lesion-row">
                    <span className="dot" style={{
                        background: segmentation.legend?.find(l => l.key === key)?.color || '#888'
                    }} />
                    <span className="lesion-name">{info.name}</span>
                    <span className={`lesion-status ${info.detected ? 'detected' : 'absent'}`}>
                        {info.detected ? `${info.area_percent}% area` : 'Not detected'}
                    </span>
                </div>
            ))}
        </div>
    </div>
)}
```

Add CSS to `frontend/src/index.css`:
```css
.lesion-summary { display: flex; flex-direction: column; gap: 8px; }
.lesion-row { display: flex; align-items: center; gap: 10px; font-size: 13px; }
.lesion-name { font-weight: 600; min-width: 140px; }
.lesion-status { margin-left: auto; font-size: 12px; color: var(--muted); }
.lesion-status.detected { color: var(--danger-deep); font-weight: 600; }
```

---

## Verification Checklist

- [ ] Upload a moderate NPDR image → colored overlays appear on lesions
- [ ] Overlays are semi-transparent (you can see the fundus underneath)
- [ ] Contours are visible around detected regions
- [ ] Legend shows area percentage for detected lesions
- [ ] "Not detected" for absent lesions shows "—" or "0%"
- [ ] No visual artifacts (solid color blocks, misaligned overlays)
- [ ] Combined overlay shows all lesion types with distinct colors

---

## Go/No-Go Criteria

| Check | Status |
|---|---|
| Overlays render correctly | Required |
| No visual artifacts | Required |
| Lesion stats in output | Required |
| Area percentage in frontend | Nice to have |
| Dice improved (if retrained) | Nice to have |
