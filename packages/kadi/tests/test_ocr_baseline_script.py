"""scripts/devanagari_ocr_baseline.py with a fake reader: no model, no network, no real PDFs."""

import importlib.util
import json
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "devanagari_ocr_baseline.py"


def _load():
    spec = importlib.util.spec_from_file_location("devanagari_ocr_baseline", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def baseline():
    return _load()


class FakeReader:
    def __init__(self, languages):
        self.languages = tuple(languages)

    def readtext(self, image):
        box = [(0, 0), (1, 0), (1, 1), (0, 1)]
        return [(box, "alpha", 0.95), (box, "beta", 0.40), (box, "gamma", 1.0)]


def _pdf(path: Path, pages: int = 2) -> Path:
    doc = fitz.open()
    for _ in range(pages):
        doc.new_page().insert_text((40, 60), "hello")
    doc.save(path)
    doc.close()
    return path


def test_confidence_histogram_bins_and_clamps(baseline):
    hist = baseline.confidence_histogram([0.0, 0.05, 0.5, 0.95, 1.0, 1.2])
    assert len(hist) == 10
    assert hist[0] == 2 and hist[5] == 1 and hist[9] == 3
    assert sum(hist) == 6


def test_run_baseline_runs_both_language_configs_per_page(baseline, tmp_path):
    pdf = _pdf(tmp_path / "doc.pdf", pages=3)
    report = baseline.run_baseline([pdf], max_pages=2, reader_factory=FakeReader)
    assert [r["languages"] for r in report["runs"]] == [["en"], ["hi", "mr", "en"]]
    assert report["documents"] == {"doc.pdf": 2}
    for run in report["runs"]:
        assert len(run["pages"]) == 2
        page = run["pages"][0]
        assert page["segments"] == 3
        assert page["below_review_threshold"] == 1
        assert sum(page["confidence_histogram"]) == 3
        assert page["latency_s"] >= 0
        assert "texts" not in page
    assert "no WER/CER" in report["note"]
    assert not any(k in report for k in ("wer", "cer", "accuracy"))


def test_text_is_written_only_when_asked(baseline, tmp_path):
    pdf = _pdf(tmp_path / "doc.pdf", pages=1)
    report = baseline.run_baseline([pdf], reader_factory=FakeReader, include_text=True)
    assert report["runs"][0]["pages"][0]["texts"] == ["alpha", "beta", "gamma"]


def test_main_writes_json_outside_the_repo(baseline, tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    _pdf(docs / "a.pdf", pages=1)
    monkeypatch.setattr(baseline, "default_reader_factory", FakeReader)
    monkeypatch.setattr(baseline, "run_baseline", _bind(baseline))
    out = tmp_path / "out" / "report.json"
    assert baseline.main(["--docs", str(docs), "--out", str(out)]) == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["kind"] == "devanagari_ocr_baseline"


def _bind(baseline):
    original = baseline.run_baseline

    def run(*args, **kwargs):
        kwargs["reader_factory"] = FakeReader
        return original(*args, **kwargs)

    return run


def test_main_refuses_an_output_path_inside_the_repository(baseline, tmp_path, capsys):
    docs = tmp_path / "docs"
    docs.mkdir()
    _pdf(docs / "a.pdf", pages=1)
    inside = baseline.REPO_ROOT / "devanagari_baseline_should_not_exist.json"
    assert baseline.main(["--docs", str(docs), "--out", str(inside)]) == 2
    assert not inside.exists()
    assert "refusing" in capsys.readouterr().err


def test_main_fails_cleanly_when_no_pdfs_are_found(baseline, tmp_path):
    assert baseline.main(["--docs", str(tmp_path), "--out", str(tmp_path / "o.json")]) == 2


def test_default_docs_dir_resolves_from_a_linked_worktree(baseline):
    # Passes both in the main checkout and a worktree; only checks it returns a path.
    assert isinstance(baseline.default_docs_dir(), Path)


def test_real_easyocr_reads_a_rendered_english_line_when_weights_are_cached(baseline):
    """Model-dependent: skipped cleanly when the EasyOCR weights are not cached locally."""
    try:
        reader = baseline.default_reader_factory(("en",))
    except Exception as exc:  # missing weights (download is disabled) or no easyocr
        pytest.skip(f"EasyOCR weights unavailable: {type(exc).__name__}")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 80), "ROOM RENT 1500", fontsize=28)
    (_, image), = _raster(doc)
    record = baseline.measure_page(reader, image, include_text=True)
    assert record["segments"] >= 1
    assert any("ROOM" in t.upper() for t in record["texts"])


def _raster(doc):
    import numpy as np

    pix = doc[0].get_pixmap(dpi=150, colorspace=fitz.csRGB, alpha=False)
    rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    return [(1, np.ascontiguousarray(rgb[:, :, ::-1]))]
