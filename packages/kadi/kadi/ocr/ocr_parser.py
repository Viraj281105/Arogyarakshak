"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import logging
import threading
from typing import Any, Dict, List, Optional

from kadi.line_items import parse_line_items

logger = logging.getLogger("Kadi.OCRParser")
logger.setLevel(logging.INFO)

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TEXT_EXTENSIONS = (".txt", ".csv", ".json", ".log")

# Decompression-bomb guard (P0-3): a small file can decode to an enormous pixel buffer
# (e.g. a crafted PNG a few KB on disk that decompresses to gigapixels), independent of
# the API's 10 MB upload BYTE limit, which only bounds the file on disk/in transit, not
# the decoded in-memory bitmap cv2.imdecode()/EasyOCR would build from it. These bound
# the decoded image itself, checked from the file header BEFORE the expensive full
# decode — a well-formed scanned hospital bill at print resolution is nowhere near these.
MAX_IMAGE_DIMENSION_PX = 8000
MAX_IMAGE_PIXELS = 40_000_000  # ~40 megapixels

# EasyOCR's Reader() loads its recognition/detection model weights from disk (or
# downloads them) on construction — expensive, and NOT something to redo on every
# request. Lazily built once per process and reused; double-checked locking so
# concurrent requests racing to build it cannot each construct their own copy
# simultaneously (each holds real memory for the model weights).
_easyocr_reader = None
_easyocr_reader_lock = threading.Lock()


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        with _easyocr_reader_lock:
            if _easyocr_reader is None:
                import easyocr

                logger.info("Initializing EasyOCR reader (once per process)...")
                _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader


def _check_image_dimensions(file_bytes: bytes) -> Optional[str]:
    """Peeks at the image's declared dimensions from its header, without decoding pixel
    data, using PIL's lazy Image.open(). Returns an error string if the image should be
    rejected, or None if it is within bounds.

    This must run BEFORE cv2.imdecode()/EasyOCR, both of which allocate a full decoded
    bitmap up front — by the time either would reject an oversized image, the memory
    spike has already happened.
    """
    try:
        from io import BytesIO

        from PIL import Image

        with Image.open(BytesIO(file_bytes)) as img:
            width, height = img.size
    except Exception as e:
        return f"Could not read image dimensions: {e}"

    if width <= 0 or height <= 0:
        return "Image has invalid (non-positive) dimensions."
    if width > MAX_IMAGE_DIMENSION_PX or height > MAX_IMAGE_DIMENSION_PX:
        return (
            f"Image dimensions {width}x{height} exceed the maximum allowed "
            f"{MAX_IMAGE_DIMENSION_PX}px per side."
        )
    if width * height > MAX_IMAGE_PIXELS:
        return (
            f"Image has {width * height:,} pixels, exceeding the {MAX_IMAGE_PIXELS:,} "
            "pixel limit."
        )
    return None


def _result(
    text: str,
    filename: str,
    extraction_ok: bool,
    extraction_error: Optional[str] = None,
    ocr_segments: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Builds the parser result, deriving line items only from real extracted text."""
    cleaned = (text or "").strip()
    return {
        # Per-segment OCR readings with the engine's own confidence (images only; text
        # and PDF text layers have no recognition uncertainty). Used to route
        # low-confidence readings to human transcription instead of trusting them.
        "ocr_segments": ocr_segments or [],
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
        dimension_error = _check_image_dimensions(file_bytes)
        if dimension_error:
            logger.warning("Rejected image %s before decode: %s", filename, dimension_error)
            return _result("", filename, False, dimension_error)

        try:
            import cv2
            import numpy as np

            reader = _get_easyocr_reader()
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return _result("", filename, False, "The image could not be decoded.")
            results = reader.readtext(img)
            text = "\n".join([res[1] for res in results])
            segments = [
                {
                    "text": res[1],
                    "confidence": float(res[2]),
                    "bbox": [[float(x), float(y)] for x, y in res[0]],
                }
                for res in results
                if len(res) >= 3
            ]
        except Exception as e:
            logger.warning("EasyOCR image parsing failed for %s: %s", filename, e)
            return _result("", filename, False, "Optical character recognition failed.")
        if not text.strip():
            return _result(
                "", filename, False, "No text could be recognised in the image."
            )
        return _result(text, filename, True, ocr_segments=segments)

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
