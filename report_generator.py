import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import Flowable
from reportlab.pdfgen import canvas as rl_canvas


# ── Color palette ──────────────────────────────────────────────────────────────
C_BG = colors.HexColor("#0a0a0a")
C_SURFACE = colors.HexColor("#111111")
C_BORDER = colors.HexColor("#222222")
C_ACCENT = colors.HexColor("#a8e063")
C_ACCENT_DK = colors.HexColor("#56ab2f")
C_TEXT = colors.HexColor("#e8e8e8")
C_MUTED = colors.HexColor("#666666")
C_WHITE = colors.white
C_BLACK = colors.HexColor("#080808")


# ── Custom flowable: coloured rectangle block ──────────────────────────────────
class ColorRect(Flowable):
    def __init__(self, width, height, fill_color, radius=4):
        super().__init__()
        self.width = width
        self.height = height
        self.fill_color = fill_color
        self.radius = radius

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        self.canv.roundRect(
            0, 0, self.width, self.height, self.radius, fill=1, stroke=0
        )


class AccentLine(Flowable):
    def __init__(self, width, thickness=1, color=None):
        super().__init__()
        self.width = width
        self.height = thickness
        self.color = color or C_BORDER

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.height)
        self.canv.line(0, 0, self.width, 0)


class ScoreBar(Flowable):
    """Horizontal score bar visual."""

    def __init__(self, label, score, max_score=10, width=160 * mm):
        super().__init__()
        self.label = label
        self.score = score
        self.max_score = max_score
        self.width = width
        self.height = 8 * mm

    def draw(self):
        c = self.canv
        bar_w = self.width - 60 * mm
        bar_h = 3 * mm
        y_bar = (self.height - bar_h) / 2

        # Label
        c.setFont("Helvetica", 7)
        c.setFillColor(C_MUTED)
        c.drawString(0, y_bar + 1 * mm, self.label.upper())

        # Track
        c.setFillColor(C_SURFACE)
        c.roundRect(55 * mm, y_bar, bar_w, bar_h, 1.5, fill=1, stroke=0)

        # Fill
        fill_w = (self.score / self.max_score) * bar_w
        c.setFillColor(C_ACCENT)
        c.roundRect(55 * mm, y_bar, fill_w, bar_h, 1.5, fill=1, stroke=0)

        # Score text
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(C_ACCENT)
        c.drawRightString(self.width, y_bar + 1 * mm, f"{self.score}/10")


# ── Page template (header/footer drawn on every page) ─────────────────────────
class CropCastDocTemplate(SimpleDocTemplate):
    def __init__(self, buffer, result_data, **kwargs):
        super().__init__(buffer, **kwargs)
        self.result_data = result_data

    def handle_pageBegin(self):
        super().handle_pageBegin()

    def afterPage(self):
        pass

    def build(
        self,
        flowables,
        onFirstPage=None,
        onLaterPages=None,
        canvasmaker=rl_canvas.Canvas,
    ):
        def _header_footer(canvas, doc):
            canvas.saveState()
            w, h = A4

            # ── Full dark background ──────────────────────────────────────────
            canvas.setFillColor(C_BG)
            canvas.rect(0, 0, w, h, fill=1, stroke=0)

            # ── Header bar ───────────────────────────────────────────────────
            canvas.setFillColor(C_SURFACE)
            canvas.rect(0, h - 22 * mm, w, 22 * mm, fill=1, stroke=0)

            # Accent stripe
            canvas.setFillColor(C_ACCENT)
            canvas.rect(0, h - 22 * mm, 3 * mm, 22 * mm, fill=1, stroke=0)

            # Brand wordmark
            canvas.setFont("Helvetica-Bold", 14)
            canvas.setFillColor(C_ACCENT)
            canvas.drawString(10 * mm, h - 14 * mm, "CROPCAST")
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(C_MUTED)
            canvas.drawString(10 * mm, h - 19 * mm, "YIELD PREDICTION INTELLIGENCE")

            # Doc title right
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(C_MUTED)
            canvas.drawRightString(w - 10 * mm, h - 14 * mm, "PREDICTION REPORT")
            canvas.setFont("Helvetica", 7)
            canvas.drawRightString(
                w - 10 * mm, h - 19 * mm, datetime.now().strftime("%B %d, %Y")
            )

            # ── Footer ────────────────────────────────────────────────────────
            canvas.setFillColor(C_SURFACE)
            canvas.rect(0, 0, w, 12 * mm, fill=1, stroke=0)
            canvas.setFillColor(C_ACCENT)
            canvas.rect(0, 0, 3 * mm, 12 * mm, fill=1, stroke=0)

            canvas.setFont("Helvetica", 6.5)
            canvas.setFillColor(C_MUTED)
            canvas.drawString(
                10 * mm,
                4.5 * mm,
                "Generated by CropCast · ML-powered agricultural yield intelligence",
            )
            canvas.drawRightString(w - 10 * mm, 4.5 * mm, f"Page {doc.page}")

            canvas.restoreState()

        super().build(
            flowables,
            onFirstPage=_header_footer,
            onLaterPages=_header_footer,
            canvasmaker=canvasmaker,
        )


# ── Style helpers ──────────────────────────────────────────────────────────────
def S(name, **kwargs):
    defaults = dict(
        fontName="Helvetica",
        fontSize=9,
        textColor=C_TEXT,
        leading=14,
        spaceAfter=4,
    )
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


STYLES = {
    "hero_num": S(
        "hero_num",
        fontName="Helvetica-Bold",
        fontSize=38,
        textColor=C_ACCENT,
        leading=42,
        spaceAfter=2,
        alignment=TA_CENTER,
    ),
    "hero_unit": S(
        "hero_unit",
        fontSize=9,
        textColor=C_MUTED,
        leading=14,
        spaceAfter=2,
        alignment=TA_CENTER,
    ),
    "hero_sub": S(
        "hero_sub",
        fontSize=8,
        textColor=C_TEXT,
        leading=12,
        spaceAfter=0,
        alignment=TA_CENTER,
    ),
    "section_hd": S(
        "section_hd",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        textColor=C_ACCENT,
        leading=10,
        spaceAfter=6,
        spaceBefore=6,
        letterSpacing=1.5,
    ),
    "body": S("body", fontSize=8.5, textColor=C_TEXT, leading=14),
    "muted": S("muted", fontSize=7.5, textColor=C_MUTED, leading=11),
    "label": S(
        "label",
        fontName="Helvetica-Bold",
        fontSize=7,
        textColor=C_MUTED,
        leading=9,
        letterSpacing=0.8,
    ),
    "value": S(
        "value", fontName="Helvetica-Bold", fontSize=8.5, textColor=C_TEXT, leading=12
    ),
    "note": S("note", fontSize=7, textColor=C_MUTED, leading=10, spaceAfter=2),
    "footer_disc": S(
        "footer_disc", fontSize=6.5, textColor=C_MUTED, leading=9, alignment=TA_CENTER
    ),
}


def section_header(text):
    return [
        Spacer(1, 4 * mm),
        Paragraph(text.upper(), STYLES["section_hd"]),
        AccentLine(170 * mm, thickness=0.5, color=C_BORDER),
        Spacer(1, 3 * mm),
    ]


def kv_table(rows, col_widths=(55 * mm, 115 * mm)):
    """Two-col key/value table with dark styling."""
    table_data = []
    for k, v in rows:
        table_data.append(
            [
                Paragraph(k.upper(), STYLES["label"]),
                Paragraph(str(v), STYLES["value"]),
            ]
        )
    t = Table(table_data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                (
                    "ROWBACKGROUNDS",
                    (0, 0),
                    (-1, -1),
                    [C_SURFACE, colors.HexColor("#141414")],
                ),
                ("TEXTCOLOR", (0, 0), (-1, -1), C_TEXT),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, C_BORDER),
                ("ROUNDEDCORNERS", [4]),
            ]
        )
    )
    return t


def hero_block(yield_hg, tonne_ha, pct_vs_avg, item, area, year):
    """Prominent yield hero card."""
    sign = "+" if pct_vs_avg >= 0 else ""
    data = [
        [
            Paragraph(f"{yield_hg:,.0f}", STYLES["hero_num"]),
        ],
        [
            Paragraph("hg / ha  ·  hectograms per hectare", STYLES["hero_unit"]),
        ],
        [
            Paragraph(
                f"&#8776; {tonne_ha:,.2f} t/ha  &nbsp;&#183;&nbsp;  {sign}{pct_vs_avg:.1f}% vs regional average",
                STYLES["hero_sub"],
            ),
        ],
    ]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0d1a06")),
                ("LINEAFTER", (0, 0), (0, -1), 2, C_ACCENT),
                ("LINEBEFORE", (0, 0), (0, -1), 2, C_ACCENT),
                ("LINEABOVE", (0, 0), (-1, 0), 2, C_ACCENT),
                ("LINEBELOW", (0, -1), (-1, -1), 2, C_ACCENT),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ROUNDEDCORNERS", [6]),
            ]
        )
    )
    return t


def metric_row(metrics):
    """Row of 4 metric mini-cards: [(label, value, unit), ...]"""
    cell_data = []
    for label, value, unit in metrics:
        cell_data.append(
            [
                Paragraph(label.upper(), STYLES["label"]),
                Paragraph(
                    str(value),
                    ParagraphStyle(
                        "mv",
                        fontName="Helvetica-Bold",
                        fontSize=13,
                        textColor=C_ACCENT,
                        leading=16,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph(
                    unit,
                    ParagraphStyle(
                        "mu",
                        fontSize=7,
                        textColor=C_MUTED,
                        leading=9,
                        alignment=TA_CENTER,
                    ),
                ),
            ]
        )

    col_w = 170 * mm / len(metrics)
    rows = [
        [Table([[r[0]], [r[1]], [r[2]]], colWidths=[col_w - 4 * mm]) for r in cell_data]
    ]
    outer = Table(rows, colWidths=[col_w] * len(metrics))
    outer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), C_SURFACE),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINERIGHT", (0, 0), (-2, -1), 0.4, C_BORDER),
                ("ROUNDEDCORNERS", [4]),
            ]
        )
    )
    return outer


def score_table(scores):
    """Render all factor scores as bar rows."""
    items = []
    for label, score in scores.items():
        items.append(ScoreBar(label, score, width=170 * mm))
        items.append(Spacer(1, 1 * mm))
    return items


def benchmark_table(predicted, reg_avg, glob_avg):
    pct_reg = ((predicted / reg_avg) - 1) * 100 if reg_avg else 0
    pct_glob = ((predicted / glob_avg) - 1) * 100 if glob_avg else 0
    sign_r = "+" if pct_reg >= 0 else ""
    sign_g = "+" if pct_glob >= 0 else ""

    header = [
        Paragraph("METRIC", STYLES["label"]),
        Paragraph("YIELD (hg/ha)", STYLES["label"]),
        Paragraph("VS PREDICTED", STYLES["label"]),
    ]
    rows = [
        header,
        [
            Paragraph("Your Prediction", STYLES["value"]),
            Paragraph(
                f"{predicted:,.0f}",
                ParagraphStyle(
                    "bv",
                    fontName="Helvetica-Bold",
                    fontSize=9,
                    textColor=C_ACCENT,
                    leading=12,
                ),
            ),
            Paragraph("—", STYLES["muted"]),
        ],
        [
            Paragraph("Regional Average", STYLES["body"]),
            Paragraph(f"{reg_avg:,.0f}", STYLES["body"]),
            Paragraph(
                f"{sign_r}{pct_reg:.1f}%",
                ParagraphStyle(
                    "pct",
                    fontSize=8.5,
                    leading=12,
                    textColor=C_ACCENT if pct_reg >= 0 else colors.HexColor("#ff6b6b"),
                ),
            ),
        ],
        [
            Paragraph("Global Average", STYLES["body"]),
            Paragraph(f"{glob_avg:,.0f}", STYLES["body"]),
            Paragraph(
                f"{sign_g}{pct_glob:.1f}%",
                ParagraphStyle(
                    "pct2",
                    fontSize=8.5,
                    leading=12,
                    textColor=C_ACCENT if pct_glob >= 0 else colors.HexColor("#ff6b6b"),
                ),
            ),
        ],
    ]
    col_w = [80 * mm, 50 * mm, 40 * mm]
    t = Table(rows, colWidths=col_w)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#141414")),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [C_SURFACE, colors.HexColor("#141414")],
                ),
                ("LINEBELOW", (0, 0), (-1, -2), 0.4, C_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("ROUNDEDCORNERS", [4]),
            ]
        )
    )
    return t


# ── Main generator ─────────────────────────────────────────────────────────────
def generate_pdf_report(result: dict) -> bytes:
    r = result
    buffer = io.BytesIO()

    doc = CropCastDocTemplate(
        buffer,
        result_data=r,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=28 * mm,
        bottomMargin=18 * mm,
    )

    yield_hg = r["yield_hg_ha"]
    tonne_ha = yield_hg / 100
    reg_avg = r.get("benchmark_avg", yield_hg * 0.88)
    glob_avg = r.get("benchmark_global", yield_hg * 0.72)
    pct_vs_avg = ((yield_hg / reg_avg) - 1) * 100
    scores = r.get("scores", {})

    story = []

    # ── HERO ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(
        hero_block(yield_hg, tonne_ha, pct_vs_avg, r["item"], r["area"], r["year"])
    )
    story.append(Spacer(1, 4 * mm))

    # ── METRICS ROW ──────────────────────────────────────────────────────────
    story.append(
        metric_row(
            [
                ("Confidence Low", f"{r.get('ci_low', yield_hg*0.9):,.0f}", "hg/ha"),
                ("Predicted", f"{yield_hg:,.0f}", "hg/ha"),
                ("Confidence High", f"{r.get('ci_high', yield_hg*1.1):,.0f}", "hg/ha"),
                ("In Tonnes", f"{tonne_ha:,.2f}", "t/ha"),
            ]
        )
    )

    # ── PREDICTION DETAILS ────────────────────────────────────────────────────
    story += section_header("Prediction Details")
    story.append(
        kv_table(
            [
                ("Crop / Item", r["item"]),
                ("Region / Country", r["area"]),
                ("Projection Year", r["year"]),
                ("Model Type", "Random Forest Regressor"),
                ("Training Dataset", "FAO Global Agricultural Data"),
                ("Report Generated", datetime.now().strftime("%B %d, %Y at %H:%M UTC")),
            ]
        )
    )

    # ── INPUT CONDITIONS ─────────────────────────────────────────────────────
    story += section_header("Input Conditions")
    story.append(
        kv_table(
            [
                ("Annual Rainfall", f"{r['rainfall']:,.1f} mm / year"),
                ("Average Temperature", f"{r['avg_temp']:.1f} °C"),
                ("Pesticides Applied", f"{r['pesticides']:,.1f} tonnes"),
            ]
        )
    )

    # ── BENCHMARK COMPARISON ─────────────────────────────────────────────────
    story += section_header("Benchmark Comparison")
    story.append(benchmark_table(yield_hg, reg_avg, glob_avg))

    # ── FACTOR INFLUENCE ─────────────────────────────────────────────────────
    if scores:
        story += section_header("Factor Influence Analysis")
        story.append(
            Paragraph(
                "Each factor is scored 1–10 based on its estimated contribution to the predicted yield outcome.",
                STYLES["muted"],
            )
        )
        story.append(Spacer(1, 3 * mm))
        story += score_table(scores)

    # ── DISCLAIMER ───────────────────────────────────────────────────────────
    story += section_header("Disclaimer & Notes")
    story.append(
        Paragraph(
            "This report is generated by the CropCast ML prediction engine trained on historical FAO agricultural data. "
            "Yield values are expressed in hectograms per hectare (hg/ha); 100 hg/ha equals 1 tonne per hectare. "
            "Confidence bands represent a ±10% illustrative estimate and do not constitute actuarial or financial guarantees. "
            "Predictions are indicative only and should be supplemented with on-ground agronomic assessment before decision-making.",
            STYLES["note"],
        )
    )

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ── HTML Report (based on AgriYield / test.py design language) ─────────────────
def build_html_report(r: dict) -> str:
    """
    Generate a self-contained HTML report based on the AgriYield design language
    from test.py. Takes the result dict from app.py (yield_hg_ha, area, item, etc.)
    """
    from datetime import datetime

    yield_hg = r.get("yield_hg_ha", 0)
    tonne_ha = round(yield_hg / 100, 2)
    item = r.get("item", "—")
    area = r.get("area", "—")
    year = r.get("year", "—")
    rainfall = r.get("rainfall", 0)
    avg_temp = r.get("avg_temp", 0)
    pesticides = r.get("pesticides", 0)
    ci_low = r.get("ci_low", yield_hg * 0.90)
    ci_high = r.get("ci_high", yield_hg * 1.10)
    b_avg = r.get("benchmark_avg", yield_hg * 0.88)
    b_glob = r.get("benchmark_global", yield_hg * 0.72)
    scores = r.get("scores", {})

    pct_vs_avg = round(((yield_hg / b_avg) - 1) * 100, 1) if b_avg else 0
    sign = "+" if pct_vs_avg >= 0 else ""

    if tonne_ha < 1.0:
        band = "Poor"
    elif tonne_ha < 3.0:
        band = "Fair"
    elif tonne_ha < 6.0:
        band = "Good"
    elif tonne_ha < 12:
        band = "High"
    else:
        band = "Exceptional"

    now = datetime.now().strftime("%B %d, %Y")
    ref = "CC-" + datetime.now().strftime("%Y%m%d-%H%M%S")

    # Design tokens (matching test.py's report palette)
    RA = "#5BB336"
    RA2 = "#7ED458"
    RB = "#080808"
    RB2 = "#111111"
    RT = "#E8E8E8"
    RM = "#888888"
    RBD = "#1F1F1F"

    rain_note = (
        "Good rainfall for the selected crop."
        if rainfall >= 800
        else "Below optimal — irrigation may be needed."
    )
    temp_note = (
        "Temperature within productive range."
        if 15 <= avg_temp <= 30
        else "Temperature may limit yield potential."
    )
    pest_note = (
        "Input level appears moderate."
        if pesticides <= 200
        else "High pesticide use — consider integrated pest management."
    )
    yr_note = f"Year {year} projection using historical trend model."

    rows_html = ""
    for i, (lbl, val) in enumerate(
        [
            ("Crop", item),
            ("Region", area),
            ("Forecast Year", year),
            ("Annual Rainfall", f"{rainfall} mm"),
            ("Avg Temperature", f"{avg_temp} °C"),
            ("Pesticides", f"{pesticides} tonnes"),
            ("Predicted Yield", f"{tonne_ha} t/ha  ({yield_hg:,.0f} hg/ha)"),
            ("Confidence Range", f"{ci_low:,.0f} – {ci_high:,.0f} hg/ha"),
            ("Quality Band", band),
        ]
    ):
        rb = RB if i % 2 == 0 else RB2
        rows_html += (
            f"<tr>"
            f'<td style="padding:10px 16px;font-size:12px;color:{RM};border-bottom:1px solid {RBD};background:{rb};">{lbl}</td>'
            f'<td style="padding:10px 16px;font-size:12px;color:{RT};font-weight:500;border-bottom:1px solid {RBD};background:{rb};">{val}</td>'
            f"</tr>"
        )

    assess_cards = "".join(
        [
            f'<div style="background:{RB2};border:1px solid {RBD};border-left:3px solid {RA};border-radius:4px;padding:18px 20px;">'
            f'<div style="font-size:10px;font-weight:600;color:{RT};text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px;">{h}</div>'
            f'<p style="font-size:12px;color:{RM};line-height:1.75;margin:0;">{body}</p>'
            f"</div>"
            for h, body in [
                ("Water Availability", f"Annual rainfall {rainfall} mm. {rain_note}"),
                ("Climate Conditions", f"Avg temperature {avg_temp}°C. {temp_note}"),
                ("Input Management", f"Pesticides {pesticides} t. {pest_note}"),
                ("Temporal Context", yr_note),
            ]
        ]
    )

    # Benchmark mini-bars (HTML)
    def bench_row(label, value, predicted, accent):
        pct = round(((value / predicted) - 1) * 100, 1) if predicted else 0
        sign_b = "+" if pct >= 0 else ""
        col = RA if pct >= 0 else "#D96060"
        bar_pct = min(100, round(value / max(predicted, 1) * 80))
        return (
            f'<div class="rp-bench-row">'
            f'<span class="rp-bench-label">{label}</span>'
            f'<div class="rp-bench-bar">'
            f'<div style="width:{bar_pct}%;height:100%;background:{accent};border-radius:2px;"></div></div>'
            f'<span class="rp-bench-val">{value:,.0f} hg/ha</span>'
            f'<span class="rp-bench-pct" style="color:{col};">{sign_b}{pct}%</span>'
            f"</div>"
        )

    benchmark_html = (
        bench_row("Your Prediction", yield_hg, yield_hg, RA)
        + bench_row("Regional Average", b_avg, yield_hg, "#555")
        + bench_row("Global Average", b_glob, yield_hg, "#555")
    )

    scores_html = ""
    if scores:
        for lbl, val in scores.items():
            bar_w = min(100, int(val / 10 * 100))
            scores_html += (
                f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">'
                f'<span style="font-size:10px;color:{RM};width:100px;text-align:right;">{lbl}</span>'
                f'<div style="flex:1;height:3px;background:{RBD};border-radius:2px;">'
                f'<div style="width:{bar_w}%;height:100%;background:{RA};border-radius:2px;"></div></div>'
                f'<span style="font-size:11px;color:{RA};font-weight:600;width:36px;">{val}/10</span>'
                f"</div>"
            )

    model_cards = "".join(
        [
            f'<div style="background:{RB2};border:1px solid {RBD};border-radius:4px;padding:14px 16px;text-align:center;">'
            f'<div style="font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:{RM};margin-bottom:6px;">{lbl}</div>'
            f'<div style="font-family:Georgia,serif;font-size:1.0rem;font-weight:700;color:{RT};">{val}</div>'
            f"</div>"
            for lbl, val in [
                ("Algorithm", "Random Forest"),
                ("Estimators", "100 Trees"),
                ("Source", "FAO Dataset"),
                ("HF Repo", "shiavm006/..."),
            ]
        ]
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CropCast Yield Report — {item} {year}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,700&family=DM+Sans:wght@300;400;500&display=swap');
*{{box-sizing:border-box;margin:0;padding:0;}}
html{{scroll-behavior:smooth;}}
body{{font-family:'DM Sans',sans-serif;background:{RB};color:{RT};}}
@media print{{body{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}}}

/* ── Responsive ── */
.rp-header-top  {{ display:flex;justify-content:space-between;align-items:center;padding:7px 48px; }}
.rp-header-main {{ padding:32px 48px 28px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px; }}
.rp-body        {{ padding:44px 48px; }}
.rp-kpi-grid    {{ display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-bottom:36px; }}
.rp-assess-grid {{ display:grid;grid-template-columns:1fr 1fr;gap:12px; }}
.rp-model-grid  {{ display:grid;grid-template-columns:repeat(4,1fr);gap:10px; }}
.rp-bench-row   {{ display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid {RBD}; }}
.rp-bench-label {{ font-size:12px;color:{RM};min-width:130px; }}
.rp-bench-bar   {{ flex:1;margin:0 16px;height:3px;background:{RBD};border-radius:2px; }}
.rp-bench-val   {{ font-size:12px;color:{RT};font-weight:500;min-width:80px;text-align:right; }}
.rp-bench-pct   {{ font-size:11px;min-width:60px;text-align:right; }}
.rp-footer      {{ display:flex;justify-content:space-between;align-items:center;margin-bottom:10px; }}

@media (max-width: 900px) {{
  .rp-header-top  {{ padding:7px 28px; }}
  .rp-header-main {{ padding:24px 28px 22px; }}
  .rp-body        {{ padding:32px 28px; }}
  .rp-kpi-grid    {{ grid-template-columns:1fr 1fr; }}
  .rp-model-grid  {{ grid-template-columns:repeat(2,1fr); }}
}}
@media (max-width: 600px) {{
  .rp-header-top  {{ padding:6px 16px;flex-direction:column;gap:4px;align-items:flex-start; }}
  .rp-header-main {{ padding:18px 16px 16px;flex-direction:column;align-items:flex-start; }}
  .rp-body        {{ padding:22px 16px; }}
  .rp-kpi-grid    {{ grid-template-columns:1fr; }}
  .rp-assess-grid {{ grid-template-columns:1fr; }}
  .rp-model-grid  {{ grid-template-columns:1fr 1fr; }}
  .rp-bench-row   {{ flex-wrap:wrap;gap:6px; }}
  .rp-bench-label {{ min-width:100%;font-weight:500; }}
  .rp-bench-bar   {{ margin:0;width:100%; }}
  .rp-bench-val, .rp-bench-pct {{ min-width:auto; }}
  .rp-footer      {{ flex-direction:column;align-items:flex-start;gap:6px; }}
  table {{ font-size:11px !important; }}
  table td, table th {{ padding:8px 10px !important; }}
}}
</style>
</head>
<body>

<!-- HEADER -->
<div style="background:{RA};">
  <div class="rp-header-top" style="background:{RA2};">
    <span style="font-size:9px;letter-spacing:.22em;text-transform:uppercase;color:rgba(255,255,255,.6);">CONFIDENTIAL — CROP YIELD ANALYSIS REPORT</span>
    <span style="font-size:9px;color:rgba(255,255,255,.5);letter-spacing:.07em;">Ref: {ref}</span>
  </div>
  <div class="rp-header-main">
    <div style="display:flex;align-items:center;gap:16px;">
      <div style="width:44px;height:44px;border:1.5px solid rgba(255,255,255,.3);border-radius:8px;display:flex;align-items:center;justify-content:center;">
        <div style="width:18px;height:18px;border:2px solid rgba(255,255,255,.75);border-radius:50%;position:relative;">
          <div style="position:absolute;bottom:0;left:0;right:0;height:40%;background:rgba(255,255,255,.45);border-radius:0 0 18px 18px;"></div>
        </div>
      </div>
      <div>
        <div style="font-family:'Fraunces',serif;font-size:1.85rem;font-weight:700;color:#fff;letter-spacing:-.03em;line-height:1;">CropCast</div>
        <div style="font-size:.56rem;letter-spacing:.22em;text-transform:uppercase;color:rgba(255,255,255,.5);margin-top:3px;">Yield Intelligence · FAO Dataset</div>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'Fraunces',serif;font-size:.95rem;color:rgba(255,255,255,.85);">Yield Analysis Report</div>
      <div style="font-size:.73rem;color:rgba(255,255,255,.5);margin-top:5px;">{now}</div>
    </div>
  </div>
</div>
<div style="height:3px;background:linear-gradient(90deg,{RA},{RA2},#9EDE68);"></div>

<!-- BODY -->
<div class="rp-body">

  <!-- 01 Executive Summary -->
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:10px;">01 — Executive Summary</div>
    <div style="font-family:'Fraunces',serif;font-size:1.45rem;font-weight:400;color:{RT};letter-spacing:-.02em;line-height:1.25;margin-bottom:14px;">{item} Yield Forecast — {year}</div>
    <p style="font-size:13px;color:{RM};line-height:1.82;max-width:600px;">
      The CropCast Random Forest model (trained on FAO global crop data, hosted at
      <strong style="color:{RT};">shiavm006/Crop-yield_pridiction</strong> on Hugging Face)
      estimated a yield of <strong style="color:{RA};">{tonne_ha} tonnes per hectare</strong>
      ({yield_hg:,.0f} hg/ha) for <strong>{item}</strong> in <strong>{area}</strong>, {year}.
      Quality classification: <strong style="color:{RA};">{band}</strong>.
      Confidence range: {ci_low:,.0f} – {ci_high:,.0f} hg/ha
      ({sign}{pct_vs_avg}% vs regional average).
    </p>
  </div>

  <!-- Yield KPI cards -->
  <div class="rp-kpi-grid">
    <div style="background:{RB2};border:1px solid {RBD};border-top:3px solid {RA};border-radius:6px;padding:22px 20px;">
      <div style="font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:{RM};margin-bottom:8px;">Predicted Yield</div>
      <div style="font-family:'Fraunces',serif;font-size:2.5rem;font-weight:700;color:{RA};letter-spacing:-.04em;line-height:1;">{tonne_ha}</div>
      <div style="font-size:10px;color:{RM};letter-spacing:.12em;text-transform:uppercase;margin-top:4px;">Tonnes / Hectare</div>
    </div>
    <div style="background:{RB2};border:1px solid {RBD};border-top:3px solid {RT};border-radius:6px;padding:22px 20px;">
      <div style="font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:{RM};margin-bottom:8px;">Quality Band</div>
      <div style="font-family:'Fraunces',serif;font-size:2.5rem;font-weight:700;color:{RT};letter-spacing:-.04em;line-height:1;">{band}</div>
      <div style="font-size:10px;color:{RM};letter-spacing:.12em;text-transform:uppercase;margin-top:4px;">Classification</div>
    </div>
    <div style="background:{RB2};border:1px solid {RBD};border-top:3px solid {RM};border-radius:6px;padding:22px 20px;">
      <div style="font-size:9px;letter-spacing:.2em;text-transform:uppercase;color:{RM};margin-bottom:8px;">Forecast Year</div>
      <div style="font-family:'Fraunces',serif;font-size:2.5rem;font-weight:700;color:{RT};letter-spacing:-.04em;line-height:1;">{year}</div>
      <div style="font-size:10px;color:{RM};letter-spacing:.12em;text-transform:uppercase;margin-top:4px;">Reference Period</div>
    </div>
  </div>

  <div style="height:1px;background:{RBD};margin-bottom:32px;"></div>

  <!-- 02 Input Parameters -->
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:14px;">02 — Input Parameters</div>
    <div style="overflow-x:auto;">
    <table style="width:100%;min-width:320px;border-collapse:collapse;border:1px solid {RBD};overflow:hidden;border-radius:6px;">
      <thead>
        <tr style="background:{RA};">
          <th style="padding:11px 16px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#fff;text-align:left;font-weight:500;width:45%;">Parameter</th>
          <th style="padding:11px 16px;font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:#fff;text-align:left;font-weight:500;">Value</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
    </div>
  </div>

  <div style="height:1px;background:{RBD};margin-bottom:32px;"></div>

  <!-- 03 Benchmark Comparison -->
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:14px;">03 — Benchmark Comparison</div>
    <div style="background:{RB2};border:1px solid {RBD};border-radius:6px;padding:16px 20px;overflow-x:auto;">
      {benchmark_html}
    </div>
  </div>

  <div style="height:1px;background:{RBD};margin-bottom:32px;"></div>

  <!-- 04 Field Assessment -->
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:14px;">04 — Field Assessment</div>
    <div class="rp-assess-grid">{assess_cards}</div>
  </div>

  {"" if not scores else f'''
  <div style="height:1px;background:{RBD};margin-bottom:32px;"></div>
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:14px;">05 — Factor Influence Analysis</div>
    <div style="background:{RB2};border:1px solid {RBD};border-radius:6px;padding:16px 20px;">{scores_html}</div>
  </div>
  '''}

  <div style="height:1px;background:{RBD};margin-bottom:32px;"></div>

  <!-- Model Information -->
  <div style="margin-bottom:36px;">
    <div style="font-size:9px;letter-spacing:.28em;text-transform:uppercase;color:{RA};margin-bottom:14px;">06 — Model Information</div>
    <div class="rp-model-grid">{model_cards}</div>
  </div>

  <!-- Footer -->
  <div style="height:1px;background:{RBD};margin-bottom:20px;"></div>
  <div class="rp-footer">
    <div style="font-family:'Fraunces',serif;font-size:.95rem;font-weight:700;color:{RA};">CropCast</div>
    <div style="font-size:10px;color:{RM};">Generated {now} · {ref}</div>
  </div>
  <div style="font-size:10px;color:{RBD};line-height:1.55;">
    Predictions are derived from a Random Forest Regressor trained on FAO global crop production data.
    Results represent statistical estimates and should not replace agronomic field assessment.
    CropCast does not guarantee harvest outcomes.
  </div>
</div>
</body>
</html>"""
