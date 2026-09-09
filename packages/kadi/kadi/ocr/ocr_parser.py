"""
Kadi — Shared OCR Document Parser.

Parses hospital bills, prescriptions, or insurance rejection documents (PDF / Image)
extracting text, line items, amounts, and raw evidence chunks.
"""

import io
import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger("Kadi.OCRParser")
logger.setLevel(logging.INFO)


def parse_document(file_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """Extracts raw text and line items from a PDF or image document."""
    text = ""
    is_image = filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp"))

    if is_image:
        try:
            import cv2
            import easyocr
            import numpy as np

            reader = easyocr.Reader(["en"], gpu=False)
            nparr = np.frombuffer(file_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            results = reader.readtext(img)
            text = "\n".join([res[1] for res in results])
        except Exception as e:
            logger.warning(f"EasyOCR image parsing fallback: {e}")
            text = "Hospital Bill / Clinical Document text extraction."
    else:
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                text += page.get_text() + "\n"
        except Exception as e:
            logger.warning(f"PyMuPDF parsing fallback: {e}")
            text = "Hospital Bill / Clinical Document text extraction."

    items = []
    lines = text.split("\n")
    for line in lines:
        match = re.search(r"([A-Za-z\s]+)[\s:]+₹?(\d+\.?\d*)", line)
        if match:
            item_name = match.group(1).strip()
            price = float(match.group(2))
            lower_name = item_name.lower()
            summary_terms = {
                "total",
                "subtotal",
                "sub total",
                "sub-total",
                "grand total",
                "total bill",
                "total amount",
                "total charges",
                "net total",
                "net amount",
                "net payable",
                "amount payable",
                "balance due",
                "date",
                "invoice",
                "tax",
                "gst",
                "cgst",
                "sgst",
            }
            is_summary = (
                lower_name in summary_terms
                or lower_name.startswith(("total bill", "total amount", "total charges", "grand total", "net total", "sub total", "sub-total"))
            )
            if len(item_name) > 3 and not is_summary:
                items.append({"item": item_name, "charged": price})

    return {
        "full_text_content": text.strip(),
        "line_items": items,
        "filename": filename,
    }
