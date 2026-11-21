"""OCR language setting, reader cache and the corrupted-text-layer PDF route (Wave 2, stream A).

All readers here are fakes: no model is loaded and nothing touches the network.
"""

import logging
import threading
import time

import numpy as np
import pytest

import kadi.ocr.ocr_parser as ocr_module
from kadi.ocr.ocr_parser import (
    DEFAULT_OCR_LANGUAGES,
    UnsupportedOCRLanguageError,
    get_ocr_languages,
    parse_document,
)

fitz = pytest.importorskip("fitz")

LEGACY_PAGE = (
    "jftLVªh laö Mhö ,yö&33004@99 vlk/kj.k izkf/dkj ls izdkf'kr ubZ fnYyh] c`gLifrokj] "
    "vizSy 27] 2017 Hkkx II mi&[k.M izkf/dkj ls izdkf'kr ubZ fnYyh] c`gLifrokj]"
)
ENGLISH_LINES = [
    "Tax invoice for room rent and nursing charges.",
    "The patient was admitted on 12 March and discharged on 15 March.",
    "Total payable is as per the policy schedule.",
]
CLEAN_ENGLISH_PAGE = "\n".join(ENGLISH_LINES)
BLANK_ERROR = (
    "The PDF contained no extractable text. It may be a scan — try uploading it "
    "as an image instead."
)


class FakeReader:
    """Stands in for easyocr.Reader. Records what it was built with and what it read."""

    built: list = []
    kwargs_seen: list = []
    fail_build: Exception | None = None

    def __init__(self, languages, gpu=False, **kwargs):
        if FakeReader.fail_build is not None:
            raise FakeReader.fail_build
        self.languages = tuple(languages)
        self.reads: list = []
        FakeReader.built.append(self.languages)
        FakeReader.kwargs_seen.append(kwargs)

    def readtext(self, image):
        self.reads.append(image)
        box = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        return [(box, "OCR READING", 0.91)]


@pytest.fixture
def fake_reader(monkeypatch):
    import easyocr

    FakeReader.built = []
    FakeReader.kwargs_seen = []
    FakeReader.fail_build = None
    monkeypatch.setattr(easyocr, "Reader", FakeReader)
    monkeypatch.setattr(ocr_module, "_easyocr_readers", {})
    for name in (
        "OCR_LANGUAGES",
        "OCR_MAX_PAGES",
        "OCR_DOCUMENT_BUDGET_SECONDS",
        "OCR_QUEUE_TIMEOUT_SECONDS",
        "OCR_PDF_MAX_PIXELS",
    ):
        monkeypatch.delenv(name, raising=False)
    yield FakeReader
    ocr_module._easyocr_readers.clear()


@pytest.fixture
def devanagari(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    return fake_reader


def _pdf(*page_texts: str) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        if text:
            for i, line in enumerate(text.split("\n")):
                page.insert_text((40, 60 + 20 * i), line, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def _legacy_pdf(*page_texts: str) -> bytes:
    """Pages of legacy-encoded text (long enough to wrap, so use a textbox)."""
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 550, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def _png(width: int, height: int) -> bytes:
    import cv2

    ok, buf = cv2.imencode(".png", np.zeros((height, width, 3), np.uint8))
    assert ok
    return buf.tobytes()


# --- OCR_LANGUAGES and the reader cache -----------------------------------------------


def test_default_languages_are_english_only(monkeypatch):
    monkeypatch.delenv("OCR_LANGUAGES", raising=False)
    assert DEFAULT_OCR_LANGUAGES == ("en",)
    assert get_ocr_languages() == ("en",)


def test_blank_setting_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "  ")
    assert get_ocr_languages() == ("en",)


def test_languages_are_parsed_in_order_and_normalised(monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", " hi , MR,en,hi ")
    assert get_ocr_languages() == ("hi", "mr", "en")


def test_unknown_language_code_is_rejected_clearly(monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "en,xx")
    with pytest.raises(UnsupportedOCRLanguageError) as err:
        get_ocr_languages()
    assert "xx" in str(err.value) and "OCR_LANGUAGES" in str(err.value)


def test_default_reader_is_built_with_english_only(fake_reader):
    reader = ocr_module._get_easyocr_reader()
    assert reader.languages == ("en",)
    assert fake_reader.built == [("en",)]


def test_configured_languages_build_one_reader_with_those_languages(devanagari):
    reader = ocr_module._get_easyocr_reader()
    assert sorted(reader.languages) == ["en", "hi", "mr"]


def test_reader_cache_key_ignores_language_order(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    first = ocr_module._get_easyocr_reader()
    monkeypatch.setenv("OCR_LANGUAGES", "en,hi,mr")
    second = ocr_module._get_easyocr_reader()
    monkeypatch.setenv("OCR_LANGUAGES", "mr,mr,hi,en")
    third = ocr_module._get_easyocr_reader()
    assert first is second is third
    assert len(fake_reader.built) == 1


def test_reader_cache_is_keyed_by_the_language_set(fake_reader, monkeypatch):
    en_1 = ocr_module._get_easyocr_reader()
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    multi = ocr_module._get_easyocr_reader()
    monkeypatch.delenv("OCR_LANGUAGES")
    en_2 = ocr_module._get_easyocr_reader()
    assert en_1 is en_2 and en_1 is not multi
    assert len(fake_reader.built) == 2


def test_reader_never_downloads_and_uses_the_configured_model_directory(fake_reader, monkeypatch):
    monkeypatch.setenv("EASYOCR_MODULE_PATH", "/opt/easyocr")
    ocr_module._get_easyocr_reader()
    kwargs = fake_reader.kwargs_seen[0]
    assert kwargs["download_enabled"] is False
    assert kwargs["model_storage_directory"].replace("\\", "/") == "/opt/easyocr/model"


def test_misconfigured_languages_surface_in_the_image_path(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "zz")
    result = parse_document(_png(40, 20), "scan.png")
    assert result["extraction_ok"] is False
    assert "OCR_LANGUAGES" in result["extraction_error"]


def test_misconfigured_languages_surface_even_for_a_clean_only_pdf(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "zz")
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE), "bill.pdf")
    assert result["extraction_ok"] is False
    assert "OCR_LANGUAGES" in result["extraction_error"]


# --- behaviour that must not change ------------------------------------------------------


def test_english_image_still_uses_an_english_reader(fake_reader):
    result = parse_document(_png(40, 20), "scan.png")
    assert fake_reader.built == [("en",)]
    assert result["extraction_ok"] is True
    assert result["full_text_content"] == "OCR READING"
    assert result["ocr_segments"][0]["confidence"] == pytest.approx(0.91)
    assert "page" not in result["ocr_segments"][0]
    assert result["partial"] is False


def test_golden_english_pdf_text_is_returned_verbatim(fake_reader):
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE), "bill.pdf")
    assert result["extraction_ok"] is True
    assert result["full_text_content"] == "\n".join(ENGLISH_LINES)
    assert fake_reader.built == []
    assert result["ocr_segments"] == []
    assert result["warnings"] == []
    assert (result["pages_total"], result["pages_read"], result["pages_skipped"]) == (1, 1, 0)
    assert result["partial"] is False and result["partial_reason"] is None


def test_english_pdf_never_constructs_a_reader_even_with_devanagari_enabled(devanagari):
    parse_document(_pdf(CLEAN_ENGLISH_PAGE, CLEAN_ENGLISH_PAGE), "bill.pdf")
    assert devanagari.built == []


@pytest.mark.parametrize(
    "text",
    [
        "Room charges bed/day 3000 and/or ICU 5000. Pay by cash/card. Discount/waiver nil.",
        "Patient uses iPhone and eBay app, email aBc@mail.com, ID XyZ12, McDonald Road",
        "Vitamin B12 500 μg daily after food. Dose 10 μg/kg twice a day. Take with water.",
    ],
)
def test_english_looking_pages_never_reach_ocr(devanagari, text):
    result = parse_document(_pdf(text), "bill.pdf")
    assert devanagari.built == []
    assert result["extraction_ok"] is True and result["partial"] is False


def test_blank_pdf_gives_the_scan_hint_exactly(fake_reader):
    result = parse_document(_pdf(""), "blank.pdf")
    assert result["extraction_ok"] is False
    assert result["extraction_error"] == BLANK_ERROR
    assert fake_reader.built == []


def test_default_behaviour_is_unchanged_for_english_pdfs_with_the_setting_on(fake_reader, monkeypatch):
    pdf = _pdf(CLEAN_ENGLISH_PAGE)
    default = parse_document(pdf, "bill.pdf")
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    enabled = parse_document(pdf, "bill.pdf")
    assert default["full_text_content"] == enabled["full_text_content"]
    assert default["line_items"] == enabled["line_items"]


# --- corrupted page route ------------------------------------------------------------


def test_corrupted_page_is_ocred_not_trusted(devanagari):
    result = parse_document(_legacy_pdf(LEGACY_PAGE), "gazette.pdf")
    assert result["extraction_ok"] is True
    assert result["full_text_content"] == "OCR READING"
    assert len(result["ocr_segments"]) == 1
    assert result["ocr_segments"][0]["page"] == 1
    assert result["ocr_segments"][0]["confidence"] == pytest.approx(0.91)
    assert result["partial"] is False


def test_only_the_corrupted_page_is_ocred_in_a_mixed_document(devanagari):
    pdf = _legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE, CLEAN_ENGLISH_PAGE)
    text = parse_document(pdf, "mixed.pdf")["full_text_content"]
    assert text.count("Tax invoice") == 2 and text.count("OCR READING") == 1
    assert "jftLVªh" not in text
    assert text.index("Tax invoice") < text.index("OCR READING") < text.rindex("Tax invoice")
    reader = ocr_module._get_easyocr_reader()
    assert len(reader.reads) == 1
    assert isinstance(reader.reads[0], np.ndarray) and reader.reads[0].ndim == 3


def test_ocr_segments_carry_the_page_index(devanagari):
    result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE, LEGACY_PAGE), "m.pdf")
    assert [s["page"] for s in result["ocr_segments"]] == [2, 3]


def test_decision_is_recorded_as_a_count_only(devanagari):
    result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "mixed.pdf")
    assert any("1 of 2" in w for w in result["warnings"])
    blob = " ".join(result["warnings"])
    assert "jftLVªh" not in blob and "Tax invoice" not in blob


# --- default en + corrupted page: skipped, never English-only noise -----------------------


def test_default_english_setting_skips_corrupted_pages_and_keeps_clean_ones(fake_reader):
    result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "mixed.pdf")
    assert fake_reader.built == []
    assert result["extraction_ok"] is True
    assert result["full_text_content"].count("Tax invoice") == 1
    assert "jftLVªh" not in result["full_text_content"] and "OCR READING" not in result["full_text_content"]
    assert result["partial"] is True
    assert result["pages_total"] == 2 and result["pages_read"] == 1 and result["pages_skipped"] == 1
    assert result["skipped_reasons"] == {"corrupted_text_layer_needs_devanagari_ocr": 1}
    assert "corrupted text layer; set OCR_LANGUAGES=hi,mr,en" in result["partial_reason"]


def test_default_english_setting_with_only_corrupted_pages_fails_with_the_reason(fake_reader):
    result = parse_document(_legacy_pdf(LEGACY_PAGE), "gazette.pdf")
    assert result["extraction_ok"] is False
    assert "OCR_LANGUAGES=hi,mr,en" in result["extraction_error"]
    assert result["full_text_content"] == ""
    assert result["partial"] is True


# --- partial documents never look complete -------------------------------------------------


def test_page_cap_default_and_ceiling_are_pinned():
    assert ocr_module.DEFAULT_OCR_MAX_PAGES == 3
    assert ocr_module.MAX_OCR_PAGES_PER_DOCUMENT == 10
    assert ocr_module.MAX_GATE_PAGES == 300


def test_pages_over_the_cap_are_reported_not_dropped_silently(devanagari):
    result = parse_document(_legacy_pdf(*([LEGACY_PAGE] * 5)), "long.pdf")
    reader = ocr_module._get_easyocr_reader()
    assert len(reader.reads) == 3
    assert (result["pages_total"], result["pages_read"], result["pages_skipped"]) == (5, 3, 2)
    assert result["skipped_reasons"] == {"page_cap": 2}
    assert result["partial"] is True and "2 of 5" in result["partial_reason"]
    assert "jftLVªh" not in result["full_text_content"]


def test_page_cap_env_is_clamped_to_the_hard_ceiling(devanagari, monkeypatch):
    monkeypatch.setenv("OCR_MAX_PAGES", "500")
    assert ocr_module.ocr_page_cap() == 10
    monkeypatch.setenv("OCR_MAX_PAGES", "0")
    assert ocr_module.ocr_page_cap() == 1
    monkeypatch.setenv("OCR_MAX_PAGES", "junk")
    assert ocr_module.ocr_page_cap() == 3


def test_a_page_whose_ocr_crashes_is_skipped_and_reported(devanagari, monkeypatch, caplog):
    def boom(self, image):
        raise RuntimeError("SECRETTEXT model crashed")

    monkeypatch.setattr(FakeReader, "readtext", boom)
    with caplog.at_level(logging.DEBUG, logger="Kadi.OCRParser"):
        result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "g.pdf")
    assert result["extraction_ok"] is True and result["partial"] is True
    assert result["skipped_reasons"] == {"ocr_failed": 1}
    assert "jftLVªh" not in result["full_text_content"]
    assert "SECRETTEXT" not in " ".join(r.getMessage() for r in caplog.records)


def test_all_pages_failing_ocr_is_an_extraction_failure(devanagari, monkeypatch):
    monkeypatch.setattr(FakeReader, "readtext", lambda self, image: (_ for _ in ()).throw(RuntimeError("x")))
    result = parse_document(_legacy_pdf(LEGACY_PAGE), "g.pdf")
    assert result["extraction_ok"] is False and result["partial"] is True
    assert result["extraction_error"]


def test_a_page_where_ocr_finds_nothing_is_skipped_and_reported(devanagari, monkeypatch):
    monkeypatch.setattr(FakeReader, "readtext", lambda self, image: [])
    result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "g.pdf")
    assert result["skipped_reasons"] == {"ocr_empty": 1}
    assert result["partial"] is True and result["pages_read"] == 1


def test_image_only_page_in_a_text_pdf_is_reported_as_unread(fake_reader):
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 60), ENGLISH_LINES[0])
    scan = doc.new_page()
    scan.insert_image(fitz.Rect(50, 50, 300, 300), stream=_png(50, 50))
    pdf = doc.tobytes()
    doc.close()
    result = parse_document(pdf, "mixed_scan.pdf")
    assert result["extraction_ok"] is True
    assert result["skipped_reasons"] == {"no_text_layer": 1}
    assert result["partial"] is True and result["pages_read"] == 1


def test_blank_page_without_images_is_not_partial(fake_reader):
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE, ""), "bill.pdf")
    assert result["partial"] is False and result["pages_skipped"] == 0


def test_pages_beyond_the_gate_cap_are_reported(fake_reader, monkeypatch):
    monkeypatch.setattr(ocr_module, "MAX_GATE_PAGES", 3)
    result = parse_document(_pdf(*([CLEAN_ENGLISH_PAGE] * 5)), "long.pdf")
    assert result["pages_total"] == 5 and result["pages_read"] == 3
    assert result["skipped_reasons"] == {"not_examined": 2}
    assert result["partial"] is True


# --- model availability ------------------------------------------------------------------


def test_missing_weights_keep_clean_pages_and_report_ocr_unavailable(devanagari):
    FakeReader.fail_build = FileNotFoundError("Missing /x/model/devanagari.pth and downloads disabled")
    result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "g.pdf")
    assert result["extraction_ok"] is True
    assert result["full_text_content"].count("Tax invoice") == 1
    assert result["skipped_reasons"] == {"ocr_unavailable": 1}
    assert result["partial"] is True
    assert any("OCR models not installed" in w for w in result["warnings"])


def test_missing_weights_with_no_clean_text_say_so_not_unreadable_pdf(devanagari):
    FakeReader.fail_build = FileNotFoundError("Missing weights")
    result = parse_document(_legacy_pdf(LEGACY_PAGE), "g.pdf")
    assert result["extraction_ok"] is False
    assert "OCR models not installed" in result["extraction_error"]
    assert "could not be read" not in result["extraction_error"]


def test_missing_weights_for_an_image_are_reported_distinctly(fake_reader):
    FakeReader.fail_build = FileNotFoundError("Missing weights")
    result = parse_document(_png(40, 20), "scan.png")
    assert result["extraction_ok"] is False
    assert "OCR models not installed" in result["extraction_error"]


def test_a_failed_build_is_not_cached(devanagari):
    FakeReader.fail_build = FileNotFoundError("Missing")
    parse_document(_png(40, 20), "scan.png")
    FakeReader.fail_build = None
    assert parse_document(_png(40, 20), "scan.png")["extraction_ok"] is True


# --- concurrency and time budget -------------------------------------------------------


def test_busy_ocr_skips_pages_instead_of_piling_up(devanagari, monkeypatch):
    monkeypatch.setenv("OCR_QUEUE_TIMEOUT_SECONDS", "0.05")
    assert ocr_module._ocr_slot.acquire(timeout=1)
    try:
        result = parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "g.pdf")
        image = parse_document(_png(40, 20), "scan.png")
    finally:
        ocr_module._ocr_slot.release()
    assert result["skipped_reasons"] == {"ocr_busy": 1} and result["partial"] is True
    assert image["extraction_ok"] is False and "busy" in image["extraction_error"].lower()
    assert devanagari.built == []


def test_only_one_ocr_job_runs_at_a_time(devanagari, monkeypatch):
    monkeypatch.setenv("OCR_QUEUE_TIMEOUT_SECONDS", "30")
    state = {"now": 0, "max": 0}
    lock = threading.Lock()

    def slow_read(self, image):
        with lock:
            state["now"] += 1
            state["max"] = max(state["max"], state["now"])
        time.sleep(0.05)
        with lock:
            state["now"] -= 1
        return [([(0, 0), (1, 0), (1, 1), (0, 1)], "x", 0.9)]

    monkeypatch.setattr(FakeReader, "readtext", slow_read)
    pdf = _legacy_pdf(LEGACY_PAGE)
    threads = [threading.Thread(target=parse_document, args=(pdf, "g.pdf")) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert state["max"] == 1


def test_document_time_budget_is_checked_between_pages(devanagari, monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(ocr_module, "_monotonic", lambda: clock["t"])
    monkeypatch.setenv("OCR_MAX_PAGES", "5")
    monkeypatch.setenv("OCR_DOCUMENT_BUDGET_SECONDS", "120")

    def timed_read(self, image):
        clock["t"] += 50
        return [([(0, 0), (1, 0), (1, 1), (0, 1)], "x", 0.9)]

    monkeypatch.setattr(FakeReader, "readtext", timed_read)
    result = parse_document(_legacy_pdf(*([LEGACY_PAGE] * 5)), "long.pdf")
    # elapsed before pages 1-3 is 0, 50 and 100 (< 120); before page 4 it is 150.
    assert result["pages_read"] == 3
    assert result["skipped_reasons"] == {"time_budget": 2}
    assert result["partial"] is True


# --- rasterisation limits ----------------------------------------------------------------


def test_raster_is_downscaled_to_the_pixel_budget(devanagari, monkeypatch):
    monkeypatch.setenv("OCR_PDF_MAX_PIXELS", "1000000")
    parse_document(_legacy_pdf(LEGACY_PAGE), "g.pdf")
    image = ocr_module._get_easyocr_reader().reads[0]
    assert image.shape[0] * image.shape[1] <= 1_000_000


def test_default_pixel_budget_is_ten_megapixels(devanagari):
    parse_document(_legacy_pdf(LEGACY_PAGE), "g.pdf")
    image = ocr_module._get_easyocr_reader().reads[0]
    assert ocr_module.DEFAULT_PDF_MAX_PIXELS == 10_000_000
    assert image.shape[0] * image.shape[1] <= 10_000_000


def test_per_side_limit_applies_after_scaling(devanagari, monkeypatch):
    monkeypatch.setenv("OCR_PDF_MAX_PIXELS", "40000000")
    doc = fitz.open()
    page = doc.new_page(width=14000, height=300)
    page.insert_textbox(fitz.Rect(10, 10, 13990, 290), LEGACY_PAGE, fontsize=10)
    pdf = doc.tobytes()
    doc.close()
    parse_document(pdf, "wide.pdf")
    image = ocr_module._get_easyocr_reader().reads[0]
    assert max(image.shape[:2]) <= ocr_module.MAX_IMAGE_DIMENSION_PX


def test_page_referencing_a_huge_embedded_image_is_refused(devanagari, monkeypatch):
    monkeypatch.setattr(ocr_module, "MAX_EMBEDDED_IMAGE_PIXELS", 1_000_000)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 550, 400), LEGACY_PAGE, fontsize=10)
    page.insert_image(fitz.Rect(50, 450, 300, 700), stream=_png(1500, 1500))
    pdf = doc.tobytes()
    doc.close()
    result = parse_document(pdf, "bomb.pdf")
    assert not any(r.reads for r in ocr_module._easyocr_readers.values())
    assert result["skipped_reasons"] == {"unsafe_page_image": 1}
    assert result["partial"] is True


def test_zero_area_page_is_refused_explicitly():
    class Rect:
        width = 0.0
        height = 100.0

    class Page:
        rect = Rect()

        def get_images(self, full=True):
            return []

    array, reason = ocr_module._rasterise_page(Page())
    assert array is None and reason == "unsafe_page_image"


def test_logs_carry_no_document_text(devanagari, caplog):
    with caplog.at_level(logging.DEBUG, logger="Kadi.OCRParser"):
        parse_document(_legacy_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "patient-name.pdf")
    logged = " ".join(r.getMessage() for r in caplog.records)
    for secret in ("jftLVªh", "Tax invoice", "OCR READING", "patient-name"):
        assert secret not in logged
