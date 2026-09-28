"""Verbatim clinical-statement annex (ADR-011)."""

from kadi.clinical_review.annex import (
    ANNEX_HEADING,
    NO_HUMAN_STATEMENT_NOTICE,
    STATEMENT_NATURE_NOTICE,
    render_annex,
)

STATEMENT = {
    "statement_id": "CS-1",
    "statement_version": 2,
    "finalized_at": "2026-09-20T10:00:00",
    "content_sha256": "ab" * 32,
    "clinical_question": "Was inpatient care clinically reasonable?",
    "reviewer_statement": "In my opinion, the records show <active> treatment & monitoring.",
    "limitations": "I did not examine the patient.",
    "coi_label": "Affiliated with the treating hospital",
    "coi_disclosure": "Visiting consultant",
    "evidence_reviewed": [{"label": "Diagnosis", "provenance": "AI_DERIVED"}],
    "reviewer_snapshot": {
        "name": "Dr. Demo Reviewer",
        "verification_label": "Self-declared registration — not verified by ArogyaRakshak",
        "registration_number": "MMC-000",
    },
}


def test_no_statement_means_explicit_notice():
    assert render_annex([]) == NO_HUMAN_STATEMENT_NOTICE
    assert "not the opinion of a named doctor" in NO_HUMAN_STATEMENT_NOTICE


def test_statement_is_verbatim_with_attribution_coi_and_limits():
    text = render_annex([STATEMENT])
    assert text.startswith(ANNEX_HEADING)
    assert STATEMENT["reviewer_statement"] in text
    assert "Affiliated with the treating hospital" in text
    assert "Self-declared registration" in text
    assert "I did not examine the patient." in text
    assert STATEMENT_NATURE_NOTICE in text
    assert "Verified Doctor" not in text


def test_annex_renders_into_pdf_with_markup_escaped():
    from billnyay.tools.pdf_compiler import compile_appeal_packet_bytes

    pdf = compile_appeal_packet_bytes("Letter body", clinical_annex=render_annex([STATEMENT]))
    assert pdf.startswith(b"%PDF")
