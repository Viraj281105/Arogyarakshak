"""
DaaviSetu — PDF Form-Field Mapping & Filler (#80).

Introspects and fills an existing fillable (AcroForm) PDF's named fields using pypdf.

This is a generic filling engine, not a claim to already ship a specific insurer's
proprietary pre-authorization form — ArogyaRakshak has no verified copy of any real
insurer's template on file, and shipping one under an insurer's name without
verifying its provenance would be a fabrication. Point it at any AcroForm PDF the
caller supplies (their own insurer's real template) and a field-name-to-value mapping;
`list_form_fields` lets a caller discover a template's actual field names first, and
`daavisetu.schema.get_claim_form_json_schema` (#79) gives DaaviSetu's own canonical
field names to map from.
"""

import io
from typing import Dict, List

from pydantic import BaseModel
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError


class MalformedPdfError(Exception):
    """SEC-12: a caller-supplied template could not be parsed as a PDF at all
    (corrupted, truncated, or not actually a PDF). Raised instead of letting pypdf's
    exception (or, for a non-PDF input, an arbitrary parsing exception) propagate
    unhandled up to a 500 — the caller should map this to a controlled 4xx response."""


class FormFieldInfo(BaseModel):
    field_name: str
    field_type: str
    current_value: str = ""


def _read_pdf(pdf_bytes: bytes) -> PdfReader:
    """Parses `pdf_bytes`, raising MalformedPdfError (never a raw pypdf/low-level
    exception) on anything that is not a well-formed PDF — a corrupted upload, a
    truncated file, or an entirely different file type someone renamed to .pdf."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        # PdfReader can construct successfully on some malformed inputs and only fail
        # once something actually walks the page tree — touching .pages forces that now,
        # in a place this module controls, rather than later inside pypdf internals.
        _ = len(reader.pages)
        return reader
    except MalformedPdfError:
        raise
    except (PdfReadError, ValueError, KeyError, IndexError, OSError) as e:
        raise MalformedPdfError(f"Could not parse the uploaded file as a PDF: {e}") from e


def list_form_fields(pdf_bytes: bytes) -> List[FormFieldInfo]:
    """Introspects an AcroForm PDF's fillable field names and current values — the
    "coordinate mapping" step of knowing which named fields exist before attempting
    to fill them. Returns an empty list for a PDF with no AcroForm fields at all.

    Raises MalformedPdfError (SEC-12) for a corrupted/non-PDF input rather than letting
    pypdf's exception propagate as an unhandled 500."""
    reader = _read_pdf(pdf_bytes)
    fields = reader.get_fields() or {}

    result = []
    for name, field in fields.items():
        field_type = str(field.get("/FT", "unknown"))
        value = field.get("/V", "")
        result.append(
            FormFieldInfo(field_name=name, field_type=field_type, current_value=str(value or ""))
        )
    return result


def fill_pdf_form(pdf_bytes: bytes, field_values: Dict[str, str]) -> bytes:
    """Fills the given AcroForm PDF's named fields with `field_values` and returns the
    filled PDF's bytes.

    Field names in `field_values` that do not exist on the template are silently
    ignored by pypdf's writer — callers who need to confirm a mapping actually landed
    should cross-check against `list_form_fields` first.

    Raises MalformedPdfError (SEC-12) for a corrupted/non-PDF input.
    """
    reader = _read_pdf(pdf_bytes)
    writer = PdfWriter()
    try:
        writer.append(reader)

        for page in writer.pages:
            writer.update_page_form_field_values(page, field_values)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()
    except MalformedPdfError:
        raise
    except (PdfReadError, ValueError, KeyError, IndexError, OSError) as e:
        raise MalformedPdfError(f"Could not fill the uploaded PDF template: {e}") from e
