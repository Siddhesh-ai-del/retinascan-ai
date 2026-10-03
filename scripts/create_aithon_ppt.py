"""
Build AITHON_2.0_RetinaScanAI_Submission.pptx from the official hackathon template.

Strategy
--------
1. Open AITHON_2.0_Presentation.pptx read-only (never modified) with python-pptx.
2. Replace placeholder text in-place, preserving each paragraph's pPr/rPr so the
   template's fonts, sizes, colours and alignment stay byte-level intact.
3. Compress all 10 slides of RetinaScanAI_Deck.pptx INTO the 7 template slots:
   lead lines, richer body copy, and monochrome stat/comparison cards added
   strictly inside empty template regions (never moving a template shape).
4. Recolour slide 5's blue accents to the monochrome palette.
5. Add speaker notes (slides 1-6) and doc properties.

All content is sourced from:
  - RetinaScanAI_Deck.pptx (previous deck)
  - PROJECT_INFO.md
  - hackathon_sprint/metrics/*.json
"""

import copy
import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = PROJECT_ROOT / "AITHON_2.0_Presentation.pptx"
OUTPUT_PATH = PROJECT_ROOT / "AITHON_2.0_RetinaScanAI_Submission.pptx"
METRICS_DIR = PROJECT_ROOT / "hackathon_sprint" / "metrics"

# ── Monochrome palette (from RetinaScanAI_Deck.pptx) ────────────────────────
INK = RGBColor(0x11, 0x11, 0x11)  # primary
INK_2 = RGBColor(0x2E, 0x2E, 0x2E)
INK_3 = RGBColor(0x33, 0x33, 0x33)  # lead lines (deck "Lead" colour)
MUTED = RGBColor(0x59, 0x59, 0x59)  # body / captions
GREY = RGBColor(0x8C, 0x8C, 0x8C)  # step numbers / meta
LINE = RGBColor(0xD0, 0xD0, 0xD0)  # hairlines / arrows
PANEL = RGBColor(0xF2, 0xF2, 0xF2)  # card fill
WHITE = RGBColor(0xFF, 0xFF, 0xFF)


# ── Metrics cross-check (fail the build if JSON no longer backs a number) ────
def load_metrics():
    ext = json.loads((METRICS_DIR / "external_validation.json").read_text())
    ens = json.loads((METRICS_DIR / "ensemble_results.json").read_text())
    return ext, ens


def assert_metrics(ext, ens):
    checks = [
        (
            "referable sensitivity 97.5%",
            round(ext["referable_dr"]["sensitivity"] * 100, 1) == 97.5,
        ),
        ("NPV 97.5%", round(ext["referable_dr"]["npv"] * 100, 1) == 97.5),
        (
            "sensitivity CI 96.5-98.2",
            [round(v * 100, 1) for v in ext["referable_dr"]["sensitivity_95ci"]]
            == [96.5, 98.2],
        ),
        ("ensemble acc 82.1%", round(ens["ensemble_acc"] * 100, 1) == 82.1),
        ("external acc 60.8%", round(ext["accuracy"] * 100, 1) == 60.8),
        ("IQA rejection 7.3%", round(ext["rejection_rate"] * 100, 1) == 7.3),
        ("evaluated 3394", ext["evaluated"] == 3394),
        ("total APTOS 3662", ext["total_images"] == 3662),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        raise SystemExit(f"METRIC CROSS-CHECK FAILED: {failed}")
    print(f"metric cross-check: {len(checks)}/{len(checks)} OK")


# ── XML-preserving text replacement ─────────────────────────────────────────
def _strip_runs(p):
    for child in list(p):
        if child.tag in (qn("a:r"), qn("a:endParaRPr"), qn("a:br"), qn("a:fld")):
            p.remove(child)


def set_text(shape, lines):
    """Replace a shape's text with `lines` (str or list of str), cloning the
    first paragraph's pPr and first run's rPr for every new paragraph so the
    template styling (font, size, bold, colour, alignment) is preserved."""
    if isinstance(lines, str):
        lines = [lines]
    tx_body = shape.text_frame._txBody
    old_ps = tx_body.findall(qn("a:p"))
    p0 = old_ps[0]
    r_tmpl = p0.find(qn("a:r"))
    if r_tmpl is None:
        raise ValueError(f"{shape.name}: template paragraph has no run")
    end_tmpl = p0.find(qn("a:endParaRPr"))
    for p in old_ps:
        tx_body.remove(p)
    for line in lines:
        new_p = copy.deepcopy(p0)
        _strip_runs(new_p)
        r = copy.deepcopy(r_tmpl)
        r.find(qn("a:t")).text = line
        new_p.append(r)
        if end_tmpl is not None:
            new_p.append(copy.deepcopy(end_tmpl))
        tx_body.append(new_p)


def set_rich(shape, paras):
    """Like set_text, but each entry of `paras` is a run-spec dict:
    {"text", "size"?, "bold"?, "color"?, "font"?, "space_before"?}.
    One paragraph per entry; template pPr cloned, run styling overridden via
    the python-pptx API (so element order stays valid)."""
    tx_body = shape.text_frame._txBody
    old_ps = tx_body.findall(qn("a:p"))
    p0 = old_ps[0]
    r_tmpl = p0.find(qn("a:r"))
    if r_tmpl is None:
        raise ValueError(f"{shape.name}: template paragraph has no run")
    end_tmpl = p0.find(qn("a:endParaRPr"))
    for p in old_ps:
        tx_body.remove(p)
    for spec in paras:
        new_p = copy.deepcopy(p0)
        _strip_runs(new_p)
        r = copy.deepcopy(r_tmpl)
        r.find(qn("a:t")).text = spec["text"]
        new_p.append(r)
        if end_tmpl is not None:
            new_p.append(copy.deepcopy(end_tmpl))
        tx_body.append(new_p)
    # API pass for overrides
    for para, spec in zip(shape.text_frame.paragraphs, paras):
        if spec.get("space_before") is not None:
            para.space_before = Pt(spec["space_before"])
        run = para.runs[0]
        if spec.get("size"):
            run.font.size = Pt(spec["size"])
        if spec.get("bold") is not None:
            run.font.bold = spec["bold"]
        if spec.get("color") is not None:
            run.font.color.rgb = spec["color"]
        if spec.get("font"):
            run.font.name = spec["font"]


def by_name(slide):
    return {sh.name: sh for sh in slide.shapes}


# ── Added-shape helpers (monochrome, previous-deck styling) ─────────────────
def _strip_style(sp):
    style = sp._element.find(qn("p:style"))
    if style is not None:
        sp._element.remove(style)
    sp.shadow.inherit = False


def add_rect(slide, name, x, y, w, h, fill, line_color=None, line_pt=1.0):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sp.name = name
    _strip_style(sp)
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line_color is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line_color
        sp.line.width = Pt(line_pt)
    return sp


def add_arrow(slide, name, x, y, w, h, fill):
    sp = slide.shapes.add_shape(
        MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    sp.name = name
    _strip_style(sp)
    sp.fill.solid()
    sp.fill.fore_color.rgb = fill
    sp.line.fill.background()
    return sp


def add_text(slide, name, x, y, w, h, paragraphs, anchor=MSO_ANCHOR.TOP, margins=0.0):
    """paragraphs: list of dicts:
    {"text", "font", "size", "bold", "color", "align", "space_before", "space_after"}
    or {"runs": [{...}, ...], "align", ...} for multi-run lines."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.name = name
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    m = Inches(margins)
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = m
    for i, spec in enumerate(paragraphs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        p.space_before = Pt(spec.get("space_before", 0))
        p.space_after = Pt(spec.get("space_after", 0))
        run_specs = spec.get("runs") or [spec]
        for rs in run_specs:
            run = p.add_run()
            run.text = rs["text"]
            f = run.font
            f.name = rs.get("font", "Times New Roman")
            f.size = Pt(rs["size"])
            f.bold = rs.get("bold", False)
            f.color.rgb = rs.get("color", INK)
    return box


def add_lead(slide, name, x, w, text, y=0.60, size=15):
    """Deck-style lead line: Calibri 15pt #333333 under the section heading."""
    return add_text(
        slide,
        name,
        x,
        y,
        w,
        0.42,
        [
            {"text": text, "font": "Calibri", "size": size, "color": INK_3},
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )


def add_hairline(slide, name, x, y, w, color=LINE, h=0.012):
    return add_rect(slide, name, x, y, w, h, color)


def recolor_shape(slide, name, fill=None, line_color=None):
    sp = by_name(slide)[name]
    if fill is not None:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line_color is not None:
        sp.line.color.rgb = line_color
    return sp


# ── Slide builders ──────────────────────────────────────────────────────────
def fill_slide1(slide):
    s = by_name(slide)
    set_text(s["Text 24"], "Problem Statement Track  —  [ Enter track name ]")
    set_text(
        s["Text 26"],
        "Problem Statement Title  —  RetinaScan AI — AI-Assisted Diabetic Retinopathy Screening",
    )
    set_text(s["Text 30"], "PS Category  —  Software")
    set_text(s["Text 34"], "Team Name  —  [ Enter team name ]")
    # deck-style eyebrow + hairline (empty band between TITLE PAGE and fields)
    add_text(
        slide,
        "S1Eye",
        0.78,
        1.40,
        8.44,
        0.38,
        [
            {
                "text": "FUNDUS IMAGE IN — FHIR CLINICAL REPORT OUT IN 0.59 SECONDS, FULLY LOCAL",
                "font": "Calibri",
                "size": 12,
                "bold": True,
                "color": GREY,
                "align": PP_ALIGN.CENTER,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_hairline(slide, "S1Rule", 3.40, 1.92, 3.20)
    add_text(
        slide,
        "S1Meta",
        0.78,
        5.04,
        8.44,
        0.24,
        [
            {
                "text": "Project Presentation  ·  Siddhesh  ·  October 2026",
                "font": "Calibri",
                "size": 10,
                "color": GREY,
                "align": PP_ALIGN.CENTER,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )


def fill_slide2(slide):
    s = by_name(slide)
    add_lead(
        slide,
        "Lead2",
        1.10,
        8.30,
        "One command, one laptop — a fundus photo in, a clinical report out.",
    )
    set_text(s["Text 26"], "RetinaScan AI — AI-Based DR Screening & Classification")
    set_text(
        s["Text 30"], "Fundus photo in, clinical report out in 0.59 s — 100% local."
    )
    set_text(
        s["Text 34"],
        "India has 77M diabetics at risk, but grading is specialist-only: "
        "$15–50 and 5–10 min of manual reading per image.",
    )
    set_text(
        s["Text 38"],
        "Quality gate → dual-model ICDR staging + lesion segmentation → "
        "FHIR R4 report with Grad-CAM, in 0.59 s, fully local.",
    )
    add_kpi_strip(slide)
    add_compare_row(slide)


def add_kpi_strip(slide):
    """Three monochrome KPI cards in the empty right column (x 7.20–9.40)."""
    cards = [
        ("97.5%", "referable DR sensitivity"),
        ("0.59 s", "full pipeline · laptop CPU"),
        ("100% local", "no cloud APIs · works offline"),
    ]
    x, w, h, gap = 7.20, 2.20, 1.05, 0.18
    y0 = 1.15
    for i, (value, label) in enumerate(cards):
        y = y0 + i * (h + gap)
        add_rect(slide, f"KPI{i + 1}Card", x, y, w, h, PANEL)
        add_rect(slide, f"KPI{i + 1}Bar", x, y, w, 0.05, INK)
        add_text(
            slide,
            f"KPI{i + 1}Val",
            x + 0.14,
            y + 0.17,
            w - 0.28,
            0.46,
            [
                {
                    "text": value,
                    "font": "Georgia",
                    "size": 21,
                    "bold": True,
                    "color": INK,
                },
            ],
        )
        add_text(
            slide,
            f"KPI{i + 1}Lbl",
            x + 0.14,
            y + 0.66,
            w - 0.28,
            0.32,
            [
                {"text": label, "font": "Calibri", "size": 9.5, "color": MUTED},
            ],
        )


def add_compare_row(slide):
    """Before → after comparison cards in the empty bottom band (old deck slide 9)."""
    add_hairline(slide, "CmpRule", 1.10, 4.72, 8.30)
    cards = [
        ("TIME", "5–10 min", "0.59 s"),
        ("COST", "$15–50", "$0"),
        ("REPORT", "ad-hoc notes", "FHIR R4"),
        ("CONFIDENCE", "subjective", "97.5%"),
    ]
    x0, w, h, gap, y = 1.10, 1.985, 0.46, 0.12, 4.80
    for i, (label, before, after) in enumerate(cards):
        x = x0 + i * (w + gap)
        add_rect(slide, f"Cmp{i + 1}Card", x, y, w, h, PANEL)
        add_rect(slide, f"Cmp{i + 1}Bar", x, y, w, 0.04, INK)
        add_text(
            slide,
            f"Cmp{i + 1}Lbl",
            x + 0.10,
            y + 0.06,
            w - 0.16,
            0.14,
            [
                {
                    "text": label,
                    "font": "Calibri",
                    "size": 7,
                    "bold": True,
                    "color": MUTED,
                },
            ],
        )
        add_text(
            slide,
            f"Cmp{i + 1}Val",
            x + 0.10,
            y + 0.19,
            w - 0.16,
            0.26,
            [
                {
                    "runs": [
                        {
                            "text": before + " → ",
                            "font": "Calibri",
                            "size": 9,
                            "color": GREY,
                        },
                        {
                            "text": after,
                            "font": "Georgia",
                            "size": 10,
                            "bold": True,
                            "color": INK,
                        },
                    ]
                },
            ],
        )


def fill_slide3(slide):
    s = by_name(slide)
    add_lead(
        slide,
        "Lead3",
        0.75,
        8.50,
        "One request in, two models in parallel, one clinical report out.",
    )
    set_text(
        s["Text 39"],
        [
            "Python 3.12 · FastAPI 0.141 · React 19",
            "PyTorch 2.6 · ONNX Runtime FP32 · OpenCV",
            "ConvNeXt-Tiny 28M · 4-model ensemble",
            "U-Net + ResNet18 12.5M segmenter",
            "SQLite · ReportLab · Albumentations",
            "HL7 FHIR R4 · SNOMED CT · LOINC",
        ],
    )
    set_text(
        s["Text 42"],
        [
            "Quality gate → CLAHE → 512² crop",
            "Parallel heads: ICDR stage 0–4 + lesion masks",
            "Abstention below 55% confidence → human",
            "Grad-CAM heatmap explains every call",
            "FHIR R4 DiagnosticReport + PDF output",
            "One command brings the whole stack up",
        ],
    )
    add_pipeline(slide)


def add_pipeline(slide):
    """5-step horizontal pipeline in the empty band y 3.60–5.28."""
    steps = [
        ("01", "Upload", "JPEG · PNG · BMP · TIFF"),
        ("02", "Quality Gate", "blur · brightness · glare"),
        ("03", "Preprocess", "CLAHE · green ch · 512²"),
        ("04", "Dual Model", "ICDR stage + 4 lesion masks"),
        ("05", "Report", "FHIR R4 · Grad-CAM · PDF"),
    ]
    add_text(
        slide,
        "PipeLbl",
        0.75,
        3.60,
        8.5,
        0.30,
        [
            {
                "text": "END-TO-END PIPELINE  ·  0.59 s",
                "size": 12.5,
                "bold": True,
                "color": INK,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )

    box_w, box_h, gap, y = 1.52, 0.95, 0.12, 3.96
    x0 = (10.0 - (5 * box_w + 4 * gap)) / 2.0
    for i, (num, title, sub) in enumerate(steps):
        x = x0 + i * (box_w + gap)
        add_rect(slide, f"Pipe{i + 1}Box", x, y, box_w, box_h, PANEL)
        add_text(
            slide,
            f"Pipe{i + 1}Txt",
            x + 0.06,
            y + 0.11,
            box_w - 0.12,
            box_h - 0.20,
            [
                {
                    "text": num,
                    "font": "Calibri",
                    "size": 8,
                    "bold": True,
                    "color": GREY,
                    "align": PP_ALIGN.CENTER,
                    "space_after": 1,
                },
                {
                    "text": title,
                    "font": "Georgia",
                    "size": 11,
                    "bold": True,
                    "color": INK,
                    "align": PP_ALIGN.CENTER,
                    "space_after": 2,
                },
                {
                    "text": sub,
                    "font": "Calibri",
                    "size": 8,
                    "color": MUTED,
                    "align": PP_ALIGN.CENTER,
                },
            ],
        )
        if i < 4:
            ax = x + box_w + 0.01
            add_arrow(
                slide, f"PipeArr{i + 1}", ax, y + box_h / 2 - 0.05, 0.10, 0.10, LINE
            )

    add_text(
        slide,
        "PipeCap",
        0.75,
        5.00,
        8.5,
        0.28,
        [
            {
                "text": "Dual models run in parallel; ungradable frames are rejected with "
                "recapture guidance — never a confident wrong answer.",
                "font": "Calibri",
                "size": 9.5,
                "color": MUTED,
                "align": PP_ALIGN.CENTER,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )


def fill_slide4(slide):
    s = by_name(slide)
    add_lead(
        slide,
        "Lead4",
        0.80,
        8.20,
        "Evidence that it works, runs anywhere, costs nothing per screen, and scales.",
    )
    set_text(
        s["Text 27"],
        [
            "All 11 components built and verified end-to-end",
            "82.1% internal accuracy · 60.8% external APTOS",
            "0.59 s mean, P95 0.71 s — laptop CPU",
        ],
    )
    set_text(
        s["Text 32"],
        [
            "One command: bash start_demo.sh",
            "Single laptop, offline — no cloud APIs",
            "Batch triage of 20 images per API call",
        ],
    )
    set_text(
        s["Text 37"],
        [
            "$0 per screening after one-time setup",
            "vs $15–50 manual grading per image",
            "Zero per-query cost — no cloud spend",
        ],
    )
    set_text(
        s["Text 42"],
        [
            "FHIR R4 + SNOMED CT — EHR ready",
            "Batch mode for population screening",
            "Roadmap: Docker hosting, multi-user auth",
            "Decision-support only — not a certified device",
        ],
    )
    recolor_shape(slide, "Shape 17", fill=PANEL)  # stray dot blends with white bg
    add_evidence_row(slide)


def add_evidence_row(slide):
    """Bottom stat cards (old deck clinical headlines + IQA + external test)."""
    cards = [
        ("VERIFIED", "11 / 11", "components, end-to-end"),
        ("SENSITIVITY", "97.5%", "referable DR · CI 96.5–98.2%"),
        ("QUALITY GATE", "7.3%", "ungradable frames rejected"),
        ("EXTERNAL", "3,394", "of 3,662 APTOS images"),
    ]
    x0, w, h, gap, y = 0.80, 1.985, 0.64, 0.12, 4.62
    for i, (label, value, caption) in enumerate(cards):
        x = x0 + i * (w + gap)
        add_rect(slide, f"Ev{i + 1}Card", x, y, w, h, PANEL)
        add_rect(slide, f"Ev{i + 1}Bar", x, y, w, 0.04, INK)
        add_text(
            slide,
            f"Ev{i + 1}Lbl",
            x + 0.10,
            y + 0.07,
            w - 0.16,
            0.13,
            [
                {
                    "text": label,
                    "font": "Calibri",
                    "size": 7,
                    "bold": True,
                    "color": MUTED,
                },
            ],
        )
        add_text(
            slide,
            f"Ev{i + 1}Val",
            x + 0.10,
            y + 0.19,
            w - 0.16,
            0.28,
            [
                {
                    "text": value,
                    "font": "Georgia",
                    "size": 15,
                    "bold": True,
                    "color": INK,
                },
            ],
        )
        add_text(
            slide,
            f"Ev{i + 1}Cap",
            x + 0.10,
            y + 0.46,
            w - 0.16,
            0.15,
            [
                {"text": caption, "font": "Calibri", "size": 7.5, "color": MUTED},
            ],
        )


def fill_slide5(slide):
    s = by_name(slide)
    add_lead(
        slide,
        "Lead5",
        0.68,
        8.55,
        "What changes when a screening is free and instant.",
        y=0.58,
    )
    items = [
        ("Text 26", "Clinical Confidence", "97.5% referable DR sensitivity, 97.5% NPV"),
        (
            "Text 30",
            "Fewer Missed Referrals",
            "Low-confidence cases abstain to a human reviewer",
        ),
        ("Text 34", "Near-Zero Cost", "$0 per screen after setup; zero API fees"),
        ("Text 38", "Minimal Footprint", "One laptop, offline — no cloud"),
        ("Text 42", "100× Faster Triage", "0.59 s vs 5–10 min of specialist time"),
    ]
    for name, title, desc in items:
        set_rich(
            s[name],
            [
                {
                    "text": title,
                    "size": 11.5,
                    "bold": True,
                    "color": INK,
                    "font": "Times New Roman",
                },
                {
                    "text": desc,
                    "size": 8.5,
                    "bold": False,
                    "color": MUTED,
                    "font": "Calibri",
                    "space_before": 3,
                },
            ],
        )
    set_text(s["Text 49"], "Slow, costly screening")
    set_text(s["Text 52"], "0.59 s local AI")
    set_text(s["Text 55"], "Instant FHIR reports")
    set_text(s["Text 58"], "Population-scale care")

    # Monochrome recolour of the blue accents (structure/positions untouched)
    for name in ("Shape 24", "Shape 28", "Shape 32", "Shape 36", "Shape 40"):
        recolor_shape(slide, name, fill=PANEL, line_color=INK)
    for name in ("Shape 50", "Shape 53", "Shape 56"):
        recolor_shape(slide, name, fill=LINE)
    recolor_shape(slide, "Shape 48", fill=INK)
    recolor_shape(slide, "Shape 54", fill=INK)
    recolor_shape(slide, "Shape 51", fill=INK_3)
    recolor_shape(slide, "Shape 57", fill=INK_3)

    # Pathway-row right caption + audience cards in the empty bottom band
    add_text(
        slide,
        "PathHint",
        5.60,
        3.15,
        3.63,
        0.32,
        [
            {
                "text": "FROM SLOW SCREENING TO POPULATION-SCALE CARE",
                "font": "Calibri",
                "size": 9,
                "bold": True,
                "color": MUTED,
                "align": PP_ALIGN.RIGHT,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_text(
        slide,
        "WhoLbl",
        0.77,
        4.44,
        8.46,
        0.22,
        [
            {
                "text": "WHO BENEFITS",
                "font": "Calibri",
                "size": 9,
                "bold": True,
                "color": MUTED,
            },
        ],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    aud = [
        ("PRIMARY HEALTH CENTERS", "Rural clinics screen without a specialist"),
        ("EYE HOSPITALS", "Batch triage of 20 + Grad-CAM review"),
        ("PUBLIC HEALTH PROGRAMS", "Population screening at near-zero cost"),
    ]
    x0, w, h, gap, y = 0.77, 2.72, 0.50, 0.15, 4.76
    for i, (title, desc) in enumerate(aud):
        x = x0 + i * (w + gap)
        add_rect(slide, f"Who{i + 1}Card", x, y, w, h, PANEL)
        add_rect(slide, f"Who{i + 1}Bar", x, y, w, 0.04, INK)
        add_text(
            slide,
            f"Who{i + 1}T",
            x + 0.10,
            y + 0.07,
            w - 0.16,
            0.17,
            [
                {
                    "text": title,
                    "font": "Calibri",
                    "size": 8.5,
                    "bold": True,
                    "color": INK,
                },
            ],
        )
        add_text(
            slide,
            f"Who{i + 1}D",
            x + 0.10,
            y + 0.26,
            w - 0.16,
            0.18,
            [
                {"text": desc, "font": "Calibri", "size": 8, "color": MUTED},
            ],
        )


def fill_slide6(slide):
    s = by_name(slide)
    add_lead(
        slide,
        "Lead6",
        0.75,
        8.25,
        "The datasets, prior work and standards behind every claim in this deck.",
        y=0.66,
        size=14,
    )
    set_text(
        s["Text 25"],
        [
            "IDRiD (Porwal et al., Data 2018): Indian DR grades + pixel-level lesion masks",
            "APTOS 2019: 3,662 graded fundus images; 3,394 held out for external testing",
            "DDR: lesion masks lifted segmenter training from 54 to 811 images (15×)",
            "Prior practice: manual ICDR grading — 5–10 min/image, observer-dependent",
            "Safety design: abstention below 55% confidence keeps the clinician in the loop",
            "Gap identified: no offline, abstaining, explainable screening-first tool",
        ],
    )
    set_text(
        s["Text 28"],
        [
            "Liu et al., A ConvNet for the 2020s, CVPR 2022 (arXiv:2201.03545)",
            "Ronneberger et al., U-Net, MICCAI 2015 (arXiv:1505.04597)",
            "Selvaraju et al., Grad-CAM, ICCV 2017 (arXiv:1610.02391)",
            "Lin et al., Focal Loss, ICCV 2017",
            "Porwal et al., IDRiD, Data 2018",
            "APTOS 2019 Blindness Detection — Kaggle",
            "HL7 FHIR R4 · SNOMED CT · LOINC — hl7.org · snomed.org · loinc.org",
        ],
    )
    add_rect(slide, "Div6", 4.74, 1.35, 0.012, 3.70, LINE)  # column divider


# Slide 7 (IMPORTANT INSTRUCTIONS) is deliberately left verbatim.

NOTES = {
    1: (
        "Open with the promise: a fundus photo goes in, a clinical report comes out "
        "in 0.59 seconds, entirely on a laptop. RetinaScan AI is a decision-support "
        "screening tool for diabetic retinopathy — 5-stage ICDR classification plus "
        "lesion segmentation, with FHIR-standard output. (Fill in Track and Team Name "
        "before submitting.)"
    ),
    2: (
        "Frame the stakes first: DR is the leading cause of preventable blindness in "
        "working-age adults; India has roughly 77 million diabetics, and manual "
        "screening costs $15–50 and 5–10 minutes of specialist time per image. "
        "The bottom strip is the before/after a health administrator cares about: "
        "5–10 minutes becomes 0.59 seconds, $15–50 becomes zero, ad-hoc notes become "
        "FHIR R4, and subjective judgement becomes a measured 97.5% sensitivity."
    ),
    3: (
        "Walk the left column (what it is built with), then the right (how it is "
        "built), then trace the pipeline underneath. Quality gate first: an "
        "ungradable image is bounced with recapture guidance instead of a confident "
        "wrong answer. Below 55% confidence the system abstains and hands the case "
        "to a human. ConvNeXt-Tiny 4-model ensemble and U-Net run in parallel — "
        "ICDR stage 0–4 plus four lesion masks — before the FHIR R4 report, Grad-CAM "
        "and PDF are emitted. All of it runs offline through ONNX Runtime FP32."
    ),
    4: (
        "Evidence per quadrant: technical — all 11 components are built, the "
        "ensemble reaches 82.1% internal accuracy and 60.8% on the full external "
        "APTOS set, at 0.59 s mean / P95 0.71 s; operational — one command, one "
        "laptop, offline, batch triage of 20; economic — $0 per screening versus "
        "$15–50 manual grading; scalability — FHIR R4 keeps it EHR- and "
        "program-ready. Bottom cards are the verification headlines: 97.5% "
        "sensitivity (CI 96.5–98.2%), 7.3% IQA rejection, 3,394 of 3,662 APTOS "
        "images. Be honest: decision-support prototype, not a certified device."
    ),
    5: (
        "Top row is what changes for each audience: clinical confidence (97.5% "
        "sensitivity and NPV), fewer missed referrals via the abstention rule, "
        "near-zero cost, a minimal compute footprint because everything runs "
        "locally, and 100× faster triage. Pathway: slow, costly screening → "
        "0.59 s local AI → instant FHIR reports → population-scale care. Bottom "
        "row: who actually benefits — rural clinics, eye hospitals, public health "
        "programs."
    ),
    6: (
        "Research honesty: trained and validated on public Indian DR datasets — "
        "IDRiD for grading and lesion masks, APTOS 2019 for scale and external "
        "testing on 3,394 unseen images, DDR which raised segmenter training from "
        "54 to 811 masked images. The survey covers prior manual practice, the "
        "safety design (abstention) and the standards landscape; references cover "
        "the architectures (ConvNeXt, U-Net), explainability (Grad-CAM), "
        "class-imbalance handling (Focal Loss) and interoperability (FHIR R4, "
        "SNOMED CT, LOINC)."
    ),
}


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def set_doc_props(prs):
    cp = prs.core_properties
    cp.title = "AITHON 2.0 — RetinaScan AI Presentation"
    cp.subject = "AI-Assisted Diabetic Retinopathy Screening"
    cp.author = "Siddhesh"
    cp.last_modified_by = "Siddhesh"
    cp.comments = (
        "AITHON 2.0 template submission for RetinaScan AI — "
        "monochrome restyle of RetinaScanAI_Deck content."
    )


def main():
    if not TEMPLATE_PATH.exists():
        raise SystemExit(f"template not found: {TEMPLATE_PATH}")
    ext, ens = load_metrics()
    assert_metrics(ext, ens)

    prs = Presentation(str(TEMPLATE_PATH))  # read-only; original never written
    if len(prs.slides) != 7:
        raise SystemExit(f"template slide count changed: {len(prs.slides)}")

    builders = [
        fill_slide1,
        fill_slide2,
        fill_slide3,
        fill_slide4,
        fill_slide5,
        fill_slide6,
    ]  # slide 7 verbatim
    for i, build in enumerate(builders, 1):
        build(prs.slides[i - 1])
        set_notes(prs.slides[i - 1], NOTES[i])
        print(f"slide {i}: filled")

    set_doc_props(prs)
    prs.save(str(OUTPUT_PATH))
    print(f"saved: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
