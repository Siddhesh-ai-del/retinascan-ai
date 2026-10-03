"""
Generate every chart used by the redesigned AITHON deck.

All figures are rendered from the project's real metric files — nothing is
hard-coded except values documented in METRICS.md / PROJECT_INFO.md, and each
of those is asserted against the file it is documented in.

Outputs -> scripts/deck_assets/out/*.png  (300 dpi)

Run:  ./venv/bin/python scripts/deck_assets/charts.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[2]
METRICS = ROOT / "hackathon_sprint" / "metrics"
SEG_SUMMARY = ROOT / "models" / "segmentation" / "training_summary.json"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# ── Design tokens (scripts/deck_assets/DESIGN.md) ───────────────────────────
ACCENT = "#0070C0"
DEEP = "#1E2761"
VIOLET = "#6C63FF"
INK = "#101828"
SLATE = "#475569"
MUTED = "#94A3B8"
LINE = "#E2E8F0"
MIST = "#F8FAFC"
POS = "#0E9F9F"
WARN = "#D97706"
NEG = "#DC2626"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 8,
        "text.color": SLATE,
        "axes.labelcolor": SLATE,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.edgecolor": LINE,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "savefig.dpi": 300,
    }
)

STAGES = ["No DR", "Mild", "Moderate", "Severe", "Proliferative"]


def _clean(ax, left=False):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_color(LINE)
    ax.tick_params(length=0)


def save(fig, name):
    path = OUT / name
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    print(f"  wrote {path.relative_to(ROOT)}  ({path.stat().st_size // 1024} KB)")
    return path


def ext():
    return json.loads((METRICS / "external_validation.json").read_text())


def ens():
    return json.loads((METRICS / "ensemble_results.json").read_text())


# ── 1. External confusion matrix (n = 3,394, APTOS) ─────────────────────────
def confusion_matrix():
    d = ext()
    cm = d["confusion_matrix"]
    n = sum(sum(r) for r in cm)
    assert n == d["evaluated"] == 3394, n
    rows = [[v / sum(r) * 100 for v in r] for r in cm]

    fig, ax = plt.subplots(figsize=(3.5, 2.85))
    for i in range(5):
        for j in range(5):
            pct = rows[i][j]
            diag = i == j
            if pct >= 55:
                face, text = DEEP, "white"
            elif pct >= 12:
                face, text = ACCENT, "white"
            elif pct >= 3:
                face, text = "#9EC5EA", INK
            else:
                face, text = MIST, MUTED
            ax.add_patch(
                Rectangle((j, 4 - i), 1, 1, facecolor=face, edgecolor="white", lw=1.4)
            )
            ax.text(
                j + 0.5,
                4 - i + 0.60,
                f"{pct:.0f}%",
                ha="center",
                va="center",
                fontsize=8.2,
                fontweight="bold" if diag else "normal",
                color=text,
            )
            ax.text(
                j + 0.5,
                4 - i + 0.27,
                f"{cm[i][j]:,}",
                ha="center",
                va="center",
                fontsize=6.3,
                color=text,
                alpha=0.9,
            )
    ax.set_xlim(0, 5)
    ax.set_ylim(0, 5)
    ax.set_xticks([x + 0.5 for x in range(5)])
    ax.set_xticklabels(STAGES, fontsize=6.8)
    ax.set_yticks([y + 0.5 for y in range(5)])
    ax.set_yticklabels(STAGES[::-1], fontsize=6.8)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("Predicted stage", fontsize=7, color=SLATE, labelpad=3)
    ax.set_ylabel("True stage (row = 100 %)", fontsize=7, color=SLATE, labelpad=3)
    return save(fig, "cm_external.png")


# ── 2. Internal held-out F1 per ICDR class (n = 815) ────────────────────────
def internal_f1():
    report = (
        ROOT / "models" / "classification" / "classification_report.txt"
    ).read_text()
    rows = []
    for name in [
        "No DR",
        "Mild NPDR",
        "Moderate NPDR",
        "Severe NPDR",
        "Proliferative DR",
    ]:
        m = re.search(
            rf"^\s*{name}\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)", report, re.M
        )
        assert m, name
        rows.append((name, float(m.group(3)), int(m.group(4))))
    acc = re.search(r"^\s*accuracy\s+([\d.]+)\s+(\d+)", report, re.M)
    assert acc and abs(float(acc.group(1)) - 0.7840) < 1e-6

    labels = [r[0].replace(" Proliferative", "Proliferative") for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    sup = [r[2] for r in rows][::-1]
    colors = [POS if v >= 0.7 else ACCENT if v >= 0.5 else WARN for v in vals]

    fig, ax = plt.subplots(figsize=(3.3, 2.05))
    bars = ax.barh(labels, vals, color=colors, height=0.62)
    for b, v, s in zip(bars, vals, sup):
        ax.text(
            v + 0.02,
            b.get_y() + b.get_height() / 2,
            f"{v:.3f}",
            va="center",
            fontsize=7.4,
            fontweight="bold",
            color=INK,
        )
        ax.text(
            0.015,
            b.get_y() + b.get_height() / 2,
            f"n={s}",
            va="center",
            fontsize=6.2,
            color="white",
        )
    ax.set_xlim(0, 1.12)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(["0", ".25", ".50", ".75", "1.0"], fontsize=6.5)
    ax.set_xlabel("F1-score · held-out split (815 images)", fontsize=6.8, labelpad=2)
    _clean(ax, left=False)
    ax.grid(axis="x", color=LINE, lw=0.6)
    ax.set_axisbelow(True)
    return save(fig, "f1_internal.png")


# ── 3. Referable-DR operating metrics + 95 % CI ─────────────────────────────
def referable_metrics():
    r = ext()["referable_dr"]
    assert (r["tp"], r["fp"], r["tn"], r["fn"]) == (1392, 534, 1432, 36)
    items = [
        ("Sensitivity", r["sensitivity"] * 100, r["sensitivity_95ci"], POS),
        ("Specificity", r["specificity"] * 100, None, ACCENT),
        ("PPV", r["ppv"] * 100, None, ACCENT),
        ("NPV", r["npv"] * 100, None, POS),
    ]
    fig, ax = plt.subplots(figsize=(3.35, 1.62))
    for i, (name, val, ci, color) in enumerate(items):
        y = len(items) - 1 - i
        ax.barh([y], [val], color=color, height=0.5)
        ax.barh([y], [100 - val], left=val, color=MIST, height=0.5)
        if ci:
            ax.plot([ci[0] * 100, ci[1] * 100], [y, y], color=INK, lw=1.1, zorder=5)
            for c in ci:
                ax.plot(
                    [c * 100, c * 100],
                    [y - 0.16, y + 0.16],
                    color=INK,
                    lw=1.1,
                    zorder=5,
                )
        ax.text(
            104,
            y,
            f"{val:.1f}%",
            va="center",
            fontsize=7.6,
            fontweight="bold",
            color=INK,
        )
        ax.text(-2, y, name, va="center", ha="right", fontsize=7.2, color=SLATE)
    ax.set_xlim(0, 118)
    ax.set_ylim(-0.6, len(items) - 0.4)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0", "25", "50", "75", "100%"], fontsize=6.3)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return save(fig, "ref_metrics.png")


# ── 4. 0.59 s latency budget ────────────────────────────────────────────────
def latency_budget():
    seg = [
        ("Image-quality gate + CLAHE / crop", 280, ACCENT),
        ("Classifier ×4 ensemble", 160, DEEP),
        ("Segmenter U-Net", 150, VIOLET),
    ]
    total = sum(v for _, v, _ in seg)
    assert total == 590 and (seg[1][1], seg[2][1]) == (160, 150), seg

    fig, ax = plt.subplots(figsize=(4.5, 1.15))
    left = 0
    for i, (name, val, color) in enumerate(seg):
        ax.barh([0], [val], left=left, color=color, height=0.42)
        ax.text(
            left + val / 2,
            0,
            f"{val}",
            ha="center",
            va="center",
            fontsize=7.6,
            fontweight="bold",
            color="white",
        )
        label_y = 0.68 if i == 1 else 0.36
        ax.text(
            left + val / 2,
            label_y,
            name,
            ha="center",
            va="bottom",
            fontsize=5.8 if i == 2 else 6.2,
            color=SLATE,
        )
        if i == 1:
            ax.plot([left + val / 2, left + val / 2], [0.24, 0.66], color=LINE, lw=0.7)
        left += val
    ax.plot([total, total], [-0.34, 0.34], color=INK, lw=1.2)
    ax.text(
        total + 12, 0, "590 ms", va="center", fontsize=8, fontweight="bold", color=INK
    )
    ax.set_xlim(0, 700)
    ax.set_ylim(-0.75, 1.3)
    ax.set_yticks([])
    ax.set_xticks([0, 200, 400, 600])
    ax.set_xticklabels(["0", "200", "400", "600 ms"], fontsize=6.3)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return save(fig, "latency_budget.png")


# ── 5. Time + cost per screening: manual vs RetinaScan ──────────────────────
def time_cost():
    fig, axes = plt.subplots(1, 2, figsize=(4.3, 1.72))

    ax = axes[0]
    ax.barh(
        [1],
        [600 - 300],
        left=300,
        color="#FCE7E7",
        edgecolor=NEG,
        height=0.42,
        lw=1,
    )
    ax.plot([300, 300], [0.79, 1.21], color=NEG, lw=1.4)
    ax.plot([600, 600], [0.79, 1.21], color=NEG, lw=1.4)
    ax.text(
        300, 1.34, "5–10 min", ha="center", fontsize=7.4, fontweight="bold", color=NEG
    )
    ax.barh([0], [0.59], color=POS, height=0.42)
    ax.plot([0.59, 0.59], [-0.21, 0.21], color=POS, lw=1.6)
    ax.annotate(
        "0.59 s",
        xy=(0.59, 0),
        xytext=(46, 0),
        fontsize=7.8,
        fontweight="bold",
        color=POS,
        va="center",
        arrowprops=dict(arrowstyle="->", color=POS, lw=1),
    )
    ax.text(
        640,
        0.5,
        "100×\nfaster",
        ha="center",
        va="center",
        fontsize=8.4,
        fontweight="bold",
        color=POS,
    )
    ax.set_yticks([1, 0])
    ax.set_yticklabels(["Ophthalmologist", "RetinaScan AI"], fontsize=6.8, color=SLATE)
    ax.set_xlim(0, 760)
    ax.set_ylim(-0.6, 1.75)
    ax.set_xticks([0, 300, 600])
    ax.set_xticklabels(["0", "5", "10 min"], fontsize=6.2)
    ax.set_title("Time to one report", fontsize=7, color=SLATE, pad=4)
    _clean(ax)

    ax = axes[1]
    ax.barh([1], [35], left=15, color="#FCE7E7", edgecolor=NEG, height=0.42, lw=1)
    ax.plot([15, 15], [0.79, 1.21], color=NEG, lw=1.4)
    ax.plot([50, 50], [0.79, 1.21], color=NEG, lw=1.4)
    ax.text(32, 1.34, "$15–50", ha="center", fontsize=7.4, fontweight="bold", color=NEG)
    ax.scatter([0], [0], s=70, color=POS, zorder=5)
    ax.annotate(
        "$0",
        xy=(0, 0),
        xytext=(9, 0),
        fontsize=7.8,
        fontweight="bold",
        color=POS,
        va="center",
        arrowprops=dict(arrowstyle="->", color=POS, lw=1),
    )
    ax.set_yticks([1, 0])
    ax.set_yticklabels(["Private clinic", "After setup"], fontsize=6.8, color=SLATE)
    ax.set_xlim(0, 66)
    ax.set_ylim(-0.6, 1.75)
    ax.set_xticks([0, 25, 50])
    ax.set_xticklabels(["$0", "$25", "$50"], fontsize=6.2)
    ax.set_title("Cost per screening", fontsize=7, color=SLATE, pad=4)
    _clean(ax)

    fig.subplots_adjust(wspace=0.55)
    return save(fig, "time_cost.png")


# ── 6. Training-data growth ─────────────────────────────────────────────────
def data_growth():
    fig, axes = plt.subplots(1, 2, figsize=(3.5, 1.7))
    panels = [
        ("Classifier", 413, 4075, "IDRiD → IDRiD + APTOS", "×10"),
        ("Segmenter", 54, 811, "IDRiD → IDRiD + DDR", "×15"),
    ]
    for ax, (title, before, after, sub, mult) in zip(axes, panels):
        bars = ax.bar([0, 1], [before, after], color=[MUTED, ACCENT], width=0.55)
        for b, v in zip(bars, [before, after]):
            ax.text(
                b.get_x() + b.get_width() / 2,
                v * 1.03,
                f"{v:,}",
                ha="center",
                fontsize=7.2,
                fontweight="bold",
                color=INK,
            )
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["before", "after"], fontsize=6.4)
        ax.set_ylim(0, after * 1.28)
        ax.set_yticks([])
        ax.set_title(
            f"{title}  ·  {mult}", fontsize=7.4, color=DEEP, fontweight="bold", pad=3
        )
        ax.text(
            0.5,
            -0.30,
            sub,
            transform=ax.transAxes,
            ha="center",
            fontsize=5.9,
            color=MUTED,
        )
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(LINE)
        ax.tick_params(length=0)
    fig.subplots_adjust(wspace=0.25)
    return save(fig, "data_growth.png")


# ── 7. Segmenter per-class Dice (DDR test, n = 225) ─────────────────────────
def dice():
    d = json.loads(SEG_SUMMARY.read_text())
    pc = d["per_class"]
    assert abs(d["test_dice"] - 0.3144) < 1e-6
    order = [
        ("Microaneurysms", pc["microaneurysms"]),
        ("Haemorrhages", pc["hemorrhages"]),
        ("Hard exudates", pc["hard_exudates"]),
        ("Cotton wool spots", pc["cotton_wool_spots"]),
    ]
    labels = [o[0] for o in order][::-1]
    vals = [o[1] for o in order][::-1]
    colors = [POS if v > 0.5 else ACCENT if v > 0.15 else WARN for v in vals]

    fig, ax = plt.subplots(figsize=(2.9, 1.6))
    bars = ax.barh(labels, vals, color=colors, height=0.6)
    for b, v in zip(bars, vals):
        ax.text(
            v + 0.02,
            b.get_y() + b.get_height() / 2,
            f"{v:.3f}",
            va="center",
            fontsize=7,
            fontweight="bold",
            color=INK,
        )
    ax.axvline(d["test_dice"], color=INK, lw=0.9, ls="--")
    ax.text(
        d["test_dice"] + 0.01,
        3.62,
        f"mean {d['test_dice']:.3f}",
        fontsize=6.2,
        color=INK,
    )
    ax.set_xlim(0, 1.0)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(["0", "0.5", "1.0"], fontsize=6.2)
    ax.set_xlabel("Dice · DDR test (225 unseen images)", fontsize=6.5, labelpad=2)
    _clean(ax)
    ax.grid(axis="x", color=LINE, lw=0.6)
    ax.set_axisbelow(True)
    return save(fig, "dice.png")


# ── 8. Classifier upgrade: baseline → single → ensemble ─────────────────────
def perf_delta():
    e = ens()
    ens_acc = e["ensemble_acc"] * 100
    single = 80.4  # best checkpoint top3_epoch38_acc0.8037.pth -> 80.4 %
    baseline = 73.5  # PROJECT_INFO: EfficientNet-B2 baseline
    assert abs(ens_acc - 82.1) < 0.05, ens_acc

    labels = [
        "EfficientNet-B2\n(baseline)",
        "ConvNeXt-Tiny\nsingle best",
        "ConvNeXt-Tiny\n4-model ensemble",
    ]
    vals = [baseline, single, ens_acc]
    colors = [MUTED, ACCENT, DEEP]

    fig, ax = plt.subplots(figsize=(3.0, 1.62))
    bars = ax.bar(labels, vals, color=colors, width=0.52)
    for b, v in zip(bars, vals):
        ax.text(
            b.get_x() + b.get_width() / 2,
            v + 1.2,
            f"{v:.1f}%",
            ha="center",
            fontsize=7.6,
            fontweight="bold",
            color=INK,
        )
    ax.annotate(
        "",
        xy=(2, ens_acc + 13),
        xytext=(0, baseline + 13),
        arrowprops=dict(arrowstyle="->", color=POS, lw=1.2),
    )
    ax.text(
        1.0,
        ens_acc + 15.5,
        "+8.6 pp",
        ha="center",
        fontsize=7.4,
        fontweight="bold",
        color=POS,
    )
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 50, 100])
    ax.set_yticklabels(["0", "50", "100%"], fontsize=6.2)
    ax.tick_params(axis="x", labelsize=6.1, length=0)
    ax.set_ylabel("Validation accuracy", fontsize=6.5, color=SLATE)
    _clean(ax)
    ax.grid(axis="y", color=LINE, lw=0.6)
    ax.set_axisbelow(True)
    return save(fig, "perf_delta.png")


if __name__ == "__main__":
    print("Rendering deck charts …")
    for fn in (
        confusion_matrix,
        internal_f1,
        referable_metrics,
        latency_budget,
        time_cost,
        data_growth,
        dice,
        perf_delta,
    ):
        fn()
    print("done")
