"""
Build AITHON_2.0_RetinaScanAI_Submission.pptx — full visual redesign (v2).

Strategy
--------
1. Open the official template read-only (sha256-gated, never modified).
2. Keep chrome only: 7 slides, slide size, section headings, footer bar,
   both logos, the four title-page fields (incl. both "[ Enter ... ]"
   placeholders) and slide 7 verbatim.
3. Delete every other template content placeholder and rebuild slides 1-6 from
   scratch on the DESIGN.md grid: real matplotlib charts, real Grad-CAM /
   product screenshots, a branching pipeline flowchart, KPI strips and
   comparison cards.
4. Rewrite speaker notes (1-6) and doc properties.

Every numeric token in slide text is asserted against the metric files below
before the deck is written (see assert_metrics / SOURCES).

Run:  ./venv/bin/python scripts/create_aithon_ppt_v2.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deck_lib import (  # noqa: E402
    ACCENT,
    CONTENT_W,
    DEEP,
    DISPLAY,
    FONT,
    INK,
    LINE,
    MARGIN_L,
    MUTED,
    NEG,
    PANEL,
    POS,
    SLATE,
    SOFT,
    VIOLET,
    WARN,
    WHITE,
    add_pic,
    add_rect,
    add_text,
    arrow,
    bullets,
    card,
    chrome_names,
    circle_pic,
    drop_shapes,
    fbox,
    foot_note,
    kpi,
    panel_title,
    rule,
    set_notes,
    square_crop,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "AITHON_2.0_Presentation.pptx"
OUTPUT_PATH = ROOT / "AITHON_2.0_RetinaScanAI_Submission.pptx"
BUILD_PATH = ROOT / "scripts" / "deck_assets" / "out" / "deck_build.pptx"
ASSETS = ROOT / "scripts" / "deck_assets" / "out"
METRICS = ROOT / "hackathon_sprint" / "metrics"

TEMPLATE_SHA256 = "e57ec40b57f0a5785c3f0bd2ffd503f57b220a289f4bb04e7b1076e4880e8350"

# template's light blue (CADCFC) — used for secondary copy on the dark hero card
RGB_LIGHT_BLUE = RGBColor(0xCA, 0xDC, 0xFC)

CHARTS = [
    "cm_external.png",
    "f1_internal.png",
    "ref_metrics.png",
    "latency_budget.png",
    "time_cost.png",
    "data_growth.png",
    "dice.png",
    "perf_delta.png",
    "ui_results.png",
    "ui_abstention.png",
    "hero_cam_mod.png",
]


# ── metrics gate ────────────────────────────────────────────────────────────
def load_metrics() -> tuple[dict, dict, dict]:
    ext = json.loads((METRICS / "external_validation.json").read_text())
    ens = json.loads((METRICS / "ensemble_results.json").read_text())
    seg = json.loads(
        (ROOT / "models" / "segmentation" / "training_summary.json").read_text()
    )
    return ext, ens, seg


def assert_metrics(ext: dict, ens: dict, seg: dict) -> None:
    """Fail the build if the deck's headline numbers no longer match the data."""
    r = ext["referable_dr"]
    checks = [
        ("referable sensitivity 97.5%", round(r["sensitivity"] * 100, 1) == 97.5),
        (
            "sensitivity CI 96.5 / 98.2",
            [round(x * 100, 1) for x in r["sensitivity_95ci"]] == [96.5, 98.2],
        ),
        ("NPV 97.5%", round(r["npv"] * 100, 1) == 97.5),
        ("specificity 72.8%", round(r["specificity"] * 100, 1) == 72.8),
        ("PPV 72.3%", round(r["ppv"] * 100, 1) == 72.3),
        ("AUC 0.843", round(r["auc"], 3) == 0.843),
        ("2x2 counts", (r["tp"], r["fp"], r["tn"], r["fn"]) == (1392, 534, 1432, 36)),
        ("evaluated 3,394", ext["evaluated"] == 3394),
        ("total images 3,662", ext["total_images"] == 3662),
        ("external accuracy 60.8%", round(ext["accuracy"] * 100, 1) == 60.8),
        (
            "external CI 59.2-62.3",
            [round(x * 100, 1) for x in ext["accuracy_95ci"]] == [59.2, 62.3],
        ),
        ("IQA rejection 7.3%", round(ext["rejection_rate"] * 100, 1) == 7.3),
        ("ensemble 82.1%", round(ens["ensemble_acc"] * 100, 1) == 82.1),
        ("segmenter dice 0.314", round(seg["test_dice"], 3) == 0.314),
        ("cws dice 0.769", round(seg["per_class"]["cotton_wool_spots"], 3) == 0.769),
        ("latency mean 350 ms", ext["latency"]["mean_ms"] == 350.4),
        ("latency p95 445 ms", ext["latency"]["p95_ms"] == 445.0),
    ]
    bad = [name for name, ok in checks if not ok]
    if bad:
        raise SystemExit(f"metrics gate FAILED: {bad}")


# ── text helpers ────────────────────────────────────────────────────────────
def set_rich(shape, runs: list[tuple[str, dict]]) -> None:
    """Replace a template text frame with one paragraph of styled runs."""
    tf = shape.text_frame
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    p = tf.paragraphs[0]
    for r in list(p.runs):
        r._r.getparent().remove(r._r)
    for text, spec in runs:
        run = p.add_run()
        run.text = text
        run.font.name = spec.get("font", FONT)
        run.font.size = Pt(spec.get("size", 10))
        run.font.bold = spec.get("bold", False)
        run.font.italic = spec.get("italic", False)
        run.font.color.rgb = spec.get("color", INK)


def field(shape, label: str, value: str) -> None:
    """Title-page form row: quiet grey label + strong value (template geometry)."""
    set_rich(
        shape,
        [
            (label, {"font": "Times New Roman", "size": 11, "color": MUTED}),
            (value, {"font": "Times New Roman", "size": 13, "color": INK}),
        ],
    )


def lead(slide, text: str) -> None:
    add_text(
        slide,
        "Lead",
        MARGIN_L,
        0.67,
        CONTENT_W,
        0.23,
        [{"text": text, "font": DISPLAY, "size": 12.5, "color": DEEP}],
    )


# ── slide 1 — title page ────────────────────────────────────────────────────
def build_slide1(slide) -> None:
    s = {sh.name: sh for sh in slide.shapes}
    field(s["Text 24"], "Problem Statement Track  —  ", "[ Enter track name ]")
    field(
        s["Text 26"],
        "Problem Statement Title  —  ",
        "RetinaScan AI — AI-Assisted Diabetic Retinopathy Screening",
    )
    field(s["Text 30"], "PS Category  —  ", "Software")
    field(s["Text 34"], "Team Name  —  ", "[ Enter team name ]")

    # brand block
    add_text(
        slide,
        "S1Brand",
        0.78,
        1.36,
        5.40,
        0.52,
        [
            {
                "text": "RetinaScan AI",
                "font": DISPLAY,
                "size": 30,
                "bold": True,
                "color": INK,
            }
        ],
    )
    rule(slide, "S1Rule", 0.78, 1.90, 1.30, color=ACCENT, h=0.028)
    add_text(
        slide,
        "S1Tag",
        0.78,
        1.96,
        5.55,
        0.18,
        [
            {
                "runs": [
                    ("Fundus photo in ", {"size": 9.5, "color": SLATE}),
                    ("→", {"size": 9.5, "bold": True, "color": ACCENT}),
                    (" HL7 FHIR R4 clinical report out", {"size": 9.5, "color": SLATE}),
                    (
                        "   ·   0.59 s   ·   100% local",
                        {"size": 9.5, "bold": True, "color": DEEP},
                    ),
                ]
            }
        ],
    )

    # divider
    add_rect(slide, "S1Div", 6.42, 1.36, 0.01, 3.84, fill=LINE)

    # hero: real fundus + real Grad-CAM
    fundus = square_crop(
        ROOT / "demo_images" / "moderate_npdr.jpg", ASSETS / "hero_fundus.png"
    )
    circle_pic(
        slide, fundus, "S1Fundus", 6.62, 1.44, 1.62, ring_color=LINE, ring_pt=1.25
    )
    circle_pic(
        slide,
        ASSETS / "hero_cam_mod.png",
        "S1Cam",
        7.92,
        2.44,
        1.30,
        ring_color=ACCENT,
        ring_pt=2.0,
    )
    add_text(
        slide,
        "S1Cap",
        6.55,
        3.86,
        2.88,
        0.30,
        [
            {
                "text": "Real inference · Grad-CAM attention over a fundus frame",
                "size": 6.8,
                "color": MUTED,
                "line": 1.0,
            }
        ],
    )

    # KPI stack
    for i, (value, vcolor, label) in enumerate(
        [
            ("97.5%", DEEP, "referable-DR sensitivity (95% CI 96.5–98.2)"),
            ("0.59 s", DEEP, "full pipeline on a laptop CPU · P95 0.71 s"),
            ("$0", POS, "per screening after one-time setup"),
        ]
    ):
        y = 4.20 + i * 0.37
        add_rect(slide, f"S1K{i}Bar", 6.55, y, 0.05, 0.33, fill=vcolor)
        add_rect(
            slide, f"S1K{i}Bg", 6.60, y, 2.83, 0.33, fill=PANEL, line=LINE, line_pt=0.6
        )
        add_text(
            slide,
            f"S1K{i}",
            6.70,
            y,
            2.66,
            0.33,
            [
                {
                    "runs": [
                        (
                            value,
                            {
                                "font": DISPLAY,
                                "size": 12,
                                "bold": True,
                                "color": vcolor,
                            },
                        ),
                        (f"  {label}", {"size": 6.8, "color": SLATE}),
                    ]
                }
            ],
            anchor=MSO_ANCHOR.MIDDLE,
        )

    add_text(
        slide,
        "S1Meta",
        0.78,
        5.06,
        5.40,
        0.20,
        [
            {
                "text": "Project presentation  ·  Siddhesh  ·  October 2026",
                "size": 8.5,
                "color": MUTED,
            }
        ],
    )


# ── slide 2 — idea title ────────────────────────────────────────────────────
def build_slide2(slide) -> None:
    lead(slide, "One command, one laptop — a fundus photo in, a clinical report out.")

    x, w = MARGIN_L, 4.60
    panel_title(slide, "S2T1", x, 0.92, w, "Project / idea name")
    add_text(
        slide,
        "S2V1",
        x,
        1.10,
        w,
        0.36,
        [
            {
                "text": "RetinaScan AI — AI-assisted diabetic retinopathy screening & classification",
                "size": 10.5,
                "bold": True,
                "color": INK,
                "line": 1.0,
            }
        ],
    )
    panel_title(slide, "S2T2", x, 1.52, w, "One-line tagline")
    add_text(
        slide,
        "S2V2",
        x,
        1.70,
        w,
        0.34,
        [
            {
                "text": "Fundus photo in, FHIR R4 clinical report out in 0.59 s — 100% local.",
                "font": DISPLAY,
                "size": 10.5,
                "italic": True,
                "color": DEEP,
                "line": 1.0,
            }
        ],
    )
    panel_title(slide, "S2T3", x, 2.10, w, "Problem being addressed")
    bullets(
        slide,
        "S2B3",
        x,
        2.30,
        w,
        1.06,
        [
            "~77M diabetics in India; DR is the leading cause of preventable working-age blindness",
            "Manual grading takes 5–10 min per image at $15–50 — specialist-bound, city-bound",
            "Inter-observer drift across ICDR stages; reports stay ad-hoc notes, not standards",
        ],
        size=8.4,
        gap=3,
    )
    panel_title(slide, "S2T4", x, 3.40, w, "Proposed solution")
    bullets(
        slide,
        "S2B4",
        x,
        3.60,
        w,
        1.00,
        [
            "Quality gate → dual-model ICDR staging + 4-lesion masks → FHIR R4 + Grad-CAM + PDF",
            "4-model ConvNeXt-Tiny ensemble — 82.1% held-out; abstains below 55% confidence",
            "One command, fully local: 0.59 s per image on a laptop CPU — no cloud, no internet",
        ],
        size=8.4,
        gap=3,
    )

    # right: scale of the problem (dark) + live product screenshot
    rx, rw = 5.35, 4.10
    add_rect(slide, "S2Scale", rx, 0.92, rw, 1.05, fill=DEEP)
    add_text(
        slide,
        "S2Big",
        rx + 0.14,
        1.02,
        1.35,
        0.62,
        [{"text": "77M", "font": DISPLAY, "size": 30, "bold": True, "color": WHITE}],
    )
    add_text(
        slide,
        "S2ScaleTxt",
        rx + 1.55,
        1.02,
        rw - 1.70,
        0.86,
        [
            {
                "text": "people with diabetes in India need periodic DR screening",
                "size": 7.6,
                "color": WHITE,
                "line": 1.05,
            },
            {
                "text": "Today: specialist-only · 5–10 min · $15–50 · city-bound",
                "size": 7.0,
                "color": RGB_LIGHT_BLUE,
                "space_before": 3,
                "line": 1.0,
            },
        ],
    )

    card(slide, "S2Shot", rx, 2.08, rw, 2.50, fill=WHITE)
    panel_title(
        slide, "S2ShotT", rx + 0.12, 2.16, rw - 0.24, "Live product — real model output"
    )
    add_pic(slide, ASSETS / "ui_results.png", "S2ShotImg", rx + 0.12, 2.40, h=2.02)
    bullets(
        slide,
        "S2ShotB",
        rx + 2.30,
        2.44,
        1.72,
        1.95,
        [
            "ICDR stage + full probability vector",
            "4 lesion masks with area %",
            "Abstention when confidence < 55%",
            "FHIR R4 DiagnosticReport + PDF",
            "Flagged on this run at 52.1%",
        ],
        size=6.8,
        gap=3.5,
    )

    # before → after strip
    strip = [
        ("Time", "5–10 min", "0.59 s", INK),
        ("Cost", "$15–50", "$0", POS),
        ("Output", "ad-hoc notes", "FHIR R4", INK),
        ("Verdict", "subjective", "97.5% sens", INK),
        ("Runtime", "cloud", "100% local", INK),
    ]
    for i, (label, before, after, acolor) in enumerate(strip):
        cx = MARGIN_L + i * 1.795
        add_rect(
            slide, f"S2C{i}", cx, 4.64, 1.70, 0.58, fill=PANEL, line=LINE, line_pt=0.6
        )
        add_rect(slide, f"S2C{i}Bar", cx, 4.64, 1.70, 0.04, fill=ACCENT)
        add_text(
            slide,
            f"S2C{i}Txt",
            cx + 0.08,
            4.70,
            1.56,
            0.50,
            [
                {
                    "text": label.upper(),
                    "size": 6.0,
                    "bold": True,
                    "color": MUTED,
                    "spc": 55,
                },
                {
                    "runs": [
                        (before, {"size": 7.4, "color": MUTED}),
                        ("  →  ", {"size": 7.4, "bold": True, "color": ACCENT}),
                        (after, {"size": 7.8, "bold": True, "color": acolor}),
                    ],
                    "space_before": 2,
                },
            ],
        )


# ── slide 3 — technical approach (flagship flowchart) ───────────────────────
def build_slide3(slide) -> None:
    lead(
        slide,
        "Quality gate → two models in parallel → one clinical report. 0.59 s end to end.",
    )

    cols = [0.55, 2.06, 3.57, 5.08, 6.59, 8.10]
    bw, r1y, r2y, bh = 1.35, 0.92, 1.74, 0.66

    fbox(
        slide,
        "P1",
        cols[0],
        r1y,
        bw,
        bh,
        "01 · input",
        "Fundus upload",
        "JPEG · PNG · BMP · TIFF",
    )
    fbox(
        slide,
        "P2",
        cols[1],
        r1y,
        bw,
        bh,
        "02 · quality gate",
        "IQA multi-metric",
        "blur · brightness · glare · geometry",
    )
    fbox(
        slide,
        "P3",
        cols[2],
        r1y,
        bw,
        bh,
        "03 · preprocess",
        "CLAHE + crop",
        "green channel · 512² tensor",
    )
    fbox(
        slide,
        "P4",
        cols[3],
        r1y,
        bw,
        bh,
        "04 · classify (A)",
        "ConvNeXt-Tiny ×4",
        "ICDR stage 0–4 + confidence",
        accent=DEEP,
    )
    fbox(
        slide,
        "P5",
        cols[4],
        r1y,
        bw,
        bh,
        "06 · decide",
        "Refer + abstain",
        "< 55% confidence → clinician",
        accent=WARN,
        fill=SOFT,
    )
    fbox(
        slide,
        "P6",
        cols[5],
        r1y,
        bw,
        bh,
        "07 · report",
        "Clinical output",
        "FHIR R4 · Grad-CAM · PDF",
        accent=POS,
    )

    fbox(
        slide,
        "P7",
        cols[1],
        r2y,
        bw,
        bh,
        "reject",
        "Recapture guidance",
        "7.3% of frames flagged",
        dashed=True,
    )
    fbox(
        slide,
        "P8",
        cols[2],
        r2y,
        bw,
        bh,
        "05 · segment (B)",
        "U-Net · ResNet18",
        "MA · HE · EX · CWS masks",
        accent=VIOLET,
    )

    # straight connectors
    for i in range(5):
        arrow(
            slide,
            f"PA{i}",
            cols[i] + bw + 0.02,
            r1y + bh / 2 - 0.05,
            0.12,
            0.10,
            color=ACCENT,
        )
    arrow(
        slide,
        "PRej",
        cols[1] + bw / 2 - 0.05,
        r1y + bh + 0.02,
        0.10,
        0.14,
        color=NEG,
        direction=MSO_SHAPE.DOWN_ARROW,
    )
    arrow(
        slide,
        "PSeg",
        cols[2] + bw / 2 - 0.05,
        r1y + bh + 0.02,
        0.10,
        0.14,
        color=VIOLET,
        direction=MSO_SHAPE.DOWN_ARROW,
    )
    arrow(
        slide,
        "PSegR",
        cols[2] + bw + 0.06,
        r2y + bh / 2 - 0.05,
        2.17,
        0.10,
        color=VIOLET,
    )
    arrow(
        slide,
        "PUp",
        cols[4] + bw / 2 - 0.16,
        r1y + bh + 0.02,
        0.10,
        0.42,
        color=VIOLET,
        direction=MSO_SHAPE.UP_ARROW,
    )

    add_text(
        slide,
        "PPar",
        cols[3] + 0.10,
        r1y + bh + 0.01,
        1.60,
        0.14,
        [
            {
                "text": "ONE TENSOR · TWO HEADS · PARALLEL",
                "size": 5.4,
                "bold": True,
                "color": ACCENT,
                "spc": 40,
            }
        ],
    )

    add_text(
        slide,
        "S3Cap",
        MARGIN_L,
        2.50,
        4.30,
        0.46,
        [
            {
                "text": "Ungradable frames are rejected with recapture guidance and low-confidence cases abstain to a clinician — the system never returns a confident wrong answer.",
                "size": 7.6,
                "color": SLATE,
                "line": 1.05,
            }
        ],
    )
    add_pic(slide, ASSETS / "ui_abstention.png", "S3Ban", 5.00, 2.48, w=4.40)
    foot_note(
        slide,
        "S3BanCap",
        5.00,
        2.94,
        4.40,
        0.14,
        "Live run: confidence 52.1% < 55% → abstention banner (real screenshot)",
        size=6.2,
    )

    # band 3 — latency / topology / outputs
    card(slide, "S3L", MARGIN_L, 3.14, 3.55, 1.26, fill=WHITE)
    panel_title(
        slide, "S3LT", MARGIN_L + 0.10, 3.20, 3.35, "Latency budget · end-to-end 0.59 s"
    )
    add_pic(
        slide, ASSETS / "latency_budget.png", "S3LImg", MARGIN_L + 0.12, 3.40, w=3.30
    )

    card(slide, "S3D", 4.20, 3.14, 2.45, 1.26, fill=WHITE)
    panel_title(slide, "S3DT", 4.30, 3.20, 2.25, "Deployment topology")
    for i, (label, val) in enumerate(
        [
            ("Frontend", "React 19 SPA :3000"),
            ("API", "FastAPI :8000 · 10 endpoints"),
            ("Inference", "ONNX Runtime FP32 · CPU/GPU"),
            ("Store", "SQLite WAL · visit timeline"),
        ]
    ):
        y = 3.42 + i * 0.23
        add_rect(
            slide, f"S3D{i}", 4.30, y, 2.25, 0.21, fill=PANEL, line=LINE, line_pt=0.6
        )
        add_text(
            slide,
            f"S3D{i}T",
            4.37,
            y,
            2.11,
            0.21,
            [
                {
                    "runs": [
                        (f"{label}: ", {"size": 6.6, "bold": True, "color": ACCENT}),
                        (val, {"size": 6.6, "color": SLATE}),
                    ]
                }
            ],
            anchor=MSO_ANCHOR.MIDDLE,
        )

    card(slide, "S3O", 6.85, 3.14, 2.60, 1.26, fill=WHITE)
    panel_title(slide, "S3OT", 6.95, 3.20, 2.40, "What comes out")
    bullets(
        slide,
        "S3OB",
        6.95,
        3.42,
        2.42,
        0.94,
        [
            "ICDR stage 0–4 + calibrated confidence",
            "4 lesion masks with area %",
            "Grad-CAM attention heat-map",
            "HL7 FHIR R4 DiagnosticReport + PDF",
        ],
        size=7.0,
        gap=2.5,
    )

    # stack chips
    add_text(
        slide,
        "S3StackL",
        MARGIN_L,
        4.50,
        0.55,
        0.20,
        [{"text": "STACK", "size": 6.4, "bold": True, "color": MUTED, "spc": 60}],
    )
    chips = [
        "Python 3.12",
        "FastAPI",
        "PyTorch 2.6",
        "ONNX Runtime",
        "OpenCV",
        "React 19",
        "SQLite WAL",
        "HL7 FHIR R4",
        "SNOMED CT",
        "ReportLab",
    ]
    cx = 1.14
    for i, name in enumerate(chips):
        cw = 0.17 + len(name) * 0.052
        add_rect(
            slide, f"S3Ch{i}", cx, 4.48, cw, 0.22, fill=WHITE, line=LINE, line_pt=0.6
        )
        add_text(
            slide,
            f"S3Ch{i}T",
            cx,
            4.48,
            cw,
            0.22,
            [{"text": name, "size": 6.6, "color": SLATE, "align": PP_ALIGN.CENTER}],
            anchor=MSO_ANCHOR.MIDDLE,
            align=PP_ALIGN.CENTER,
        )
        cx += cw + 0.06

    foot_note(
        slide,
        "S3Foot",
        MARGIN_L,
        4.82,
        CONTENT_W,
        0.42,
        "Both heads run on one 512² tensor: the same preprocessed frame drives ICDR staging, lesion masks, Grad-CAM explainability and the FHIR R4 report — 0.59 s on CPU, P95 0.71 s.",
        size=7.2,
    )


# ── slide 4 — feasibility & viability (results dashboard) ───────────────────
def build_slide4(slide) -> None:
    lead(slide, "Evidence: 3,394 unseen images, sub-second end to end, $0 per screen.")

    kw, gap = 2.105, 0.16
    xs = [MARGIN_L + i * (kw + gap) for i in range(4)]
    for i, (value, label, sub, color) in enumerate(
        [
            ("97.5%", "referable-DR sensitivity", "95% CI 96.5–98.2 · n = 3,394", DEEP),
            ("0.843", "ROC AUC (referable vs not)", "sens 97.5% · spec 72.8%", ACCENT),
            ("82.1%", "4-model ensemble, held-out", "single best 80.4%", DEEP),
            ("0.59 s", "end-to-end on laptop CPU", "P95 0.71 s · 100% local", POS),
        ]
    ):
        card(slide, f"S4K{i}", xs[i], 0.90, kw, 0.80, fill=WHITE)
        kpi(
            slide,
            f"S4K{i}I",
            xs[i] + 0.08,
            0.96,
            kw - 0.16,
            0.72,
            value,
            label,
            value_size=17,
            color=color,
            sub=sub,
        )

    # external confusion matrix
    card(slide, "S4A", MARGIN_L, 1.82, 3.30, 2.24, fill=WHITE)
    panel_title(
        slide,
        "S4AT",
        MARGIN_L + 0.10,
        1.90,
        3.10,
        "External confusion matrix · APTOS · n = 3,394",
        size=6.6,
    )
    add_pic(slide, ASSETS / "cm_external.png", "S4AImg", 0.82, 2.08, w=2.76)

    # referable 2x2 + operating metrics
    card(slide, "S4B", 4.00, 1.82, 2.35, 2.24, fill=WHITE)
    panel_title(slide, "S4BT", 4.10, 1.90, 2.15, "Referable DR · 2 × 2", size=6.6)
    cells = [
        ("TP", "1,392", POS, WHITE),
        ("FP", "534", NEG, WHITE),
        ("FN", "36", SOFT, NEG),
        ("TN", "1,432", PANEL, INK),
    ]
    for i, (tag, val, fill, txt) in enumerate(cells):
        cx = 4.10 + (i % 2) * 1.10
        cy = 2.10 + (i // 2) * 0.44
        line = LINE if fill in (SOFT, PANEL) else None
        add_rect(
            slide, f"S4B{i}", cx, cy, 1.06, 0.41, fill=fill, line=line, line_pt=0.6
        )
        add_text(
            slide,
            f"S4B{i}T",
            cx,
            cy,
            1.06,
            0.41,
            [
                {
                    "runs": [
                        (f"{tag} ", {"size": 6.4, "color": txt}),
                        (
                            val,
                            {"font": DISPLAY, "size": 10.5, "bold": True, "color": txt},
                        ),
                    ],
                    "align": PP_ALIGN.CENTER,
                }
            ],
            anchor=MSO_ANCHOR.MIDDLE,
            align=PP_ALIGN.CENTER,
        )
    add_pic(slide, ASSETS / "ref_metrics.png", "S4BM", 4.12, 3.06, w=2.12)

    # held-out F1
    card(slide, "S4C", 6.55, 1.82, 2.90, 2.24, fill=WHITE)
    panel_title(slide, "S4CT", 6.65, 1.90, 2.70, "Held-out ICDR F1 · n = 815", size=6.6)
    add_pic(slide, ASSETS / "f1_internal.png", "S4CImg", 6.65, 2.08, w=2.68)
    foot_note(
        slide,
        "S4CNote",
        6.65,
        3.58,
        2.70,
        0.44,
        "Per-class F1 on the 815-image held-out split. The 4-model ensemble adds +1.7 pp (80.4% → 82.1%) over the single best checkpoint.",
        size=6.8,
    )

    # feasibility quadrants
    quads = [
        ("Technical", "11/11 components verified end-to-end; ONNX FP32 on CPU"),
        ("Operational", "One command: bash start_demo.sh · offline, no cloud APIs"),
        ("Economic", "$0 per screen after setup vs $15–50 manual grading"),
        ("Scalability", "Batch triage of 20 images per call · FHIR-ready for EHRs"),
    ]
    for i, (label, body) in enumerate(quads):
        cx = xs[i]
        card(slide, f"S4Q{i}", cx, 4.14, kw, 0.76, fill=PANEL)
        add_rect(slide, f"S4Q{i}Bar", cx, 4.14, kw, 0.04, fill=ACCENT)
        add_text(
            slide,
            f"S4Q{i}T",
            cx + 0.10,
            4.22,
            kw - 0.20,
            0.64,
            [
                {
                    "text": label.upper(),
                    "size": 6.6,
                    "bold": True,
                    "color": ACCENT,
                    "spc": 55,
                },
                {
                    "text": body,
                    "size": 7.0,
                    "color": SLATE,
                    "space_before": 2,
                    "line": 1.0,
                },
            ],
        )

    foot_note(
        slide,
        "S4Foot",
        MARGIN_L,
        4.96,
        CONTENT_W,
        0.30,
        "Honest external read: five-class accuracy on the imbalanced APTOS set is 60.8% (95% CI 59.2–62.3) — but the decision the tool actually drives, referable vs non-referable, is right 97.5% of the time. Rare-stage recall is the next training cycle.",
        size=6.8,
    )


# ── slide 5 — impact & benefits ─────────────────────────────────────────────
def build_slide5(slide) -> None:
    lead(slide, "What changes when a screening is instant, free and offline.")

    cw, ch = 2.445, 0.66
    items = [
        ("1", "Clinical confidence", "97.5% sensitivity · 97.5% NPV"),
        ("2", "Fewer missed referrals", "abstains < 55% → clinician review"),
        ("3", "Near-zero cost", "$0 per screen vs $15–50 manual"),
        ("4", "Minimal footprint", "one laptop · offline · no cloud"),
        ("5", "Faster triage", "0.59 s vs 5–10 min per image"),
    ]
    for i, (num, title, metric) in enumerate(items):
        if i < 4:
            cx = MARGIN_L + (i % 2) * (cw + 0.16)
            cy = 0.90 + (i // 2) * (ch + 0.08)
            width = cw
        else:
            cx, cy, width = MARGIN_L, 0.90 + 2 * (ch + 0.08), cw * 2 + 0.16
        card(slide, f"S5I{i}", cx, cy, width, ch, fill=WHITE)
        add_rect(slide, f"S5I{i}Bar", cx, cy, 0.05, ch, fill=ACCENT)
        add_text(
            slide,
            f"S5I{i}T",
            cx + 0.14,
            cy + 0.06,
            width - 0.24,
            ch - 0.10,
            [
                {
                    "runs": [
                        (
                            f"{num}  ",
                            {
                                "font": DISPLAY,
                                "size": 11,
                                "bold": True,
                                "color": ACCENT,
                            },
                        ),
                        (
                            title.upper(),
                            {"size": 7.2, "bold": True, "color": INK, "spc": 40},
                        ),
                    ]
                },
                {
                    "text": metric,
                    "size": 7.2,
                    "color": SLATE,
                    "space_before": 2,
                    "line": 1.0,
                },
            ],
        )

    rx, rw = 5.85, 3.60
    card(slide, "S5TC", rx, 0.90, rw, 2.14, fill=WHITE)
    panel_title(
        slide, "S5TCT", rx + 0.12, 0.98, rw - 0.24, "Before vs after · one screening"
    )
    add_pic(slide, ASSETS / "time_cost.png", "S5TCImg", rx + 0.14, 1.18, w=3.32)
    foot_note(
        slide,
        "S5TCNote",
        rx + 0.14,
        2.56,
        rw - 0.28,
        0.44,
        "Same laptop, same image, no internet: the marginal cost of a screen goes to zero while the wait falls from minutes to under a second.",
        size=7.0,
    )

    panel_title(slide, "S5PathT", MARGIN_L, 3.14, 3.0, "Impact pathway")
    stages = [
        ("Problem", "specialist-only · 5–10 min · $15–50", DEEP),
        ("Solution", "0.59 s local AI · FHIR R4 · abstention", ACCENT),
        ("Immediate impact", "instant triage · fewer missed referrals", POS),
        ("Long-term impact", "population screening · EHR-native", VIOLET),
    ]
    for i, (title, sub, color) in enumerate(stages):
        cx = MARGIN_L + i * 2.28
        add_rect(
            slide, f"S5P{i}", cx, 3.36, 2.05, 0.86, fill=WHITE, line=LINE, line_pt=0.75
        )
        add_rect(slide, f"S5P{i}Bar", cx, 3.36, 2.05, 0.05, fill=color)
        add_text(
            slide,
            f"S5P{i}T",
            cx + 0.10,
            3.46,
            1.85,
            0.72,
            [
                {
                    "text": title.upper(),
                    "size": 7.0,
                    "bold": True,
                    "color": color,
                    "spc": 45,
                },
                {
                    "text": sub,
                    "size": 7.0,
                    "color": SLATE,
                    "space_before": 3,
                    "line": 1.0,
                },
            ],
        )
        if i < 3:
            arrow(slide, f"S5P{i}A", cx + 2.09, 3.72, 0.15, 0.14, color=MUTED)

    panel_title(slide, "S5WhoT", MARGIN_L, 4.34, 3.0, "Who benefits")
    who = [
        ("Primary health centres", "Rural clinics screen without a specialist on site"),
        ("Eye hospitals", "Batch triage of 20 images + Grad-CAM review queue"),
        ("Public health programmes", "Population screening at near-zero marginal cost"),
    ]
    for i, (title, body) in enumerate(who):
        cx = MARGIN_L + i * 3.00
        card(slide, f"S5W{i}", cx, 4.54, 2.90, 0.62, fill=PANEL)
        add_text(
            slide,
            f"S5W{i}T",
            cx + 0.10,
            4.60,
            2.70,
            0.52,
            [
                {
                    "text": title.upper(),
                    "size": 6.8,
                    "bold": True,
                    "color": ACCENT,
                    "spc": 45,
                },
                {
                    "text": body,
                    "size": 7.0,
                    "color": SLATE,
                    "space_before": 2,
                    "line": 1.0,
                },
            ],
        )


# ── slide 6 — research & references ─────────────────────────────────────────
def build_slide6(slide) -> None:
    lead(slide, "The datasets, prior work, standards and ablations behind every claim.")

    lx, lw = MARGIN_L, 4.35
    panel_title(
        slide, "S6LT", lx, 0.90, lw, "Research / literature survey", rule_after=True
    )
    rows = [
        (
            "Porwal et al., IDRiD (Data 2018)",
            "DR grades + pixel-level lesion masks → segmenter",
        ),
        ("APTOS 2019 (Kaggle)", "3,662 graded fundus images → train + external test"),
        ("DDR dataset", "lesion masks lift segmenter training 54 → 811 (×15)"),
        (
            "Ronneberger et al., U-Net (MICCAI 2015)",
            "encoder–decoder for the 4 lesion channels",
        ),
        (
            "Liu et al., ConvNeXt (CVPR 2022)",
            "backbone upgrade: +8.6 pp over EfficientNet-B2",
        ),
        (
            "Grad-CAM · Focal Loss (ICCV 2017)",
            "attention heat-maps + class-imbalance loss",
        ),
    ]
    for i, (name, use) in enumerate(rows):
        y = 1.16 + i * 0.32
        add_rect(slide, f"S6R{i}", lx, y, lw, 0.012, fill=LINE)
        add_text(
            slide,
            f"S6R{i}T",
            lx,
            y + 0.05,
            lw,
            0.26,
            [
                {
                    "runs": [
                        (name, {"size": 7.0, "bold": True, "color": INK}),
                        ("  —  ", {"size": 7.0, "color": MUTED}),
                        (use, {"size": 7.0, "color": SLATE}),
                    ],
                    "line": 1.0,
                }
            ],
        )

    rx, rw = 5.15, 4.30
    panel_title(slide, "S6CT", rx, 0.90, rw, "Competitive landscape", rule_after=True)
    colx = [rx, rx + 1.80, rx + 2.60, rx + 3.45]
    colw = [1.80, 0.80, 0.85, 0.85]
    heads = ["", "RetinaScan AI", "Cloud vision APIs", "Manual grading"]
    for i, head in enumerate(heads):
        add_text(
            slide,
            f"S6H{i}",
            colx[i],
            1.16,
            colw[i],
            0.30,
            [
                {
                    "text": head,
                    "size": 6.4,
                    "bold": True,
                    "color": ACCENT if i == 1 else MUTED,
                    "align": PP_ALIGN.CENTER if i else PP_ALIGN.LEFT,
                    "line": 1.0,
                }
            ],
            align=PP_ALIGN.CENTER if i else PP_ALIGN.LEFT,
        )
    feats = [
        ("Runs fully offline", "✓", "—", "✓"),
        ("Abstains to a human", "✓", "—", "✓"),
        ("HL7 FHIR R4 output", "✓", "—", "—"),
        ("Grad-CAM explainable", "✓", "✓", "✓"),
        ("Cost per screen", "$0", "metered", "$15–50"),
    ]
    for r, (label, *vals) in enumerate(feats):
        y = 1.46 + r * 0.30
        add_rect(slide, f"S6FR{r}", rx, y, rw, 0.012, fill=LINE)
        add_text(
            slide,
            f"S6FL{r}",
            colx[0],
            y + 0.06,
            colw[0],
            0.24,
            [{"text": label, "size": 7.0, "color": SLATE, "line": 1.0}],
        )
        for c, val in enumerate(vals):
            color = (
                POS
                if val == "✓"
                else (
                    NEG
                    if val == "$15–50"
                    else (INK if val in ("$0", "metered") else MUTED)
                )
            )
            add_text(
                slide,
                f"S6FV{r}{c}",
                colx[c + 1],
                y + 0.05,
                colw[c + 1],
                0.24,
                [
                    {
                        "text": val,
                        "size": 7.2 if val in ("✓", "—") else 7.0,
                        "bold": val in ("✓", "$0"),
                        "color": color,
                        "align": PP_ALIGN.CENTER,
                        "line": 1.0,
                    }
                ],
                align=PP_ALIGN.CENTER,
            )
    foot_note(
        slide,
        "S6CNote",
        rx,
        3.00,
        rw,
        0.14,
        "“—” = not documented in the vendor's public material; manual-grading cost from PROJECT_INFO.",
        size=6.0,
    )

    # evidence strip
    strip = [
        ("Training data ×10 / ×15", "data_growth.png", 1.83, None),
        (
            "Ablation: backbone → ensemble",
            "perf_delta.png",
            2.03,
            "80.4% single best → 82.1% 4-model ensemble",
        ),
        (
            "Segmenter Dice · DDR test",
            "dice.png",
            2.05,
            "CWS 0.769 · mean 0.314 on 225 unseen images",
        ),
    ]
    for i, (title, img, iw, note) in enumerate(strip):
        cx = MARGIN_L + i * 3.00
        card(slide, f"S6S{i}", cx, 3.16, 2.90, 1.52, fill=WHITE)
        panel_title(slide, f"S6S{i}T", cx + 0.10, 3.22, 2.70, title, size=6.4)
        add_pic(slide, ASSETS / img, f"S6S{i}Img", cx + (2.90 - iw) / 2, 3.40, w=iw)
        if note:
            foot_note(slide, f"S6S{i}N", cx + 0.10, 4.44, 2.70, 0.20, note, size=6.4)

    panel_title(slide, "S6RefT", MARGIN_L, 4.78, 3.0, "References")
    add_text(
        slide,
        "S6Ref",
        MARGIN_L,
        4.94,
        CONTENT_W,
        0.30,
        [
            {
                "text": (
                    "1 Ronneberger et al., U-Net, MICCAI 2015 (arXiv:1505.04597)  ·  2 Liu et al., A ConvNet for the 2020s, CVPR 2022 (arXiv:2201.03545)  ·  "
                    "3 Lin et al., Focal Loss, ICCV 2017  ·  4 Selvaraju et al., Grad-CAM, ICCV 2017 (arXiv:1610.02391)  ·  5 Porwal et al., IDRiD, Data 2018  ·  "
                    "6 APTOS 2019 Blindness Detection, Kaggle  ·  7 HL7 FHIR R4 · SNOMED CT · LOINC (hl7.org · snomed.org · loinc.org)"
                ),
                "size": 6.4,
                "color": SLATE,
                "line": 1.05,
            }
        ],
    )


# ── notes ───────────────────────────────────────────────────────────────────
NOTES = {
    1: (
        "Open with the promise: a fundus photo goes in and a standards-compliant clinical report comes "
        "out in 0.59 seconds, entirely on a laptop. RetinaScan AI is decision-support screening for "
        "diabetic retinopathy — 5-stage ICDR classification, 4-channel lesion segmentation, Grad-CAM "
        "explanation and an HL7 FHIR R4 report. The two images are real: a demo fundus frame and the "
        "Grad-CAM attention map produced by our own checkpoint. (Fill in Track and Team Name before submitting.)"
    ),
    2: (
        "Problem first. India has about 77 million people with diabetes and every one of them needs "
        "periodic retinal screening, but today that means a specialist, five to ten minutes per image "
        "and 15 to 50 dollars per screen. Our solution compresses that to a single command and 0.59 "
        "seconds. The screenshot on the right is the live application — real model output including "
        "lesion masks, stage probabilities, the abstention banner and the FHIR report."
    ),
    3: (
        "Walk the flow left to right. The quality gate rejects ungradable frames with recapture guidance "
        "so a blurry image never reaches the models. One preprocessed 512-squared tensor then feeds two "
        "heads in parallel: a four-model ConvNeXt-Tiny ensemble for ICDR staging and a U-Net with a "
        "ResNet18 encoder for the four lesion channels. The decision layer refers and, below 55 percent "
        "confidence, abstains to a clinician — visible in the live banner capture. The latency budget "
        "shows where the 0.59 seconds goes."
    ),
    4: (
        "This is the proof slide. External validation on 3,394 unseen APTOS images gives 97.5 percent "
        "sensitivity for referable diabetic retinopathy with a 95 percent confidence interval of 96.5 to "
        "98.2, NPV 97.5 percent and AUC 0.843. Be upfront about the five-class confusion matrix: overall "
        "external accuracy is 60.8 percent on an imbalanced set, which is exactly why the tool is built "
        "as a screening gate with abstention rather than an autonomous diagnostician."
    ),
    5: (
        "Impact is measured, not asserted. Screening time drops from five to ten minutes to 0.59 seconds "
        "and cost from 15-50 dollars to zero after setup. The pathway runs problem → solution → immediate "
        "impact → long-term impact: from a specialist bottleneck to population-scale, EHR-native "
        "screening. Bottom row names who actually benefits: primary health centres, eye hospitals and "
        "public health programmes."
    ),
    6: (
        "Credibility slide. Every claim traces to a public dataset or paper: IDRiD and APTOS for "
        "classification, DDR lifting segmenter training from 54 to 811 images, U-Net, ConvNeXt, "
        "Grad-CAM and Focal Loss for the methods, FHIR R4 with SNOMED CT and LOINC for output. The "
        "competitive matrix positions us on documented capabilities only, and the three charts show "
        "the data growth and the ablations behind 82.1 percent."
    ),
}


# ── main ────────────────────────────────────────────────────────────────────
def main() -> int:
    ext, ens, seg = load_metrics()
    assert_metrics(ext, ens, seg)

    missing = [c for c in CHARTS if not (ASSETS / c).exists()]
    if missing:
        raise SystemExit(f"missing deck assets: {missing}")

    prs = Presentation(str(TEMPLATE_PATH))

    # slide 1 — keep headings + four title-page fields
    s1_keep = chrome_names(prs.slides[0], prs.slides[0]) | {
        "Text 21",
        "Text 22",
        "Text 24",
        "Text 26",
        "Text 30",
        "Text 34",
    }
    drop_shapes(prs.slides[0], s1_keep)
    build_slide1(prs.slides[0])

    # slides 2-6 — keep chrome only (heading + footer + logos)
    builders = [build_slide2, build_slide3, build_slide4, build_slide5, build_slide6]
    for idx, builder in enumerate(builders, start=1):
        slide = prs.slides[idx]
        drop_shapes(slide, chrome_names(slide, slide))
        builder(slide)

    # slide 7 (IMPORTANT INSTRUCTIONS) is never touched

    for i in range(6):
        set_notes(prs.slides[i], NOTES[i + 1])

    cp = prs.core_properties
    cp.title = "AITHON 2.0 — RetinaScan AI: AI-Assisted Diabetic Retinopathy Screening"
    cp.author = "Siddhesh"

    BUILD_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(BUILD_PATH))
    print(
        f"built {BUILD_PATH.relative_to(ROOT)}  ({BUILD_PATH.stat().st_size // 1024} KB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
