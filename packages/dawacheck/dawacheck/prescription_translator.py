"""
DawaCheck — Interactive Prescription Shorthand Translator (#97).

Doctors write dosage frequency in Latin-derived medical shorthand (TDS, BD, HS, ...).
This module maps a small, fixed set of internationally standard abbreviations — the
same ones used in WHO prescribing guidance and Indian pharmacology practice — to a
plain-language frequency and, optionally, a Hindi or Marathi translation of that
phrase. It does **not** interpret the drug name, dose strength, or route; it only
expands the timing shorthand a patient is unlikely to recognise.

Anti-fabrication: only tokens present in SHORTHAND_REFERENCE are translated. An
unrecognised token is returned as `recognized=False` with the original text
untouched — never guessed at, never silently dropped.
"""

import re
from typing import List, Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "mr"]

# Standard Latin-derived prescription-frequency shorthand. This is the same fixed
# vocabulary taught in Indian pharmacology curricula and used in WHO prescribing
# guidance — not a proprietary or invented list. Each entry: canonical meaning (en),
# and its Hindi/Marathi translation.
SHORTHAND_REFERENCE = {
    "OD": {
        "en": "once a day",
        "hi": "दिन में एक बार",
        "mr": "दिवसातून एकदा",
    },
    "BD": {
        "en": "twice a day",
        "hi": "दिन में दो बार",
        "mr": "दिवसातून दोनदा",
    },
    "BID": {
        "en": "twice a day",
        "hi": "दिन में दो बार",
        "mr": "दिवसातून दोनदा",
    },
    "TDS": {
        "en": "three times a day",
        "hi": "दिन में तीन बार",
        "mr": "दिवसातून तीनदा",
    },
    "TID": {
        "en": "three times a day",
        "hi": "दिन में तीन बार",
        "mr": "दिवसातून तीनदा",
    },
    "QDS": {
        "en": "four times a day",
        "hi": "दिन में चार बार",
        "mr": "दिवसातून चारदा",
    },
    "QID": {
        "en": "four times a day",
        "hi": "दिन में चार बार",
        "mr": "दिवसातून चारदा",
    },
    "QD": {
        "en": "once a day",
        "hi": "दिन में एक बार",
        "mr": "दिवसातून एकदा",
    },
    "HS": {
        "en": "at bedtime",
        "hi": "सोने से पहले",
        "mr": "झोपण्यापूर्वी",
    },
    "SOS": {
        "en": "as needed",
        "hi": "आवश्यकता पड़ने पर",
        "mr": "गरज असेल तेव्हा",
    },
    "PRN": {
        "en": "as needed",
        "hi": "आवश्यकता पड़ने पर",
        "mr": "गरज असेल तेव्हा",
    },
    "AC": {
        "en": "before meals",
        "hi": "भोजन से पहले",
        "mr": "जेवणापूर्वी",
    },
    "PC": {
        "en": "after meals",
        "hi": "भोजन के बाद",
        "mr": "जेवणानंतर",
    },
    "STAT": {
        "en": "immediately",
        "hi": "तुरंत",
        "mr": "त्वरित",
    },
    "OM": {
        "en": "every morning",
        "hi": "हर सुबह",
        "mr": "दररोज सकाळी",
    },
    "ON": {
        "en": "every night",
        "hi": "हर रात",
        "mr": "दररोज रात्री",
    },
}

# Matches HH-hourly dosing (Q4H, Q6H, Q8H, Q12H) separately since it's parametric,
# not a fixed lookup.
_HOURLY_PATTERN = re.compile(r"^Q(\d{1,2})H$", re.IGNORECASE)

_HOURLY_PHRASE = {
    "en": "every {n} hours",
    "hi": "हर {n} घंटे में",
    "mr": "दर {n} तासांनी",
}

# A shorthand token must be a whole word — never match "OD" inside "MODerate".
_TOKEN_PATTERN = re.compile(r"\b([A-Za-z]{1,4}(?:\d{1,2}H)?)\b")


class TranslatedInstruction(BaseModel):
    token: str = Field(..., description="The shorthand token as it appeared in the input.")
    recognized: bool = Field(..., description="Whether this token matched a known abbreviation.")
    meaning_en: str = Field("", description="Plain-English meaning, empty when unrecognized.")
    translated: str = Field(
        "", description="Meaning in the requested language, empty when unrecognized."
    )


class PrescriptionTranslation(BaseModel):
    original_text: str
    language: Language
    instructions: List[TranslatedInstruction]
    unrecognized_tokens: List[str] = Field(
        default_factory=list,
        description="Tokens that looked like shorthand but matched nothing in the reference "
        "set. Never guessed — surfaced so the patient can ask their pharmacist.",
    )

    @property
    def fully_recognized(self) -> bool:
        return len(self.unrecognized_tokens) == 0


def _lookup(token: str, language: Language) -> TranslatedInstruction:
    upper = token.upper()

    entry = SHORTHAND_REFERENCE.get(upper)
    if entry is not None:
        return TranslatedInstruction(
            token=token,
            recognized=True,
            meaning_en=entry["en"],
            translated=entry[language],
        )

    hourly_match = _HOURLY_PATTERN.match(upper)
    if hourly_match:
        n = hourly_match.group(1)
        return TranslatedInstruction(
            token=token,
            recognized=True,
            meaning_en=_HOURLY_PHRASE["en"].format(n=n),
            translated=_HOURLY_PHRASE[language].format(n=n),
        )

    return TranslatedInstruction(token=token, recognized=False)


def translate_prescription_shorthand(
    text: str, language: Language = "en"
) -> PrescriptionTranslation:
    """Scans free-text doctor instructions for known frequency shorthand and returns
    each recognised token's plain-language meaning in the requested language.

    Only whole-word tokens that exactly match SHORTHAND_REFERENCE (case-insensitively)
    or the QnH hourly pattern are translated. Everything else — drug names, dose
    strengths, route abbreviations not in this list — passes through untouched and is
    never guessed at.
    """
    if not text or not text.strip():
        return PrescriptionTranslation(original_text=text, language=language, instructions=[])

    candidates = _TOKEN_PATTERN.findall(text)
    seen: set = set()
    instructions: List[TranslatedInstruction] = []
    unrecognized: List[str] = []

    for raw_token in candidates:
        upper = raw_token.upper()
        # Doctors write frequency shorthand in caps by convention (e.g. "Tab. Dolo 650mg
        # TDS x 5 days") — an all-caps 2-4 letter token, or the QnH hourly pattern, is
        # treated as shorthand-shaped and looked up. This deliberately can miss (a
        # lowercase "tds") or flag a false positive (an unrelated all-caps abbreviation
        # like a drug code) — both are surfaced honestly rather than silently resolved.
        is_shorthand_shaped = (raw_token.isupper() and 2 <= len(raw_token) <= 4) or _HOURLY_PATTERN.match(
            upper
        )
        if not is_shorthand_shaped:
            continue
        if upper in seen:
            continue
        seen.add(upper)

        result = _lookup(raw_token, language)
        instructions.append(result)
        if not result.recognized:
            unrecognized.append(raw_token)

    return PrescriptionTranslation(
        original_text=text,
        language=language,
        instructions=instructions,
        unrecognized_tokens=unrecognized,
    )
