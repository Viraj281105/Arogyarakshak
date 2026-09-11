"""Regression tests for direct-identifier redaction (ADR-003)."""

from kadi.redaction import REDACTION_MARK, contains_direct_identifier, redact_pii

SAMPLE = (
    "Lifeline Multispeciality Hospital\n"
    "Patient Name: Ramesh Kulkarni\n"
    "Contact: 9876543210\n"
    "Email: ramesh.kulkarni@example.com\n"
    "Aadhaar: 1234 5678 9012\n"
    "Address: 12 MG Road, Pune\n"
    "Diagnosis: Acute Appendicitis\n"
    "Denial Code: DEN-4471\n"
    "Consultation: 900\n"
    "ICU: 18500\n"
)


def test_removes_every_direct_identifier():
    out = redact_pii(SAMPLE)
    for identifier in (
        "Ramesh Kulkarni",
        "9876543210",
        "ramesh.kulkarni@example.com",
        "1234 5678 9012",
        "12 MG Road",
    ):
        assert identifier not in out, f"identifier survived redaction: {identifier}"


def test_preserves_clinical_and_billing_content():
    """The appeal pipeline consumes this text; it must stay useful."""
    out = redact_pii(SAMPLE)
    assert "Acute Appendicitis" in out
    assert "DEN-4471" in out
    assert "Consultation: 900" in out
    assert "ICU: 18500" in out
    assert "Lifeline Multispeciality Hospital" in out


def test_keeps_field_labels_for_structure():
    out = redact_pii(SAMPLE)
    assert "Patient Name:" in out
    assert REDACTION_MARK in out


def test_does_not_redact_currency_amounts():
    """Billed amounts must never be mistaken for phone numbers or IDs."""
    text = "Total Amount: 1800000\nICU: 18500\nRoom Rent: 2500\n"
    assert redact_pii(text) == text


def test_handles_empty_input():
    assert redact_pii("") == ""
    assert redact_pii(None) == ""


def test_contains_direct_identifier_detects_and_clears():
    assert contains_direct_identifier(SAMPLE) is True
    assert contains_direct_identifier(redact_pii(SAMPLE)) is False
    assert contains_direct_identifier("") is False


def test_redaction_is_idempotent():
    once = redact_pii(SAMPLE)
    assert redact_pii(once) == once
