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

# SEC-09: a real hospital bill, even an itemized multi-day ICU stay, does not run to
# thousands of billable lines. Without a ceiling, a pathological document (a malformed
# OCR read that turns a scanned image into thousands of matching "noise" lines, or a
# deliberately crafted .txt/.csv upload) can push an unbounded number of KadiEntity rows
# into a single upload/extraction cycle — a memory and database-write exhaustion vector,
# not a real audit improvement. Configurable per call so a caller with a genuinely
# different bound (e.g. a test) is not forced to reach into module internals.
MAX_LINE_ITEMS = 500


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

    if any(
        f" {hint} " in lowered or f" {hint}." in lowered for hint in _MEDICINE_HINTS
    ):
        return True

    # Bare trailing strength, e.g. "Dolo 650" — only when the leading word is not a
    # facility/occupancy term.
    bare = _BARE_STRENGTH_RE.match(cleaned)
    if bare and bare.group(1).lower() not in _NON_DRUG_LEADERS:
        return True

    return False


# Leading numbering commonly produced by printed/ocr'd bill tables:
#   "01 OPD Consultation ..."
#   "1. ICU Day Charges ..."
# The number is a row identifier, not part of the bill description.
_LEADING_ROW_NUMBER_RE = re.compile(r"^\s*\d{1,3}\s*[\.\)\-:]\s*")

# Obvious document/reference metadata that can contain trailing numbers but can never
# represent a billable charge. These checks happen before numeric extraction so strings
# such as "IRDAI ... 2016" and "Page 3" do not become bill items.
_NON_BILLABLE_NAME_PATTERNS = (
    re.compile(r"^\s*page(?:\s+no(?:\.|)|\s+number)?\b", re.IGNORECASE),
    re.compile(
        r"^\s*(?:regulation|regulations|section|clause|chapter)\b", re.IGNORECASE
    ),
    re.compile(
        r"^\s*-\s*(?:regulation|regulations|section|clause|chapter)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:statute|policy reference|reference key|aliases?)\b", re.IGNORECASE
    ),
    re.compile(
        r"\b(?:jurisdiction|category|verification status|issued on|verified on)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"^\s*(?:dataset|test note|ocr edge|ocr noise|reference formulation)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*irdai\b", re.IGNORECASE),
)

# A pure numeric line in a vertically extracted PDF may be a row number, quantity,
# strength, or actual amount. This pattern is deliberately used only after a candidate
# description has been identified.
_PURE_AMOUNT_RE = re.compile(
    rf"^\s*{_CURRENCY}?\s*\d[\d,]*(?:\.\d{{1,2}})?\s*$",
    re.IGNORECASE,
)

# Common bare medicine strengths seen in the supplied DawaCheck dataset and in
# medicine packaging OCR. A line such as "augmentin 625" or "Pan 40" should not be
# treated as a billed amount merely because the parser sees a number at end of line.
_COMMON_MEDICINE_STRENGTHS = {
    40.0,
    50.0,
    75.0,
    100.0,
    125.0,
    200.0,
    250.0,
    500.0,
    625.0,
    650.0,
    750.0,
    1000.0,
    2000.0,
    3000.0,
    4000.0,
}

# "<brand> <strength>" where the strength is written without a unit.
_BARE_MEDICINE_STRENGTH_RE = re.compile(
    r"^\s*(?P<name>[A-Za-z][A-Za-z\-]*(?:\s+[A-Za-z][A-Za-z\-]*)?)\s+"
    r"(?P<strength>\d{2,4}(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)


def _clean_bill_name(name: str) -> str:
    """Normalizes a parsed billing description without changing the public API."""
    name = _LEADING_ROW_NUMBER_RE.sub("", name or "").strip()
    name = re.sub(r"^\s*(?:[•·▪◦\-]+)\s*", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip(" :|-").strip()


def _is_non_billable_document_name(name: str) -> bool:
    """True for page markers, reference/statutory appendix text and similar OCR noise."""
    cleaned = _clean_bill_name(name)
    lowered = cleaned.lower()

    if not cleaned:
        return True

    if any(pattern.search(cleaned) for pattern in _NON_BILLABLE_NAME_PATTERNS):
        return True

    if lowered in {
        "page",
        "reference",
        "reference key",
        "strength",
        "ceiling price",
        "aliases",
        "statute",
        "policy",
        "dataset summary",
        "test status",
        "benchmark",
        "hospital charge line",
        "line item",
        "description",
        "amount",
        "qty",
        "quantity",
    }:
        return True

    return False


def _is_bare_medicine_strength_line(name: str, charged: float) -> bool:
    """Narrow guard used for a bare medicine-strength value."""
    return bool(name) and charged in _COMMON_MEDICINE_STRENGTHS


def _has_explicit_price_marker(original: str, raw_amount: str) -> bool:
    """
    True when the amount is explicitly introduced as a price.

    Examples:
        "Dolo 650: 33"          -> True
        "Dolo 650 MRP Rs. 33"   -> True
        "Dolo 650 33"           -> False
        "augmentin 625"         -> False
    """
    escaped_amount = re.escape(raw_amount)
    return bool(
        re.search(
            rf"(?:[:]|(?:₹|rs\.?|inr))\s*{escaped_amount}\s*$",
            original,
            re.IGNORECASE,
        )
    )


def _is_bare_medicine_strength_source(original: str, charged: float) -> bool:
    """True when the complete source line is exactly a bare medicine-strength form."""
    if not original or charged not in _COMMON_MEDICINE_STRENGTHS:
        return False
    return _BARE_MEDICINE_STRENGTH_RE.match(original.strip()) is not None


def parse_line_item(line: str) -> Optional[Dict[str, Any]]:
    """
    Parses one line into ``{"item", "charged"}``, or None if it is not a charge.

    The amount is anchored to the end of the line. Metadata/reference/page lines are
    rejected explicitly. Bare medicine strengths are rejected only when the strength
    itself is what the parser would otherwise interpret as the charge; explicit prices
    such as "Dolo 650: 33" remain valid.
    """
    if not line or not line.strip():
        return None

    original = line.strip()
    match = _LINE_ITEM_RE.match(original)
    if not match:
        return None

    name = _clean_bill_name(match.group("name"))
    if (
        not name
        or _is_non_billable_document_name(name)
        or is_noise_name(name)
        or is_summary_line(name)
        or is_identity_line(name)
    ):
        return None

    raw_amount = match.group("amount")
    if len(raw_amount.replace(",", "").split(".")[0]) >= _MAX_AMOUNT_DIGITS:
        return None

    try:
        charged = normalise_amount(raw_amount)
    except ValueError:
        return None

    # "augmentin 625" / "Dolo 650" / "Pan 40" are reference/medicine strengths,
    # not prices. An explicit ":" or currency marker means the number is intentionally
    # presented as a price, so retain it (e.g. "Dolo 650: 33").
    if not _has_explicit_price_marker(
        original, raw_amount
    ) and _is_bare_medicine_strength_source(original, charged):
        return None

    # Long comma-separated alias/reference rows frequently end in a strength token:
    # "Mox 500, Novamox 500, Amoxil 500". These are reference-data prose, not charges.
    lowered_name = name.lower()
    if (
        "," in name
        and len(name) > 20
        and charged in _COMMON_MEDICINE_STRENGTHS
        and any(
            token in lowered_name
            for token in (
                "dolo",
                "crocin",
                "calpol",
                "pacimol",
                "mox",
                "augmentin",
                "amox",
                "pan ",
                "pantocid",
                "pantodac",
                "azithral",
                "aziwok",
                "zithrox",
            )
        )
    ):
        return None

    return {"item": name, "charged": charged}


def _is_vertical_bill_description(line: str) -> bool:
    """
    Identifies a likely description line whose amount may have been extracted into the
    next OCR/text line by a PDF column layout.
    """
    candidate = _clean_bill_name(line)
    if not candidate or len(candidate) < _MIN_NAME_LENGTH:
        return False
    if len(candidate) > 160:
        return False
    if not re.search(r"[A-Za-z]", candidate):
        return False
    if _is_non_billable_document_name(candidate):
        return False
    if is_summary_line(candidate) or is_identity_line(candidate):
        return False

    lowered = candidate.lower()
    blocked_phrases = (
        "benchmark",
        "test status",
        "dataset",
        "statute",
        "guideline",
        "regulation",
        "chapter",
        "clause",
        "reference formulation",
        "aliases",
        "verification status",
        "ocr stress",
    )
    if any(phrase in lowered for phrase in blocked_phrases):
        return False

    # A medicine-strength-only line is not a useful description candidate.
    if _BARE_MEDICINE_STRENGTH_RE.match(candidate):
        return False

    return True


def _extract_pure_amount(line: str) -> Optional[float]:
    """Returns a numeric amount when the whole OCR line is an amount."""
    if not _PURE_AMOUNT_RE.match(line or ""):
        return None

    raw = re.sub(rf"^\s*{_CURRENCY}\s*", "", line.strip(), flags=re.IGNORECASE)
    try:
        value = normalise_amount(raw)
    except ValueError:
        return None

    if len(raw.replace(",", "").split(".")[0]) >= _MAX_AMOUNT_DIGITS:
        return None
    return value


def parse_line_items(
    text: str, max_items: int = MAX_LINE_ITEMS
) -> List[Dict[str, Any]]:
    """
    Extracts billable line items from document text, up to `max_items`.

    Handles both normal one-line entries and a common PDF/OCR columnar form where the
    description and final amount are emitted on adjacent lines. Standalone numeric
    row numbers and quantities are ignored rather than treated as charges.
    """
    raw_lines = [
        re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()
    ]

    items: List[Dict[str, Any]] = []
    used: set[int] = set()

    def append_item(item: Optional[Dict[str, Any]]) -> None:
        if item is not None and len(items) < max_items:
            items.append(item)

    i = 0
    while i < len(raw_lines) and len(items) < max_items:
        if i in used:
            i += 1
            continue

        line = raw_lines[i]
        if not line:
            i += 1
            continue

        # Standalone page/row numbers are not charge descriptions.
        if re.fullmatch(r"\d{1,4}", line):
            i += 1
            continue

        direct = parse_line_item(line)
        if direct is not None:
            append_item(direct)
            used.add(i)
            i += 1
            continue

        # Reconstruct a vertical PDF table:
        #   01
        #   OPD Consultation ...
        #   1
        #   Rs. 450.00
        if _is_vertical_bill_description(line):
            candidate_name = _clean_bill_name(line)

            for j in range(i + 1, min(i + 4, len(raw_lines))):
                if j in used:
                    continue

                future = raw_lines[j]

                if re.fullmatch(r"\d{1,4}", future):
                    continue

                amount = _extract_pure_amount(future)
                if amount is None:
                    if _is_vertical_bill_description(future):
                        break
                    continue

                # A pure number on the next line is only safe to associate with the
                # description when the OCR shows a table-row marker immediately before
                # the description, or when the amount line itself carries an explicit
                # currency marker. Without that guard, reference text such as:
                #     augmentin
                #     625
                # would be misread as a hospital charge.
                previous_is_row_marker = (
                    i > 0
                    and re.fullmatch(r"\d{1,4}", raw_lines[i - 1] or "") is not None
                )
                amount_has_currency = bool(
                    re.match(rf"^\s*{_CURRENCY}", future, re.IGNORECASE)
                )
                if not previous_is_row_marker and not amount_has_currency:
                    continue

                synthetic = f"{candidate_name} {future}"
                parsed = parse_line_item(synthetic)

                if parsed is None:
                    # The synthetic form removes the explicit currency/colon relationship,
                    # so a legitimate amount can fail the stricter medicine-strength guard.
                    # Re-apply the normal non-billable checks directly for this vertical case.
                    if (
                        not _is_non_billable_document_name(candidate_name)
                        and not is_noise_name(candidate_name)
                        and not is_summary_line(candidate_name)
                        and not is_identity_line(candidate_name)
                        and not (
                            _BARE_MEDICINE_STRENGTH_RE.match(
                                f"{candidate_name} {int(amount) if amount.is_integer() else amount}"
                            )
                            and amount in _COMMON_MEDICINE_STRENGTHS
                        )
                    ):
                        parsed = {"item": candidate_name, "charged": amount}

                if parsed is not None:
                    append_item(parsed)
                    used.update({i, j})
                    for k in range(i + 1, j):
                        if re.fullmatch(r"\d{1,4}", raw_lines[k] or ""):
                            used.add(k)
                    break

        i += 1

    return items


_NAME_TOKEN_RE = re.compile(r"[a-z][a-z\-]{2,}")


def ground_medicine_source_lines(text: str, medicines: List[Dict[str, Any]]) -> None:
    """Sets ``source_line`` on each medicine dict to the description of the one document
    line it was read from, when that line can be identified with certainty.

    An extractor (the LLM especially) may normalise "Pan 40 (Strip of 15)" to "Pan 40",
    dropping what the document says about quantity or pack size — the facts needed to
    know whether a price is per tablet or per strip. A line is accepted only when it is
    the single line whose amount equals the medicine's cost and which contains a word of
    the medicine's name; otherwise ``source_line`` is left unset (never guessed).
    Mutates the dicts in place; the line text is used transiently and is not a stored field.
    """
    lines = [(parse_line_item(raw), raw) for raw in (text or "").splitlines()]
    for med in medicines:
        if med.get("source_line"):
            continue
        name = str(med.get("name") or "").lower()
        tokens = set(_NAME_TOKEN_RE.findall(name)) - {
            "tab",
            "tablet",
            "cap",
            "capsule",
            "inj",
            "syr",
        }
        try:
            cost = float(med.get("cost")) if med.get("cost") is not None else None
        except (TypeError, ValueError):
            cost = None
        if cost is None or not tokens:
            continue
        hits = [
            item["item"]
            for item, raw in lines
            if item is not None
            and abs(item["charged"] - cost) < 0.005
            and tokens & set(_NAME_TOKEN_RE.findall(raw.lower()))
        ]
        if len(hits) == 1:
            med["source_line"] = hits[0]


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
