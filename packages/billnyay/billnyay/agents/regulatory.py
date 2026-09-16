"""
BillNyay — Regulatory Agent.

Retrieves applicable statutory provisions, IRDAI regulations, CGHS rate caps,
and Consumer Protection Act clauses to support medical appeal claims.

Every law_library.json entry carries provenance (source_url, issued_on,
verified_on, verification_status). Entries marked "unverified" have not been
checked against a primary source and must not be presented as settled law.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger("BillNyay.RegulatoryAgent")
logger.setLevel(logging.INFO)


# Used only when law_library.json is missing or unreadable. Kept identical to the
# matching entries in that file (enforced by tests/test_law_library.py).
_FALLBACK_LAW_LIBRARY: List[dict] = [
    {
        "statute_name": "IRDAI Guidelines on Standardization of Exclusions in Health Insurance Contracts (Ref: IRDAI/HLT/REG/CIR/177/09/2019) — Chapter VI, Clause 4",
        "statute_text": "Exclusion and waiting-period wordings in health insurance policy contracts must be specific and unambiguous; open-ended phrasing such as 'indirectly related to', 'such as' or 'etc.' is not permitted when framing exclusions or waiting periods.",
        "jurisdiction": "IRDAI",
        "category": "claims_exclusion",
        "source_url": "https://irdai.gov.in/documents/37343/365525/Guidelines+on+Standardization+of+Exclusions+in+Health+Insurance+Contracts.pdf/39629f3a-a65b-7cea-f045-ca50f66ce6d0?version=1.1&t=1665918387659&download=true",
        "issued_on": "2019-09-27",
        "verified_on": "2026-09-13",
        "verification_status": "verified",
        "verification_note": "Reference number and date read from page 1 of the IRDAI PDF, and confirmed by IRDAI circular IRDAI/HLT/REG/CIR/046/02/2020 (10.02.2020), which amends these guidelines citing Ref No. IRDAI/HLT/REG/CIR/177/09/2019 (https://irdai.gov.in/documents/37343/365525/Amendments+in+respect+of+provisions+of+Guidelines+on+Standardization+of+Exc.pdf/fe4822bf-c5eb-de32-d65a-868067bccaab?version=1.0&t=1631531403603). Summary checked against Chapter VI, Clause 4. Not among the circulars superseded by Annexure-6 of Master Circular IRDAI/HLT/CIR/PRO/84/5/2024 (29.05.2024). Previously mis-cited here as IRDAI/HLT/REG/CIR/194/09/2020, a reference not found on irdai.gov.in (IRDAI/HLT/REG/CIR/194/07/2020 is a different circular: Consolidated Guidelines on Product Filing, 22.07.2020). The earlier summary's statement that prior approval or medical-necessity justification must be established before rejecting claims does not appear in these guidelines and was removed.",
    },
    {
        "statute_name": "Consumer Protection Act, 2019 — Section 2(47)",
        "statute_text": "Defines Unfair Trade Practice: Imposing unreasonable conditions, delayed claim processing without justifiable cause, or arbitrary reduction of claimed expenses constitutes unfair trade practice.",
        "jurisdiction": "India Federal",
        "category": "consumer_rights",
        "source_url": None,
        "issued_on": None,
        "verified_on": None,
        "verification_status": "unverified",
        "verification_note": "Not verified. The Gazette of India copy of the Act could not be retrieved from egazette.gov.in on 2026-09-13 (TLS certificate error), so this summary has not been checked against the text of section 2(47). Do not present it as settled law until verified.",
    },
]


def _load_law_library() -> List[dict]:
    library_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "law_library.json")
    )
    if os.path.exists(library_path):
        try:
            with open(library_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read law_library.json: {e}")

    return [dict(entry) for entry in _FALLBACK_LAW_LIBRARY]


def run_regulatory_agent(
    denial_data: dict, client=None, **kwargs
) -> Dict[str, List[dict]]:
    """Retrieves relevant statutory provisions and IRDAI rules."""
    procedure = denial_data.get("procedure_denied", "")
    reason = denial_data.get("insurer_reason_snippet", "")
    code = denial_data.get("denial_code", "")

    query_text = f"{procedure} {reason} {code}".lower()
    statutes = _load_law_library()

    legal_points = []
    for stat in statutes:
        name = stat.get("statute_name", "")
        text = stat.get("statute_text", "")
        legal_points.append(
            {
                "statute": name,
                "summary": text,
                "jurisdiction": stat.get("jurisdiction", "India"),
                "category": stat.get("category", "regulatory"),
                "source_url": stat.get("source_url"),
                "issued_on": stat.get("issued_on"),
                "verified_on": stat.get("verified_on"),
                # Missing provenance is treated as unverified, never as verified.
                "verification_status": stat.get("verification_status", "unverified"),
            }
        )

    return {
        "legal_points": legal_points[:4],
        "query_used": query_text,
        "statute_count": len(legal_points[:4]),
    }
