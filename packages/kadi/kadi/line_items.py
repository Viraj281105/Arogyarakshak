"""
Kadi — Shared Billing Line-Item Parsing.

Single source of truth for turning a raw document line into a billing line item.

Both the OCR parser (``kadi.ocr.ocr_parser``) and the heuristic extraction fallback
(``kadi.extraction``) previously carried their own near-duplicate regex and their own
summary-term filter. They disagreed: the same source line could be persisted twice under
two different names and two different amounts. Everything that interprets a
``<description> <amount>`` line now lives here so the two callers cannot drift apart.
"""

import re
from typing import Any, Dict, List, Optional

# Currency prefixes seen on Indian hospital bills.
_CURRENCY = r"(?:₹|rs\.?|inr)"

# A billing line is "<description><separator><optional currency><amount>" with the amount
# anchored to END OF LINE. Anchoring is what makes "Dolo 650: 33" resolve to
# (name="Dolo 650", amount=33) instead of (name="Dolo", amount=650) — i.e. it stops the
# drug strength being read as the price. Requiring the separator to be whitespace or a
# colon (never a hyphen) is what stops "Date: 2024-01-15" parsing as an item costing 15.
_LINE_ITEM_RE = re.compile(
    rf"^\s*(?P<name>\S.*?)[\s:]\s*{_CURRENCY}?\s*(?P<amount>\d[\d,]*(?:\.\d{{1,2}})?)\s*$",
    re.IGNORECASE,
)

# Totals, taxes and document metadata. These are not billable line items; counting them
# would double the audited total.
SUMMARY_TERMS = {
    "total",
    "subtotal",
    "sub total",
    "sub-total",
    "grand total",
    "total bill",
    "total amount",
    "total charges",
    "total due",
    "total payable",
    "net total",
    "net amount",
    "net payable",
    "amount payable",
    "amount due",
    "balance due",
    "balance",
    "rounded off",
    "round off",
    "discount",
    "advance",
    "advance paid",
    "amount paid",
    "date",
    "invoice",
    "invoice no",
    "invoice number",
    "bill no",
    "bill number",
    "receipt no",
    "tax",
    "gst",
    "cgst",
    "sgst",
    "igst",
    "vat",
    "mrp",
}

_SUMMARY_PREFIXES = (
    "total bill",
    "total amount",
    "total charges",
    "total due",
    "total payable",
    "grand total",
    "net total",
    "net amount",
    "net payable",
    "sub total",
    "sub-total",
    "subtotal",
    "amount payable",
    "amount due",
    "balance due",
)

# Short clinical abbreviations that are legitimate, frequently-overcharged bill lines.
# Without this allowlist a blanket minimum-length filter silently deletes "ICU" — the
# single most commonly inflated item on an Indian hospital bill.
SHORT_CLINICAL_TERMS = {
    "icu",
    "ccu",
    "hdu",
    "nicu",
    "picu",
    "sicu",
    "ot",
    "ct",
    "mri",
    "ecg",
    "ekg",
    "eeg",
    "usg",
    "abg",
    "cbc",
    "lft",
    "kft",
    "rft",
    "tsh",
    "crp",
    "esr",
    "hba1c",
    "iv",
    "im",
    "ppe",
    "tpa",
    "bp",
    "spo2",
    "xray",
    "x-ray",
    "echo",
    "dialysis",
}

# Dosage-form and route hints that mark a line as a medicine rather than a procedure.
_MEDICINE_HINTS = (
    "tab",
    "tablet",
    "cap",
    "capsule",
    "syr",
    "syrup",
    "inj",
    "injection",
    "vial",
    "ampoule",
    "infusion",
    "ointment",
    "cream",
    "drops",
    "suspension",
    "sachet",
    "mg",
    "mcg",
    "ml",
    "gm",
    "iu",
)

_MIN_NAME_LENGTH = 4

# Identity / contact fields. These carry digits and therefore match the line-item shape,
# but they are not charges. Left unfiltered, "Contact: 9876543210" was persisted as a
# billing item worth 9.8 billion rupees and "Aadhaar: 1234 5678 9012" leaked government-ID
# digits into an entity name. Matched on the label before the first colon, so legitimate
# lines such as "Doctor Consultation: 500" are unaffected.
IDENTITY_TERMS = {
    "patient",
    "patient name",
    "name",
    "insured",
    "insured name",
    "attendant",
    "guardian",
    "contact",
    "contact no",
    "contact number",
    "phone",
    "phone no",
    "mobile",
    "mobile no",
    "tel",
    "telephone",
    "email",
    "e-mail",
    "address",
    "residence",
    "city",
    "pin",
    "pincode",
    "pin code",
    "aadhaar",
    "aadhar",
    "uid",
    "pan",
    "uhid",
    "mrn",
    "age",
    "dob",
    "date of birth",
    "gender",
    "sex",
    "policy no",
    "policy number",
    "claim no",
    "claim number",
    "registration no",
    "reg no",
    "ip no",
    "opd no",
    "room no",
    "bed no",
    "ward no",
}

# No single hospital bill line item reaches ten integer digits; a value that long is an
# identifier (phone number, account number) that slipped through the label check.
_MAX_AMOUNT_DIGITS = 10


def is_identity_line(name: str) -> bool:
    """True when the description labels an identity/contact field rather than a charge."""
    label = name.split(":", 1)[0].strip().lower().rstrip(".-").strip()
    return label in IDENTITY_TERMS


def normalise_amount(raw: str) -> float:
    """Converts a captured amount such as ``"2,500.00"`` into a float."""
    return float(raw.replace(",", "").strip())


def is_summary_line(name: str) -> bool:
    """True when the description is a total/tax/metadata row rather than a charge."""
    lowered = name.lower().strip().rstrip(":").strip()
    if lowered in SUMMARY_TERMS:
        return True
    return lowered.startswith(_SUMMARY_PREFIXES)


def is_noise_name(name: str) -> bool:
    """True when the description is too short or too degraded to be a real item."""
    cleaned = name.strip()
    if not re.search(r"[A-Za-z]", cleaned):
        return True
    if len(cleaned) >= _MIN_NAME_LENGTH:
        return False
    # Short strings survive only if they are recognised clinical abbreviations.
    return cleaned.lower().strip(".:-") not in SHORT_CLINICAL_TERMS


# Words that make a trailing bare number a room/ward/bed identifier rather than a drug
# strength, so "Room 302" is not mistaken for a medicine the way "Dolo 650" is.
_NON_DRUG_LEADERS = {
    "room",
    "ward",
    "bed",
    "cabin",
    "floor",
    "suite",
    "counter",
    "block",
    "unit",
    "icu",
    "ot",
    "day",
    "days",
    "night",
    "visit",
    "visits",
    "session",
    "sessions",
}

# "<brand> <strength>" with the strength written bare, e.g. "Dolo 650", "Pan 40".
_BARE_STRENGTH_RE = re.compile(r"^([A-Za-z][A-Za-z\-]*)\s+(\d{2,4})$")


def looks_like_medicine(name: str) -> bool:
    """True when a description carries a dosage form, route or strength marker."""
    cleaned = name.strip()
    lowered = f" {cleaned.lower()} "

    # Explicit strength with a unit is unambiguous.
    if re.search(r"\d+\s*(mg|mcg|ml|gm|g|iu)\b", lowered):
        return True

    if any(f" {hint} " in lowered or f" {hint}." in lowered for hint in _MEDICINE_HINTS):
        return True

    # Bare trailing strength, e.g. "Dolo 650" — only when the leading word is not a
    # facility/occupancy term.
    bare = _BARE_STRENGTH_RE.match(cleaned)
    if bare and bare.group(1).lower() not in _NON_DRUG_LEADERS:
        return True

    return False


def parse_line_item(line: str) -> Optional[Dict[str, Any]]:
    """Parses one line into ``{"item", "charged"}``, or None if it is not a charge."""
    match = _LINE_ITEM_RE.match(line)
    if not match:
        return None

    name = match.group("name").strip().rstrip(":").strip()
    if not name or is_noise_name(name) or is_summary_line(name) or is_identity_line(name):
        return None

    raw_amount = match.group("amount")
    if len(raw_amount.replace(",", "").split(".")[0]) >= _MAX_AMOUNT_DIGITS:
        return None

    try:
        charged = normalise_amount(raw_amount)
    except ValueError:
        return None

    return {"item": name, "charged": charged}


def parse_line_items(text: str) -> List[Dict[str, Any]]:
    """Extracts every billable line item from a block of document text."""
    items: List[Dict[str, Any]] = []
    for line in (text or "").splitlines():
        item = parse_line_item(line)
        if item is not None:
            items.append(item)
    return items


def extract_total_amount(text: str) -> float:
    """Returns the document's stated grand total, or 0.0 when none is present.

    Prefers the most specific label available so that a "Total Amount" row is not shadowed
    by an earlier "Total Tax" row.
    """
    best = 0.0
    pattern = re.compile(
        rf"^\s*(?P<label>[^:\d]*\b(?:total|net|amount\s+payable|balance\s+due)\b[^:\d]*)"
        rf"[\s:]\s*{_CURRENCY}?\s*(?P<amount>\d[\d,]*(?:\.\d{{1,2}})?)\s*$",
        re.IGNORECASE,
    )
    for line in (text or "").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        label = match.group("label").lower()
        if any(skip in label for skip in ("tax", "gst", "discount", "advance")):
            continue
        try:
            value = normalise_amount(match.group("amount"))
        except ValueError:
            continue
        best = max(best, value)
    return best
