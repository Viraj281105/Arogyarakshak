"""
DaaviSetu — Claim Package Assembler (#81).

Bundles everything ArogyaRakshak can honestly assemble for a cashless
pre-authorization submission into one ZIP: the generated Annexure-B PDF and a
redacted case-summary text excerpt (when one exists), plus a manifest that discloses
exactly what is and is not included.

What this does NOT include, by design: the original scanned bill/document the patient
uploaded. ArogyaRakshak's BYOD zero-retention policy (see
`scripts/ci_guardrails.py`'s `FORBIDDEN_PERSISTENT_DIRS` check and ADR-003) means an
uploaded file is read once for extraction and never written to disk or the database —
only de-identified structured entities and a redacted text excerpt survive that. Bundling
a "bill copy" that is not the actual document would be a fabrication, so the manifest
tells the user plainly to attach their own scanned bill before submitting to the insurer.
"""

import io
import zipfile
from datetime import datetime
from typing import Optional

MANIFEST_TEMPLATE = """ArogyaRakshak -- DaaviSetu Claim Package Manifest
Claim ID: {claim_id}
Case ID: {case_id}
Generated: {generated_at}

CONTENTS OF THIS PACKAGE
-------------------------
1. preauth_form.pdf
   The filled IRDAI Standard Cashless Pre-Authorization Request Form (Annexure-B),
   generated from the claim details you submitted.
{case_summary_line}
{readiness_line}

WHAT IS NOT INCLUDED, AND WHY
-------------------------------
This package does NOT include a copy of your original scanned hospital bill or
supporting documents. ArogyaRakshak does not retain uploaded documents after
extracting structured information from them (zero-retention by design) -- only the
de-identified text excerpt described above, if any, survives. You must attach your own
copy of the original bill, discharge summary, and any other documents your insurer
requires before submitting this package.
"""


def build_claim_package_zip(
    claim_id: str,
    case_id: str,
    preauth_pdf_bytes: bytes,
    case_summary_text: Optional[str] = None,
    readiness_text: Optional[str] = None,
) -> bytes:
    """Assembles the claim package ZIP and returns its bytes.

    `case_summary_text` is the case's redacted document-text excerpt, if Kadi
    extracted one (KadiEntity type="document_text"). It is never invented when
    absent — the manifest states plainly that no summary is included.

    `readiness_text` (ADR-011) is the documentation checklist, including any clinical
    facts a named reviewer actually confirmed or rejected. Absent means none was built.
    """
    generated_at = datetime.now().strftime("%d-%b-%Y %H:%M")
    case_summary_line = (
        "2. case_summary.txt\n"
        "   A redacted text excerpt of the uploaded document, as extracted by Kadi."
        if case_summary_text
        else "(No case document summary is included: none was extracted for this case.)"
    )
    readiness_line = (
        "3. preauth_readiness.txt\n"
        "   Documentation checklist for this case. Clinical facts are marked confirmed only\n"
        "   where a named reviewer confirmed them; it does not predict approval."
        if readiness_text
        else "(No readiness checklist is included.)"
    )

    manifest = MANIFEST_TEMPLATE.format(
        claim_id=claim_id,
        case_id=case_id,
        generated_at=generated_at,
        case_summary_line=case_summary_line,
        readiness_line=readiness_line,
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.txt", manifest)
        zf.writestr("preauth_form.pdf", preauth_pdf_bytes)
        if case_summary_text:
            zf.writestr("case_summary.txt", case_summary_text)
        if readiness_text:
            zf.writestr("preauth_readiness.txt", readiness_text)

    return buffer.getvalue()
