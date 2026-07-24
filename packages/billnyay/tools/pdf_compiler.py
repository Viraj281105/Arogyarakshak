"""
BillNyay — PDF Appeal Packet Compiler.

Generates a formal, beautifully formatted ReportLab PDF appeal document containing
the formal appeal letter, audit findings, clinical evidence, and regulatory support.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PURPLE = colors.HexColor("#1e3a8a")
DARK = colors.HexColor("#0f172a")
MUTED = colors.HexColor("#475569")
BORDER = colors.HexColor("#cbd5e1")


def _styles():
    base = getSampleStyleSheet()

    def add(name, **kw):
        if name not in base:
            base.add(ParagraphStyle(name=name, **kw))
        return base[name]

    add("HeaderTitle", fontName="Helvetica-Bold", fontSize=20, textColor=PURPLE, leading=24, alignment=TA_CENTER)
    add("HeaderSub", fontName="Helvetica", fontSize=11, textColor=MUTED, leading=15, alignment=TA_CENTER)
    add("SectionHead", fontName="Helvetica-Bold", fontSize=13, textColor=PURPLE, leading=18, spaceAfter=4)
    add("LetterBody", fontName="Helvetica", fontSize=10, textColor=DARK, leading=15, alignment=TA_JUSTIFY)
    return base


def compile_appeal_packet(
    appeal_letter: str,
    output_path: str,
    case_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Compiles appeal letter text into a formal PDF appeal document."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = _styles()
    story = []

    # Title Banner
    story.append(Paragraph("ArogyaRakshak — BillNyay Formal Appeal Packet", styles["HeaderTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y')} | Medical Bill & Insurance Audit Support", styles["HeaderSub"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PURPLE))
    story.append(Spacer(1, 14))

    # Appeal Letter Paragraphs
    paragraphs = appeal_letter.split("\n\n") if appeal_letter else ["No letter text provided."]
    for p in paragraphs:
        text = p.strip().replace("\n", "<br/>")
        if text.startswith("### ") or text.startswith("## ") or text.startswith("# "):
            clean_title = text.lstrip("#").strip()
            story.append(Paragraph(clean_title, styles["SectionHead"]))
            story.append(Spacer(1, 4))
        else:
            story.append(Paragraph(text, styles["LetterBody"]))
            story.append(Spacer(1, 8))

    doc.build(story)
    return output_path
