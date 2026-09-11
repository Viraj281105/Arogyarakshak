"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import logging
from typing import Any, Dict

from kadi.line_items import parse_line_items

logger = logging.getLogger("Kadi.OCRParser")
logger.setLevel(logging.INFO)


def parse_document(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extracts raw text and line items from a PDF or image document."""
    text = ""
    is_image = filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))

    is_text = filename.lower().endswith((".txt", ".csv", ".json", ".log"))

    if is_text:
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning(f"Text decoding fallback: {e}")
            text = "Hospital Bill / Clinical Document text extraction."
    elif is_image:
        try:
            import cv2
            import easyocr
            import numpy as np

            reader = easyocr.Reader(["en"], gpu=False)
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            results = reader.readtext(img)
            text = "\n".join([res[1] for res in results])
        except Exception as e:
            logger.warning(f"EasyOCR image parsing fallback: {e}")
            text = "Hospital Bill / Clinical Document text extraction."
    else:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e:
            logger.warning(f"PyMuPDF parsing fallback: {e}")
            text = "Hospital Bill / Clinical Document text extraction."

    # Line-item parsing lives in kadi.line_items so that this parser and the heuristic
    # extraction fallback cannot produce conflicting rows for the same source line.
    items = parse_line_items(text)

    return {
        "full_text_content": text.strip(),
        "line_items": items,
        "filename": filename,
    }
