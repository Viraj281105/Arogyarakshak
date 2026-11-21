"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from kadi.line_items import parse_line_items
from kadi.pdf_text_quality import assess_text_layer

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

# OCR languages (Wave 2, stream A). Read from the OCR_LANGUAGES environment variable so this
# package stays free of the API's settings object. The default is English only, which keeps
# the behaviour from before Devanagari OCR was enabled; "hi,mr,en" turns Devanagari reading on.
DEFAULT_OCR_LANGUAGES: Tuple[str, ...] = ("en",)
SUPPORTED_OCR_LANGUAGES = frozenset({"en", "hi", "mr"})
OCR_LANGUAGES_ENV = "OCR_LANGUAGES"
DEVANAGARI_OCR_LANGUAGES = frozenset({"hi", "mr"})

# A corrupted PDF page is rasterised for OCR. 200 dpi was the resolution of the Devanagari
# probe in data/raw/devanagari_public_docs/README.md. CPU OCR is slow (about 30 s per page
# there), so the number of pages OCR'd for one document is capped; pages over the cap are
# skipped and the unreliable text layer is never used in their place.
PDF_OCR_DPI = 200
MAX_OCR_PAGES_PER_DOCUMENT = 10


class UnsupportedOCRLanguageError(ValueError):
    """OCR_LANGUAGES names a language code this build does not support."""


def get_ocr_languages() -> Tuple[str, ...]:
    """The OCR language tuple from OCR_LANGUAGES (comma separated), default ("en",).

    Codes are lower-cased, de-duplicated and kept in order. An unknown code raises
    UnsupportedOCRLanguageError instead of being passed to the model loader.
    """
    raw = os.environ.get(OCR_LANGUAGES_ENV, "")
    codes: List[str] = []
    for part in raw.split(","):
        code = part.strip().lower()
        if code and code not in codes:
            codes.append(code)
    if not codes:
        return DEFAULT_OCR_LANGUAGES
    unknown = [c for c in codes if c not in SUPPORTED_OCR_LANGUAGES]
    if unknown:
        raise UnsupportedOCRLanguageError(
            f"Unsupported {OCR_LANGUAGES_ENV} code(s): {', '.join(unknown)}. "
            f"Supported: {', '.join(sorted(SUPPORTED_OCR_LANGUAGES))}."
        )
    return tuple(codes)


# EasyOCR's Reader() loads its recognition/detection model weights from disk (or
# downloads them) on construction — expensive, and NOT something to redo on every
# request. Lazily built once per language tuple and reused; double-checked locking so
# concurrent requests racing to build it cannot each construct their own copy
# simultaneously (each holds real memory for the model weights).
_easyocr_readers: Dict[Tuple[str, ...], Any] = {}
_easyocr_reader_lock = threading.Lock()


def _get_easyocr_reader(languages: Optional[Tuple[str, ...]] = None):
    languages = tuple(languages) if languages else get_ocr_languages()
    reader = _easyocr_readers.get(languages)
    if reader is None:
        with _easyocr_reader_lock:
            reader = _easyocr_readers.get(languages)
            if reader is None:
                import easyocr

                logger.info("Initializing EasyOCR reader for %s (once per process)...", languages)
                reader = easyocr.Reader(list(languages), gpu=False)
                _easyocr_readers[languages] = reader
    return reader


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
    warnings: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Builds the parser result, deriving line items only from real extracted text."""
    cleaned = (text or "").strip()
    return {
        # Per-segment OCR readings with the engine's own confidence (images and OCR'd PDF
        # pages; a trusted PDF text layer has no recognition uncertainty). Used to route
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
        # Counts only, never document text: e.g. how many PDF pages had an unreliable text
        # layer and were read with OCR instead.
        "warnings": list(warnings or []),
    }


def parse_document(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extracts raw text and line items from a PDF, image or plain-text document.

    Returns a dict carrying `extraction_ok`. When false, `full_text_content` is empty and
    `extraction_error` explains why — the caller must surface the failure rather than
    treating the document as successfully processed.
    """
    lowered = (filename or "").lower()
    # Log the file type only: an uploaded file name can identify the patient (ADR-003).
    file_type = lowered.rsplit(".", 1)[-1] if "." in lowered else "(none)"

    if lowered.endswith(TEXT_EXTENSIONS):
        try:
            text = file_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning("Text decoding failed for a .%s file: %s", file_type, e)
            return _result("", filename, False, "Could not decode the text document.")
        if not text.strip():
            return _result("", filename, False, "The document contained no readable text.")
        return _result(text, filename, True)

    if lowered.endswith(IMAGE_EXTENSIONS):
        dimension_error = _check_image_dimensions(file_bytes)
        if dimension_error:
            logger.warning("Rejected a .%s image before decode: %s", file_type, dimension_error)
            return _result("", filename, False, dimension_error)

        try:
            import cv2
            import numpy as np

            reader = _get_easyocr_reader(get_ocr_languages())
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return _result("", filename, False, "The image could not be decoded.")
            results = reader.readtext(img)
            text = "\n".join([res[1] for res in results])
            segments = _segments(results)
        except UnsupportedOCRLanguageError as e:
            logger.error("OCR is misconfigured: %s", e)
            return _result("", filename, False, f"OCR is misconfigured: {e}")
        except Exception as e:
            logger.warning("EasyOCR image parsing failed for a .%s file: %s", file_type, e)
            return _result("", filename, False, "Optical character recognition failed.")
        if not text.strip():
            return _result(
                "", filename, False, "No text could be recognised in the image."
            )
        return _result(text, filename, True, ocr_segments=segments)

    return _parse_pdf(file_bytes, filename, file_type)


def _segments(results) -> List[Dict[str, Any]]:
    return [
        {
            "text": res[1],
            "confidence": float(res[2]),
            "bbox": [[float(x), float(y)] for x, y in res[0]],
        }
        for res in results
        if len(res) >= 3
    ]


def _rasterise_page(page) -> Any:
    """Renders one PDF page to a BGR numpy array in memory (nothing is written to disk).

    The render scale is reduced if the page at PDF_OCR_DPI would exceed the decoded-image
    pixel budget used for uploaded images.
    """
    import fitz
    import numpy as np

    scale = PDF_OCR_DPI / 72.0
    pixels = (page.rect.width * scale) * (page.rect.height * scale)
    if pixels > MAX_IMAGE_PIXELS:
        scale *= (MAX_IMAGE_PIXELS / pixels) ** 0.5
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return np.ascontiguousarray(rgb[:, :, ::-1])


def _parse_pdf(file_bytes: bytes, filename: str, file_type: str) -> Dict[str, Any]:
    """PDF text layer first, page by page; a page whose layer is judged corrupted is OCR'd.

    See kadi.pdf_text_quality: legacy-font and glyph-mapped Devanagari extract as plausible
    looking nonsense, so such a page is never trusted. Only counts are logged or recorded.
    """
    corrupted_pages: List[int] = []
    warnings: List[str] = []
    segments: List[Dict[str, Any]] = []
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_texts: List[Optional[str]] = []
        for index, page in enumerate(doc):
            text = page.get_text()
            if assess_text_layer(text).verdict == "corrupted":
                corrupted_pages.append(index)
                page_texts.append(None)  # filled by OCR below, or left empty
            else:
                page_texts.append(text)
        total_pages = len(page_texts)

        if corrupted_pages:
            logger.info(
                "PDF text layer judged unreliable on %d of %d page(s); routing them to OCR",
                len(corrupted_pages),
                total_pages,
            )
            warnings.append(
                f"PDF text layer judged unreliable on {len(corrupted_pages)} of {total_pages} "
                "page(s); those pages were read with OCR instead of the embedded text."
            )
            languages = get_ocr_languages()
            if not DEVANAGARI_OCR_LANGUAGES.intersection(languages):
                warnings.append(
                    f"OCR languages exclude Devanagari ({OCR_LANGUAGES_ENV}={','.join(languages)}); "
                    "the reading of those pages is unreliable. Set OCR_LANGUAGES=hi,mr,en."
                )
            to_read = corrupted_pages[:MAX_OCR_PAGES_PER_DOCUMENT]
            skipped = len(corrupted_pages) - len(to_read)
            if skipped:
                warnings.append(
                    f"OCR page cap reached: {skipped} of {total_pages} page(s) skipped "
                    f"(cap {MAX_OCR_PAGES_PER_DOCUMENT}); the unreliable text layer was not used."
                )
            reader = _get_easyocr_reader(languages)
            failed = 0
            for index in to_read:
                try:
                    results = reader.readtext(_rasterise_page(doc[index]))
                except Exception as e:  # one bad page must not lose the others
                    failed += 1
                    logger.warning("OCR of a corrupted PDF page failed: %s", type(e).__name__)
                    continue
                page_texts[index] = "\n".join(res[1] for res in results)
                segments.extend(_segments(results))
            if failed:
                warnings.append(f"OCR failed on {failed} of {len(to_read)} page(s) it attempted.")
        text = "".join((t or "") + "\n" for t in page_texts)
    except UnsupportedOCRLanguageError as e:
        logger.error("OCR is misconfigured: %s", e)
        return _result("", filename, False, f"OCR is misconfigured: {e}")
    except Exception as e:
        logger.warning("PyMuPDF parsing failed for a .%s file: %s", file_type, e)
        return _result("", filename, False, "The PDF could not be read.")

    if not text.strip():
        if corrupted_pages:
            return _result(
                "",
                filename,
                False,
                "The PDF text layer was unreliable and OCR produced no text. Try uploading "
                "the pages as images.",
                warnings=warnings,
            )
        return _result(
            "",
            filename,
            False,
            "The PDF contained no extractable text. It may be a scan — try uploading it "
            "as an image instead.",
        )
    return _result(text, filename, True, ocr_segments=segments, warnings=warnings)
