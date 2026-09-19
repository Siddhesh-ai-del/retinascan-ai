# Day 9: Polish Everything

## Deadline
- **Day 9 full day:** Fix all rough edges, test everything
- **STOP when:** Every item on the checklist passes

## Goal
Make the demo bulletproof. No crashes, no errors, no embarrassing moments.

---

## Task 1: Full System Test (2 hours)

### Start Fresh
```bash
cd /home/siddhesh/Desktop/Draft_confidential
# Kill everything
pkill -f "uvicorn src.api.server" 2>/dev/null
fuser -k 3000/tcp 2>/dev/null
sleep 2

# Start clean
bash start_demo.sh
```

### Test Script
Run through every scenario and check off:

```bash
# 1. Health check
curl -s http://localhost:8000/api/health
# Expected: {"status":"ok","models_loaded":true}

# 2. Single image — healthy
curl -s -X POST http://localhost:8000/api/predict \
  -F "file=@demo_images/healthy.jpg" -F "patient_id=test-001" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}, Stage: {d[\"classification\"][\"stage\"]}')"
# Expected: Stage 0

# 3. Single image — moderate NPDR
curl -s -X POST http://localhost:8000/api/predict \
  -F "file=@demo_images/moderate_npdr.jpg" -F "patient_id=test-002" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}, Stage: {d[\"classification\"][\"stage\"]}')"
# Expected: Stage 2

# 4. Quality rejection
curl -s -X POST http://localhost:8000/api/assess-quality \
  -F "file=@demo_images/blurry_ungradable.jpg" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(f'Gradable: {d[\"gradable\"]}, Issues: {d[\"quality_issues\"]}')"
# Expected: Gradable: False

# 5. Invalid file type
curl -s -X POST http://localhost:8000/api/predict \
  -F "file=@requirements.txt;filename=test.txt" \
  | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail', d))"
# Expected: 415 error

# 6. Demo images list
curl -s http://localhost:8000/api/demo-images
# Expected: list of images

# 7. FHIR report
curl -s http://localhost:8000/api/fhir/test-001
# Expected: valid FHIR DiagnosticReport JSON

# 8. PDF report
curl -s -o /tmp/test_report.pdf http://localhost:8000/api/report/test-001.pdf
ls -lh /tmp/test_report.pdf
# Expected: PDF file exists, > 10KB
```

---

## Task 2: Frontend Testing (2 hours)

### Manual Browser Tests

Open http://localhost:3000 and test:

| # | Action | Expected Result | Pass? |
|---|---|---|---|
| 1 | Page loads without errors | No console errors | ☐ |
| 2 | Click "Screening" tab | Upload form visible | ☐ |
| 3 | Drag and drop an image | Preview appears | ☐ |
| 4 | Click "Analyze Image" | Progress spinner → results | ☐ |
| 5 | Results show ICDR stage | Grade card with confidence bars | ☐ |
| 6 | Lesion overlay visible | Colored overlays on fundus | ☐ |
| 7 | Toggle lesion checkboxes | Layers show/hide | ☐ |
| 8 | Scroll to FHIR section | JSON visible | ☐ |
| 9 | Click "View JSON" | FHIR JSON expands | ☐ |
| 10 | Click "Copy" | "Copied" confirmation | ☐ |
| 11 | Click "Download .json" | File downloads | ☐ |
| 12 | Click "Download Report (PDF)" | PDF downloads | ☐ |
| 13 | Click "How It Works" tab | Pipeline diagram visible | ☐ |
| 14 | Click "Batch Mode" tab | Batch upload visible | ☐ |
| 15 | Select 3+ images | Progress bar → results table | ☐ |
| 16 | Click "View" on a result | Individual results shown | ☐ |
| 17 | Click "Export CSV" | CSV file downloads | ☐ |
| 18 | Click "New Analysis" | Returns to upload form | ☐ |
| 19 | Enter patient ID | ID saved and used in API calls | ☐ |
| 20 | Select eye (L/R) | Eye saved and used | ☐ |

### Console Error Check
```bash
# Open Chrome DevTools → Console tab
# Upload an image and check for:
# - No red errors
# - No uncaught promise rejections
# - No CORS errors
# - No 4xx/5xx network errors
```

---

## Task 3: Edge Cases (1 hour)

### Test These Scenarios

| Scenario | Expected Behavior |
|---|---|
| Upload a 5MB image | Succeeds (limit is 10MB) |
| Upload a 15MB image | 413 error "exceeds limit" |
| Upload a .txt file | 415 error "unsupported format" |
| Upload a 100x100px image | IQA rejection "low_resolution" |
| Upload a completely black image | IQA rejection "dark" or "no_fundus_detected" |
| Upload the same image twice | Both produce same results |
| Click "Analyze" without selecting file | Button is disabled |
| Rapidly click "Analyze" multiple times | Only one request fires |
| Close browser during analysis | No server crash |
| Refresh page during analysis | State resets cleanly |

---

## Task 4: Performance Check (30 minutes)

### Backend Timing
```bash
# Time 10 sequential predictions
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" \
    -X POST http://localhost:8000/api/predict \
    -F "file=@demo_images/moderate_npdr.jpg" -F "patient_id=bench"
done
```

Target:
- Single prediction: < 3 seconds
- Health check: < 100ms
- No request > 10 seconds

### Frontend Timing
- Page load: < 3 seconds
- Tab switch: < 100ms
- Image preview: < 500ms

---

## Task 5: Visual Polish (1 hour)

### Check These Visual Elements

| Element | Check |
|---|---|
| Logo renders correctly | SVG eye icon visible |
| Font loads properly | DM Serif + DM Sans (not fallback) |
| Color scheme consistent | Green/blue/amber/red throughout |
| Buttons have hover effects | Lift + color change |
| Cards have shadows | Subtle box-shadow |
| Responsive layout | Works at 1200px and 800px width |
| Loading spinner animates | Smooth rotation |
| Error alerts styled | Red border + background |
| Warning alerts styled | Amber border + background |
| Footer text visible | "Decision support only" |

### CSS Quick Fixes
If any visual issues found, check `frontend/src/index.css`:
- Box shadows: `box-shadow: 0 1px 2px rgba(51,50,45,0.04), 0 8px 28px rgba(51,50,45,0.05);`
- Border radius: `border-radius: 10px;`
- Transitions: `transition: transform 0.08s ease, opacity 0.15s ease;`

---

## Task 6: Documentation (30 minutes)

### Update README.md

Ensure README has:
- [ ] Project description (1 paragraph)
- [ ] Screenshot of the app
- [ ] Prerequisites (Python 3.12, Node.js 20)
- [ ] Installation steps
- [ ] How to run (`bash start_demo.sh`)
- [ ] API endpoints list
- [ ] Model performance summary
- [ ] License

### Create hackathon_sprint/README.md

```markdown
# RetinaScan AI — Hackathon Submission

## Quick Start
1. `bash start_demo.sh`
2. Open http://localhost:3000
3. Upload a fundus image and click "Analyze"

## What's Included
- AI-powered DR screening (5-stage ICDR classification)
- Lesion segmentation overlay
- HL7 FHIR R4 clinical reports
- Batch screening mode
- Clinical validation report

## Model Performance
- Classifier: XX.X% accuracy on external validation (APTOS 2019, 3,662 images)
- Referable DR sensitivity: XX.X% (95% CI: XX.X–XX.X%)
- Inference time: ~XXX ms per image (CPU)

## Files
- `hackathon_sprint/clinical_validation_report.pdf` — Clinical metrics report
- `hackathon_sprint/demo_video.mp4` — Demo video
- `hackathon_sprint/metrics/` — Raw metrics data
```

---

## Final Checklist

### System
- [ ] `bash start_demo.sh` works cleanly
- [ ] Backend starts in < 10 seconds
- [ ] Frontend loads in < 3 seconds
- [ ] No console errors

### Functionality
- [ ] Single image analysis works
- [ ] Batch analysis works
- [ ] All 5 demo images produce correct stages
- [ ] IQA rejects blurry/ungradable images
- [ ] Invalid file types rejected
- [ ] PDF report downloads
- [ ] FHIR JSON valid
- [ ] CSV export works

### Visual
- [ ] No layout breaks
- [ ] Colors consistent
- [ ] Fonts loaded
- [ ] Responsive (works at 800px width)

### Documentation
- [ ] README updated
- [ ] hackathon_sprint/README.md created

### Presentation
- [ ] PPT complete (10-12 slides)
- [ ] Demo video recorded
- [ ] Backup plan for live demo failure

---

## Go/No-Go Criteria

| Metric | Target |
|---|---|
| All 20 browser tests pass | Required |
| All 9 backend tests pass | Required |
| No console errors | Required |
| Demo video ready | Required |
| PPT ready | Required |
| README updated | Required |
