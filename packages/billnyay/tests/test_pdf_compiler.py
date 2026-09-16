"""SEC-02 regression: the LLM-drafted appeal letter (document-derived, untrusted) must
never crash or inject markup when compiled into the ReportLab appeal packet PDF."""

from billnyay.tools.pdf_compiler import compile_appeal_packet_bytes


def test_compiles_a_normal_appeal_letter():
    letter = (
        "### SUBJECT LINE: Formal Notice of Representation & Appeal\n\n"
        "Dear Sir/Madam,\n\nWe write to appeal the denial of claim #1234.\n\n"
        "Sincerely,\nPolicyholder"
    )
    pdf_bytes = compile_appeal_packet_bytes(letter)
    assert pdf_bytes.startswith(b"%PDF")


def test_survives_unescaped_angle_brackets_that_previously_crashed_reportlab():
    """Before the fix, ReportLab's Paragraph parser treated '<' as the start of a tag;
    malformed/unclosed markup raised inside doc.build(), turning any denial letter or
    OCR excerpt containing a stray '<' into a 500 on every appeal draft/download."""
    letter = "Denial reason: <script>alert(1)</script>\n\nPolicy clause: <unclosed tag here"
    pdf_bytes = compile_appeal_packet_bytes(letter)
    assert pdf_bytes.startswith(b"%PDF")


def test_survives_ampersand_and_normal_medical_comparison_text():
    letter = (
        "Lab findings: Hb < 5.0 mg/dL, ALT > 200 U/L.\n\n"
        "Johnson & Johnson supplies were billed at AT&T Tower Pharmacy."
    )
    pdf_bytes = compile_appeal_packet_bytes(letter)
    assert pdf_bytes.startswith(b"%PDF")


def test_survives_malformed_markup_in_a_heading_line():
    letter = "### Section <b onmouseover=alert(1)>Title\n\nBody text follows."
    pdf_bytes = compile_appeal_packet_bytes(letter)
    assert pdf_bytes.startswith(b"%PDF")


def test_fuzz_a_battery_of_adversarial_and_normal_paragraphs():
    payloads = [
        "<script>alert(1)</script>",
        "unterminated <tag attr='x",
        "5 < 10 and 10 > 5",
        "AT&T Hospital & Research Centre",
        "normal clinical text with no markup at all",
        "",
    ]
    for payload in payloads:
        pdf_bytes = compile_appeal_packet_bytes(f"Dear Sir,\n\n{payload}\n\nSincerely.")
        assert pdf_bytes.startswith(b"%PDF"), f"PDF build failed for payload: {payload!r}"


def test_empty_letter_still_compiles():
    pdf_bytes = compile_appeal_packet_bytes("")
    assert pdf_bytes.startswith(b"%PDF")
