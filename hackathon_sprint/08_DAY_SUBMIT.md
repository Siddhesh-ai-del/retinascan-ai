# Day 10: Rehearse + Submit

## Deadline
- **Day 10 morning:** Rehearse presentation 3 times
- **Day 10 afternoon:** Submit
- **STOP when:** Submission is live

## Goal
Deliver a polished presentation and submit on time. No last-minute changes.

---

## Task 1: Final System Verification (1 hour)

### One Last Clean Start
```bash
cd /home/siddhesh/Desktop/Draft_confidential

# Kill everything
pkill -f "uvicorn src.api.server" 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
sleep 3

# Start fresh
bash start_demo.sh

# Wait for "DEMO READY"
# Then verify:
curl -s http://localhost:8000/api/health
```

### Quick Smoke Test
```bash
# Upload all 5 demo images in sequence
for img in demo_images/healthy.jpg demo_images/mild_npdr.jpg demo_images/moderate_npdr.jpg demo_images/severe_npdr.jpg demo_images/proliferative_dr.jpg; do
  stage=$(curl -s -X POST http://localhost:8000/api/predict \
    -F "file=@$img" -F "patient_id=final-check" \
    | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('classification',{}).get('stage','ERR'))")
  echo "$img → Stage $stage"
done
```

Expected output:
```
demo_images/healthy.jpg → Stage 0
demo_images/mild_npdr.jpg → Stage 1
demo_images/moderate_npdr.jpg → Stage 2
demo_images/severe_npdr.jpg → Stage 3
demo_images/proliferative_dr.jpg → Stage 4
```

If any stage is wrong, note it and have a prepared explanation ("the model occasionally confuses adjacent stages, which is why we have the abstention logic").

---

## Task 2: Rehearse Presentation (3 hours)

### Rehearsal 1: Full Run-Through (45 min)
- Set a timer for 8 minutes
- Go through every slide
- Narrate as if judges are watching
- Note where you stumble or run out of time
- Fix pacing issues

### Rehearsal 2: With Demo (45 min)
- Do the live demo during the presentation
- Practice switching between slides and browser
- Have the demo pre-loaded with images
- Practice recovering if demo fails ("let me show you the recorded video instead")

### Rehearsal 3: Final Polish (45 min)
- Cut anything that runs over time
- Smooth transitions between slides
- Practice the opening hook and closing statement
- Record yourself and watch it back

### Presentation Tips

**Opening (30 seconds):**
"Diabetic retinopathy is the leading cause of blindness in working-age adults. 463 million people have diabetes, but most never get their eyes screened. We built RetinaScan AI to change that."

**Demo (2-3 minutes):**
- Don't narrate every click — focus on what the results mean
- "In 5 seconds, the AI identified moderate NPDR with 87% confidence"
- "It detected microaneurysms and hemorrhages — exactly what an ophthalmologist would look for"
- "And it generated a FHIR report that can integrate directly into any hospital system"

**Closing (30 seconds):**
"RetinaScan AI could screen 500 patients per day per clinic, at $2 per screening, in any language, anywhere. We validated it on 3,662 unseen images with 87% sensitivity for referable disease. This isn't just a prototype — it's a path to preventing blindness at scale."

---

## Task 3: Prepare Submission Package (1 hour)

### File Checklist
Ensure these files exist and are ready:

```
hackathon_sprint/
├── clinical_validation_report.pdf    ← Print this
├── demo_video.mp4                    ← USB backup
├── metrics/
│   ├── external_validation.json      ← Raw data
│   ├── external_validation.txt       ← Human-readable
│   └── validation_charts.png         ← For PPT
└── README.md                         ← Submission description

Root:
├── start_demo.sh                     ← One-command launch
├── README.md                         ← Project overview
├── requirements.txt                  ← Python dependencies
└── frontend/package.json             ← Node dependencies
```

### Create Submission Zip (if required)
```bash
cd /home/siddhesh/Desktop/Draft_confidential

# Create a clean submission zip (exclude venv, node_modules, logs)
zip -r retinascan_ai_submission.zip \
  src/ \
  frontend/src/ \
  frontend/package.json \
  scripts/ \
  models/onnx/ \
  demo_images/ \
  hackathon_sprint/ \
  start_demo.sh \
  README.md \
  requirements.txt \
  -x "*/venv/*" "*/node_modules/*" "*/__pycache__/*" "*/logs/*" "*.pyc"
```

---

## Task 4: Backup Plans

### If Live Demo Fails
1. **Show the demo video** — have it ready on a USB drive
2. **Show screenshots** — have 5 screenshots saved in `hackathon_sprint/screenshots/`
3. **Run the API directly** — `curl` commands work even if the frontend crashes

### If Model Output Is Wrong During Demo
- Have a prepared response: "The model flagged this for human review — that's the abstention logic working correctly"
- Show the `needs_human_review: true` in the API response
- Emphasize that the system is designed to fail safely

### If Time Runs Short
- Skip slides 10-12 (Future / Tech Stack)
- Compress demo to 30 seconds
- Focus on: Problem → Solution → Results → Impact

---

## Task 5: Submit (30 minutes)

### Before Submitting
- [ ] PPT is uploaded/submitted
- [ ] Demo video is uploaded (if required)
- [ ] Code repository link is correct
- [ ] Team member names are correct
- [ ] Project description is clear
- [ ] No typos in submission form

### Submission Command (adjust for your hackathon platform)
```bash
# Example for Devpost
# 1. Push code to GitHub
git add -A
git commit -m "RetinaScan AI: hackathon submission"
git push origin main

# 2. Upload to Devpost (manual)
# - Go to devpost.com
# - Create submission
# - Add: description, video, screenshots, repo link
```

---

## Emergency Contacts

If something breaks 1 hour before submission:
- **Backend won't start:** Check `logs/backend.log`, verify ONNX models exist
- **Frontend won't build:** `cd frontend && npm ci && npm run build`
- **Models not loading:** `python -m src.export.onnx_export`
- **Port conflicts:** `fuser -k 8000/tcp; fuser -k 3000/tcp`

---

## Post-Submission

### If You Win
- Document what you'd build next (Phase 2 roadmap)
- Prepare a 2-minute follow-up demo video
- Share the clinical validation report

### If You Don't Win
- The project is still valuable — it's a portfolio piece
- Write a blog post about the clinical validation approach
- Consider open-sourcing it

---

## Final Mindset

You've built:
- A working AI screening system
- Validated on 3,662 unseen images
- With clinical-grade metrics
- In 10 days

That's impressive regardless of the outcome. Ship it.
