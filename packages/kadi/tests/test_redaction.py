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


# ---------------------------------------------------------------------------
# P2: Devanagari-labelled fields. Before this fix, only English labels
# ("Patient Name:", "Address:", ...) were redacted — a Hindi/Marathi-labelled identity
# field survived verbatim into the persisted document_text excerpt, even though this
# project explicitly supports trilingual documents.
# ---------------------------------------------------------------------------

HINDI_SAMPLE = (
    "लाइफलाइन मल्टीस्पेशियलिटी अस्पताल\n"
    "रोगी का नाम: रमेश कुलकर्णी\n"
    "संपर्क: 9876543210\n"
    "ईमेल: ramesh.kulkarni@example.com\n"
    "पता: 12 एमजी रोड, पुणे\n"
    "निदान: तीव्र एपेंडिसाइटिस\n"
    "परामर्श: 900\n"
    "आईसीयू: 18500\n"
)

MARATHI_SAMPLE = (
    "लाईफलाईन मल्टिस्पेशालिटी हॉस्पिटल\n"
    "रुग्णाचे नाव: रमेश कुलकर्णी\n"
    "मोबाईल: 9876543210\n"
    "पत्ता: १२ एमजी रोड, पुणे\n"
    "निदान: तीव्र अपेंडिसायटिस\n"
    "सल्ला: 900\n"
)


def test_redacts_hindi_labelled_patient_name():
    out = redact_pii(HINDI_SAMPLE)
    assert "रमेश कुलकर्णी" not in out
    assert "रोगी का नाम:" in out  # label kept for structure
    assert REDACTION_MARK in out


def test_redacts_hindi_labelled_address():
    out = redact_pii(HINDI_SAMPLE)
    assert "12 एमजी रोड" not in out
    assert "पता:" in out


def test_redacts_marathi_labelled_patient_name():
    out = redact_pii(MARATHI_SAMPLE)
    assert "रमेश कुलकर्णी" not in out
    assert "रुग्णाचे नाव:" in out


def test_hindi_document_preserves_clinical_content():
    """Redaction must not destroy the Devanagari clinical text downstream agents need,
    same invariant as the English case above."""
    out = redact_pii(HINDI_SAMPLE)
    assert "तीव्र एपेंडिसाइटिस" in out  # diagnosis
    assert "लाइफलाइन मल्टीस्पेशियलिटी अस्पताल" in out  # hospital name
    assert "परामर्श: 900" in out  # billing line


def test_devanagari_free_standing_identifiers_still_caught_by_script_independent_patterns():
    """Email/phone/Aadhaar patterns match by character shape, not by label language —
    confirms these already worked before this fix and still do after it."""
    out = redact_pii(HINDI_SAMPLE)
    assert "9876543210" not in out
    assert "ramesh.kulkarni@example.com" not in out


def test_contains_direct_identifier_detects_devanagari_labelled_fields():
    assert contains_direct_identifier(HINDI_SAMPLE) is True
    assert contains_direct_identifier(redact_pii(HINDI_SAMPLE)) is False
    assert contains_direct_identifier(MARATHI_SAMPLE) is True
    assert contains_direct_identifier(redact_pii(MARATHI_SAMPLE)) is False


def test_hindi_redaction_is_idempotent():
    once = redact_pii(HINDI_SAMPLE)
    assert redact_pii(once) == once


# ---------------------------------------------------------------------------
# SEC-11: whitespace/tabular layouts (no ':' or '-') and ABHA numbers.
# ---------------------------------------------------------------------------

TABULAR_SAMPLE = (
    "Lifeline Multispeciality Hospital\n"
    "Patient Name        Ramesh Kulkarni\n"
    "ABHA Number         91-2345-6789-0123\n"
    "Address             12 MG Road, Pune\n"
    "Diagnosis           Acute Appendicitis\n"
    "Consultation        900\n"
)


def test_redacts_patient_name_in_tabular_whitespace_layout():
    """A hospital document that lays fields out as a whitespace-aligned table, with no
    ':' or '-' separator at all, previously survived redaction entirely."""
    out = redact_pii(TABULAR_SAMPLE)
    assert "Ramesh Kulkarni" not in out
    assert "Patient Name" in out
    assert REDACTION_MARK in out


def test_redacts_abha_number_in_tabular_layout():
    out = redact_pii(TABULAR_SAMPLE)
    assert "91-2345-6789-0123" not in out
    assert "ABHA Number" in out


def test_tabular_layout_preserves_clinical_and_billing_content():
    out = redact_pii(TABULAR_SAMPLE)
    assert "Acute Appendicitis" in out
    assert "Consultation" in out and "900" in out
    assert "Lifeline Multispeciality Hospital" in out


def test_does_not_redact_ordinary_single_spaced_prose():
    """A single space must never be mistaken for a tabular label separator — only 2+
    spaces (or a tab) count, so normal sentences are untouched."""
    text = "Name calling is not permitted on hospital premises.\n"
    assert redact_pii(text) == text


def test_redacts_free_standing_abha_number_without_a_label():
    text = "ABDM health id on file: 91 2345 6789 0123 for verification.\n"
    out = redact_pii(text)
    assert "91 2345 6789 0123" not in out


def test_redacts_abha_number_with_no_separators():
    text = "Patient ABHA: 91234567890123\n"
    out = redact_pii(text)
    assert "91234567890123" not in out


def test_contains_direct_identifier_detects_tabular_layout():
    assert contains_direct_identifier(TABULAR_SAMPLE) is True
    assert contains_direct_identifier(redact_pii(TABULAR_SAMPLE)) is False


def test_tabular_redaction_is_idempotent():
    once = redact_pii(TABULAR_SAMPLE)
    assert redact_pii(once) == once
