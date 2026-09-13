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


class FormFieldInfo(BaseModel):
    field_name: str
    field_type: str
    current_value: str = ""


def list_form_fields(pdf_bytes: bytes) -> List[FormFieldInfo]:
    """Introspects an AcroForm PDF's fillable field names and current values — the
    "coordinate mapping" step of knowing which named fields exist before attempting
    to fill them. Returns an empty list for a PDF with no AcroForm fields at all."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
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
    """
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    writer.append(reader)

    for page in writer.pages:
        writer.update_page_form_field_values(page, field_values)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
