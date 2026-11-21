"""OCR language setting, reader cache and the corrupted-text-layer PDF route (Wave 2, stream A).

All readers here are fakes: no model is loaded and nothing touches the network.
"""

import logging

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
CLEAN_ENGLISH_PAGE = (
    "Tax invoice for room rent and nursing charges. The patient was admitted on 12 March and "
    "discharged on 15 March. Total payable is as per the policy schedule."
)


class FakeReader:
    """Stands in for easyocr.Reader. Records what it was built with and what it read."""

    built: list = []

    def __init__(self, languages, gpu=False, **kwargs):
        self.languages = tuple(languages)
        self.reads: list = []
        FakeReader.built.append(self.languages)

    def readtext(self, image):
        self.reads.append(image)
        box = [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 5.0)]
        return [(box, "OCR READING", 0.91)]


@pytest.fixture
def fake_reader(monkeypatch):
    import easyocr

    FakeReader.built = []
    monkeypatch.setattr(easyocr, "Reader", FakeReader)
    monkeypatch.setattr(ocr_module, "_easyocr_readers", {})
    monkeypatch.delenv("OCR_LANGUAGES", raising=False)
    yield FakeReader
    ocr_module._easyocr_readers.clear()


def _pdf(*page_texts: str) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_textbox(fitz.Rect(40, 40, 550, 800), text, fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


# --- OCR_LANGUAGES ----------------------------------------------------------------------


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


def test_configured_tuple_is_what_the_reader_is_built_with(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    reader = ocr_module._get_easyocr_reader()
    assert reader.languages == ("hi", "mr", "en")


def test_reader_cache_is_keyed_by_the_language_tuple(fake_reader, monkeypatch):
    en_1 = ocr_module._get_easyocr_reader()
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    multi_1 = ocr_module._get_easyocr_reader()
    multi_2 = ocr_module._get_easyocr_reader()
    monkeypatch.delenv("OCR_LANGUAGES")
    en_2 = ocr_module._get_easyocr_reader()
    assert en_1 is en_2
    assert multi_1 is multi_2
    assert en_1 is not multi_1
    assert fake_reader.built == [("en",), ("hi", "mr", "en")]


def test_misconfigured_languages_surface_as_a_clear_extraction_error(fake_reader, monkeypatch):
    monkeypatch.setenv("OCR_LANGUAGES", "zz")
    png = _small_png()
    result = parse_document(png, "scan.png")
    assert result["extraction_ok"] is False
    assert "OCR_LANGUAGES" in result["extraction_error"]


def _small_png() -> bytes:
    import cv2

    ok, buf = cv2.imencode(".png", np.full((20, 40, 3), 255, np.uint8))
    assert ok
    return buf.tobytes()


# --- PDF route --------------------------------------------------------------------------


def test_clean_english_pdf_keeps_the_text_path_and_never_loads_a_reader(fake_reader):
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE), "bill.pdf")
    assert result["extraction_ok"] is True
    assert "Tax invoice" in result["full_text_content"]
    assert fake_reader.built == []
    assert result["ocr_segments"] == []
    assert result["warnings"] == []


def test_corrupted_page_is_rasterised_and_ocred_not_trusted(fake_reader):
    result = parse_document(_pdf(LEGACY_PAGE), "gazette.pdf")
    assert result["extraction_ok"] is True
    assert "OCR READING" in result["full_text_content"]
    assert "jftLVªh" not in result["full_text_content"]
    assert len(result["ocr_segments"]) == 1
    assert result["ocr_segments"][0]["confidence"] == pytest.approx(0.91)
    assert len(fake_reader.built) == 1


def test_only_the_corrupted_page_is_ocred_in_a_mixed_document(fake_reader):
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE, CLEAN_ENGLISH_PAGE), "mixed.pdf")
    text = result["full_text_content"]
    assert text.count("Tax invoice") == 2
    assert text.count("OCR READING") == 1
    assert "jftLVªh" not in text
    # Page order is preserved: clean, OCR, clean.
    assert text.index("Tax invoice") < text.index("OCR READING") < text.rindex("Tax invoice")
    reader = ocr_module._get_easyocr_reader()
    assert len(reader.reads) == 1
    assert isinstance(reader.reads[0], np.ndarray)
    assert reader.reads[0].ndim == 3


def test_decision_is_recorded_as_a_count_only(fake_reader):
    result = parse_document(_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "mixed.pdf")
    warnings = result["warnings"]
    assert any("1 of 2" in w for w in warnings)
    blob = " ".join(warnings)
    assert "jftLVªh" not in blob and "Tax invoice" not in blob and "mixed" not in blob


def test_english_only_ocr_of_a_corrupted_page_warns_that_reading_is_unreliable(fake_reader):
    result = parse_document(_pdf(LEGACY_PAGE), "gazette.pdf")
    assert any("Devanagari" in w for w in result["warnings"])


def test_devanagari_languages_configured_remove_the_unreliable_reading_warning(
    fake_reader, monkeypatch
):
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    result = parse_document(_pdf(LEGACY_PAGE), "gazette.pdf")
    assert not any("Devanagari" in w for w in result["warnings"])
    assert fake_reader.built == [("hi", "mr", "en")]


def test_default_behaviour_is_unchanged_for_english_pdfs_with_the_setting_on(
    fake_reader, monkeypatch
):
    pdf = _pdf(CLEAN_ENGLISH_PAGE)
    default = parse_document(pdf, "bill.pdf")
    monkeypatch.setenv("OCR_LANGUAGES", "hi,mr,en")
    enabled = parse_document(pdf, "bill.pdf")
    assert default["full_text_content"] == enabled["full_text_content"]
    assert default["line_items"] == enabled["line_items"]


def test_ocr_failure_on_a_corrupted_page_does_not_leak_the_corrupted_text(
    fake_reader, monkeypatch
):
    def boom(self, image):
        raise RuntimeError("model crashed")

    monkeypatch.setattr(FakeReader, "readtext", boom)
    result = parse_document(_pdf(LEGACY_PAGE), "gazette.pdf")
    assert result["extraction_ok"] is False
    assert "jftLVªh" not in result["full_text_content"]
    assert result["extraction_error"]


def test_logs_carry_no_document_text(fake_reader, caplog):
    with caplog.at_level(logging.DEBUG, logger="Kadi.OCRParser"):
        parse_document(_pdf(CLEAN_ENGLISH_PAGE, LEGACY_PAGE), "patient-name.pdf")
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "jftLVªh" not in logged
    assert "Tax invoice" not in logged
    assert "OCR READING" not in logged
    assert "patient-name" not in logged


def test_a_page_cap_bounds_ocr_work_and_is_reported(fake_reader, monkeypatch):
    monkeypatch.setattr(ocr_module, "MAX_OCR_PAGES_PER_DOCUMENT", 2)
    result = parse_document(_pdf(*([LEGACY_PAGE] * 4)), "long.pdf")
    reader = ocr_module._get_easyocr_reader()
    assert len(reader.reads) == 2
    assert any("2 of 4" in w and "skipped" in w for w in result["warnings"])
    assert "jftLVªh" not in result["full_text_content"]
