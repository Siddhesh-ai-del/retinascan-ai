# Day 1-2: Model Accuracy Blitz

## Deadline
- **Day 1 morning:** Implement all training improvements
- **Day 1 evening:** Start overnight training run
- **Day 2 morning:** Evaluate results, iterate if needed
- **STOP when:** Classifier val accuracy ≥ 82% OR after 3 training attempts (pick best)

## Goal
Push the DR classifier from **76.7% accuracy** to **82-85%** by stacking multiple quick-win improvements.

## Current State
- Model: EfficientNet-B2 (`src/models/classifier.py`)
- Loss: FocalLoss with class weights (`src/models/train.py`)
- Training: 30 epochs, batch_size=16, lr=1e-4, AdamW + CosineAnnealing
- Datasets: IDRiD + APTOS combined (~4,500 images)
- Best val accuracy: 76.7%

## Why Current Model Underperforms

### Root Cause Analysis
1. **Class imbalance:** No DR (388 samples) vs Severe NPDR (53 samples) — 7:1 ratio
2. **Insufficient epochs:** 30 epochs may not be enough for convergence
3. **No label smoothing:** Hard labels cause overconfident predictions
4. **No test-time augmentation:** Single-pass inference leaves accuracy on the table
5. **Learning rate may be too low:** 1e-4 with AdamW is conservative for transfer learning

### What the Classification Report Shows
```
No DR:           F1=0.97 (388 samples) — excellent
Mild NPDR:       F1=0.54 (78 samples) — weak
Moderate NPDR:   F1=0.67 (227 samples) — decent
Severe NPDR:     F1=0.43 (53 samples) — poor
Proliferative:   F1=0.42 (69 samples) — poor
```
The model is great at "No DR" but fails on the clinically important stages.

---

## Task 1: Improve Class Balancing (Day 1, 1-2 hours)

### What to Change
File: `src/models/train.py`

#### 1a. Increase class weights for minority classes

Current `compute_class_weights` function uses inverse frequency. The weights are too mild. Multiply them by an additional factor for severe classes:

```python
# In compute_class_weights(), after computing base weights:
def compute_class_weights(labels, severity_boost=2.0):
    counts = np.bincount(labels, minlength=NUM_CLASSES).astype(np.float64)
    weights = len(labels) / (NUM_CLASSES * np.maximum(counts, 1))
    weights = weights / weights.mean()
    # Extra boost for underrepresented severe classes
    boost = np.ones(NUM_CLASSES, dtype=np.float64)
    boost[3] = severity_boost   # Severe NPDR
    boost[4] = severity_boost   # Proliferative DR
    weights = weights * boost
    weights = weights / weights.mean()  # re-normalize
    return torch.tensor(weights, dtype=torch.float32)
```

#### 1b. Add severity_boost parameter to make_loaders

Update `make_loaders` to pass severity_boost:

```python
def make_loaders(args, severity_boost=2.0):
    # ... existing code ...
    class_weights = compute_class_weights(labels[train_idx], severity_boost=severity_boost)
    # ... rest unchanged ...
```

### Validation
After this change, the class weights printed during training should show Severe NPDR and Proliferative DR with ~2x the weight of other classes.

---

## Task 2: Add Label Smoothing (Day 1, 30 minutes)

### What to Change
File: `src/models/train.py`

#### 2a. Modify FocalLoss to support label smoothing

```python
class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0, label_smoothing=0.0):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.label_smoothing = label_smoothing

    def forward(self, logits, targets):
        num_classes = logits.size(-1)
        if self.label_smoothing > 0:
            with torch.no_grad():
                smooth = torch.full_like(logits, self.label_smoothing / (num_classes - 1))
                smooth.scatter_(1, targets.unsqueeze(1), 1.0 - self.label_smoothing)
            log_probs = F.log_softmax(logits, dim=-1)
            loss = -(smooth * log_probs).sum(dim=-1)
            pt = torch.exp(-loss)
            focal = (1 - pt) ** self.gamma * loss
        else:
            ce = F.cross_entropy(logits, targets, weight=self.alpha, reduction="none")
            pt = torch.exp(-ce)
            focal = (1 - pt) ** self.gamma * ce
        return focal.mean()
```

#### 2b. Use label_smoothing=0.1 in training

In `train_classification()`:
```python
criterion = FocalLoss(
    alpha=class_weights.to(device),
    gamma=2.0,
    label_smoothing=0.1  # NEW
)
```

### Why
Label smoothing prevents the model from becoming overconfident on the majority class ("No DR") and encourages it to learn better representations for minority classes.

---

## Task 3: Increase Training Epochs (Day 1, 5 minutes)

### What to Change
File: `src/models/train.py`, in `main()`:

```python
if args.mode == "classification":
    args.epochs = args.epochs or 50  # Was 30
```

Also update the default in `train_classification`:
```python
# In train_classification, the default comes from args, which defaults to 50
```

### Why
30 epochs with cosine annealing may not reach the optimal point. 50 epochs gives the model more time to converge, especially for the minority classes.

---

## Task 4: Tune Learning Rate Schedule (Day 1, 30 minutes)

### What to Change
File: `src/models/train.py`

#### 4a. Use OneCycleLR instead of CosineAnnealing

OneCycleLR often converges faster and better than CosineAnnealing for transfer learning:

```python
# In train_classification(), replace scheduler line:
# OLD: scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
# NEW:
scheduler = torch.optim.lr_scheduler.OneCycleLR(
    optimizer,
    max_lr=args.lr * 10,  # Peak LR is 10x base
    epochs=args.epochs,
    steps_per_epoch=len(train_loader),
    pct_start=0.3,  # Warmup for 30% of training
)
```

**Important:** OneCycleLR requires stepping per batch, not per epoch. Add `scheduler.step()` inside the training loop:

```python
for imgs, labels, _ in pbar:
    # ... forward pass, loss, backward ...
    scaler.step(optimizer)
    scaler.update()
    scheduler.step()  # ADD THIS inside the batch loop
    running_loss += loss.item()
```

Remove the `scheduler.step()` that was after the epoch loop.

#### 4b. Increase base learning rate slightly

```python
if args.mode == "classification":
    args.epochs = args.epochs or 50
    args.batch_size = args.batch_size or 16
    args.lr = args.lr or 2e-4  # Was 1e-4, doubled for OneCycleLR peak
```

### Why
OneCycleLR with warmup is designed for transfer learning. The 10x peak LR helps escape local minima in the early training phase.

---

## Task 5: Add Test-Time Augmentation (Day 2, 1 hour)

### What to Change
File: `src/inference/predictor.py`

#### 5a. Add TTA to the `_classify` method

```python
def _classify_tta(self, input_tensor, n_augments=4):
    """Average predictions over augmented versions of the input."""
    import albumentations as A
    import cv2

    base = input_tensor[0]  # (3, 512, 512) CHW

    # Generate augmented versions
    augmented_tensors = [input_tensor]  # original

    # Horizontal flip
    flipped = torch.flip(base, dims=[2])  # flip W
    augmented_tensors.append(flipped.unsqueeze(0))

    # Vertical flip
    vflipped = torch.flip(base, dims=[1])  # flip H
    augmented_tensors.append(vflipped.unsqueeze(0))

    # Both flips
    both = torch.flip(base, dims=[1, 2])
    augmented_tensors.append(both.unsqueeze(0))

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
```

#### 5b. Update predict() to use TTA

In `predict()` method, change:
```python
# OLD:
classification = self._classify(input_tensor) if self.classifier else None
# NEW:
classification = self._classify_tta(input_tensor) if self.classifier else None
```

### Why
TTA typically adds 2-4% accuracy at the cost of 4x inference time. For a demo, this trade-off is worth it.

---

## Task 6: Run Training (Day 1 evening → Day 2 morning)

### Command
```bash
cd /home/siddhesh/Desktop/Draft_confidential
source venv/bin/activate

# Run training with all improvements
python -m src.models.train \
    --mode classification \
    --epochs 50 \
    --batch_size 16 \
    --lr 2e-4
```

### Expected Timeline
- Training starts: Day 1, ~8 PM
- Training completes: Day 2, ~6 AM (estimate: ~8-10 hours for 50 epochs)
- Evaluation: Day 2, 7 AM

### Monitor Training
Watch for:
- `val_acc` should be steadily increasing
- If `val_acc` plateaus below 80% after 30 epochs, the improvements aren't enough
- If `val_acc` exceeds 82% by epoch 30, you're on track

---

## Task 7: Evaluate Results (Day 2, 1 hour)

### Run Evaluation
After training completes, the model saves to `models/classification/best_classifier.pth`.

#### 7a. Check the training summary
```bash
cat models/classification/training_summary.json
```
Should show `best_val_accuracy` ≥ 0.82.

#### 7b. Check the classification report
```bash
cat models/classification/classification_report.txt
```
Look for:
- Overall accuracy ≥ 82%
- Severe NPDR F1 ≥ 0.55
- Proliferative DR F1 ≥ 0.55

#### 7c. Visual check — confusion matrix
```bash
# The confusion matrix is saved as models/classification/confusion_matrix.png
# Open it and verify:
# - Diagonal should be dominant (correct predictions)
# - Off-diagonal errors should be between adjacent stages (e.g., Stage 2↔3, not Stage 0↔4)
```

### If Results Are Below Target

**Attempt 2:** Increase severity_boost to 3.0 and label_smoothing to 0.15:
```python
# In make_loaders call:
class_weights = compute_class_weights(labels[train_idx], severity_boost=3.0)

# In FocalLoss:
label_smoothing=0.15
```
Re-train with 50 epochs.

**Attempt 3 (last resort):** Try a larger model — EfficientNet-B3:
```python
# In src/models/classifier.py:
from torchvision.models import efficientnet_b3, EfficientNet_B3_Weights
# Change backbone to efficientnet_b3
# Reduce head: Dropout(0.3) → Linear(1280, 256) → ReLU → Dropout(0.2) → Linear(256, 5)
```
Train for 40 epochs (larger model, slower training).

---

## Task 8: Export Updated Model (Day 2, 30 minutes)

### Command
```bash
cd /home/siddhesh/Desktop/Draft_confidential
source venv/bin/activate

# Export to ONNX
python -m src.export.onnx_export --skip-segmenter
```

### Verify
```bash
# Check ONNX file exists and has reasonable size
ls -lh models/onnx/classifier.onnx
# Should be ~30-50 MB for EfficientNet-B2
```

---

## Go/No-Go Criteria

| Metric | Target | Minimum Acceptable |
|---|---|---|
| Val accuracy | 85% | 82% |
| Severe NPDR F1 | 0.60 | 0.55 |
| Proliferative DR F1 | 0.60 | 0.55 |
| Training completed without errors | Yes | Yes |

**If minimum acceptable not met after 3 attempts:** Move to Day 3 with current best model. The external validation story is more important than squeezing out a few more percentage points.

---

## Files Modified
- `src/models/train.py` — class weights, label smoothing, OneCycleLR, 50 epochs
- `src/models/classifier.py` — possibly B3 upgrade (attempt 3 only)
- `src/inference/predictor.py` — TTA in _classify

## Files Generated
- `models/classification/best_classifier.pth` — updated model
- `models/classification/training_summary.json` — metrics
- `models/classification/classification_report.txt` — per-class report
- `models/classification/confusion_matrix.png` — visual
- `models/onnx/classifier.onnx` — exported model
