"""
Generate a clinical validation report PDF.
Uses ReportLab for PDF generation.
"""
import json
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

METRICS_DIR = PROJECT_ROOT / "hackathon_sprint" / "metrics"
OUTPUT_DIR = PROJECT_ROOT / "hackathon_sprint"

# Colors
BRAND_DARK = colors.HexColor("#22301f")
BRAND_ACCENT = colors.HexColor("#3e8a6c")
OK_GREEN = colors.HexColor("#4a9377")
WARN_AMBER = colors.HexColor("#8f6a24")
DANGER_RED = colors.HexColor("#bf4b3e")
MUTED = colors.HexColor("#6b6b60")
LINE = colors.HexColor("#d8d5c9")


def build_report(metrics):
    """Build the clinical report PDF."""
    buf = str(OUTPUT_DIR / "clinical_validation_report.pdf")
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=14*mm, bottomMargin=12*mm,
                            leftMargin=18*mm, rightMargin=18*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"], fontSize=22,
                                 textColor=BRAND_DARK, alignment=TA_CENTER, spaceAfter=4)
    subtitle = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10,
                              textColor=MUTED, alignment=TA_CENTER, spaceAfter=20)
    section = ParagraphStyle("section", parent=styles["Heading2"], fontSize=13,
                             textColor=BRAND_ACCENT, spaceBefore=16, spaceAfter=8)
    body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10,
                          leading=14, textColor=colors.HexColor("#333330"))
    metric_large = ParagraphStyle("metric", parent=styles["Normal"], fontSize=28,
                                  textColor=BRAND_DARK, alignment=TA_CENTER, fontName="Helvetica-Bold")
    metric_label = ParagraphStyle("mlabel", parent=styles["Normal"], fontSize=9,
                                  textColor=MUTED, alignment=TA_CENTER)

    story = []

    # Title
    story.append(Paragraph("RetinaScan AI", title_style))
    story.append(Paragraph("Clinical Validation Report — External Dataset", subtitle))
    story.append(Spacer(1, 8*mm))

    # Key Metrics Cards
    acc = metrics.get("accuracy", 0)
    ci = metrics.get("accuracy_95ci", (0, 0))
    ref = metrics.get("referable_dr", {})
    sens = ref.get("sensitivity", 0)
    sens_ci = ref.get("sensitivity_95ci", (0, 0))
    spec = ref.get("specificity", 0)
    auc = ref.get("auc", 0)

    story.append(Paragraph("Key Performance Indicators", section))

    kpi_data = [
        [
            Paragraph(f"{acc:.1%}", metric_large),
            Paragraph(f"{sens:.1%}", metric_large),
            Paragraph(f"{spec:.1%}", metric_large),
            Paragraph(f"{auc:.3f}" if auc else "N/A", metric_large),
        ],
        [
            Paragraph("Overall Accuracy", metric_label),
            Paragraph("Referable DR Sensitivity", metric_label),
            Paragraph("Referable DR Specificity", metric_label),
            Paragraph("AUC (Referable DR)", metric_label),
        ],
        [
            Paragraph(f"95% CI: {ci[0]:.1%} – {ci[1]:.1%}", metric_label),
            Paragraph(f"95% CI: {sens_ci[0]:.1%} – {sens_ci[1]:.1%}", metric_label),
            Paragraph("", metric_label),
            Paragraph("", metric_label),
        ],
    ]

    kpi_table = Table(kpi_data, colWidths=[42*mm]*4)
    kpi_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (0, -1), 0.5, LINE),
        ('BOX', (1, 0), (1, -1), 0.5, LINE),
        ('BOX', (2, 0), (2, -1), 0.5, LINE),
        ('BOX', (3, 0), (3, -1), 0.5, LINE),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
    ]))
    story.append(kpi_table)
    story.append(Spacer(1, 10*mm))

    # Dataset Info
    story.append(Paragraph("Dataset", section))
    n_total = metrics.get("total_images", 0)
    n_eval = metrics.get("evaluated", 0)
    n_rej = metrics.get("rejected_by_iqa", 0)
    story.append(Paragraph(
        f"<b>External dataset:</b> APTOS 2019 Blindness Detection (Indian diabetic retinopathy dataset)<br/>"
        f"<b>Total images:</b> {n_total} (all unseen during model training)<br/>"
        f"<b>Evaluated:</b> {n_eval} | <b>Rejected by IQA:</b> {n_rej} ({metrics.get('rejection_rate', 0):.1%})<br/>"
        f"<b>Model:</b> EfficientNet-B2 (ONNX Runtime, CPU)<br/>"
        f"<b>Preprocessing:</b> CLAHE → green channel → pupil-centered crop → 512×512",
        body
    ))
    story.append(Spacer(1, 8*mm))

    # Per-Class Metrics
    story.append(Paragraph("Per-Class Performance", section))
    per_class = metrics.get("per_class", {})
    cls_header = ["Class", "Precision", "Recall", "F1", "Support"]
    cls_rows = [cls_header]
    for cls_name in ["No DR", "Mild NPDR", "Moderate NPDR", "Severe NPDR", "Proliferative DR"]:
        if cls_name in per_class:
            c = per_class[cls_name]
            cls_rows.append([
                cls_name,
                f"{c['precision']:.3f}",
                f"{c['recall']:.3f}",
                f"{c['f1']:.3f}",
                str(int(c['support'])),
            ])

    cls_table = Table(cls_rows, colWidths=[40*mm, 28*mm, 28*mm, 28*mm, 28*mm])
    cls_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f0ede6")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, LINE),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(cls_table)
    story.append(Spacer(1, 8*mm))

    # Confusion Matrix
    story.append(Paragraph("Confusion Matrix", section))
    cm = metrics.get("confusion_matrix", [])
    if cm:
        from src.constants import CLASS_NAMES as _CN
        short_names = ["No DR", "Mild", "Mod", "Sev", "PDR"]
        cm_header = ["True \\ Pred"] + short_names
        cm_rows = [cm_header]
        for i, row in enumerate(cm):
            cm_rows.append([short_names[i]] + [str(int(v)) for v in row])

        cm_table = Table(cm_rows, colWidths=[30*mm] + [24*mm]*5)
        cm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f0ede6")),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f0ede6")),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.4, LINE),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(cm_table)

    story.append(Spacer(1, 8*mm))

    # Clinical Significance
    story.append(Paragraph("Clinical Significance", section))
    story.append(Paragraph(
        f"This validation demonstrates that RetinaScan AI achieves <b>{sens:.1%} sensitivity</b> "
        f"for detecting referable diabetic retinopathy (ICDR Stage ≥ 2) on an external dataset "
        f"of <b>{n_eval} unseen images</b>. "
        f"At the operating point of {spec:.1%} specificity, the system would correctly identify "
        f"approximately {sens:.0%} of patients requiring ophthalmologist referral while "
        f"flagging only {1-spec:.0%} false positives for manual review.",
        body
    ))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(
        "These results support the use of RetinaScan AI as a <b>screening triage tool</b> "
        "in settings with limited ophthalmologist availability, particularly in rural and "
        "underserved communities where diabetic retinopathy screening coverage is lowest.",
        body
    ))

    # Disclaimer
    story.append(Spacer(1, 12*mm))
    story.append(Paragraph(
        "<i>This report was generated by an automated validation pipeline. "
        "Results are on a single external dataset and do not constitute clinical validation "
        "for regulatory purposes. Further multi-site, prospective studies are required.</i>",
        ParagraphStyle("disc", parent=body, fontSize=8, textColor=MUTED)
    ))

    doc.build(story)
    print(f"Report saved to {buf}")
    return buf


def main():
    metrics_path = METRICS_DIR / "external_validation.json"
    if not metrics_path.exists():
        print(f"ERROR: {metrics_path} not found. Run external_validation.py first.")
        return

    with open(metrics_path) as f:
        metrics = json.load(f)

    build_report(metrics)


if __name__ == "__main__":
    main()
