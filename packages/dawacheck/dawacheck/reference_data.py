"""
DawaCheck NPPA reference data.

The authoritative dataset is the official 2025 NPPA Schedule-I CSV
containing 748 formulations.

Legacy DawaCheck aliases are kept separately so existing price-basis
contracts continue to work without contaminating the authoritative
748-row dataset.
"""

import csv
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional
from dawacheck.metaphone import phonetic_codes_match

REFERENCE_SOURCE = "NPPA Schedule-I 2025 (748 formulations)"
EXPECTED_REFERENCE_ENTRY_COUNT = 748


def _find_nppa_csv() -> Path:
    filename = "NPPA_schedule_2025.csv"
    current = Path(__file__).resolve()

    for parent in current.parents:
        candidate = parent / "data" / "raw" / filename
        if candidate.exists():
            return candidate

    candidate = Path.cwd() / "data" / "raw" / filename
    if candidate.exists():
        return candidate

    raise FileNotFoundError(
        f"Could not find {filename}. "
        "Expected it at data/raw/NPPA_schedule_2025.csv"
    )


def _normalize(value: str) -> str:
    value = str(value or "").lower().strip()
    value = value.replace("µ", "u").replace("μ", "u")
    value = re.sub(r"[/(),:;]+", " ", value)
    value = re.sub(r"[-]+", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _extract_dosage_mg(text: str) -> Optional[float]:
    if not text:
        return None

    text = str(text).lower().replace("µ", "u").replace("μ", "u")

    match = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", text)
    if match:
        return float(match.group(1))

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mcg|ug)\b", text)
    if match:
        return float(match.group(1)) / 1000.0

    match = re.search(r"(\d+(?:\.\d+)?)\s*g\b", text)
    if match:
        return float(match.group(1)) * 1000.0

    return None


def extract_dosage_mg(text: str) -> Optional[float]:
    return _extract_dosage_mg(text)


def strip_dosage_token(text: str) -> str:
    if not text:
        return ""

    result = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|ug|g)\b",
        " ",
        str(text),
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", result).strip()


def _derive_unit_form(dosage_form_strength: str, unit: str) -> str:
    text = f"{dosage_form_strength} {unit}".lower()

    for form in (
        "tablet", "capsule", "injection", "ointment", "cream", "gel",
        "syrup", "solution", "suspension", "drops", "drop", "powder",
        "inhaler", "respules", "suppository", "patch", "implant", "iud",
        "vial", "ampoule", "ampule", "oral liquid", "nasal spray",
        "spray", "lotion", "mouth paint", "eye drops", "ear drops",
    ):
        if form in text:
            return form

    words = _normalize(dosage_form_strength).split()
    return words[0] if words else _normalize(unit)


def _active_ingredient_display(
    medicine: str,
    dosage_mg: Optional[float],
) -> str:
    if dosage_mg is None:
        return medicine
    if dosage_mg.is_integer():
        return f"{medicine} {int(dosage_mg)}mg"
    return f"{medicine} {dosage_mg:g}mg"


def _load_nppa_reference_data() -> dict[str, dict[str, Any]]:
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

    data: dict[str, dict[str, Any]] = {}

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

            try:
                ceiling_price = float(
                    (row.get("ceiling_price") or "").strip()
                )
                sl_no = int(row["sl_no"])
            except (ValueError, TypeError):
                continue

            dosage_mg = _extract_dosage_mg(
                f"{medicine} {dosage_form_strength}"
            )

            entry = {
                "unit_form": _derive_unit_form(
                    dosage_form_strength, unit
                ),
                "ingredient_base": _normalize(medicine),
                "dosage_mg": dosage_mg,
                "active_ingredient": _active_ingredient_display(
                    medicine, dosage_mg
                ),
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
                "sl_no": sl_no,
                "reference_source": REFERENCE_SOURCE,
            }

            # IMPORTANT: sl_no is the stable unique key.
            # Medicine/formulation text is NOT a unique identifier in NPPA.
            key = f"nppa-{sl_no:03d}"

            if key in data:
                raise ValueError(
                    f"Duplicate NPPA serial number detected: {sl_no}"
                )

            data[key] = entry

    if len(data) != EXPECTED_REFERENCE_ENTRY_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_REFERENCE_ENTRY_COUNT} "
            f"NPPA formulations, but loaded {len(data)}."
        )

    serials = sorted(entry["sl_no"] for entry in data.values())
    if serials != list(range(1, EXPECTED_REFERENCE_ENTRY_COUNT + 1)):
        raise ValueError(
            "NPPA serial numbers are not continuous from 1 to 748."
        )

    return data


NPPA_REFERENCE_DATA = _load_nppa_reference_data()


# These are compatibility records for existing DawaCheck contracts.
# They are deliberately NOT added to NPPA_REFERENCE_DATA, so the
# authoritative reference count remains exactly 748.
LEGACY_REFERENCE_DATA: dict[str, dict[str, Any]] = {
    "dolo 650": {
        "unit_form": "tablet",
        "ingredient_base": "paracetamol",
        "dosage_mg": 650.0,
        "active_ingredient": "Paracetamol 650mg",
        "ceiling_price": 2.30,
        "generic_info": (
            "Generic Paracetamol 650mg available at "
            "PMBJP Jan Aushadhi Kendras."
        ),
        "aliases": [
            "dolo 650", "dolo 650mg", "dolo 650mg tablet",
            "crocin 650", "crocin 650mg", "calpol 650", "pacimol 650",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
    "pan 40": {
        "unit_form": "tablet",
        "ingredient_base": "pantoprazole",
        "dosage_mg": 40.0,
        "active_ingredient": "Pantoprazole 40mg",
        "ceiling_price": 3.20,
        "generic_info": "",
        "aliases": [
            "pan 40", "pan 40mg", "pantocid 40", "pantodac 40",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
    "augmentin 625": {
        "unit_form": "tablet",
        "ingredient_base": "amoxicillin clavulanate",
        "dosage_mg": 625.0,
        "active_ingredient": (
            "Amoxicillin (500mg) + Clavulanic Acid (125mg)"
        ),
        "ceiling_price": 20.10,
        "generic_info": "",
        "aliases": [
            "augmentin 625", "augmentin 625 duo",
            "augmentin 625 duo tablet", "moxikind cv 625",
            "clavum 625", "amoxyclav 625", "augmntn 625",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
    "metformin 500mg": {
        "unit_form": "tablet",
        "ingredient_base": "metformin",
        "dosage_mg": 500.0,
        "active_ingredient": "Metformin Hydrochloride 500mg SR",
        "ceiling_price": 2.15,
        "generic_info": "",
        "aliases": [
            "glycomet 500", "glyciphage 500", "metformin sr 500",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
    "meropenem 1g": {
        "unit_form": "injection",
        "ingredient_base": "meropenem",
        "dosage_mg": 1000.0,
        "active_ingredient": "Meropenem 1000mg Powder for Injection",
        "ceiling_price": 850.00,
        "generic_info": "",
        "aliases": [
            "meropenem 1g", "meropenem 1g injection",
            "meronem 1g", "meromac 1g", "tab meropenem 1g",
            "inj meropenem 1g",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
    "azithromycin 500mg": {
        "unit_form": "tablet",
        "ingredient_base": "azithromycin",
        "dosage_mg": 500.0,
        "active_ingredient": "Azithromycin 500mg",
        "ceiling_price": 21.50,
        "generic_info": "",
        "aliases": [
            "azithral 500", "aziwok 500", "zithrox 500",
        ],
        "reference_source": "DawaCheck legacy compatibility reference",
    },
}


def _legacy_hit(query: str) -> Optional[tuple[str, dict[str, Any]]]:
    normalized = _normalize(query)

    for key, entry in LEGACY_REFERENCE_DATA.items():
        candidates = [key, *entry.get("aliases", [])]
        for alias in candidates:
            alias_normalized = _normalize(alias)
            if (
                normalized == alias_normalized
                or alias_normalized in normalized
            ):
                return key, entry

    return None


def _official_exact_hit(
    query: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    normalized = _normalize(query)
    query_dosage = _extract_dosage_mg(query)
    query_medicine = _normalize(strip_dosage_token(query))

    candidates: list[tuple[str, dict[str, Any]]] = []

    for key, entry in NPPA_REFERENCE_DATA.items():
        medicine = _normalize(entry["ingredient_base"])
        dosage_form = _normalize(
            entry.get("dosage_form_strength", "")
        )

        # Exact medicine + formulation/strength.
        if normalized == _normalize(f"{medicine} {dosage_form}"):
            candidates.append((key, entry))

    if len(candidates) == 1:
        return candidates[0]

    if len(candidates) > 1:
        return None

    if query_dosage is not None and query_medicine:
        candidates = [
            (key, entry)
            for key, entry in NPPA_REFERENCE_DATA.items()
            if _normalize(entry["ingredient_base"]) == query_medicine
            and entry.get("dosage_mg") is not None
            and abs(entry["dosage_mg"] - query_dosage) < 0.01
        ]

        if len(candidates) == 1:
            return candidates[0]

        if len(candidates) > 1:
            # If multiple formulations share the same ingredient/strength,
            # don't guess which one the caller meant.
            return None

    # Medicine-only is safe only when exactly one formulation exists.
    if query_medicine:
        candidates = [
            (key, entry)
            for key, entry in NPPA_REFERENCE_DATA.items()
            if _normalize(entry["ingredient_base"]) == query_medicine
        ]
        if len(candidates) == 1:
            return candidates[0]

    return None


def find_exact_or_alias(
    query: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    legacy = _legacy_hit(query)
    if legacy:
        return legacy

    return _official_exact_hit(query)


def find_ingredient_family(
    ingredient_base: str,
) -> list[tuple[str, dict[str, Any]]]:
    target = _normalize(strip_dosage_token(ingredient_base))

    results = [
        (key, entry)
        for key, entry in NPPA_REFERENCE_DATA.items()
        if _normalize(entry["ingredient_base"]) == target
    ]

    for key, entry in LEGACY_REFERENCE_DATA.items():
        if _normalize(entry["ingredient_base"]) == target:
            results.append((key, entry))

    return results


def find_phonetic_match(
    query: str,
) -> Optional[tuple[str, dict[str, Any]]]:
    """Find an OCR/spelling variant using Double Metaphone."""

    query_ingredient = _normalize(
        strip_dosage_token(query)
    )
    query_dosage = _extract_dosage_mg(query)

    if not query_ingredient:
        return None

    candidates: list[
        tuple[int, str, dict[str, Any]]
    ] = []

    # Prefer the legacy compatibility mappings when they provide
    # an unambiguous formulation. These mappings preserve known
    # DawaCheck behaviour while NPPA remains the authoritative
    # price source.
    for key, entry in LEGACY_REFERENCE_DATA.items():
        candidate = _normalize(
            entry["ingredient_base"]
        )

        if not phonetic_codes_match(
            query_ingredient,
            candidate,
        ):
            continue

        reference_dosage = entry.get("dosage_mg")

        if (
            query_dosage is not None
            and reference_dosage is not None
            and abs(
                reference_dosage - query_dosage
            ) > 0.01
        ):
            continue

        candidates.append(
            (0, key, entry)
        )

    # Then consider the authoritative NPPA records.
    for key, entry in NPPA_REFERENCE_DATA.items():
        candidate = _normalize(
            entry["ingredient_base"]
        )

        if not phonetic_codes_match(
            query_ingredient,
            candidate,
        ):
            continue

        reference_dosage = entry.get("dosage_mg")

        if (
            query_dosage is not None
            and reference_dosage is not None
            and abs(
                reference_dosage - query_dosage
            ) > 0.01
        ):
            continue

        candidates.append(
            (1, key, entry)
        )

    if not candidates:
        return None

    # For an exact dosage, prefer the first known formulation.
    # NPPA rows are loaded in official serial-number order.
    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    _, best_key, best_entry = candidates[0]

    return best_key, best_entry