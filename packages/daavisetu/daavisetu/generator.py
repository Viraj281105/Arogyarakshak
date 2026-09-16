"""
DaaviSetu — Claim & Pre-Authorization Form Generator.

Fills common insurance claim forms using parsed Kadi case context.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("DaaviSetu.Generator")
logger.setLevel(logging.INFO)


import io
import os
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from daavisetu.schema import FORM_SECTIONS


class ClaimData(BaseModel):
    policy_number: str = Field(..., description="Insurance policy ID")
    patient_name: str = Field(..., description="Full name of the patient")
    hospital_name: str = Field(..., description="Name of the hospital")
    diagnosis: str = Field(..., description="ICD-10 clinical diagnosis code or description")
    estimated_cost: float = Field(..., description="Estimated treatment cost")
    treatment_plan: str = Field(..., description="Summary of medical procedure or treatment plan")
    sum_insured: Optional[float] = Field(
        None,
        description="Policy's maximum sum insured, as declared by the policyholder. "
        "Policy-limit validation (#84) is skipped when this is not supplied — "
        "ArogyaRakshak never guesses a policy's coverage limit.",
    )


class PolicyLimitCheck(BaseModel):
    """Result of comparing an estimated cost against a declared policy sum insured."""

    sum_insured: float
    estimated_cost: float
    exceeds_limit: bool
    shortfall_amount: float = Field(
        ..., description="Amount by which estimated_cost exceeds sum_insured; 0 when within limit."
    )
    note: str


def check_policy_limit(estimated_cost: float, sum_insured: Optional[float]) -> Optional[PolicyLimitCheck]:
    """Flags an estimated cost that exceeds the policyholder's declared sum insured.

    Returns None when no sum insured was declared — absence of the field must never be
    read as "within limit", so callers must not treat None as a clean bill of health.
    """
    if sum_insured is None:
        return None

    exceeds = estimated_cost > sum_insured
    shortfall = round(estimated_cost - sum_insured, 2) if exceeds else 0.0
    note = (
        f"Estimated cost (₹{estimated_cost:,.2f}) exceeds the declared sum insured "
        f"(₹{sum_insured:,.2f}) by ₹{shortfall:,.2f}. The insurer may only approve "
        "cashless treatment up to the policy limit; the balance would typically be "
        "payable out of pocket or via reimbursement under a separate policy."
        if exceeds
        else (
            f"Estimated cost (₹{estimated_cost:,.2f}) is within the declared sum "
            f"insured (₹{sum_insured:,.2f})."
        )
    )
    return PolicyLimitCheck(
        sum_insured=sum_insured,
        estimated_cost=estimated_cost,
        exceeds_limit=exceeds,
        shortfall_amount=shortfall,
        note=note,
    )


class ClaimPackage(BaseModel):
    claim_id: str
    form_data: ClaimData
    form_filled_pdf_path: Optional[str] = None
    form_filled_pdf_url: Optional[str] = None
    status: str = Field("ready_for_review", description='"ready_for_review" | "completed"')
    policy_limit_check: Optional[PolicyLimitCheck] = Field(
        None, description="Set only when the claim declared a sum_insured (#84)."
    )


def generate_preauth_pdf(claim_id: str, claim_input: ClaimData) -> bytes:
    """Generates an authentic IRDAI Standard Cashless Pre-Authorization Form (Annexure-B) PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    base = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FormTitle",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    sub_style = ParagraphStyle(
        "FormSub",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        alignment=1,
    )
    cell_label_style = ParagraphStyle(
        "CellLabel",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    cell_val_style = ParagraphStyle(
        "CellVal",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Header
    story.append(Paragraph("IRDAI STANDARD CASHLESS PRE-AUTHORIZATION REQUEST FORM", title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("ANNEXURE-B | GUIDELINES ON STANDARDIZATION OF HEALTH INSURANCE CLAIMS", sub_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Pre-Auth Dossier Ref: <b>{claim_id}</b> | Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M')}", sub_style))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#06b6d4")))
    story.append(Spacer(1, 10))

    # Form Fields Table. Labels come from daavisetu.schema.FORM_SECTIONS — the same
    # constants the universal claim-form JSON Schema (#79) annotates its fields with —
    # so the rendered form and the schema cannot silently drift apart.
    #
    # SEC-02: every value cell below is patient/policyholder-submitted (POST .../claim)
    # or extracted-from-document text — untrusted. ReportLab's Paragraph parses its text
    # as a small XML/HTML dialect, so an unescaped '<' either crashes the PDF build or
    # lets submitted text inject markup into a document that is later signed and filed
    # with an insurer. Escaped with xml.sax.saxutils.escape before rendering; normal
    # medical text such as "Hb < 5.0 mg/dL" renders as literal text, not a crash.
    table_data = [
        [
            Paragraph(FORM_SECTIONS["patient_name"], cell_label_style),
            Paragraph(_xml_escape(claim_input.patient_name), cell_val_style),
            Paragraph(FORM_SECTIONS["policy_number"], cell_label_style),
            Paragraph(_xml_escape(claim_input.policy_number), cell_val_style),
        ],
        [
            Paragraph(FORM_SECTIONS["hospital_name"], cell_label_style),
            Paragraph(_xml_escape(claim_input.hospital_name), cell_val_style),
            Paragraph(FORM_SECTIONS["estimated_cost"], cell_label_style),
            Paragraph(f"INR {claim_input.estimated_cost:,.2f}", cell_val_style),
        ],
        [
            Paragraph(FORM_SECTIONS["diagnosis"], cell_label_style),
            Paragraph(_xml_escape(claim_input.diagnosis), cell_val_style),
            Paragraph(FORM_SECTIONS["treatment_plan"], cell_label_style),
            Paragraph(_xml_escape(claim_input.treatment_plan), cell_val_style),
        ],
    ]

    t = Table(table_data, colWidths=[130, 130, 130, 130])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(t)
    story.append(Spacer(1, 14))

    # Policy-limit warning (#84) — only rendered when a sum insured was actually
    # declared and the estimate exceeds it. Never asserted when sum_insured is None:
    # silence here must not be mistaken for "within limit".
    limit_check = check_policy_limit(claim_input.estimated_cost, claim_input.sum_insured)
    if limit_check and limit_check.exceeds_limit:
        warn_style = ParagraphStyle(
            "PolicyLimitWarning",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#b91c1c"),
        )
        story.append(Paragraph(f"⚠ POLICY LIMIT ALERT: {limit_check.note}", warn_style))
        story.append(Spacer(1, 10))

    # Declarations section
    dec_style = ParagraphStyle(
        "DecStyle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
    )
    story.append(Paragraph("<b>PATIENT / INSURED DECLARATION:</b> I hereby declare that the clinical information provided above is complete and truthful to the best of my knowledge. I authorize the hospital and TPA to verify policy records in accordance with IRDAI protection guidelines.", dec_style))
    story.append(Spacer(1, 20))

    # Signature lines
    sig_table = Table(
        [
            [
                Paragraph("__________________________<br/><b>Patient / Attendant Signature</b>", cell_val_style),
                Paragraph("__________________________<br/><b>Hospital TPA Desk Stamp & Sign</b>", cell_val_style),
                Paragraph("__________________________<br/><b>Treating Doctor Sign & Reg No.</b>", cell_val_style),
            ]
        ],
        colWidths=[170, 175, 175]
    )
    sig_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(sig_table)

    doc.build(story)
    return buffer.getvalue()


def generate_claim_package(case_id: str, claim_input: ClaimData) -> ClaimPackage:
    """Auto-fills a claim form and returns the structured claim package with downloadable PDF endpoint."""
    logger.info(f"[DaaviSetu] Auto-filling claim form for Case: {case_id}")
    claim_id = f"CLAIM-{case_id.replace('CASE-', '')[:8]}"

    package = ClaimPackage(
        claim_id=claim_id,
        form_data=claim_input,
        form_filled_pdf_path=f"/api/v1/daavisetu/cases/{case_id}/claim/pdf",
        form_filled_pdf_url=f"/api/v1/daavisetu/cases/{case_id}/claim/pdf",
        status="ready_for_review",
        policy_limit_check=check_policy_limit(claim_input.estimated_cost, claim_input.sum_insured),
    )

    logger.info(f"[DaaviSetu] Created claim package {package.claim_id} with status {package.status}")
    return package
