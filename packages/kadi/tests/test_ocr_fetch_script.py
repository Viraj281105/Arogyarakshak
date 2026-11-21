"""scripts/fetch_ocr_models.py: operator-run download step. Tests never download."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "fetch_ocr_models.py"


@pytest.fixture
def fetch():
    spec = importlib.util.spec_from_file_location("fetch_ocr_models", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_nothing_is_downloaded_without_the_explicit_flag(fetch, monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(fetch, "default_reader_factory", lambda *a: called.append(a))
    assert fetch.main(["--dest", str(tmp_path)]) == 2
    assert called == []


def test_download_flag_calls_the_reader_with_downloads_enabled(fetch, tmp_path):
    seen = {}

    def factory(languages, dest):
        seen["languages"] = tuple(languages)
        (dest / "devanagari.pth").write_bytes(b"x")

    files = fetch.fetch(["en", "hi"], tmp_path / "model", reader_factory=factory)
    assert seen["languages"] == ("en", "hi") and files == ["devanagari.pth"]


def test_unknown_language_is_rejected_before_any_download(fetch, tmp_path):
    with pytest.raises(ValueError):
        fetch.fetch(["xx"], tmp_path, reader_factory=lambda *a: pytest.fail("downloaded"))


def test_only_this_script_enables_downloads():
    assert "download_enabled=True" in SCRIPT.read_text(encoding="utf-8")
    parser = SCRIPT.parents[1] / "packages" / "kadi" / "kadi" / "ocr" / "ocr_parser.py"
    assert "download_enabled=False" in parser.read_text(encoding="utf-8")
