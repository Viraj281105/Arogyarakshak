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

# Labelled identity fields: keep the label, drop the value. Bounded to a single line with
# [^\n] so a match can never run on into the following line.
_LABELLED_IDENTIFIER_PATTERNS: List[Tuple[Pattern[str], str]] = [
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:patient(?:[^\S\n]*name)?|name[^\S\n]*of[^\S\n]*patient|"
            r"insured(?:[^\S\n]*name)?|attendant|guardian|father'?s?[^\S\n]*name|"
            r"mother'?s?[^\S\n]*name|spouse)[^\S\n]*[:\-][^\S\n]*)[^\n]+",
            re.IGNORECASE | re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
    (
        re.compile(
            r"(?P<label>^[^\S\n]*(?:address|residence|street|city|pin(?:[^\S\n]*code)?|"
            r"contact|phone|mobile|tel(?:ephone)?|email|e-mail)[^\S\n]*[:\-][^\S\n]*)[^\n]+",
            re.IGNORECASE | re.MULTILINE,
        ),
        r"\g<label>" + REDACTION_MARK,
    ),
]

# Free-standing identifiers that can appear anywhere in the text.
_FREE_IDENTIFIER_PATTERNS: List[Tuple[Pattern[str], str]] = [
    # Email
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]{2,}\b"), REDACTION_MARK),
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
    for pattern, replacement in _FREE_IDENTIFIER_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def contains_direct_identifier(text: str) -> bool:
    """True when text still carries a recognisable direct identifier.

    Used by tests as a guard against regressions in the persistence path.
    """
    if not text:
        return False
    for pattern, _ in _LABELLED_IDENTIFIER_PATTERNS:
        for match in pattern.finditer(text):
            if REDACTION_MARK not in match.group(0):
                return True
    return any(pattern.search(text) for pattern, _ in _FREE_IDENTIFIER_PATTERNS)
