"""
Kadi — Shared Document Extraction Agent.

Invokes LLM (Groq) to parse raw document text into normalized patient/clinical entities.
"""

import os
import json
import logging
import urllib.request
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

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

def run_heuristic_extraction_fallback(text: str) -> ExtractedEntities:
    """Fallback parser using regex heuristics when Groq API key is missing or calls fail."""
    # Simple regex rules
    hospital_name = None
    patient_name = None
    diagnosis = None
    total_amount = 0.0
    procedures = []
    medicines = []

    # Hospital Name lookup
    hosp_match = re.search(r"(hospital|clinic|medical center|healthcare)\s+([A-Za-z\s]+)", text, re.IGNORECASE)
    if hosp_match:
        hospital_name = hosp_match.group(0).strip()

    # Total charged lookup
    total_match = re.search(r"total\s*(amount|charge|due|bill)?\s*[:₹]?\s*(\d+\.?\d*)", text, re.IGNORECASE)
    if total_match:
        total_amount = float(total_match.group(2))

    # Identify lines with pricing
    lines = text.split("\n")
    import re
    for line in lines:
        match = re.search(r"([A-Za-z\s0-9]+)[\s:]+₹?(\d+\.?\d*)", line)
        if match:
            item_name = match.group(1).strip()
            price = float(match.group(2))
            if len(item_name) > 3 and item_name.lower() not in ["total", "subtotal", "date", "invoice", "tax", "mrp"]:
                if any(x in item_name.lower() for x in ["tab", "cap", "syr", "inj", "mg", "ml", "paracetamol", "aspirin"]):
                    medicines.append({"name": item_name, "dosage": None, "cost": price})
                else:
                    procedures.append({"name": item_name, "amount": price})

    return ExtractedEntities(
        hospital_name=hospital_name,
        patient_name=patient_name,
        diagnosis=diagnosis,
        procedures=procedures,
        medicines=medicines,
        total_amount=total_amount
    )
