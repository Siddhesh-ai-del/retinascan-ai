# RetinaScan AI — Deck Design System (v2 redesign)

Target: `AITHON_2.0_RetinaScanAI_Submission.pptx` (AITHON 2.0 official template, 7 slides, 10.0 × 5.625 in).

## Direction
**Editorial white + one vivid accent.** Light canvas (matches template chrome and the
AIESA / AITHON logos), charcoal-navy type, a single saturated accent taken *from the
template itself*, and a saturated colour scale reserved for data.

## Palette (template-derived first)
| Token | Hex | Use |
|---|---|---|
| `ACCENT` | `#0070C0` | template footer blue — primary accent, key rules, focus |
| `DEEP` | `#1E2761` | template navy — display headings, hero panel |
| `VIOLET` | `#6C63FF` | template violet — 2nd data series only |
| `INK` | `#101828` | primary text / display numerals |
| `SLATE` | `#475569` | body copy |
| `MUTED` | `#94A3B8` | captions, axis labels, meta |
| `LINE` | `#E2E8F0` | hairlines, card borders |
| `MIST` | `#F8FAFC` | card fill |
| `POS` | `#0E9F9F` | positive / safe metrics |
| `WARN` | `#D97706` | caution / abstention |
| `NEG` | `#DC2626` | misses, rejected frames |

Rule: **no slide uses more than accent + 1 alert colour + neutrals**; chart colour
scales (viridis-free, sequential `MIST → ACCENT → DEEP`) are data, not decoration.

## Type
- **Display numerals:** Georgia — 28–40 pt, tight, `INK` or `ACCENT`.
- **Section headings:** template-owned, untouched (Times/Cambria per template).
- **Lead line:** Calibri Bold 14 pt, `DEEP`, one sentence per slide.
- **Panel title:** Calibri Bold 9.5 pt, UPPERCASE, +letterspacing, `SLATE`.
- **Body:** Calibri 9–10 pt, `SLATE`, line spacing 1.0.
- **Caption / axis:** Calibri 7.5–8 pt, `MUTED`.
- Calibri renders slightly narrower in PowerPoint than the Noto Sans LibreOffice
  substitutes used for render-QA → sizes chosen so LibreOffice fit is *conservative*.

## Grid
- Margins 0.55 in L/R; content band `y = 0.95 → 5.20` (footer bar starts 5.32).
- 12 columns, 0.18 in gutter. Cards align to column edges.
- Baseline stack: lead (0.95) → panel row 1 (1.30) → panel row 2 (3.05) →
  KPI strip (4.55) → footnote (5.02).

## Components
`card()` panel with 1 pt `LINE` border + `MIST` fill · `kpi()` Georgia numeral +
Calibri caption + accent top-rule · `chip()` rounded outline pill ·
`rule()` 2 pt accent hairline · `flow()` chevron/arrow pipeline ·
`panel_title()` uppercase label · `footnote()` sourced-metrics line.

## Content rules (non-negotiable)
1. Chrome-only template gate: 7 slides, size, section headings, footer bar +
   geometry, both logos, slide 7 verbatim, notes on 1–6, docProps, template sha256.
2. Slide 1 `[ Enter track name ]` / `[ Enter team name ]` untouched.
3. Every number in slide text traces to a documented source (verifier whitelist).
4. ≥ 1 real chart / flowchart / product image per slide — no bullet-only slides.
5. Lead with 97.5 % referable-DR sensitivity; show external 5-class matrix
   transparently (honesty = credibility), framed as screening-first.
