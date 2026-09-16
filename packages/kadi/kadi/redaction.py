"""
Kadi — Direct-Identifier Redaction.

ADR-003 and the README state that persistent records retain only de-identified clinical
metadata. The raw OCR excerpt stored as a ``document_text`` entity previously violated
that: it kept the first 1000 characters of the document verbatim, patient name and
contact details included.

That excerpt cannot simply be dropped — BillNyay's appeal pipeline reads it to recover
denial codes, insurer reasons and policy clauses. So direct identifiers are stripped while
the clinical and billing content the agents need is preserved.

Scope note: this removes *direct* identifiers (name, phone, government ID, email,
address). It is not formal anonymisation — a diagnosis plus a hospital name can still be
re-identifying in a small population. Documentation must not claim more than this.
"""

import re
from typing import List, Pattern, Tuple

REDACTION_MARK = "[REDACTED]"

# The separator between a label and its value. Historically only ":" or "-" (SEC-11
# expands this): hospital documents commonly lay identity fields out in a whitespace-
# aligned table instead — "Patient Name        John Doe" with no colon at all — and that
# shape was NOT redacted before. Two-or-more spaces/tabs is deliberately required (not a
# single space) so an ordinary sentence like "Name calling is not permitted" is never
# mistaken for a labelled field.
_LABEL_SEPARATOR = r"(?:[^\S\n]*[:\-][^\S\n]*|[^\S\n]{2,})"

# Labelled identity fields: keep the label, drop the value. Bounded to a single line with
# [^\n] so a match can never run on into the following line.
_LABELLED_IDENTIFIER_PATTERNS: List[Tuple[Pattern[str], str]] = [
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:patient(?:[^\S\n]*name)?|name[^\S\n]*of[^\S\n]*patient|"
            r"insured(?:[^\S\n]*name)?|attendant|guardian|father'?s?[^\S\n]*name|"
            r"mother'?s?[^\S\n]*name|spouse)" + _LABEL_SEPARATOR + r")[^\n]+",
            re.IGNORECASE | re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:address|residence|street|city|pin(?:[^\S\n]*code)?|"
            r"contact|phone|mobile|tel(?:ephone)?|email|e-mail|abha(?:[^\S\n]*(?:number|no|id))?)"
            + _LABEL_SEPARATOR + r")[^\n]+",
            re.IGNORECASE | re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
]

# P2: the labelled-identifier patterns above only match English labels. A document with
# a Hindi/Marathi-labelled identity field (common — this project explicitly supports
# trilingual documents) was NOT redacted at all by the check above, even though the
# free-standing patterns below (email/Aadhaar/PAN/phone — script-independent, matching
# digit/character shapes) still caught those. Standard Hindi/Marathi administrative
# vocabulary, not project-invented terms.
_LABELLED_IDENTIFIER_PATTERNS_DEVANAGARI: List[Tuple[Pattern[str], str]] = [
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:"
            r"रोगी(?:[^\S\n]*का)?[^\S\n]*नाम|मरीज़?(?:[^\S\n]*का)?[^\S\n]*नाम|"  # patient's name (Hindi)
            r"रुग्णाच[ें][^\S\n]*नाव|"  # patient's name (Marathi)
            r"पिता[^\S\n]*का[^\S\n]*नाम|माता[^\S\n]*का[^\S\n]*नाम|"  # father's/mother's name (Hindi)
            r"वडिलांचे[^\S\n]*नाव|आईचे[^\S\n]*नाव|"  # father's/mother's name (Marathi)
            r"पति[^\S\n]*/?[^\S\n]*पत्नी[^\S\n]*का[^\S\n]*नाम|"  # spouse's name (Hindi)
            r"नाम|नाव"  # bare "name" (Hindi / Marathi) — kept last, most general
            r")" + _LABEL_SEPARATOR + r")[^\n]+",
            re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:"
            r"पता|पत्ता|"  # address (Hindi / Marathi)
            r"संपर्क|सम्पर्क|"  # contact
            r"फोन|मोबाइल|मोबाईल|दूरभाष|"  # phone / mobile / telephone
            r"ईमेल|इमेल|"  # email
            r"आभा(?:[^\S\n]*(?:नंबर|संख्या))?"  # ABHA (Hindi transliteration)
            r")" + _LABEL_SEPARATOR + r")[^\n]+",
            re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
]

# Free-standing identifiers that can appear anywhere in the text.
_FREE_IDENTIFIER_PATTERNS: List[Tuple[Pattern[str], str]] = [
    # Email
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), REDACTION_MARK),
    # ABHA (Ayushman Bharat Health Account) number: 14 digits, optionally grouped
    # 2-4-4-4 with spaces or hyphens (e.g. "91-2345-6789-0123"). Checked before Aadhaar
    # (12 digits) so a 14-digit ABHA number is never left with a redacted 12-digit
    # substring and 2 stray leading digits.
    (re.compile(r"(?<![\d₹])\b\d{2}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}\b(?![\d])"), REDACTION_MARK),
    # Aadhaar: 12 digits, optionally grouped 4-4-4. Checked before phone numbers.
    (re.compile(r"(?<![\d₹])\b\d{4}[ -]?\d{4}[ -]?\d{4}\b(?![\d])"), REDACTION_MARK),
    # PAN: AAAAA9999A
    (re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), REDACTION_MARK),
    # Indian mobile number, optionally +91 prefixed. Not preceded by a currency symbol,
    # so billed amounts are never mistaken for phone numbers.
    (
        re.compile(r"(?<![\d₹.])(?:\+?91[ -]?)?\b[6-9]\d{9}\b(?![\d.])"),
        REDACTION_MARK,
    ),
]


def redact_pii(text: str) -> str:
    """Removes direct personal identifiers, preserving clinical and billing content.

    Labelled fields keep their label so downstream agents still see the document's
    structure; only the identifying value is replaced.
    """
    if not text:
        return text or ""

    redacted = text
    for pattern, replacement in _LABELLED_IDENTIFIER_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    for pattern, replacement in _LABELLED_IDENTIFIER_PATTERNS_DEVANAGARI:
        redacted = pattern.sub(replacement, redacted)
    for pattern, replacement in _FREE_IDENTIFIER_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def contains_direct_identifier(text: str) -> bool:
    """True when text still carries a recognisable direct identifier.

    Used by tests as a guard against regressions in the persistence path.
    """
    if not text:
        return False
    for pattern, _ in _LABELLED_IDENTIFIER_PATTERNS + _LABELLED_IDENTIFIER_PATTERNS_DEVANAGARI:
        for match in pattern.finditer(text):
            if REDACTION_MARK not in match.group(0):
                return True
    return any(pattern.search(text) for pattern, _ in _FREE_IDENTIFIER_PATTERNS)
