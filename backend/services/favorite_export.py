import io
from pathlib import Path
from typing import Any


FONT_CANDIDATES = [
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
]

PALETTE = {
    "paper": "#f4f0e8",
    "card": "#fffdf8",
    "muted_card": "#f8f5ef",
    "green": "#315c4c",
    "green_light": "#e3ece7",
    "brown": "#a76d3c",
    "brown_light": "#f1eadf",
    "ink": "#29312d",
    "muted": "#777b75",
    "line": "#e4ddd2",
}


def _font_path() -> str | None:
    for item in FONT_CANDIDATES:
        if Path(item).exists():
            return item
    return None


def _snapshot_value(snapshot: dict[str, Any], key: str) -> str:
    value = snapshot.get(key) or ""
    return str(value).strip()


def _wrap_text(text: str, width: int) -> list[str]:
    text = (text or "未提供").replace("\r", "").strip()
    lines: list[str] = []
    for paragraph in text.split("\n"):
        current = ""
        for char in paragraph:
            current += char
            if len(current) >= width:
                lines.append(current)
                current = ""
        if current:
            lines.append(current)
    return lines or ["未提供"]


def favorite_pdf(favorite, report: bool = False) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer

    font_name = "Helvetica"
    path = _font_path()
    if path:
        font_name = "AINameCN"
        pdfmetrics.registerFont(TTFont(font_name, path))

    class HeroCard(Flowable):
        def __init__(self, name: str, subtitle: str):
            super().__init__()
            self.name = name
            self.subtitle = subtitle
            self.width = 160 * mm
            self.height = 54 * mm

        def draw(self):
            canvas = self.canv
            canvas.saveState()
            canvas.setFillColor(colors.HexColor(PALETTE["green"]))
            canvas.roundRect(0, 0, self.width, self.height, 16, fill=1, stroke=0)
            canvas.setFillColor(colors.Color(1, 1, 1, alpha=.12))
            canvas.circle(self.width - 15 * mm, self.height + 1 * mm, 34 * mm, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor("#f8f3ea"))
            canvas.setFont(font_name, 30)
            canvas.drawCentredString(self.width / 2, 28 * mm, self.name)
            canvas.setFillColor(colors.HexColor("#d9e5de"))
            canvas.setFont(font_name, 10)
            canvas.drawCentredString(self.width / 2, 15 * mm, self.subtitle)
            canvas.restoreState()

    class InfoBlock(Flowable):
        def __init__(self, label: str, text: str):
            super().__init__()
            self.label = label
            self.text = text
            self.width = 160 * mm
            self.lines = _wrap_text(text, 43)
            self.height = (18 + len(self.lines) * 8) * mm

        def draw(self):
            canvas = self.canv
            canvas.saveState()
            canvas.setFillColor(colors.HexColor(PALETTE["card"]))
            canvas.setStrokeColor(colors.HexColor(PALETTE["line"]))
            canvas.roundRect(0, 0, self.width, self.height, 10, fill=1, stroke=1)
            canvas.setFillColor(colors.HexColor(PALETTE["brown_light"]))
            canvas.roundRect(9 * mm, self.height - 13 * mm, 25 * mm, 7 * mm, 4, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor(PALETTE["brown"]))
            canvas.setFont(font_name, 9)
            canvas.drawCentredString(21.5 * mm, self.height - 10.5 * mm, self.label)
            canvas.setFillColor(colors.HexColor(PALETTE["ink"]))
            canvas.setFont(font_name, 10.5)
            y = self.height - 22 * mm
            for line in self.lines:
                canvas.drawString(12 * mm, y, line)
                y -= 8 * mm
            canvas.restoreState()

    def page_background(canvas, _):
        width, height = A4
        canvas.saveState()
        canvas.setFillColor(colors.HexColor(PALETTE["paper"]))
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#ede7dc"))
        canvas.circle(width - 12 * mm, height - 12 * mm, 42 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor(PALETTE["brown"]))
        canvas.setFont(font_name, 8)
        canvas.drawCentredString(width / 2, 16 * mm, "AIName · 名字，是故事的第一句话")
        canvas.restoreState()

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=25 * mm,
        leftMargin=25 * mm,
        topMargin=23 * mm,
        bottomMargin=24 * mm,
        title=favorite.name,
    )
    styles = getSampleStyleSheet()
    eyebrow = ParagraphStyle(
        "Eyebrow",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor(PALETTE["brown"]),
        spaceAfter=6,
    )
    note = ParagraphStyle(
        "Note",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor(PALETTE["muted"]),
    )
    snapshot = favorite.snapshot or {}
    subtitle = f"{favorite.category} · {'企业命名报告' if report else '收藏起名方案'} · {favorite.created_at:%Y.%m.%d}"
    story = [
        Paragraph("AI NAMING STUDIO", eyebrow),
        HeroCard(favorite.name, subtitle),
        Spacer(1, 11 * mm),
        InfoBlock("出处", _snapshot_value(snapshot, "reference")),
        Spacer(1, 7 * mm),
        InfoBlock("寓意", _snapshot_value(snapshot, "moral")),
    ]
    analysis = _snapshot_value(snapshot, "analysis")
    if analysis:
        story.extend([
            Spacer(1, 7 * mm),
            InfoBlock("推演", analysis),
        ])
    if report or favorite.category == "企业名":
        story.extend([
            Spacer(1, 7 * mm),
            InfoBlock("域名", _snapshot_value(snapshot, "domain") or "未提供"),
            Spacer(1, 7 * mm),
            InfoBlock("状态", _snapshot_value(snapshot, "domain_status") or "未查询"),
        ])
    story.extend([
        Spacer(1, 10 * mm),
        Paragraph("本文件由 AIName 自动生成，仅供命名灵感、品牌讨论与前期筛选参考。", note),
    ])
    document.build(story, onFirstPage=page_background, onLaterPages=page_background)
    return buffer.getvalue()


def favorite_png(favorite) -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    path = _font_path()
    title_font = ImageFont.truetype(path, 72) if path else ImageFont.load_default()
    label_font = ImageFont.truetype(path, 28) if path else ImageFont.load_default()
    body_font = ImageFont.truetype(path, 32) if path else ImageFont.load_default()
    small_font = ImageFont.truetype(path, 24) if path else ImageFont.load_default()
    tiny_font = ImageFont.truetype(path, 20) if path else ImageFont.load_default()

    def rounded(draw, xy, radius, fill, outline=None, width=1):
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

    def text_block(draw, label: str, text: str, x: int, y: int, w: int) -> int:
        lines = _wrap_text(text, 24)
        height = 100 + len(lines) * 44
        rounded(draw, (x, y, x + w, y + height), 28, PALETTE["card"], PALETTE["line"], 2)
        rounded(draw, (x + 36, y + 30, x + 126, y + 68), 19, PALETTE["brown_light"])
        draw.text((x + 81, y + 49), label, fill=PALETTE["brown"], font=label_font, anchor="mm")
        ty = y + 92
        for line in lines:
            draw.text((x + 38, ty), line, fill=PALETTE["ink"], font=body_font)
            ty += 44
        return y + height + 28

    snapshot = favorite.snapshot or {}
    width, height = 1080, 1500
    image = Image.new("RGB", (width, height), PALETTE["paper"])
    draw = ImageDraw.Draw(image)
    draw.ellipse((width - 350, -120, width + 160, 390), fill="#ebe4d8")
    draw.ellipse((-220, height - 300, 240, height + 160), fill="#e8eee9")
    rounded(draw, (70, 70, width - 70, height - 70), 42, "#fffaf2", "#ebe3d8", 2)

    draw.text((width // 2, 135), "AI NAMING STUDIO", fill=PALETTE["brown"], font=tiny_font, anchor="mm")
    rounded(draw, (135, 190, width - 135, 430), 36, PALETTE["green"])
    draw.ellipse((width - 270, 120, width - 10, 380), fill="#416d5c")
    draw.text((width // 2, 285), favorite.name, fill="#fffdf8", font=title_font, anchor="mm")
    draw.text(
        (width // 2, 355),
        f"{favorite.category} · 收藏起名方案 · {favorite.created_at:%Y.%m.%d}",
        fill="#d9e5de",
        font=small_font,
        anchor="mm",
    )

    y = 505
    y = text_block(draw, "出处", _snapshot_value(snapshot, "reference"), 120, y, width - 240)
    y = text_block(draw, "寓意", _snapshot_value(snapshot, "moral"), 120, y, width - 240)
    if _snapshot_value(snapshot, "analysis"):
        y = text_block(draw, "推演", _snapshot_value(snapshot, "analysis"), 120, y, width - 240)

    draw.line((150, height - 170, width - 150, height - 170), fill=PALETTE["line"], width=2)
    draw.text((width // 2, height - 126), "名字，是故事的第一句话", fill=PALETTE["green"], font=small_font, anchor="mm")
    draw.text((width // 2, height - 92), "Generated by AIName", fill=PALETTE["muted"], font=tiny_font, anchor="mm")

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
