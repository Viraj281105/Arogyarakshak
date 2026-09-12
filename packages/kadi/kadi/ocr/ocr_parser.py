"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import logging
from typing import Any, Dict, Optional

from kadi.line_items import parse_line_items

logger = logging.getLogger("Kadi.OCRParser")
logger.setLevel(logging.INFO)

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TEXT_EXTENSIONS = (".txt", ".csv", ".json", ".log")


def _result(
    text: str,
    filename: str,
    extraction_ok: bool,
    extraction_error: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds the parser result, deriving line items only from real extracted text."""
    cleaned = (text or "").strip()
    return {
        "full_text_content": cleaned,
        # Line-item parsing lives in kadi.line_items so this parser and the heuristic
        # extraction fallback cannot produce conflicting rows for the same source line.
        "line_items": parse_line_items(cleaned) if extraction_ok else [],
        "filename": filename,
        # Callers MUST check this. Extraction failures previously substituted a fixed
        # placeholder sentence and returned it as though it were the document body, so the
        # pipeline reported "processed successfully" on a document it had never read.
        "extraction_ok": extraction_ok,
        "extraction_error": extraction_error,
    }


def parse_document(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extracts raw text and line items from a PDF, image or plain-text document.

    Returns a dict carrying `extraction_ok`. When false, `full_text_content` is empty and
    `extraction_error` explains why — the caller must surface the failure rather than
    treating the document as successfully processed.
    """
    lowered = (filename or "").lower()

    if lowered.endswith(TEXT_EXTENSIONS):
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning("Text decoding failed for %s: %s", filename, e)
            return _result("", filename, False, "Could not decode the text document.")
        if not text.strip():
            return _result("", filename, False, "The document contained no readable text.")
        return _result(text, filename, True)

    if lowered.endswith(IMAGE_EXTENSIONS):
        try:
            import cv2
            import easyocr
            import numpy as np

            reader = easyocr.Reader(["en"], gpu=False)
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return _result("", filename, False, "The image could not be decoded.")
            results = reader.readtext(img)
            text = "\n".join([res[1] for res in results])
        except Exception as e:
            logger.warning("EasyOCR image parsing failed for %s: %s", filename, e)
            return _result("", filename, False, "Optical character recognition failed.")
        if not text.strip():
            return _result(
                "", filename, False, "No text could be recognised in the image."
            )
        return _result(text, filename, True)

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text() + "\n"
    except Exception as e:
        logger.warning("PyMuPDF parsing failed for %s: %s", filename, e)
        return _result("", filename, False, "The PDF could not be read.")

    if not text.strip():
        return _result(
            "",
            filename,
            False,
            "The PDF contained no extractable text. It may be a scan — try uploading it "
            "as an image instead.",
        )
    return _result(text, filename, True)
