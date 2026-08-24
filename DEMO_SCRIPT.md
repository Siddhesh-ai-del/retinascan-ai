# 90-Second Demo Script — RetinaScan AI

**Pre-flight (before judges arrive):**
```bash
bash start_demo.sh        # waits for "DEMO READY"
```
Browser on http://localhost:3000 · window maximized · `demo_images/` folder pinned in the file manager.

---

| Time | Action | What to say |
|---|---|---|
| 0:00–0:10 | **Screening tab** → drop `blurry_ungradable.jpg` | "Real screening starts before any AI diagnosis — watch the system refuse this image." |
| 0:10–0:20 | Point at rejection card | "Blur, brightness, glare and fundus-likelihood checks. A selfie gets rejected the same way — the model can never hallucinate a diagnosis from a bad image." *(if asked, demo it live with your webcam photo)* |
| 0:20–0:40 | Drop `moderate_npdr.jpg` | "Now a genuine grade-2 fundus… quality gate passed, classified Moderate NPDR at 85% confidence, and the segmenter localized the lesions — red microaneurysms, orange hemorrhages, yellow exudates." |
| 0:40–0:55 | **Toggle lesion layers** in the legend | "Each lesion type is independently visualized so an ophthalmologist can audit exactly why the AI decided what it did." |
| 0:55–1:10 | Scroll to referral card → open **FHIR JSON** | "Referral guidance follows ICDR protocol — refer within 4 weeks. And this is a standards-compliant HL7 FHIR R4 DiagnosticReport with SNOMED CT coding — it plugs into any hospital information system, ABDM-ready." |
| 1:10–1:20 | **Download .json**, then switch to **Batch Mode** tab | "One command deployment, batch screening for camps…" *(drop 3–4 images if time allows — table sorts by severity)* |
| 1:20–1:30 | Open **How It Works** tab | "Everything runs locally on a laptop GPU in under half a second — no cloud dependency for patient data. Built on IDRiD and APTOS, 4,000+ real fundus images." |

## Q&A ammunition

| Likely question | Answer |
|---|---|
| "How accurate?" | 76.7% validation accuracy across 5 classes; No DR class F1 is 0.97. Full breakdown in METRICS.md. Rare stages are harder due to imbalance — that's where referral guidance errs on the safe side. |
| "What about garbage input?" | IQA gate rejects blurry/dark/non-fundus images *before* inference — demonstrated live above. |
| "Does it need internet/GPU?" | No. ONNX models run CPU-only in <0.5s; designed for offline eye camps. |
| "Why FHIR?" | SNOMED-coded DiagnosticReport is the interoperability standard for ABDM/HIS integration. |
| "Segmentation quality?" | Dice 0.21 on only 81 annotated images; EX/HE localize reliably, MA/CWS sparse. Roadmap: DDR dataset + patch-based training. |

## Edge-case arsenal (if judges push)

- Selfie / random photo → rejected: *"does not appear to be a retinal fundus image"*
- All-black or all-white frame → rejected (brightness)
- Low-res image → rejected (resolution floor)
