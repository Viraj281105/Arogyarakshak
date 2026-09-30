"""
NPPA Schedule-I reference data loader for DawaCheck.

Loads the curated 2025 NPPA Schedule-I CSV containing 748 formulations
and exposes the same matching functions expected by checker.py.
"""

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import List, Optional, Tuple


REFERENCE_SOURCE = "NPPA Schedule-I 2025 (748 formulations)"


# ---------------------------------------------------------------------------
# Locate NPPA CSV
# ---------------------------------------------------------------------------

def _find_nppa_csv() -> Path:
    """Find data/raw/NPPA_schedule_2025.csv from the package location."""

    filename = "NPPA_schedule_2025.csv"

    current = Path(__file__).resolve()

    for parent in current.parents:
        candidate = parent / "data" / "raw" / filename
        if candidate.exists():
            return candidate

    # Fallback: search from current working directory.
    cwd_candidate = Path.cwd() / "data" / "raw" / filename
    if cwd_candidate.exists():
        return cwd_candidate

    raise FileNotFoundError(
        f"Could not find {filename}. "
        "Expected it at data/raw/NPPA_schedule_2025.csv"
    )


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------

def _normalize(value: str) -> str:
    """Normalize text for reliable matching."""

    value = str(value or "").lower().strip()

    value = value.replace("µ", "u")
    value = value.replace("μ", "u")

    # Normalize common punctuation/separators.
    value = re.sub(r"[/(),:;]+", " ", value)
    value = re.sub(r"[-]+", " ", value)

    # Normalize whitespace.
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _extract_dosage_mg(text: str) -> Optional[float]:
    """
    Extract dosage strength and convert it to mg.

    Examples:
        500mg   -> 500
        1g      -> 1000
        250 mcg -> 0.25
        650 mg  -> 650
    """

    if not text:
        return None

    text = str(text).lower().replace("µ", "u").replace("μ", "u")

    # Prefer mg first.
    match = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", text)
    if match:
        return float(match.group(1))

    # Micrograms.
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mcg|ug)\b", text)
    if match:
        return float(match.group(1)) / 1000.0

    # Grams.
    match = re.search(r"(\d+(?:\.\d+)?)\s*g\b", text)
    if match:
        return float(match.group(1)) * 1000.0

    return None


def extract_dosage_mg(text: str) -> Optional[float]:
    """Public dosage extraction helper used by checker.py."""

    return _extract_dosage_mg(text)


def strip_dosage_token(text: str) -> str:
    """Remove a dosage-strength token from a medicine query."""

    if not text:
        return ""

    result = str(text)

    result = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g)\b",
        " ",
        result,
        flags=re.IGNORECASE,
    )

    result = re.sub(r"\s+", " ", result)

    return result.strip()


# ---------------------------------------------------------------------------
# Unit/form helper
# ---------------------------------------------------------------------------

def _derive_unit_form(dosage_form_strength: str, unit: str) -> str:
    """Derive a simple formulation name for compatibility with DawaCheck."""

    text = f"{dosage_form_strength} {unit}".lower()

    form_words = [
        "tablet",
        "capsule",
        "injection",
        "ointment",
        "cream",
        "gel",
        "syrup",
        "solution",
        "suspension",
        "drops",
        "drop",
        "powder",
        "inhaler",
        "respules",
        "suppository",
        "patch",
        "implant",
        "iud",
        "vial",
        "ampoule",
        "ampule",
        "oral liquid",
        "oral solution",
        "oral suspension",
        "nasal spray",
        "spray",
        "cream",
        "lotion",
        "mouth paint",
        "eye drops",
        "ear drops",
    ]

    for form in form_words:
        if form in text:
            return form

    # Fall back to the first meaningful part of the dosage/formulation text.
    words = _normalize(dosage_form_strength).split()

    if words:
        return words[0]

    return _normalize(unit)


# ---------------------------------------------------------------------------
# Load NPPA reference data
# ---------------------------------------------------------------------------

def _load_nppa_reference_data() -> dict:
    """Load all 748 NPPA formulations from the extracted CSV."""

    csv_path = _find_nppa_csv()

    required_columns = {
        "sl_no",
        "medicine",
        "dosage_form_strength",
        "unit",
        "ceiling_price",
        "existing_so_no",
        "existing_so_date",
    }

    data = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("NPPA CSV has no header row.")

        missing = required_columns - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"NPPA CSV is missing required columns: {sorted(missing)}"
            )

        for row in reader:
            medicine = (row.get("medicine") or "").strip()
            dosage_form_strength = (
                row.get("dosage_form_strength") or ""
            ).strip()
            unit = (row.get("unit") or "").strip()

            if not medicine:
                continue

            ceiling_price_text = (
                row.get("ceiling_price") or ""
            ).strip()

            if not ceiling_price_text:
                continue

            try:
                ceiling_price = float(ceiling_price_text)
            except ValueError:
                continue

            dosage_mg = _extract_dosage_mg(
                f"{medicine} {dosage_form_strength}"
            )

            entry = {
                "unit_form": _derive_unit_form(
                    dosage_form_strength,
                    unit,
                ),
                "ingredient_base": medicine.lower(),
                "dosage_mg": dosage_mg,
                "active_ingredient": medicine,
                "ceiling_price": ceiling_price,
                "generic_info": "",
                "aliases": [],
                "dosage_form_strength": dosage_form_strength,
                "unit": unit,
                "existing_so_no": (
                    row.get("existing_so_no") or ""
                ).strip(),
                "existing_so_date": (
                    row.get("existing_so_date") or ""
                ).strip(),
                "sl_no": int(row["sl_no"]),
            }

            # Include medicine + formulation + unit in the key.
            #
            # Unit is important because some NPPA medicines have
            # otherwise identical medicine/formulation text but different
            # units and ceiling prices.
            key = _normalize(
                f"{medicine} {dosage_form_strength} {unit}"
            )

            if key in data:
                raise ValueError(
                    f"Duplicate NPPA reference key detected: {key}"
                )

            data[key] = entry

    if len(data) != 748:
        raise ValueError(
            f"Expected 748 NPPA formulations, but loaded {len(data)}."
        )

    return data


NPPA_REFERENCE_DATA = _load_nppa_reference_data()


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def find_exact_or_alias(query: str) -> Optional[Tuple[str, dict]]:
    """
    Find an exact NPPA formulation or alias.

    Matching order:
    1. Full generated NPPA key.
    2. Medicine + dosage/formulation.
    3. Medicine + strength, only if unambiguous.
    4. Medicine alone, only if exactly one formulation exists.
    5. Alias.
    """

    normalized_query = _normalize(query)

    if not normalized_query:
        return None

    # ---------------------------------------------------------------
    # 1. Exact full-key match
    # ---------------------------------------------------------------

    if normalized_query in NPPA_REFERENCE_DATA:
        return (
            normalized_query,
            NPPA_REFERENCE_DATA[normalized_query],
        )

    # ---------------------------------------------------------------
    # 2. Exact medicine + formulation + strength match
    #
    # Example:
    #   "amoxicillin Capsule 500mg"
    # ---------------------------------------------------------------

    formulation_matches = []

    for key, entry in NPPA_REFERENCE_DATA.items():
        medicine = _normalize(entry["active_ingredient"])
        dosage = _normalize(
            entry.get("dosage_form_strength", "")
        )

        if not dosage:
            continue

        combined = _normalize(
            f"{medicine} {dosage}"
        )

        if normalized_query == combined:
            formulation_matches.append((key, entry))

    if len(formulation_matches) == 1:
        return formulation_matches[0]

    # If somehow multiple identical formulations exist, do not
    # randomly select one.
    if len(formulation_matches) > 1:
        return None

    # ---------------------------------------------------------------
    # 3. Medicine + strength match
    #
    # Only return a result when exactly one formulation has that
    # medicine and strength.
    #
    # Example:
    #   "some medicine 50mg"
    # ---------------------------------------------------------------

    query_strength = _extract_dosage_mg(normalized_query)
    query_medicine = strip_dosage_token(normalized_query)

    if query_strength is not None and query_medicine:
        strength_matches = []

        for key, entry in NPPA_REFERENCE_DATA.items():
            medicine = _normalize(
                entry["active_ingredient"]
            )

            reference_strength = entry.get("dosage_mg")

            if (
                medicine == query_medicine
                and reference_strength is not None
                and abs(reference_strength - query_strength) < 1e-9
            ):
                strength_matches.append((key, entry))

        if len(strength_matches) == 1:
            return strength_matches[0]

        # Multiple formulations with the same strength are ambiguous.
        # Do not select one arbitrarily.
        if len(strength_matches) > 1:
            return None

    # ---------------------------------------------------------------
    # 4. Medicine-only match
    #
    # Only return a result if that medicine has exactly one NPPA
    # formulation.
    # ---------------------------------------------------------------

    medicine_matches = [
        (key, entry)
        for key, entry in NPPA_REFERENCE_DATA.items()
        if normalized_query
        == _normalize(entry["active_ingredient"])
    ]

    if len(medicine_matches) == 1:
        return medicine_matches[0]

    # ---------------------------------------------------------------
    # 5. Alias matching
    # ---------------------------------------------------------------

    for key, entry in NPPA_REFERENCE_DATA.items():
        for alias in entry.get("aliases", []):
            alias_normalized = _normalize(alias)

            if (
                normalized_query == alias_normalized
                or alias_normalized in normalized_query
            ):
                return key, entry

    return None


def find_ingredient_family(
    ingredient_base: str,
) -> List[Tuple[str, dict]]:
    """
    Return all NPPA formulations belonging to the same medicine.
    """

    target = _normalize(ingredient_base)

    return [
        (key, entry)
        for key, entry in NPPA_REFERENCE_DATA.items()
        if _normalize(entry["ingredient_base"]) == target
    ]


def find_phonetic_match(
    query: str,
) -> Optional[Tuple[str, dict]]:
    """
    Find a conservative fuzzy/phonetic-style match.

    A match is returned only when there is one clearly best candidate.
    """

    normalized_query = _normalize(query)

    if not normalized_query:
        return None

    candidates = []

    for key, entry in NPPA_REFERENCE_DATA.items():
        medicine = _normalize(entry["active_ingredient"])

        similarity = SequenceMatcher(
            None,
            normalized_query,
            medicine,
        ).ratio()

        if similarity >= 0.88:
            candidates.append(
                (similarity, key, entry)
            )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    # Require a clear winner.
    best = candidates[0]

    if len(candidates) > 1:
        second = candidates[1]

        if best[0] - second[0] < 0.03:
            return None

    return best[1], best[2]