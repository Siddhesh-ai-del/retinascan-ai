# Day 8: Presentation (PPT) + Demo Video

## Deadline
- **Day 8 morning:** Build PPT slides
- **Day 8 afternoon:** Record demo video
- **STOP when:** PPT is complete AND demo video is recorded

## Goal
A 10-12 slide presentation that tells a compelling story: Problem → Solution → Results → Impact.

---

## Slide Structure

### Slide 1: Title
```
RetinaScan AI
Automated Diabetic Retinopathy Screening
[Your Names] | [Hackathon Name] | [Date]
```
- Clean, minimal design
- Eye-catching logo or fundus image as background (faded)

### Slide 2: The Problem
```
463 million people have diabetes.
1 in 3 will develop diabetic retinopathy.
But there are only 200,000 ophthalmologists worldwide.
```
- Big numbers, small text
- Use a world map or icon visual
- Key stat: "80% of preventable blindness is in low-income countries"

### Slide 3: The Gap
```
Current screening: Manual grading by ophthalmologists
→ Slow (50 patients/day per doctor)
→ Expensive ($50-100 per screening)
→ Inaccessible in rural areas

What if AI could help?
```
- Before/after visual
- Show the bottleneck

### Slide 4: Our Solution
```
RetinaScan AI: From fundus photo to clinical report in 5 seconds

Upload → Quality Check → Classify → Segment → Report
```
- Pipeline diagram (clean, horizontal arrows)
- Mention: ICDR 5-stage classification, FHIR R4, referral urgency

### Slide 5: Live Demo (or Demo Video)
```
[SCREEN RECORDING: Upload image → See results → Batch mode → PDF report]
```
- Record a 60-90 second screen capture
- Show: single image analysis, batch mode, PDF download
- Have a backup video in case live demo fails

### Slide 6: How It Works (Architecture)
```
┌─────────────┐    ┌──────────────┐    ┌────────────┐
│  Quality     │ →  │  Preprocess  │ →  │  Classify  │
│  Gate (IQA) │    │  CLAHE→Crop  │    │  EffNet-B2 │
└─────────────┘    └──────────────┘    └────────────┘
                                              │
                    ┌──────────────┐    ┌──────┴─────┐
                    │  FHIR R4     │ ←  │  Segment   │
                    │  Report      │    │  U-Net     │
                    └──────────────┘    └────────────┘
```
- Clean architecture diagram
- Mention: ONNX Runtime, FastAPI, React

### Slide 7: Results — Before/After
```
Before (Baseline)          After (Optimized)
─────────────────          ─────────────────
Accuracy: 76.7%      →     Accuracy: XX.X%
Severe F1: 0.43      →     Severe F1: 0.XX
No external data     →     Validated on 3,662 unseen images
```
- Two-column comparison
- Green arrows showing improvement
- Big bold numbers

### Slide 8: External Validation
```
Validated on APTOS 2019 dataset
(3,662 images — NEVER seen during training)

Overall Accuracy:  XX.X% (95% CI: XX.X–XX.X%)
Referable DR Sensitivity:  XX.X% (95% CI: XX.X–XX.X%)
Referable DR Specificity:  XX.X%
AUC:  X.XXXX
```
- Include the confusion matrix image
- Include the per-class F1 bar chart
- This is your strongest slide

### Slide 9: Safety & Clinical Integration
```
✓ Image Quality Gate — rejects ungradable images
✓ Abstention Logic — flags uncertain cases for human review
✓ Referral Urgency — maps ICDR stage to clinical action
✓ FHIR R4 — interoperable with hospital systems
✓ SNOMED CT coded — standard medical terminology
```
- Checkmark list
- Show a screenshot of the FHIR JSON

### Slide 10: Impact
```
What this could mean:

Screening capacity: 50 → 500 patients/day per clinic
Cost per screening: $50 → $2 (compute cost)
Time to result: 3 days → 5 seconds
Reach: Urban hospitals → Rural health camps

In India alone: 77 million diabetics, < 20,000 retinal specialists
```
- Big impact numbers
- Map showing underserved regions

### Slide 11: Tech Stack
```
Backend:    FastAPI + Python
Models:     EfficientNet-B2 + U-Net (ResNet18)
Export:     ONNX Runtime (CPU/GPU)
Frontend:   React 19 + Axios
Database:   SQLite (visit history)
Standards:  HL7 FHIR R4, SNOMED CT, LOINC
Training:   IDRiD + APTOS datasets, PyTorch
```
- Clean tech stack visual
- Logos of key technologies

### Slide 12: Future / What's Next
```
Phase 1 (Done):    AI screening prototype + clinical report
Phase 2 (Next):    Multi-language UI (Hindi, Marathi, Tamil)
Phase 3:           Mobile-first PWA for rural health camps
Phase 4:           Regulatory pathway (CDSCO / FDA clearance)
Phase 5:           EHR integration via SMART on FHIR
```
- Roadmap visual
- Show ambition but stay grounded

---

## PPT Design Guidelines

### Colors
- Primary: #3e8a6c (green — medical trust)
- Accent: #647fbe (blue — technology)
- Danger: #bf4b3e (red — urgency)
- Background: #f6f3ec (warm paper)
- Text: #33322d (dark ink)

### Fonts
- Titles: DM Serif Display (or Georgia)
- Body: DM Sans (or system sans-serif)
- Code/metrics: Consolas or monospace

### Layout Rules
- **Maximum 6 lines of text per slide**
- **One idea per slide**
- **No code in slides** (only architecture diagrams)
- **Big numbers** — metrics in 48-72pt font
- **Consistent alignment** — left-aligned text, centered metrics
- **Use images** — fundus photos, charts, pipeline diagrams

---

## Task 1: Record Demo Video (2 hours)

### Setup
```bash
# Start the demo
bash start_demo.sh
# Open http://localhost:3000 in Chrome
```

### Recording Script (60-90 seconds)
1. **[0-5s]** Show the landing page — "RetinaScan AI"
2. **[5-15s]** Upload moderate_npdr.jpg — show the drag-and-drop
3. **[15-25s]** Quality check passes → AI analysis runs
4. **[25-40s]** Results page — show the ICDR grade, confidence bars
5. **[40-50s]** Scroll down — show lesion overlay, legend
6. **[50-60s]** Click "How It Works" tab — show the pipeline
7. **[60-70s]** Click "Batch Mode" — upload 3-4 images
8. **[70-80s]** Show the batch results table
9. **[80-90s]** Download PDF — show the report

### Recording Tool
```bash
# Option 1: OBS Studio (best quality)
# Option 2: Chrome DevTools (Record tab)
# Option 3: Simple: ffmpeg screen capture
ffmpeg -f x11grab -video_size 1920x1080 -i :0.0 -t 90 -c:v libx264 demo_video.mp4
```

### Tips
- **Record at 1080p** — PPT will look crisp
- **Slow down** — don't rush through the demo
- **Narrate** — record voiceover explaining what's happening
- **Have a backup** — save the video file in `hackathon_sprint/demo_video.mp4`

---

## Task 2: Build PPT (3 hours)

### Option A: Use python-pptx (code-generated)

```python
# Create: scripts/create_ppt.py
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Helper function
def add_text(slide, left, top, width, height, text, font_size=18,
             bold=False, color=RGBColor(0x33, 0x32, 0x2d), alignment=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(font_size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = alignment
    return tf

# Slide 1: Title
slide = prs.slides.add_slide(prs.slide_layouts[6])  # Blank
add_text(slide, 1, 2, 11, 1.5, "RetinaScan AI", 48, True,
         RGBColor(0x3e, 0x8a, 0x6c), PP_ALIGN.CENTER)
add_text(slide, 1, 3.5, 11, 1, "Automated Diabetic Retinopathy Screening", 24, False,
         RGBColor(0x33, 0x32, 0x2d), PP_ALIGN.CENTER)
add_text(slide, 1, 5, 11, 0.5, "[Your Names] | [Hackathon] | [Date]", 14, False,
         RGBColor(0x8b, 0x86, 0x7a), PP_ALIGN.CENTER)

# ... add remaining slides ...

prs.save(str(output_path))
```

### Option B: Use Google Slides / PowerPoint manually
- Use the slide structure above
- Copy metrics from `hackathon_sprint/metrics/`
- Use screenshots from the demo

---

## Go/No-Go Criteria

| Check | Status |
|---|---|
| PPT has 10-12 slides | Required |
| Slide 7 shows before/after metrics | Required |
| Slide 8 shows external validation | Required |
| Demo video recorded (60-90s) | Required |
| Demo video saved in hackathon_sprint/ | Required |
| PPT is presentable (no typos, consistent design) | Required |
| Backup video ready for live demo failure | Required |
