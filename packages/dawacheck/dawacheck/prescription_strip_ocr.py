"""
Prescription Strip & Medicine Packaging OCR Analysis.

Extracts medicine names, dosages, and quantities from pharmacy prescription photos,
medicine strips, and packaging. Bridges between Kadi's generic OCR output and
DawaCheck's pricing intelligence (#27, Phase 2 Acceptance Criterion).

This module does NOT perform OCR itself — it processes Kadi's parse_document output
(raw text) or user-supplied structured medicine lists from prescription photos.
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from dawacheck.reference_data import (
    extract_dosage_mg,
    strip_dosage_token,
    find_exact_or_alias,
    find_ingredient_family,
    find_phonetic_match,
)

logger = logging.getLogger("DawaCheck.PrescriptionStripOCR")
logger.setLevel(logging.INFO)


@dataclass
class ExtractedMedicine:
    """A single medicine extracted from a prescription strip or packaging photo."""

    name: str
    dosage_mg: Optional[float] = None
    quantity: Optional[int] = None  # e.g., "10 tablets", "5 capsules"
    unit: Optional[str] = None  # e.g., "tablet", "capsule", "injection", "suspension"
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    mrp: Optional[float] = None  # MRP if printed on packaging
    confidence: float = 1.0  # 0.0-1.0: how confident the extraction is


class PrescriptionStripAnalysis(BaseModel):
    """Result of analyzing a prescription or medicine strip photo."""

    medicines: List[ExtractedMedicine] = Field(default_factory=list)
    raw_text: str = Field(
        default="",
        description="Raw OCR text before parsing",
    )
    parsing_notes: List[str] = Field(
        default_factory=list,
        description="Warnings/notes about parsing",
    )
    extraction_confidence: float = Field(
        default=1.0,
        description=(
            "Overall confidence in the extraction (0.0-1.0). "
            "Lower when parsing is ambiguous."
        ),
    )


class MedicineStripParser:
    """
    Parses medicine strip text (from Kadi OCR output or user-supplied text)
    to extract medicine information.

    Handles common patterns found on Indian medicine strips and packaging:
    - Medicine name with dosage (e.g., "Paracetamol 500mg")
    - Quantity (e.g., "10 tablets", "5 caps")
    - Manufacturer info
    - Batch numbers, expiry dates
    - Printed MRP
    """

    # Regex patterns for common extraction tasks
    _QUANTITY_PATTERN = re.compile(
        r"(?:qty\s*:?\s*)?"
        r"(?:\d+\s*x\s*)?"
        r"(\d+)\s*"
        r"(?:tablets?|tabs?|capsules?|caps?|strips?|sheets?|"
        r"vials?|ampoules?|injections?|infusions?|suspensions?|"
        r"syrups?|creams?|ointments?)",
        re.IGNORECASE,
    )

    _MRP_PATTERN = re.compile(
        r"[Mm][Rr][Pp]\s*[Rr]s\.?\s*(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    _BATCH_PATTERN = re.compile(
        r"(?:[Bb]atch|[Bb]\.?\s*[Nn]o?)\s*[:=]?\s*(\w+)",
        re.IGNORECASE,
    )

    _EXPIRY_PATTERN = re.compile(
        r"(?:exp|expiry|exp\.|valid\s+till|use\s+by)"
        r"\s*[:=\-]?\s*([0-9]{1,2}[/-][0-9]{2,4})",
        re.IGNORECASE,
    )

    _MANUFACTURER_PATTERN = re.compile(
        r"(?:[Mm]fg\.|[Mm]anufacturer|[Cc]o\.?|[Pp]vt\.?|Ltd\.?)"
        r"\s+(?P<mfg>[\w\s&\(\)]+?)(?:\.|,|$)",
        re.IGNORECASE,
    )

    def __init__(self):
        self.parsing_notes: List[str] = []
        self.confidence: float = 1.0

    def parse_medicine_strip_text(
        self, text: str, source: str = "ocr"
    ) -> PrescriptionStripAnalysis:
        """
        Parses OCR text from a medicine strip and extracts medicine information.

        Args:
            text: Raw OCR output or user-supplied text from a prescription photo.
            source: Where the text came from ("ocr", "user_typed", "fhir", etc.)

        Returns:
            PrescriptionStripAnalysis with extracted medicines and confidence scores.
        """
        self.parsing_notes.clear()
        self.confidence = 1.0

        if not text or not isinstance(text, str):
            logger.warning("Empty or invalid text provided for medicine strip parsing")
            return PrescriptionStripAnalysis(
                raw_text=text or "",
                parsing_notes=["No text provided or invalid format"],
                extraction_confidence=0.0,
            )

        text = text.strip()
        medicines: List[ExtractedMedicine] = []

        # Split text into lines and process each
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        for line in lines:
            extracted = self._parse_line(line)
            if extracted:
                medicines.append(extracted)

        if not medicines:
            logger.info("No medicines found in strip text")
            self.parsing_notes.append(
                "No medicine information could be extracted from the text"
            )
            self.confidence = 0.0

        return PrescriptionStripAnalysis(
            medicines=medicines,
            raw_text=text,
            parsing_notes=self.parsing_notes,
            extraction_confidence=self.confidence,
        )

    def _parse_line(self, line: str) -> Optional[ExtractedMedicine]:
        """
        Parses a single line from a prescription strip, extracting a medicine.

        Returns None if the line does not appear to contain medicine information.
        """
        if len(line) < 2:
            return None

        # Skip lines that look like headers, timestamps, or metadata
        line_lower = line.lower().strip()
        metadata_prefixes = {
            "patient",
            "doctor",
            "age",
            "gender",
            "date",
            "prescription",
            "address",
            "phone",
            "hospital",
            "clinic",
            "email",
            "signature",
        }

        if any(line_lower.startswith(prefix) for prefix in metadata_prefixes):
            return None

        working_line = line
        medicine = ExtractedMedicine(name="")

        # Extract MRP (won't be part of medicine name)
        mrp_match = self._MRP_PATTERN.search(working_line)
        if mrp_match:
            try:
                medicine.mrp = float(mrp_match.group(1))
            except ValueError:
                pass

            working_line = self._MRP_PATTERN.sub("", working_line).strip()

        # Extract batch number
        batch_match = self._BATCH_PATTERN.search(working_line)
        if batch_match:
            medicine.batch_number = batch_match.group(1)
            working_line = self._BATCH_PATTERN.sub("", working_line).strip()

        # Extract expiry date
        expiry_match = self._EXPIRY_PATTERN.search(working_line)
        if expiry_match:
            medicine.expiry_date = expiry_match.group(1)
            working_line = self._EXPIRY_PATTERN.sub("", working_line).strip()

        # Extract manufacturer
        mfg_match = self._MANUFACTURER_PATTERN.search(working_line)
        if mfg_match:
            medicine.manufacturer = mfg_match.group("mfg").strip()
            working_line = self._MANUFACTURER_PATTERN.sub("", working_line).strip()

        # Extract quantity
        # Handles:
        #   "10 tablets"
        #   "2 x 10 Tablets"
        #   "Qty:2 x 10 Tablets"
        qty_match = self._QUANTITY_PATTERN.search(working_line)

        if qty_match:
            medicine.quantity = int(qty_match.group(1))

            # Extract unit from the full matched text
            full_match = qty_match.group(0)

            unit_match = re.search(
                r"(tablet|tab|capsule|cap|strip|sheet|vial|ampoule|"
                r"injection|infusion|suspension|syrup|cream|ointment)s?",
                full_match,
                re.IGNORECASE,
            )

            if unit_match:
                medicine.unit = unit_match.group(1).lower()

            # Remove the entire quantity expression, including
            # optional Qty: and "2 x" prefixes.
            working_line = (
                working_line[: qty_match.start()] + working_line[qty_match.end() :]
            ).strip()

        # Extract dosage (e.g., "500mg") and remove it from the line
        dosage_mg = extract_dosage_mg(working_line)

        if dosage_mg is not None:
            medicine.dosage_mg = dosage_mg

            # Remove dosage pattern from line using the utility function
            working_line = strip_dosage_token(working_line).strip()

        # What remains should be the medicine name
        medicine.name = self._clean_medicine_name(working_line)

        if not medicine.name:
            return None

        return medicine

    def _clean_medicine_name(self, name: str) -> str:
        """
        Cleans a medicine name by removing dosages, quantities, and extra whitespace.
        Returns normalized lowercase medicine name.
        """
        if not name:
            return ""

        # Normalize to lowercase first
        name = name.lower().strip()

        # Remove dosage patterns such as:
        #   500mg
        #   250 mcg
        #   1g
        #   30ml
        #   100IU
        #   100IU/ml
        name = re.sub(
            r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|iu/ml|iu)\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove quantity expressions such as:
        #   Qty:2 x
        #   Qty:2
        #   2 x
        name = re.sub(
            r"\bqty\s*:?\s*\d*\s*x?\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\b\d+\s*x\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove dosage-form prefixes that are not part of the medicine name
        # e.g. TAB, CAP, INJ, SYRUP
        name = re.sub(
            r"\b(?:tab|tablet|cap|capsule|inj|injection|syrup)\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove quantity/unit patterns left behind by OCR
        name = re.sub(
            r"\b\d+\s+(?:tablets?|capsules?|caps?|tabs?|"
            r"strips?|bottles?|vials?|injections?)\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove common OCR metadata tokens and everything after them
        # so fields such as "Batch", "EXP", and "MRP" don't become
        # part of the medicine name.
        name = re.sub(
            r"\b(?:mrp|exp|expiry|batch|b\.?no)\b.*",
            "",
            name,
            flags=re.IGNORECASE,
        )

        # Remove a standalone trailing "s" sometimes introduced by OCR
        name = re.sub(r"\bs\b$", "", name).strip()

        # Clean up whitespace
        name = re.sub(r"\s+", " ", name)

        # Remove trailing punctuation
        name = re.sub(r"[:\-,]+\s*$", "", name)

        return name.strip()

    def parse_structured_medicines(
        self, medicines_list: List[Dict[str, Any]]
    ) -> PrescriptionStripAnalysis:
        """
        Parses a pre-structured list of medicines (e.g., from user form input).

        Args:
            medicines_list: List of dicts with keys like "name", "dosage", "qty", "mrp"

        Returns:
            PrescriptionStripAnalysis with parsed medicines.
        """
        self.parsing_notes.clear()
        self.confidence = 1.0

        extracted_medicines: List[ExtractedMedicine] = []

        for med_dict in medicines_list:
            if not isinstance(med_dict, dict):
                continue

            name = med_dict.get("name", "").strip()

            if not name:
                continue

            # Normalize name to lowercase and clean
            name = self._clean_medicine_name(name)

            medicine = ExtractedMedicine(name=name)

            # Parse dosage if provided
            dosage_str = med_dict.get("dosage") or med_dict.get("strength")

            if dosage_str:
                dosage_mg = extract_dosage_mg(str(dosage_str))

                if dosage_mg:
                    medicine.dosage_mg = dosage_mg

            # Parse quantity
            qty = med_dict.get("quantity") or med_dict.get("qty")

            if qty:
                try:
                    medicine.quantity = int(qty)
                except (ValueError, TypeError):
                    pass

            # Parse unit
            medicine.unit = (
                str(med_dict.get("unit") or med_dict.get("form") or "").lower() or None
            )

            # Parse MRP
            mrp = med_dict.get("mrp") or med_dict.get("price")

            if mrp:
                try:
                    medicine.mrp = float(mrp)
                except (ValueError, TypeError):
                    pass

            # Parse other optional fields
            medicine.manufacturer = (
                str(med_dict.get("manufacturer") or "").strip() or None
            )

            medicine.batch_number = str(med_dict.get("batch") or "").strip() or None

            medicine.expiry_date = str(med_dict.get("expiry") or "").strip() or None

            # Set confidence based on how many fields were provided
            fields_provided = sum(1 for v in [name, dosage_str, qty, medicine.mrp] if v)

            medicine.confidence = min(
                1.0,
                fields_provided / 2.0,
            )

            extracted_medicines.append(medicine)

        return PrescriptionStripAnalysis(
            medicines=extracted_medicines,
            raw_text="",
            parsing_notes=self.parsing_notes,
            extraction_confidence=self.confidence,
        )


def extract_medicines_from_prescription(
    ocr_text: str,
    source: str = "kadi_ocr",
) -> PrescriptionStripAnalysis:
    """
    Convenience function: extracts medicines from OCR text in one call.

    Args:
        ocr_text: Raw OCR output from Kadi's parse_document.
        source: Where the text originated.

    Returns:
        PrescriptionStripAnalysis with extracted medicines.
    """
    parser = MedicineStripParser()
    return parser.parse_medicine_strip_text(
        ocr_text,
        source=source,
    )


def extract_medicines_from_form(
    medicines_data: List[Dict[str, Any]],
) -> PrescriptionStripAnalysis:
    """
    Convenience function: parses user-supplied medicine list from a form.

    Args:
        medicines_data: List of medicine dicts from a form submission.

    Returns:
        PrescriptionStripAnalysis with parsed medicines.
    """
    parser = MedicineStripParser()
    return parser.parse_structured_medicines(medicines_data)
