"""
Kadi Package.
"""

from .ocr.ocr_parser import parse_document
from .vector_store import KadiVectorStore
from .extraction import extract_entities_from_text, ExtractedEntities

__all__ = [
    "parse_document",
    "KadiVectorStore",
    "extract_entities_from_text",
    "ExtractedEntities",
]


