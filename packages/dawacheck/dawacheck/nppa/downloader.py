"""
NPPA Schedule-I PDF downloader.

Downloads the official NPPA 2025 Schedule-I
ceiling-price PDF.
"""

from pathlib import Path

import requests
import truststore


NPPA_PDF_URL = (
    "https://www.nppa.gov.in/storage/uploads/tender/"
    "83cfb8c85fc0ceeae3ca5063d1c2c763.pdf"
)

truststore.inject_into_ssl()


def find_nppa_pdf_url() -> str:
    """Return the official NPPA 2025 Schedule-I PDF URL."""

    return NPPA_PDF_URL


def download_nppa_pdf(
    pdf_url: str,
    output_path: str | Path,
) -> Path:
    """Download an NPPA PDF to the specified path."""

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    response = requests.get(
        pdf_url,
        timeout=60,
    )
    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    ).lower()

    if "pdf" not in content_type:
        raise ValueError(
            f"Expected a PDF response, "
            f"got Content-Type: {content_type}"
        )

    output_path.write_bytes(response.content)

    return output_path