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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


class ClaimData(BaseModel):
    policy_number: str = Field(..., description="Insurance policy ID")
    patient_name: str = Field(..., description="Full name of the patient")
    hospital_name: str = Field(..., description="Name of the hospital")
    diagnosis: str = Field(..., description="ICD-10 clinical diagnosis code or description")
    estimated_cost: float = Field(..., description="Estimated treatment cost")
    treatment_plan: str = Field(..., description="Summary of medical procedure or treatment plan")


class ClaimPackage(BaseModel):
    claim_id: str
    form_data: ClaimData
    form_filled_pdf_path: Optional[str] = None
    form_filled_pdf_url: Optional[str] = None
    status: str = Field("ready_for_review", description='"ready_for_review" | "completed"')


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

    # Form Fields Table
    table_data = [
        [
            Paragraph("1. PATIENT FULL NAME", cell_label_style),
            Paragraph(claim_input.patient_name, cell_val_style),
            Paragraph("2. HEALTH INSURANCE POLICY ID", cell_label_style),
            Paragraph(claim_input.policy_number, cell_val_style),
        ],
        [
            Paragraph("3. NETWORK HOSPITAL NAME", cell_label_style),
            Paragraph(claim_input.hospital_name, cell_val_style),
            Paragraph("4. ESTIMATED ADMISSION EXPENSES", cell_label_style),
            Paragraph(f"INR {claim_input.estimated_cost:,.2f}", cell_val_style),
        ],
        [
            Paragraph("5. PROVISIONAL / CLINICAL DIAGNOSIS", cell_label_style),
            Paragraph(claim_input.diagnosis, cell_val_style),
            Paragraph("6. PROPOSED MEDICAL PROCEDURE", cell_label_style),
            Paragraph(claim_input.treatment_plan, cell_val_style),
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
    )

    logger.info(f"[DaaviSetu] Created claim package {package.claim_id} with status {package.status}")
    return package
