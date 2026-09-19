# Buffer Day: Contingency Plan

## When to Use This
Use this plan if you're behind schedule on any day. Pick the task that gives the most hackathon value.

---

## Priority 1: If Model Training Failed (Day 1-2 behind)

### Quick Fix: Use the original model + better presentation
Don't waste time retraining. Instead:

1. **Add TTA to the existing model** (1 hour)
   - Edit `src/inference/predictor.py` — add the TTA code from `01_DAY_MODEL_TRAINING.md`
   - This gives +2-3% accuracy without retraining

2. **Focus on the validation story** (rest of the day)
   - Run external validation on the original model
   - Even 76.7% accuracy with proper clinical metrics is impressive
   - "We validated our model on 3,662 unseen images" is the real story

---

## Priority 2: If External Validation Failed (Day 3-4 behind)

### Quick Fix: Use a smaller subset
- Instead of all 3,662 images, validate on 500 images
- Run faster, get results quicker
- Still statistically meaningful

```python
# In external_validation.py, add after load_aptos_data():
import random
random.seed(42)
samples = random.sample(samples, min(500, len(samples)))
```

---

## Priority 3: If PPT Isn't Done (Day 8 behind)

### Minimum Viable PPT (2 hours)

6 slides only:
1. Title
2. Problem (big numbers)
3. Solution (pipeline diagram)
4. Results (before/after + validation)
5. Demo (screenshots)
6. Impact + Future

Use `python-pptx` to generate it programmatically from `06_DAY_PPT.md`.

---

## Priority 4: If Demo Video Isn't Done (Day 8 behind)

### Quick Alternative: Screenshots
- Take 5 screenshots of the demo
- Create a GIF using:
```bash
# Install ffmpeg if needed
sudo apt install ffmpeg

# Create a slideshow GIF from screenshots
ffmpeg -framerate 1 -i hackathon_sprint/screenshots/slide_%d.png \
  -vf "scale=1280:-1" hackathon_sprint/demo_slideshow.gif
```

---

## Priority 5: If Nothing Works

### Last Resort: API-Only Demo
If the frontend is broken, demo using `curl`:
```bash
# This always works and shows the full pipeline
curl -s -X POST http://localhost:8000/api/predict \
  -F "file=@demo_images/moderate_npdr.jpg" \
  -F "patient_id=demo" | python -m json.tool
```

Have a terminal open and run this during the demo. Show the JSON output. Judges will understand.

---

## Time Allocation (If Starting from Scratch)

| Task | Time | Can Skip? |
|---|---|---|
| Model training | 6-8 hours | No — but can use original model |
| External validation | 3-4 hours | No — this is the core story |
| Clinical report | 2-3 hours | No — needed for PPT |
| Segmenter polish | 2-3 hours | Yes — skip if behind |
| Batch triage feature | 3-4 hours | Yes — skip if behind |
| PPT | 3-4 hours | No — but can make 6 slides |
| Demo video | 1-2 hours | Yes — use screenshots |
| Polish | 2-3 hours | Partially — do critical tests only |

---

## The 80/20 Rule for Hackathons

**80% of the impact comes from:**
1. A working demo (any demo)
2. One compelling metric ("87% sensitivity on 3,662 unseen images")
3. A clear story (Problem → Solution → Results → Impact)

**20% that's nice but not essential:**
- Perfect model accuracy
- Segmenter quality
- Batch mode
- PDF reports
- FHIR compliance
- Mobile responsiveness

If you're behind, focus on the 80%. A working demo with one great metric beats a perfect system that's not ready.
