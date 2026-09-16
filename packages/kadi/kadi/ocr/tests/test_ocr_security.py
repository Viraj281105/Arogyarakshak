"""
Tests for the image decompression-bomb guard and EasyOCR reader reuse (P0-3).

Prior implementation: `cv2.imdecode()` was called on every uploaded image with no
dimension check first, and `easyocr.Reader(["en"], gpu=False)` was constructed fresh
inside every call to `parse_document` — loading model weights from disk (or triggering a
download) on every single image upload, and racing under concurrent requests.
"""

import io
import struct
import threading
import zlib

import pytest

from kadi.ocr.ocr_parser import (
    MAX_IMAGE_DIMENSION_PX,
    MAX_IMAGE_PIXELS,
    _check_image_dimensions,
    _get_easyocr_reader,
    parse_document,
)


def _make_png_with_declared_dimensions(width: int, height: int) -> bytes:
    """Builds a syntactically valid, TINY (~70 byte) PNG whose IHDR chunk declares
    arbitrary width/height — the classic decompression-bomb shape: a small file on disk
    that would decode to an enormous in-memory bitmap. The IDAT payload is bogus (does
    not actually contain `width*height` pixels of real data), which is irrelevant here:
    the guard under test must reject the image from the HEADER alone, before any
    attempt to decode real pixel data.
    """
    sig = b"\x89PNG\r\n\x1a\n"

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)  # 8-bit RGB
    idat_data = zlib.compress(b"\x00\xff\x00\x00")
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat_data) + chunk(b"IEND", b"")


# ---------------------------------------------------------------------------
# Dimension guard
# ---------------------------------------------------------------------------


def test_a_normal_sized_image_passes_the_dimension_check():
    png = _make_png_with_declared_dimensions(800, 600)
    assert _check_image_dimensions(png) is None


def test_an_image_over_the_pixel_count_limit_is_rejected():
    # 7000x6000 = 42M pixels > MAX_IMAGE_PIXELS (40M), with BOTH sides individually
    # under MAX_IMAGE_DIMENSION_PX (8000) — isolates the pixel-COUNT check from the
    # per-side check exercised separately below.
    width, height = 7000, 6000
    assert width <= MAX_IMAGE_DIMENSION_PX and height <= MAX_IMAGE_DIMENSION_PX
    assert width * height > MAX_IMAGE_PIXELS
    png = _make_png_with_declared_dimensions(width, height)
    error = _check_image_dimensions(png)
    assert error is not None
    assert "pixel" in error.lower()


def test_an_image_over_the_per_side_dimension_limit_is_rejected_even_with_few_total_pixels():
    # A pathologically thin-but-long image: tiny pixel COUNT, but one side is huge.
    width = MAX_IMAGE_DIMENSION_PX + 1000
    png = _make_png_with_declared_dimensions(width, 3)
    assert width * 3 < MAX_IMAGE_PIXELS  # pixel-count check alone would NOT catch this
    error = _check_image_dimensions(png)
    assert error is not None
    assert "dimensions" in error.lower()


def test_an_extreme_decompression_bomb_is_rejected():
    """A ~70-byte file declaring a 50000x50000 image (2.5 billion pixels) — the
    scenario the audit named. PIL's own DecompressionBombError fires for images this
    extreme; our guard must still surface it as a rejection, not propagate an
    unhandled exception up through parse_document."""
    png = _make_png_with_declared_dimensions(50000, 50000)
    assert len(png) < 200, "the point of a decompression bomb is a small file"
    error = _check_image_dimensions(png)
    assert error is not None


def test_dimension_check_runs_before_cv2_imdecode_never_allocates_the_bitmap(monkeypatch):
    """The guard must reject before the expensive decode is even attempted — verified
    by asserting parse_document never reaches cv2.imdecode for an oversized image."""
    import cv2

    called = {"imdecode": False}
    original_imdecode = cv2.imdecode

    def spy_imdecode(*args, **kwargs):
        called["imdecode"] = True
        return original_imdecode(*args, **kwargs)

    monkeypatch.setattr(cv2, "imdecode", spy_imdecode)

    png = _make_png_with_declared_dimensions(50000, 50000)
    result = parse_document(file_bytes=png, filename="bomb.png")

    assert result["extraction_ok"] is False
    assert called["imdecode"] is False, "cv2.imdecode was called despite the oversized image"


def test_oversized_image_is_reported_as_a_failure_not_silently_accepted():
    png = _make_png_with_declared_dimensions(20000, 20000)
    result = parse_document(file_bytes=png, filename="huge_scan.png")
    assert result["extraction_ok"] is False
    assert result["extraction_error"]
    assert result["full_text_content"] == ""
    assert result["line_items"] == []


def test_corrupt_image_header_fails_cleanly_not_with_an_unhandled_exception():
    garbage = b"not a real image at all, just random bytes 0123456789"
    error = _check_image_dimensions(garbage)
    assert error is not None
    # Must not raise — parse_document must be able to call this safely for any bytes.
    result = parse_document(file_bytes=garbage, filename="corrupt.png")
    assert result["extraction_ok"] is False


# ---------------------------------------------------------------------------
# EasyOCR reader reuse
# ---------------------------------------------------------------------------


class _FakeEasyOCRReader:
    """Stands in for easyocr.Reader so these tests exercise the singleton/locking logic
    in ocr_parser.py without paying for real model-weight loading (slow, and may need a
    network fetch on a machine with no cached EasyOCR models)."""

    instances_constructed = 0

    def __init__(self, *args, **kwargs):
        _FakeEasyOCRReader.instances_constructed += 1
        # A real construction is not instant; a small delay makes the race in the
        # concurrency test below actually exercisable instead of finishing too fast for
        # the lock's absence to matter.
        import time

        time.sleep(0.05)


@pytest.fixture
def fake_easyocr_reader(monkeypatch):
    import easyocr
    import kadi.ocr.ocr_parser as ocr_module

    _FakeEasyOCRReader.instances_constructed = 0
    monkeypatch.setattr(easyocr, "Reader", _FakeEasyOCRReader)
    ocr_module._easyocr_reader = None
    yield
    ocr_module._easyocr_reader = None


def test_easyocr_reader_is_a_singleton_reused_across_calls(fake_easyocr_reader):
    reader_1 = _get_easyocr_reader()
    reader_2 = _get_easyocr_reader()
    assert reader_1 is reader_2
    assert _FakeEasyOCRReader.instances_constructed == 1


def test_concurrent_reader_requests_all_get_the_same_instance(fake_easyocr_reader):
    """Regression guard for the race this fixes: before the lock, N concurrent first
    requests could each construct their own Reader() (each holding real model-weight
    memory) before any of them finished assigning the module-level singleton."""
    results = []
    barrier = threading.Barrier(5)

    def worker():
        barrier.wait()  # maximize the chance all 5 threads race into construction together
        results.append(_get_easyocr_reader())

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 5
    assert all(r is results[0] for r in results), "concurrent callers received different Reader instances"
    assert _FakeEasyOCRReader.instances_constructed == 1, (
        f"expected exactly 1 Reader construction under concurrent access, got "
        f"{_FakeEasyOCRReader.instances_constructed} — the lock did not prevent a race"
    )
