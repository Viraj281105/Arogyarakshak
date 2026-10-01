from pathlib import Path

from dawacheck.nppa.downloader import (
    download_nppa_pdf,
    find_nppa_pdf_url,
)


def test_find_nppa_pdf_url() -> None:
    """The downloader should return the official NPPA PDF URL."""

    url = find_nppa_pdf_url()

    assert url.endswith(
        "83cfb8c85fc0ceeae3ca5063d1c2c763.pdf"
    )


def test_download_nppa_pdf(tmp_path: Path) -> None:
    """The downloader should save the NPPA PDF locally."""

    url = find_nppa_pdf_url()

    output_path = tmp_path / "NPPA_test.pdf"

    downloaded_path = download_nppa_pdf(
        url,
        output_path,
    )

    assert downloaded_path == output_path
    assert downloaded_path.exists()
    assert downloaded_path.stat().st_size > 0