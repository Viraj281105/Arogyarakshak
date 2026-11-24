"""
Kadi Package.

``parse_document`` is re-exported lazily (PEP 562): ``kadi.ocr.ocr_parser`` imports Kadi root
modules (``kadi.line_items``, ``kadi.pdf_text_quality``), so importing it while ``kadi`` itself
is being imported made ``kadi`` and ``kadi.ocr`` import each other at package level (ADR-027).
``from kadi import parse_document`` and ``kadi.parse_document`` behave as before; the OCR module
(and its heavy optional dependencies) now loads on first use instead of on ``import kadi``.
"""

from typing import TYPE_CHECKING, Any

from .extraction import extract_entities_from_text, ExtractedEntities
from .redaction import redact_pii, contains_direct_identifier

if TYPE_CHECKING:  # for type checkers and IDEs only; never executed
    from .ocr.ocr_parser import parse_document

__all__ = [
    "parse_document",
    "extract_entities_from_text",
    "ExtractedEntities",
    "redact_pii",
    "contains_direct_identifier",
]


def __getattr__(name: str) -> Any:
    if name == "parse_document":
        from .ocr.ocr_parser import parse_document

        globals()["parse_document"] = parse_document  # cache: later lookups skip __getattr__
        return parse_document
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
