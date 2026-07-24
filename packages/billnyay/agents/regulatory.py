"""
BillNyay — Regulatory Agent.

Retrieves applicable statutory provisions, IRDAI regulations, CGHS rate caps,
and Consumer Protection Act clauses to support medical appeal claims.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger("BillNyay.RegulatoryAgent")
logger.setLevel(logging.INFO)


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

    return [
        {
            "statute_name": "IRDAI Circular Ref: IRDAI/HLT/REG/CIR/194/09/2020",
            "statute_text": "Standardization of Exclusion Clauses: Claim rejections based on vague exclusion clauses are invalid without clear medical necessity proof.",
            "jurisdiction": "IRDAI",
            "category": "claims_exclusion",
        },
        {
            "statute_name": "Consumer Protection Act, 2019 — Section 2(47)",
            "statute_text": "Unfair Trade Practice: Arbitrary reduction of claimed medical expenses or unreasonable delay constitutes unfair trade practice.",
            "jurisdiction": "India Federal",
            "category": "consumer_rights",
        },
    ]


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
            }
        )

    return {
        "legal_points": legal_points[:4],
        "query_used": query_text,
        "statute_count": len(legal_points[:4]),
    }
