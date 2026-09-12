"""
Kadi — Shared Document Extraction Agent.

Invokes LLM (Groq) to parse raw document text into normalized patient/clinical entities.
"""

import os
import re
import json
import logging
import urllib.request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from kadi.line_items import extract_total_amount, looks_like_medicine, parse_line_items

logger = logging.getLogger("Kadi.ExtractionAgent")
logger.setLevel(logging.INFO)

class ExtractedEntities(BaseModel):
    """Pydantic model representing structured Kadi entities."""
    hospital_name: Optional[str] = Field(None, description="Name of the hospital")
    patient_name: Optional[str] = Field(None, description="Name of the patient")
    diagnosis: Optional[str] = Field(None, description="Primary clinical diagnosis")
    procedures: List[Dict[str, Any]] = Field(default_factory=list, description="List of procedures with name and amount")
    medicines: List[Dict[str, Any]] = Field(default_factory=list, description="List of medicines with name, dosage, and cost")
    total_amount: Optional[float] = Field(0.0, description="Total billed amount")

def extract_entities_from_text(text: str, api_key: Optional[str] = None, model: Optional[str] = None) -> ExtractedEntities:
    """Uses Groq API to extract structured entities from raw document text."""
    # Resolve API keys and models
    groq_api_key = api_key or os.environ.get("GROQ_API_KEY", "")
    groq_model = model or os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

    if not groq_api_key:
        logger.warning("GROQ_API_KEY not configured. Falling back to heuristic rule extraction.")
        return run_heuristic_extraction_fallback(text)

    sys_instr = (
        "You are the Kadi Shared Extraction Agent.\n"
        "Your task is to parse raw medical/billing text and output a STRICT JSON object representing extracted entities.\n"
        "Ensure the output conforms exactly to this schema:\n"
        "{\n"
        '  "hospital_name": "string or null",\n'
        '  "patient_name": "string or null",\n'
        '  "diagnosis": "string or null",\n'
        '  "procedures": [{"name": "string", "amount": 0.0}],\n'
        '  "medicines": [{"name": "string", "dosage": "string or null", "cost": 0.0}],\n'
        '  "total_amount": 0.0\n'
        "}\n"
        "Do not output markdown code blocks, explanatory text, or trailing characters. Only raw JSON."
    )

    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": sys_instr},
            {"role": "user", "content": f"Parse the following text and extract entities:\n\n{text[:6000]}"}
        ],
        "temperature": 0.0,
        "max_tokens": 1024,
        "response_format": {"type": "json_object"}
    }

    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {groq_api_key}"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            content = res_data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return ExtractedEntities.model_validate(parsed)
    except Exception as e:
        logger.error(f"Groq API extraction failed: {e}. Falling back to heuristic rules.")
        return run_heuristic_extraction_fallback(text)

# Labelled-field patterns. These are matched per line with [^\n] character classes —
# using \s here would let the match run across a newline and swallow the following line
# (the cause of hospital names such as "Hospital\nPatient Name").
_HOSPITAL_KEYWORDS = ("hospital", "clinic", "medical center", "medical centre", "nursing home", "healthcare")

# Word-boundary matcher. Plain substring matching made every line containing "clinical"
# (e.g. "unstructured clinical note") match the keyword "clinic" and become the facility
# name — garbage that then appeared as the hospital on a pre-authorization form.
_HOSPITAL_KEYWORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _HOSPITAL_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

_PATIENT_RE = re.compile(
    r"^[^\S\n]*(?:patient(?:[^\S\n]*name)?|name[^\S\n]*of[^\S\n]*patient)[^\S\n]*[:\-][^\S\n]*(?P<value>[^\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)

_DIAGNOSIS_RE = re.compile(
    r"^[^\S\n]*(?:provisional[^\S\n]+|final[^\S\n]+|primary[^\S\n]+|clinical[^\S\n]+)?"
    r"diagnosis[^\S\n]*[:\-][^\S\n]*(?P<value>[^\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)

_HOSPITAL_LABELLED_RE = re.compile(
    r"^[^\S\n]*(?:hospital|clinic|facility|provider)[^\S\n]*(?:name)?[^\S\n]*[:\-][^\S\n]*(?P<value>[^\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)


def _clean_field(value: Optional[str]) -> Optional[str]:
    """Trims a captured field and discards empty or placeholder values."""
    if not value:
        return None
    cleaned = value.strip().strip(",;").strip()
    return cleaned or None


def _find_hospital_name(text: str) -> Optional[str]:
    """Finds the facility name from a labelled field, else the first facility-like line."""
    labelled = _HOSPITAL_LABELLED_RE.search(text)
    if labelled:
        value = _clean_field(labelled.group("value"))
        if value:
            return value

    # Unlabelled letterhead: the first line that names a facility. Bounded to one line.
    for line in text.splitlines():
        candidate = line.strip()
        if not candidate or len(candidate) > 120:
            continue
        lowered = candidate.lower()
        if _HOSPITAL_KEYWORD_RE.search(candidate):
            # Skip lines that are really labelled fields for something else.
            if re.match(r"^\s*(patient|diagnosis|date|invoice|bill)\b", lowered):
                continue
            return candidate
    return None


def run_heuristic_extraction_fallback(text: str) -> ExtractedEntities:
    """Fallback parser using regex heuristics when Groq API key is missing or calls fail."""
    patient_match = _PATIENT_RE.search(text)
    diagnosis_match = _DIAGNOSIS_RE.search(text)

    hospital_name = _find_hospital_name(text)
    patient_name = _clean_field(patient_match.group("value")) if patient_match else None
    diagnosis = _clean_field(diagnosis_match.group("value")) if diagnosis_match else None
    total_amount = extract_total_amount(text)

    # Line items come from the same shared parser the OCR stage uses, so the two stages
    # cannot report different names or amounts for one source line.
    procedures = []
    medicines = []
    for item in parse_line_items(text):
        name = item["item"]
        if looks_like_medicine(name):
            medicines.append({"name": name, "dosage": None, "cost": item["charged"]})
        else:
            procedures.append({"name": name, "amount": item["charged"]})

    return ExtractedEntities(
        hospital_name=hospital_name,
        patient_name=patient_name,
        diagnosis=diagnosis,
        procedures=procedures,
        medicines=medicines,
        total_amount=total_amount
    )
