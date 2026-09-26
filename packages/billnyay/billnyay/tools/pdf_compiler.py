"""
BillNyay — PDF Appeal Packet Compiler.

Generates a formal, beautifully formatted ReportLab PDF appeal document containing
the formal appeal letter, audit findings, clinical evidence, and regulatory support.
"""

import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape as _xml_escape

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


def _append_annex(story: list, clinical_annex: str, styles) -> None:
    """ADR-011: the clinical-statement annex (or the notice that none exists), rendered
    verbatim. Reviewer-typed text is untrusted markup to ReportLab exactly like the
    LLM-drafted letter, so every line is XML-escaped before any tag is added."""
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=BORDER))
    story.append(Spacer(1, 8))
    for block in clinical_annex.split("\n\n"):
        raw = block.strip()
        if not raw:
            continue
        text = _xml_escape(raw).replace("\n", "<br/>")
        style = styles["SectionHead"] if raw.startswith("ANNEXURE") and "\n" not in raw else styles["LetterBody"]
        story.append(Paragraph(text, style))
        story.append(Spacer(1, 6))


def _build_story(appeal_letter: str, styles, clinical_annex: Optional[str] = None) -> list:
    """Shared story-building logic for both the file-path and in-memory compilers,
    so the two can never silently render different documents."""
    story = []

    # Title Banner
    story.append(Paragraph("ArogyaRakshak — BillNyay Formal Appeal Packet", styles["HeaderTitle"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y')} | Medical Bill & Insurance Audit Support", styles["HeaderSub"]))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PURPLE))
    story.append(Spacer(1, 14))

    # Appeal Letter Paragraphs
    # SEC-02: `appeal_letter` is LLM-drafted from document-derived (untrusted) facts —
    # it can legitimately contain '<', '>' or '&' (e.g. "Hb < 5.0 mg/dL"). ReportLab's
    # Paragraph parses its text as a small XML/HTML dialect, so passing that straight
    # through either raises on malformed "tags" or, worse, lets attacker-controlled text
    # inject real markup. Untrusted content is XML-escaped BEFORE any markup this
    # function itself adds (the "### " heading strip, the "\n" -> "<br/>" line break) so
    # the escaping can never touch tags the app intentionally generated.
    paragraphs = appeal_letter.split("\n\n") if appeal_letter else ["No letter text provided."]
    for p in paragraphs:
        raw = p.strip()
        is_heading = raw.startswith("### ") or raw.startswith("## ") or raw.startswith("# ")
        if is_heading:
            clean_title = _xml_escape(raw.lstrip("#").strip())
            story.append(Paragraph(clean_title, styles["SectionHead"]))
            story.append(Spacer(1, 4))
        else:
            text = _xml_escape(raw).replace("\n", "<br/>")
            story.append(Paragraph(text, styles["LetterBody"]))
            story.append(Spacer(1, 8))

    if clinical_annex:
        _append_annex(story, clinical_annex, styles)

    return story


def compile_appeal_packet(
    appeal_letter: str,
    output_path: str,
    case_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Compiles appeal letter text into a formal PDF appeal document on disk."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(_build_story(appeal_letter, _styles()))
    return output_path


def compile_appeal_packet_bytes(
    appeal_letter: str,
    case_meta: Optional[Dict[str, Any]] = None,
    clinical_annex: Optional[str] = None,
) -> bytes:
    """Compiles appeal letter text into a formal PDF and returns its bytes directly,
    with no file written to disk — used by the appeal PDF-download/signing endpoint
    (#66), consistent with how DawaCheck/DaaviSetu build PDFs entirely in-memory."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    doc.build(_build_story(appeal_letter, _styles(), clinical_annex))
    return buffer.getvalue()
