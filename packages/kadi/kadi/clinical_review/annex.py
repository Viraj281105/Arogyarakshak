"""
Deterministic rendering of human clinical statements into dispute packages (ADR-011).

The appeal letter itself may be LLM-drafted; a human reviewer's statement never passes
through an LLM. It is appended verbatim, with its attribution, conflict-of-interest
disclosure, verification status and limitations, by this plain formatter. When no
finalized statement exists, the package says so — it never implies one.
"""

from typing import Any, Dict, List, Sequence

ANNEX_HEADING = "ANNEXURE — ATTRIBUTED CLINICAL STATEMENT (HUMAN-AUTHORED)"

NO_HUMAN_STATEMENT_NOTICE = (
    "CLINICAL STATEMENT STATUS: No statement from a named clinician is attached to this "
    "document. Any clinical reasoning above is general reasoning drafted by software, not "
    "the opinion of a named doctor, and must not be presented as one."
)

STATEMENT_NATURE_NOTICE = (
    "Nature of this statement: the professional opinion of the named reviewer, written and "
    "confirmed by them. It is not an insurer determination, not a finding of ArogyaRakshak, "
    "and has not been accepted or verified by any insurer or regulator."
)


def _line(label: str, value: Any) -> str:
    return f"{label}: {value if value not in (None, '') else 'Not provided'}"


def render_statement_block(statement: Dict[str, Any]) -> str:
    rv = statement.get("reviewer_snapshot") or {}
    evidence = statement.get("evidence_reviewed") or []
    evidence_lines = [
        f"  - {e.get('label', e.get('kind', 'Item'))} [{e.get('provenance', 'AI_DERIVED')}]"
        for e in evidence
    ] or ["  - (none listed)"]

    parts: List[str] = [
        ANNEX_HEADING,
        _line("Reviewer", rv.get("name")),
        _line("Professional designation", rv.get("designation")),
        _line("Reviewer category", rv.get("category_label")),
        _line("Specialty", rv.get("specialty")),
        _line("Registration number", rv.get("registration_number")),
        _line("Registration authority", rv.get("registration_authority")),
        _line("Verification status", rv.get("verification_label")),
        _line("Affiliation", rv.get("affiliation")),
        _line("Conflict of interest", statement.get("coi_label")),
        _line("Conflict-of-interest disclosure", statement.get("coi_disclosure")),
        _line("Statement version", statement.get("statement_version")),
        _line("Finalized at (UTC)", statement.get("finalized_at")),
        _line("Statement reference", statement.get("statement_id")),
        _line("Content SHA-256", statement.get("content_sha256")),
        "",
        "Clinical question put to the reviewer:",
        str(statement.get("clinical_question") or ""),
        "",
        "Evidence the reviewer confirmed they reviewed (with provenance):",
        *evidence_lines,
        "",
        "Reviewer's statement (verbatim):",
        str(statement.get("reviewer_statement") or ""),
        "",
        "Limitations stated by the reviewer:",
        str(statement.get("limitations") or ""),
        "",
        STATEMENT_NATURE_NOTICE,
    ]
    return "\n".join(parts)


def render_annex(statements: Sequence[Dict[str, Any]]) -> str:
    if not statements:
        return NO_HUMAN_STATEMENT_NOTICE
    return "\n\n".join(render_statement_block(s) for s in statements)
