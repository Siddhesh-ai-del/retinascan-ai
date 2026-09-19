# Day 3: External Validation & Clinical Metrics

## Completed
- [x] External validation script (APTOS 2019 dataset)
- [x] Bootstrap confidence intervals (1000 iterations)
- [x] Referable DR detection metrics (sensitivity, specificity, AUC)
- [x] Confusion matrix visualization
- [x] Clinical report PDF generator (ReportLab)

## External Validation Setup
- **Dataset**: APTOS 2019 (3,662 images, NEVER seen during training)
- **Task**: Validate generalization to unseen data
- **Metrics**: Accuracy, per-class F1, referable DR sensitivity/specificity/AUC

## Clinical Metrics Computed
1. **Overall Accuracy** with 95% CI
2. **Per-Class Metrics**: Precision, Recall, F1 for each DR stage
3. **Referable DR Detection** (Stage ≥ 2):
   - Sensitivity (true positive rate)
   - Specificity (true negative rate)
   - PPV (positive predictive value)
   - NPV (negative predictive value)
   - AUC-ROC
4. **Inference Latency**: Mean, P95, P99

## Clinical Report PDF
- KPI dashboard with key metrics
- Per-class performance breakdown
- Confusion matrix heatmap
- Recommendations for clinical use

## Files Created
- `scripts/external_validation.py` - Full validation pipeline
- `scripts/generate_clinical_report.py` - PDF report generator
- `hackathon_sprint/metrics/external_validation.json` - Raw metrics
- `hackathon_sprint/metrics/external_validation.txt` - Human-readable report
