#!/usr/bin/env python3
"""Generate 科二代上海高考选校指导手册 PDF.

Fixes: strip markdown formatting, properly parse tables, clean emoji.
Uses STHeiti TrueType font for Chinese rendering.
"""

import re, os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Font setup ──
FONT_DIR = "/System/Library/AssetsV2/com_apple_MobileAsset_Font8"
stheit_path = None
for root, dirs, files in os.walk(FONT_DIR):
    for f in files:
        if f == "STHEITI.ttf":
            stheit_path = os.path.join(root, f)
            break
    if stheit_path:
        break
if not stheit_path:
    raise FileNotFoundError("No STHEITI.ttf found on system")

pdfmetrics.registerFont(TTFont("STHeiti", stheit_path))
FONT = "STHeiti"
print(f"Using font: {stheit_path}")

# ── Cleaners ──

def clean_text(text):
    """Remove true emoji only (U+1Fxxx range). Keep all CJK, symbols, and ★."""
    # Step 1: replace specific symbols BEFORE emoji cleanup
    text = text.replace('☑', '[v]')    # keep ballot box with check
    text = text.replace('☐', '[ ]')    # ballot box
    text = text.replace('✔', '[v]')    # check mark
    text = text.replace('✖', 'x')      # heavy multiplication x
    text = text.replace('⚙', '')       # gear
    text = text.replace('⭐', '')       # star (emoji-style)
    text = text.replace('✅', '')       # white heavy check mark

    # Step 2: Remove only TRUE emoji (Supplementary Multilingual Plane U+1F000+)
    # These are pictographic emoji that Chinese fonts often lack
    emoji_ranges = [
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F300, 0x1F5FF),  # Misc Symbols and Pictographs
        (0x1F680, 0x1F6FF),  # Transport and Map
        (0x1F1E0, 0x1F1FF),  # Regional Indicators (flags)
        (0x1F900, 0x1F9FF),  # Supplemental Symbols
        (0x1FA00, 0x1FA6F),  # Chess Symbols
        (0x1FA70, 0x1FAFF),  # Symbols Extended-A
        (0xFE00, 0xFE0F),    # Variation Selectors
        (0x200D, 0x200D),    # Zero-Width Joiner
    ]
    for lo, hi in emoji_ranges:
        text = re.sub(f'[\\U{lo:08X}-\\U{hi:08X}]', '', text)

    return text

def strip_markdown(text):
    """Strip markdown formatting markers."""
    # Remove **bold** markers
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    # Remove __bold__
    text = re.sub(r'__(.*?)__', r'\1', text)
    # Remove *italic* (but not if it might be a bullet)
    text = re.sub(r'(?<!\s)\*(?!\s)(.*?)(?<!\s)\*(?!\s)', r'\1', text)
    # Remove `code` markers
    text = re.sub(r'`([^`]*)`', r'\1', text)
    return text

def is_table_separator(line):
    """Check if a line is a markdown table separator (|:---|:---|)."""
    cleaned = re.sub(r'[\s|:]', '', line).replace('-', '')
    return len(cleaned) == 0 and '-' in line

# ── Styles ──
def make_styles():
    return {
        'title': ParagraphStyle("st", fontName=FONT, fontSize=16, leading=24,
            alignment=TA_CENTER, spaceAfter=3*mm, textColor=colors.HexColor("#004098")),
        'subtitle': ParagraphStyle("ss", fontName=FONT, fontSize=8, leading=13,
            alignment=TA_CENTER, spaceAfter=5*mm, textColor=colors.HexColor("#666")),
        'h2': ParagraphStyle("sh2", fontName=FONT, fontSize=12, leading=18,
            spaceBefore=4*mm, spaceAfter=1.5*mm, textColor=colors.HexColor("#004098")),
        'h3': ParagraphStyle("sh3", fontName=FONT, fontSize=10.5, leading=16,
            spaceBefore=2.5*mm, spaceAfter=1*mm, textColor=colors.HexColor("#2c3e50")),
        'body': ParagraphStyle("sb", fontName=FONT, fontSize=8.5, leading=14,
            spaceBefore=0.5, spaceAfter=1*mm, alignment=TA_JUSTIFY),
        'bullet': ParagraphStyle("sbl", fontName=FONT, fontSize=8.5, leading=14,
            spaceBefore=0, spaceAfter=0.5*mm, leftIndent=4*mm, firstLineIndent=-2*mm),
        'quote': ParagraphStyle("sq", fontName=FONT, fontSize=8, leading=13,
            spaceBefore=1*mm, spaceAfter=1*mm, leftIndent=3*mm,
            textColor=colors.HexColor("#555")),
        'th': ParagraphStyle("sth", fontName=FONT, fontSize=7, leading=11,
            alignment=TA_CENTER, textColor=colors.white),
        'td': ParagraphStyle("std", fontName=FONT, fontSize=7, leading=11,
            alignment=TA_LEFT, textColor=colors.HexColor("#333")),
        'disclaimer': ParagraphStyle("sd", fontName=FONT, fontSize=6.5, leading=10,
            alignment=TA_CENTER, textColor=colors.HexColor("#999")),
    }

def add_table_to(elements, rows, styles):
    """Render a list of row-lists as a PDF table."""
    if not rows:
        return
    ncols = max(len(r) for r in rows)
    avail = A4[0] - 40*mm
    # Heuristic column widths
    if ncols == 2:
        cw = [avail*0.25, avail*0.75]
    elif ncols == 3:
        cw = [avail*0.2, avail*0.35, avail*0.45]
    elif ncols == 4:
        cw = [avail*0.15, avail*0.25, avail*0.25, avail*0.35]
    elif ncols == 5:
        cw = [avail*0.14, avail*0.13, avail*0.13, avail*0.30, avail*0.30]
    elif ncols == 6:
        cw = [avail*0.14, avail*0.09, avail*0.09, avail*0.24, avail*0.22, avail*0.22]
    elif ncols >= 7:
        cw = [avail*0.13, avail*0.09, avail*0.09, avail*0.18, avail*0.12, avail*0.14, avail*0.25]
    else:
        cw = [avail/ncols] * ncols

    data = []
    for i, row in enumerate(rows):
        sty = styles['th'] if i == 0 else styles['td']
        data.append([Paragraph(cell, sty) for cell in row])

    t = Table(data, colWidths=cw[:ncols], repeatRows=1)
    tstyle = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#004098")),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor("#d0d0d0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]
    for ri in range(2, len(data), 2):
        tstyle.append(('BACKGROUND', (0, ri), (-1, ri), colors.HexColor("#f5f7fa")))
    t.setStyle(TableStyle(tstyle))
    elements.append(t)
    elements.append(Spacer(1, 1.5*mm))

def build_pdf(output_path):
    md_path = os.path.join(os.path.dirname(__file__), "科二代上海高考选校指导手册.md")
    with open(md_path, "r", encoding="utf-8") as f:
        md_text = f.read()

    lines = md_text.split("\n")
    styles = make_styles()
    elements = []
    table_rows = []

    def add_hr():
        elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.HexColor("#e0e0e0")))

    def flush_table():
        nonlocal table_rows
        if table_rows:
            add_table_to(elements, table_rows, styles)
            table_rows = []

    def emit(text, style_key):
        text = clean_text(strip_markdown(text))
        if text.strip():
            elements.append(Paragraph(text.strip(), styles[style_key]))

    # ── Title and subtitle ──
    emit("科二代 上海高考选校决策路径", 'title')
    emit("范围：上海本地大学 + C9联盟 | 方向：STEM优先 | v2.0 2026年5月", 'subtitle')

    # ── Parse line by line ──
    for raw_line in lines:
        line = raw_line.strip()

        # Skip empty lines and markdown fences
        if not line or line.startswith("```"):
            flush_table()
            continue
        if line == "---":
            flush_table()
            elements.append(Spacer(1, 2*mm))
            continue

        # Detect table rows (both | data and |:--- separator)
        if line.startswith("|"):
            # Skip table separator lines (|:---|:---|)
            if is_table_separator(line):
                continue
            # Parse table row cells
            cells = [c.strip() for c in line.strip("|").split("|")]
            cells = [strip_markdown(clean_text(c)) for c in cells]
            # Keep empty cells to preserve column structure
            if cells and any(c for c in cells):
                table_rows.append(cells)
            continue
        else:
            flush_table()

        # Heading detection - strip leading # markers
        if line.startswith("## "):
            emit(line[3:], 'h2')
            add_hr()
        elif line.startswith("### "):
            emit(line[4:], 'h3')
        elif line.startswith("# "):
            pass  # title already rendered
        elif line.startswith("> "):
            emit(line[2:], 'quote')
        elif line.startswith("- "):
            emit("  " + line[2:], 'bullet')
        elif line.startswith("* "):
            emit("  " + line[2:], 'bullet')
        elif line and line[0].isdigit() and (". " in line[:4]):
            emit(line, 'bullet')
        else:
            emit(line, 'body')

    flush_table()

    # ── Disclaimer ──
    elements.append(Spacer(1, 6*mm))
    add_hr()
    elements.append(Spacer(1, 1.5*mm))
    emit("免责声明：数据基于2025年招生季和2026年已公布政策，具体填报以当年官方发布为准。仅供决策参考。", 'disclaimer')
    emit("数据来源：上海市教育考试院、阳光高考平台、各校招生网 | v2.0 2026年5月31日", 'disclaimer')

    doc = SimpleDocTemplate(
        output_path, pagesize=A4,
        topMargin=20*mm, bottomMargin=16*mm,
        leftMargin=18*mm, rightMargin=18*mm,
    )
    doc.build(elements)
    return output_path

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(out_dir, "科二代上海高考选校指导手册.pdf")
    if os.path.exists(out):
        os.remove(out)
    build_pdf(out)
    size = os.path.getsize(out)
    print(f"PDF generated: {out} ({size:,} bytes)")
