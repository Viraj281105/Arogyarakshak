"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import logging
import math
import os
import threading
import time
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
# package stays free of the API's settings object. The default is English only; "hi,mr,en"
# turns Devanagari reading on.
DEFAULT_OCR_LANGUAGES: Tuple[str, ...] = ("en",)
SUPPORTED_OCR_LANGUAGES = frozenset({"en", "hi", "mr"})
OCR_LANGUAGES_ENV = "OCR_LANGUAGES"
DEVANAGARI_OCR_LANGUAGES = frozenset({"hi", "mr"})

# Bounds on the work one PDF can cause (all env-configurable except the hard ceilings).
PDF_OCR_DPI = 200
DEFAULT_PDF_MAX_PIXELS = 10_000_000  # OCR_PDF_MAX_PIXELS: rasterised page budget
MAX_EMBEDDED_IMAGE_PIXELS = MAX_IMAGE_PIXELS  # a page referencing a larger image is not rendered
DEFAULT_OCR_MAX_PAGES = 3  # OCR_MAX_PAGES: pages OCR'd per document
MAX_OCR_PAGES_PER_DOCUMENT = 10  # hard ceiling for OCR_MAX_PAGES
DEFAULT_DOCUMENT_BUDGET_SECONDS = 120.0  # OCR_DOCUMENT_BUDGET_SECONDS, checked between pages
DEFAULT_QUEUE_TIMEOUT_SECONDS = 30.0  # OCR_QUEUE_TIMEOUT_SECONDS: wait for the single OCR slot
MAX_GATE_PAGES = 300  # pages examined by the text-layer gate; more are reported, not read

OCR_UNAVAILABLE_MESSAGE = (
    "OCR models not installed on this server. An operator must install them at image build "
    "time (scripts/fetch_ocr_models.py); they are never downloaded while serving a request."
)
OCR_BUSY_MESSAGE = "OCR is busy with another document; try again shortly."

# Why a PDF page was not read (key) and how that is phrased for a person (value).
SKIP_REASON_TEXT = {
    "corrupted_text_layer_needs_devanagari_ocr": "corrupted text layer; set OCR_LANGUAGES=hi,mr,en",
    "page_cap": "over the OCR page cap",
    "ocr_failed": "OCR failed",
    "ocr_empty": "OCR found no text",
    "ocr_unavailable": "OCR models not installed",
    "ocr_busy": "OCR busy, try again shortly",
    "time_budget": "OCR time budget exhausted",
    "unsafe_page_image": "page image too large to render safely",
    "no_text_layer": "no text layer (image-only page)",
    "not_examined": "beyond the page examination limit",
}

# Wall clock; a module attribute so tests can control time.
_monotonic = time.monotonic
# One OCR job per process at a time: a flood of corrupted PDFs must queue (bounded wait) and
# then be told "busy", not pile up threads each holding a model's worth of memory.
_ocr_slot = threading.BoundedSemaphore(1)


class UnsupportedOCRLanguageError(ValueError):
    """OCR_LANGUAGES names a language code this build does not support."""


class OCRModelsUnavailableError(RuntimeError):
    """The OCR reader could not be built (weights missing, or an unusable combination)."""


def _env_number(name: str, default: float, minimum: float, maximum: Optional[float] = None) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if not math.isfinite(value):
        return default
    value = max(minimum, value)
    return min(maximum, value) if maximum is not None else value


def ocr_page_cap() -> int:
    """Pages OCR'd per document: OCR_MAX_PAGES (default 3), between 1 and the hard ceiling."""
    return int(
        _env_number("OCR_MAX_PAGES", DEFAULT_OCR_MAX_PAGES, 1, MAX_OCR_PAGES_PER_DOCUMENT)
    )


def _document_budget_seconds() -> float:
    return _env_number("OCR_DOCUMENT_BUDGET_SECONDS", DEFAULT_DOCUMENT_BUDGET_SECONDS, 1)


def _queue_timeout_seconds() -> float:
    return _env_number("OCR_QUEUE_TIMEOUT_SECONDS", DEFAULT_QUEUE_TIMEOUT_SECONDS, 0)


def _pdf_max_pixels() -> int:
    return int(_env_number("OCR_PDF_MAX_PIXELS", DEFAULT_PDF_MAX_PIXELS, 10_000, MAX_IMAGE_PIXELS))


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


# EasyOCR's Reader() loads its recognition/detection model weights from disk on construction
# — expensive, and NOT something to redo on every request. Lazily built once per language SET
# (order-insensitive) and reused; double-checked locking so concurrent requests racing to build
# it cannot each construct their own copy simultaneously (each holds real memory for the model
# weights). Weights are never downloaded here: see scripts/fetch_ocr_models.py.
_easyocr_readers: Dict[Tuple[str, ...], Any] = {}
_easyocr_reader_lock = threading.Lock()


def _model_directory() -> Optional[str]:
    base = os.environ.get("EASYOCR_MODULE_PATH", "").strip()
    return os.path.join(base, "model") if base else None


def _get_easyocr_reader(languages: Optional[Tuple[str, ...]] = None):
    key = tuple(sorted(set(languages or get_ocr_languages())))
    reader = _easyocr_readers.get(key)
    if reader is None:
        with _easyocr_reader_lock:
            reader = _easyocr_readers.get(key)
            if reader is None:
                try:
                    import easyocr

                    logger.info("Initializing EasyOCR reader for %s (once per process)...", key)
                    reader = easyocr.Reader(
                        list(key),
                        gpu=False,
                        download_enabled=False,
                        model_storage_directory=_model_directory(),
                    )
                except Exception as e:
                    logger.warning("EasyOCR reader could not be built: %s", type(e).__name__)
                    raise OCRModelsUnavailableError(OCR_UNAVAILABLE_MESSAGE) from e
                _easyocr_readers[key] = reader
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
    pages_total: int = 1,
    pages_read: Optional[int] = None,
    skipped_reasons: Optional[Dict[str, int]] = None,
    partial_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Builds the parser result, deriving line items only from real extracted text."""
    cleaned = (text or "").strip()
    reasons = dict(skipped_reasons or {})
    if pages_read is None:
        pages_read = 1 if extraction_ok else 0
    skipped = sum(reasons.values())
    return {
        # Per-segment OCR readings with the engine's own confidence (images and OCR'd PDF
        # pages, the latter with a 1-based "page"; a trusted PDF text layer has no recognition
        # uncertainty). Used to route low-confidence readings to human transcription.
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
        # Counts only, never document text.
        "warnings": list(warnings or []),
        # A document with unread pages must never look complete: extraction_ok can be True
        # (at least one page was read) while partial is True and partial_reason says why.
        "pages_total": pages_total,
        "pages_read": pages_read,
        "pages_skipped": skipped,
        "skipped_reasons": reasons,
        "partial": skipped > 0,
        "partial_reason": partial_reason if skipped > 0 else None,
    }


def parse_document(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extracts raw text and line items from a PDF, image or plain-text document.

    Returns a dict carrying `extraction_ok`. When false, `full_text_content` is empty and
    `extraction_error` explains why — the caller must surface the failure rather than
    treating the document as successfully processed. Also check `partial`: when true some
    PDF pages were not read and `partial_reason` says which and why.
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
        return _parse_image(file_bytes, filename, file_type)

    return _parse_pdf(file_bytes, filename, file_type)


def _parse_image(file_bytes: bytes, filename: str, file_type: str) -> Dict[str, Any]:
    dimension_error = _check_image_dimensions(file_bytes)
    if dimension_error:
        logger.warning("Rejected a .%s image before decode: %s", file_type, dimension_error)
        return _result("", filename, False, dimension_error)

    if not _ocr_slot.acquire(timeout=_queue_timeout_seconds()):
        return _result("", filename, False, OCR_BUSY_MESSAGE)
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
    except OCRModelsUnavailableError:
        return _result("", filename, False, OCR_UNAVAILABLE_MESSAGE)
    except Exception as e:
        logger.warning("EasyOCR image parsing failed for a .%s file: %s", file_type, type(e).__name__)
        return _result("", filename, False, "Optical character recognition failed.")
    finally:
        _ocr_slot.release()
    if not text.strip():
        return _result("", filename, False, "No text could be recognised in the image.")
    return _result(text, filename, True, ocr_segments=segments)


def _segments(results, page: Optional[int] = None) -> List[Dict[str, Any]]:
    out = []
    for res in results:
        if len(res) < 3:
            continue
        segment = {
            "text": res[1],
            "confidence": float(res[2]),
            "bbox": [[float(x), float(y)] for x, y in res[0]],
        }
        if page is not None:
            segment["page"] = page
        out.append(segment)
    return out


def _rasterise_page(page) -> Tuple[Any, Optional[str]]:
    """Renders one PDF page to a BGR numpy array in memory (nothing is written to disk).

    Returns ``(array, None)`` or ``(None, "unsafe_page_image")`` when the page must not be
    rendered: zero-area geometry, an embedded image above the pixel budget (decompression
    bomb), or a render that would exceed the pixel budget or the per-side limit. Limits are
    checked from the geometry before rendering and again on the pixmap before its samples are
    read.
    """
    import fitz
    import numpy as np

    unsafe = (None, "unsafe_page_image")
    width_pt, height_pt = float(page.rect.width), float(page.rect.height)
    if not (math.isfinite(width_pt) and math.isfinite(height_pt) and width_pt > 0 and height_pt > 0):
        return unsafe
    for image in page.get_images(full=True):
        if int(image[2]) * int(image[3]) > MAX_EMBEDDED_IMAGE_PIXELS:
            return unsafe

    budget = _pdf_max_pixels()
    scale = PDF_OCR_DPI / 72.0
    limit = min(
        math.sqrt(budget / (width_pt * height_pt)),
        (MAX_IMAGE_DIMENSION_PX - 1) / max(width_pt, height_pt),
    )
    if limit < scale:
        scale = limit * 0.999  # stay under the limit despite rounding up to whole pixels
    if scale <= 0:
        return unsafe
    out_w, out_h = math.ceil(width_pt * scale), math.ceil(height_pt * scale)
    if out_w * out_h > budget or max(out_w, out_h) > MAX_IMAGE_DIMENSION_PX:
        return unsafe

    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
    if pix.width * pix.height > budget or max(pix.width, pix.height) > MAX_IMAGE_DIMENSION_PX:
        return unsafe
    rgb = np.frombuffer(pix.samples_mv, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return np.ascontiguousarray(rgb[:, :, ::-1]), None


def _partial_reason(reasons: Dict[str, int], total: int) -> str:
    skipped = sum(reasons.values())
    details = "; ".join(f"{n} {SKIP_REASON_TEXT.get(k, k)}" for k, n in sorted(reasons.items()))
    return f"{skipped} of {total} page(s) were not read: {details}."


def _ocr_corrupted_pages(
    doc,
    corrupted: List[int],
    languages: Tuple[str, ...],
    page_texts: List[Optional[str]],
    segments: List[Dict[str, Any]],
    reasons: Dict[str, int],
) -> int:
    """OCR the pages whose text layer is corrupted. Returns the number of pages read.

    Every page that is not read is counted in ``reasons``; the corrupted text is never used.
    """
    if not DEVANAGARI_OCR_LANGUAGES.intersection(languages):
        # The English-only model would replace untrusted text with English-only noise
        # reported as success, so these pages are skipped and reported instead.
        reasons["corrupted_text_layer_needs_devanagari_ocr"] = len(corrupted)
        return 0
    if not _ocr_slot.acquire(timeout=_queue_timeout_seconds()):
        reasons["ocr_busy"] = len(corrupted)
        return 0
    read = 0
    try:
        try:
            reader = _get_easyocr_reader(languages)
        except OCRModelsUnavailableError:
            reasons["ocr_unavailable"] = len(corrupted)
            return 0
        cap = ocr_page_cap()
        deadline = _monotonic() + _document_budget_seconds()
        attempted = 0
        for index in corrupted:
            if attempted >= cap:
                reasons["page_cap"] = reasons.get("page_cap", 0) + 1
                continue
            if _monotonic() >= deadline:
                reasons["time_budget"] = reasons.get("time_budget", 0) + 1
                continue
            try:
                array, reason = _rasterise_page(doc[index])
                if array is None:
                    reasons[reason] = reasons.get(reason, 0) + 1
                    continue
                attempted += 1
                results = reader.readtext(array)
            except Exception as e:  # one bad page must not lose the others
                attempted += 1
                reasons["ocr_failed"] = reasons.get("ocr_failed", 0) + 1
                logger.warning("OCR of a corrupted PDF page failed: %s", type(e).__name__)
                continue
            text = "\n".join(res[1] for res in results)
            if not text.strip():
                reasons["ocr_empty"] = reasons.get("ocr_empty", 0) + 1
                continue
            page_texts[index] = text
            segments.extend(_segments(results, page=index + 1))
            read += 1
    finally:
        _ocr_slot.release()
    return read


def _parse_pdf(file_bytes: bytes, filename: str, file_type: str) -> Dict[str, Any]:
    """PDF text layer first, page by page; a page whose layer is judged corrupted is OCR'd.

    See kadi.pdf_text_quality: legacy-font and glyph-mapped Devanagari extract as plausible
    looking nonsense, so such a page is never trusted. Pages that cannot be read are counted
    by reason and reported as ``partial``; only counts are logged or recorded.
    """
    reasons: Dict[str, int] = {}
    segments: List[Dict[str, Any]] = []
    try:
        import fitz  # PyMuPDF

        languages = get_ocr_languages()  # validate eagerly: a bad setting must be visible
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            total = doc.page_count
            examined = min(total, MAX_GATE_PAGES)
            page_texts: List[Optional[str]] = [None] * examined
            corrupted: List[int] = []
            read = 0
            for index in range(examined):
                page = doc[index]
                text = page.get_text()
                if assess_text_layer(text).verdict == "corrupted":
                    corrupted.append(index)
                elif text.strip():
                    page_texts[index] = text
                    read += 1
                elif page.get_images():
                    reasons["no_text_layer"] = reasons.get("no_text_layer", 0) + 1
                else:
                    page_texts[index] = ""  # a genuinely blank page
                    read += 1
            if total > examined:
                reasons["not_examined"] = total - examined

            warnings: List[str] = []
            if corrupted:
                logger.info(
                    "PDF text layer judged unreliable on %d of %d page(s)", len(corrupted), total
                )
                warnings.append(
                    f"PDF text layer judged unreliable on {len(corrupted)} of {total} page(s); "
                    "the embedded text of those pages was not used."
                )
                read += _ocr_corrupted_pages(doc, corrupted, languages, page_texts, segments, reasons)
        text = "".join((t or "") + "\n" for t in page_texts)
    except UnsupportedOCRLanguageError as e:
        logger.error("OCR is misconfigured: %s", e)
        return _result("", filename, False, f"OCR is misconfigured: {e}")
    except Exception as e:
        logger.warning("PDF parsing failed for a .%s file: %s", file_type, type(e).__name__)
        return _result("", filename, False, "The PDF could not be read.")

    reason_text = _partial_reason(reasons, total) if reasons else None
    if reason_text:
        warnings.append(reason_text)
    info = {
        "warnings": warnings,
        "pages_total": total,
        "pages_read": read,
        "skipped_reasons": reasons,
        "partial_reason": reason_text,
    }
    if not text.strip():
        if "ocr_unavailable" in reasons:
            error = OCR_UNAVAILABLE_MESSAGE
        elif set(reasons) <= {"no_text_layer"}:
            error = (
                "The PDF contained no extractable text. It may be a scan — try uploading it "
                "as an image instead."
            )
        else:
            error = f"No text could be extracted. {reason_text}"
        info["pages_read"] = 0
        return _result("", filename, False, error, **info)
    return _result(text, filename, True, ocr_segments=segments, **info)
