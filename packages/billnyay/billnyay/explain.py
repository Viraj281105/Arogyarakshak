"""
BillNyay — "Why am I seeing this?" explanation for one audited bill line (ADR-017).

Built next to the audit decision from the values the audit used: the bill line as
extracted, the CGHS reference row it was matched to, and the per-day/visit/service basis
(`billnyay.rate_basis`). Deterministic; no model call; a value the audit did not record is
reported as "not recorded", never inferred.
"""

from typing import Any, Mapping, Optional

from kadi.explanation import (
    EvidenceItem,
    Explanation,
    ProvenanceClass,
    RuleUsed,
    TrustState,
    Undetermined,
    fact,
)


def _money(v: Optional[float]) -> Optional[str]:
    if v is None:
        return None
    return f"₹{v:,.0f}" if float(v).is_integer() else f"₹{v:,.2f}"


def explain_audit_line(
    *,
    item_name: str,
    charged: float,
    status: str,
    source_file: Optional[str],
    matched_key: Optional[str],
    matched_entry: Optional[Mapping[str, Any]],
    exact_match: bool,
    rates_version: Optional[str],
    benchmark_total: Optional[float],
    deviation_percentage: float,
    benchmark_basis: Optional[str],
    not_benchmarked_reason: Optional[str],
) -> Explanation:
    """`status` is the audit's own status (overcharged / within_benchmark / bundled /
    not_benchmarked); this function reports it, it does not re-decide it."""
    entry = matched_entry if isinstance(matched_entry, Mapping) else {}
    evidence = [
        EvidenceItem(
            label="Bill line",
            value=item_name or None,
            provenance=ProvenanceClass.OCR_EXTRACTED,
            document=source_file,
        ),
        EvidenceItem(
            label="Amount charged",
            value=_money(charged),
            provenance=ProvenanceClass.OCR_EXTRACTED,
            document=source_file,
        ),
    ]
    rules = []
    undetermined = []

    if matched_key is not None:
        rate = entry.get("benchmark_rate")
        rules.append(
            RuleUsed(
                kind="REFERENCE_TABLE_ROW",
                name=f"CGHS reference rate: {entry.get('name') or matched_key}",
                source=f"CGHS rate schedule {rates_version}" if rates_version else None,
                facts=[
                    fact("Reference table key", matched_key),
                    fact("Reference rate", _money(float(rate)) if rate is not None else None),
                    fact("Rate covers", (entry.get("billing_unit") or "").replace("per_", "per ") or None),
                    fact("Category", entry.get("category")),
                    fact("Bundled into a larger package", "yes" if entry.get("bundled") else "no"),
                    fact("How the line was matched", "exact name" if exact_match else "the longest reference name contained in the line"),
                    fact("CGHS procedure code", entry.get("code")),
                    fact("Reference note", entry.get("notes")),
                ],
            )
        )
        if status in ("overcharged", "within_benchmark"):
            rules.append(
                RuleUsed(
                    kind="COMPUTATION",
                    name="Charged amount compared with the reference total for this line",
                    facts=[
                        fact("Reference total used", _money(benchmark_total)),
                        fact("How it was worked out", benchmark_basis),
                        fact("Amount charged", _money(charged)),
                        fact("Difference above reference", f"{deviation_percentage:g}%" if status == "overcharged" else "none"),
                    ],
                )
            )

    if status == "overcharged":
        headline = (
            f"“{item_name}” was charged {_money(charged)}; the CGHS reference for this line is "
            f"{_money(benchmark_total)} ({deviation_percentage:g}% above)."
        )
    elif status == "within_benchmark":
        headline = f"“{item_name}” was charged {_money(charged)}, within the CGHS reference of {_money(benchmark_total)}."
    elif status == "bundled":
        headline = f"“{item_name}” matches a CGHS item that is normally included in a larger package."
        undetermined.append(
            Undetermined(
                code="BUNDLED_ITEM",
                reason=(
                    "The reference marks this item as bundled. Whether this hospital's package actually "
                    "included it is not determined from the documents."
                ),
            )
        )
    else:
        headline = f"“{item_name}” was not compared with a CGHS reference rate."
        if matched_key is None:
            undetermined.append(
                Undetermined(
                    code="NO_REFERENCE_MATCH",
                    reason=(
                        "No row of the bundled CGHS reference table matched this line. That does not mean the "
                        "charge is fair or unfair — it was not checked."
                    ),
                )
            )
        else:
            undetermined.append(
                Undetermined(
                    code="CANNOT_COMPARE_BASIS",
                    reason=not_benchmarked_reason or "The system did not record why this line was not compared.",
                )
            )

    undetermined.append(
        Undetermined(
            code="REFERENCE_IS_BENCHMARK",
            reason=(
                "The CGHS rate is a benchmark, not the rate a private hospital is bound to charge, and the "
                "system has not checked room category, package inclusions or accreditation tier."
            ),
        )
    )
    return Explanation(
        finding_type="BILLNYAY_LINE",
        headline=headline,
        evidence=evidence,
        rules=rules,
        trust=TrustState(
            code="MACHINE_READ_LINE",
            label="Machine-read bill line",
            detail=(
                "The line text and amount were read from your document by OCR/extraction. A per-line "
                "confidence score is not recorded."
            ),
        ),
        undetermined=undetermined,
    )
