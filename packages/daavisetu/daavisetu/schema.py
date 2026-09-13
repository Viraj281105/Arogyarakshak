"""
DaaviSetu — Universal Claim Form Data Mapping.

A single JSON Schema describing the canonical pre-authorization/claim fields DaaviSetu
collects (hospital, policy details, procedure, cost), annotated with the physical form
section each field renders into on the IRDAI Standard Cashless Pre-Authorization Request
Form (Annexure-B) — the actual document `daavisetu.generator.generate_preauth_pdf`
produces today.

"Universal" means one internal schema that every output format (the Annexure-B PDF
today; any other insurer form layout added later) maps from, so a client never has to
hardcode DaaviSetu's field names to know what a claim form needs. It is not a claim
that this already covers every insurer's proprietary form — ArogyaRakshak has no
verified source for those, so this schema models only the standardized IRDAI form it
actually generates.
"""

from typing import Any, Dict, List

# Physical field labels, exactly as printed on the Annexure-B PDF
# (packages/daavisetu/daavisetu/generator.py). This is the single source of truth for
# those labels — the PDF generator imports them from here rather than duplicating the
# strings, so the schema and the rendered form cannot drift apart.
FORM_SECTIONS: Dict[str, str] = {
    "patient_name": "1. PATIENT FULL NAME",
    "policy_number": "2. HEALTH INSURANCE POLICY ID",
    "hospital_name": "3. NETWORK HOSPITAL NAME",
    "estimated_cost": "4. ESTIMATED ADMISSION EXPENSES",
    "diagnosis": "5. PROVISIONAL / CLINICAL DIAGNOSIS",
    "treatment_plan": "6. PROPOSED MEDICAL PROCEDURE",
}

# Groups fields the way a claim is actually assembled: who is claiming, under what
# policy, where/for what clinical reason, and at what cost. `sum_insured` (#84) has no
# fixed Annexure-B field — the standard form does not carry the policy limit — so it is
# grouped under "policy" without an `x-form-section` entry.
FORM_GROUPS: Dict[str, List[str]] = {
    "patient": ["patient_name"],
    "policy": ["policy_number", "sum_insured"],
    "hospital_and_procedure": ["hospital_name", "diagnosis", "treatment_plan"],
    "cost": ["estimated_cost"],
}


def get_claim_form_json_schema() -> Dict[str, Any]:
    """Returns DaaviSetu's `ClaimData` JSON Schema, annotated with form metadata.

    Each property gains `x-form-section` (the Annexure-B label it renders into, where
    one exists) and `x-form-group`. A client can build an intake form or map to a
    different document layout from this alone, without hardcoding field names.

    Imports `ClaimData` lazily to avoid a circular import: `generator.py` imports
    `FORM_SECTIONS` from this module at load time.
    """
    from daavisetu.generator import ClaimData

    schema = ClaimData.model_json_schema()
    group_of = {
        field: group for group, fields in FORM_GROUPS.items() for field in fields
    }
    for field_name, prop in schema.get("properties", {}).items():
        if field_name in FORM_SECTIONS:
            prop["x-form-section"] = FORM_SECTIONS[field_name]
        if field_name in group_of:
            prop["x-form-group"] = group_of[field_name]
    schema["x-form-groups"] = list(FORM_GROUPS.keys())
    return schema
