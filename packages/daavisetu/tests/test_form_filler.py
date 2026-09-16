import io

import pytest
from reportlab.pdfgen import canvas

from daavisetu.form_filler import fill_pdf_form, list_form_fields, MalformedPdfError


def _fillable_pdf(field_names) -> bytes:
    """Builds a minimal AcroForm PDF fixture with one text field per name in
    `field_names` — a test fixture, not a claim to represent any real insurer's form."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    form = c.acroForm
    y = 700
    for name in field_names:
        form.textfield(
            name=name, tooltip=name, x=100, y=y, width=200, height=20,
            borderStyle="inset", forceBorder=True,
        )
        y -= 40
    c.save()
    return buffer.getvalue()


def test_list_form_fields_finds_all_fields():
    pdf_bytes = _fillable_pdf(["patient_name", "policy_number", "hospital_name"])
    fields = list_form_fields(pdf_bytes)
    names = {f.field_name for f in fields}
    assert names == {"patient_name", "policy_number", "hospital_name"}


def test_list_form_fields_empty_for_pdf_without_acroform():
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 700, "Just plain text, no form fields.")
    c.save()
    fields = list_form_fields(buffer.getvalue())
    assert fields == []


def test_fill_pdf_form_sets_field_values():
    pdf_bytes = _fillable_pdf(["patient_name", "policy_number"])
    filled = fill_pdf_form(pdf_bytes, {"patient_name": "Sunita Deshmukh", "policy_number": "POL-STAR-774411"})

    filled_fields = {f.field_name: f.current_value for f in list_form_fields(filled)}
    assert filled_fields["patient_name"] == "Sunita Deshmukh"
    assert filled_fields["policy_number"] == "POL-STAR-774411"


def test_fill_pdf_form_ignores_unknown_field_names():
    """Values for fields that don't exist on the template must not raise — the
    template's actual fields are the source of truth, not the caller's mapping."""
    pdf_bytes = _fillable_pdf(["patient_name"])
    filled = fill_pdf_form(pdf_bytes, {"patient_name": "Test", "nonexistent_field": "ignored"})
    filled_fields = {f.field_name: f.current_value for f in list_form_fields(filled)}
    assert filled_fields == {"patient_name": "Test"}


def test_fill_pdf_form_returns_valid_pdf_bytes():
    pdf_bytes = _fillable_pdf(["patient_name"])
    filled = fill_pdf_form(pdf_bytes, {"patient_name": "Test"})
    assert filled.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# SEC-12: a corrupted/non-PDF template must raise a controlled, catchable error —
# never an unhandled parser exception that would surface as a 500.
# ---------------------------------------------------------------------------


def test_list_form_fields_rejects_a_non_pdf_file():
    with pytest.raises(MalformedPdfError):
        list_form_fields(b"this is not a pdf at all, just plain text bytes")


def test_list_form_fields_rejects_an_empty_file():
    with pytest.raises(MalformedPdfError):
        list_form_fields(b"")


def test_list_form_fields_rejects_a_truncated_pdf():
    real_pdf = _fillable_pdf(["patient_name"])
    truncated = real_pdf[: len(real_pdf) // 2]
    with pytest.raises(MalformedPdfError):
        list_form_fields(truncated)


def test_fill_pdf_form_rejects_a_non_pdf_file():
    with pytest.raises(MalformedPdfError):
        fill_pdf_form(b"\x00\x01\x02not a pdf", {"patient_name": "Test"})


def test_fill_pdf_form_rejects_a_pdf_masquerading_random_bytes():
    """A file merely starting with the %PDF magic bytes but otherwise garbage must
    still be rejected cleanly, not crash partway through writing."""
    with pytest.raises(MalformedPdfError):
        fill_pdf_form(b"%PDF-1.4\n" + b"\xff" * 200, {"patient_name": "Test"})
