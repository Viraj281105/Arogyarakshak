import zipfile
from io import BytesIO

from daavisetu.package_assembler import build_claim_package_zip


def _zip_names(zip_bytes: bytes):
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        return set(zf.namelist())


def test_package_includes_manifest_and_pdf_without_summary():
    zip_bytes = build_claim_package_zip(
        claim_id="CLAIM-ABC123",
        case_id="CASE-ABC123",
        preauth_pdf_bytes=b"%PDF-1.4 fake pdf bytes",
    )
    names = _zip_names(zip_bytes)
    assert names == {"manifest.txt", "preauth_form.pdf"}

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        manifest = zf.read("manifest.txt").decode("utf-8")
        assert "CLAIM-ABC123" in manifest
        assert "does NOT include a copy of your original scanned hospital bill" in manifest
        assert "No case document summary is included" in manifest
        assert zf.read("preauth_form.pdf") == b"%PDF-1.4 fake pdf bytes"


def test_package_includes_case_summary_when_provided():
    zip_bytes = build_claim_package_zip(
        claim_id="CLAIM-XYZ789",
        case_id="CASE-XYZ789",
        preauth_pdf_bytes=b"%PDF-1.4 fake pdf bytes",
        case_summary_text="Redacted excerpt of the uploaded bill.",
    )
    names = _zip_names(zip_bytes)
    assert names == {"manifest.txt", "preauth_form.pdf", "case_summary.txt"}

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        assert zf.read("case_summary.txt").decode("utf-8") == "Redacted excerpt of the uploaded bill."
        manifest = zf.read("manifest.txt").decode("utf-8")
        assert "case_summary.txt" in manifest


def test_package_never_fabricates_an_original_bill_copy():
    """No matter the inputs, the assembler must never claim to include the original
    scanned document — only what ArogyaRakshak's zero-retention design actually keeps."""
    zip_bytes = build_claim_package_zip(
        claim_id="CLAIM-1",
        case_id="CASE-1",
        preauth_pdf_bytes=b"%PDF-1.4",
        case_summary_text="Some summary",
    )
    names = _zip_names(zip_bytes)
    assert "original_bill.pdf" not in names
    assert "bill_copy.pdf" not in names
    assert len(names) == 3
