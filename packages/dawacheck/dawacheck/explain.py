"""
DawaCheck — "Why am I seeing this?" explanation for a medicine finding (ADR-017).

Built from the values the benchmark already holds (``MedicineBenchmark``) plus the
provenance the caller passes in. Deterministic; no model call; never infers a reason that
was not recorded. Lives in its own module so the matching/reference code is untouched.
"""

import logging
from typing import Iterable, Optional

from kadi.explanation import (
    EvidenceItem,
    Explanation,
    ProvenanceClass,
    RuleUsed,
    TrustState,
    Undetermined,
    fact,
)

from dawacheck.checker import MedicineBenchmark
from dawacheck.price_basis import ComparisonStatus

logger = logging.getLogger("arogyarakshak.dawacheck.explain")

_MATCH_METHOD_TEXT = {
    "exact_or_alias": "Direct match on the reference name or a listed brand alias.",
    "ingredient_dosage_variant": (
        "Same active ingredient as a reference entry but a different strength; the reference ceiling was "
        "scaled in proportion to the strength."
    ),
    "fuzzy_phonetic": (
        "Spelling/sound-alike match (lowest confidence) — a suggestion, not a certain identification."
    ),
    "learned_mapping": "Matched through a brand-to-generic mapping saved from an earlier case.",
}

_BASIS_SOURCE_PROVENANCE = {
    "DECLARED": ProvenanceClass.USER_ENTERED,
    "DOCUMENT_LINE": ProvenanceClass.OCR_EXTRACTED,
    "DOCUMENT_HEADER": ProvenanceClass.OCR_EXTRACTED,
    "API_DEFAULT": ProvenanceClass.RULE_COMPUTED,
    "NONE": ProvenanceClass.NOT_RECORDED,
}


_BASIS_SOURCE_TEXT = {
    "DECLARED": "you declared it",
    "DOCUMENT_LINE": "the bill line itself states it",
    "DOCUMENT_HEADER": "a column heading in the document states it",
    "API_DEFAULT": "assumed per unit (default for a manual check with no basis given)",
    "NONE": "not stated anywhere",
}


def _money(v: Optional[float]) -> Optional[str]:
    return None if v is None else f"₹{v:,.2f}"


def explain_medicine(
    *,
    brand_name: str,
    benchmark: Optional[MedicineBenchmark],
    name_provenance: ProvenanceClass,
    trust_code: str,
    trust_label: str,
    trust_detail: Optional[str] = None,
    not_compared_note: Optional[str] = None,
    source_file: Optional[str] = None,
    entered_by_user: bool = False,
    billed_amount: Optional[float] = None,
    ocr_reasons: Iterable[str] = (),
) -> Explanation:
    """Explains one medicine finding.

    `benchmark` is None when nothing was compared (held back by the trust gate, no cost on
    record, or the name is not in the reference list); `not_compared_note` then carries the
    reason the system already produced, and is shown as is.
    """
    amount_provenance = ProvenanceClass.USER_ENTERED if entered_by_user else ProvenanceClass.OCR_EXTRACTED
    evidence = [
        EvidenceItem(
            label="Medicine name",
            value=brand_name or None,
            provenance=name_provenance,
            document=None if entered_by_user else source_file,
        )
    ]
    rules = []
    undetermined = []

    if benchmark is None:
        evidence.append(
            EvidenceItem(
                label="Billed amount",
                value=_money(billed_amount),
                provenance=amount_provenance if billed_amount is not None else ProvenanceClass.NOT_RECORDED,
                document=None if entered_by_user else source_file,
            )
        )
        code = "HELD_BY_TRUST_GATE" if trust_code not in ("MACHINE_EXTRACTED", "HUMAN_RESOLVED") else (
            "NO_REFERENCE_MATCH" if billed_amount is not None else "NO_COST_RECORDED"
        )
        reason = not_compared_note or "The system did not record why this medicine was not compared."
        undetermined.append(Undetermined(code=code, reason=reason))
        for r in ocr_reasons:
            undetermined.append(Undetermined(code=f"OCR_{r}", reason=f"OCR reading flag recorded: {r}."))
        return Explanation(
            finding_type="DAWACHECK_MEDICINE",
            headline=f"“{brand_name}” was not compared with an NPPA ceiling price.",
            evidence=evidence,
            rules=rules,
            trust=TrustState(code=trust_code, label=trust_label, detail=trust_detail),
            undetermined=undetermined,
        )

    b = benchmark
    evidence.append(
        EvidenceItem(
            label="Billed amount",
            value=_money(b.mrp),
            provenance=amount_provenance,
            document=None if entered_by_user else source_file,
        )
    )
    basis_provenance = _BASIS_SOURCE_PROVENANCE.get(b.basis_source, ProvenanceClass.NOT_RECORDED)
    evidence.append(
        EvidenceItem(
            label=f"Price basis ({b.price_basis_label})",
            value=b.price_basis_label or None,
            provenance=basis_provenance,
            document=None if b.basis_source in ("DECLARED", "API_DEFAULT", "NONE") else source_file,
            source_text=b.basis_evidence,
        )
    )

    rules.append(
        RuleUsed(
            kind="REFERENCE_TABLE_ROW",
            name=f"{b.data_source}: {b.active_ingredient}",
            source=b.data_source,
            facts=[
                fact("Ceiling price", f"{_money(b.nppa_ceiling_price)} per {b.unit_label}"),
                fact("Reference strength (mg)", f"{b.reference_dosage_mg:g}" if b.reference_dosage_mg else None),
                fact("Strength parsed from your medicine name (mg)", f"{b.queried_dosage_mg:g}" if b.queried_dosage_mg else None),
                fact("Ceiling scaled to your strength", "yes" if b.dosage_normalized else "no"),
                fact("How the name was matched", _MATCH_METHOD_TEXT.get(b.match_method, b.match_method)),
                fact("Formulations in the reference table", b.reference_entry_count or None),
                fact("NPPA notification / serial number for this row", None),
            ],
        )
    )
    rules.append(
        RuleUsed(
            kind="PRICE_BASIS",
            name="Price converted to a per-unit price before comparing (ADR-012)",
            facts=[
                fact("Basis of the billed amount", b.price_basis_label),
                fact("Where the basis came from", _BASIS_SOURCE_TEXT.get(b.basis_source, b.basis_source)),
                fact("Billed price per unit", _money(b.billed_unit_price)),
                fact("Ceiling per unit", _money(b.nppa_ceiling_price)),
            ],
        )
    )

    if b.comparison_status == ComparisonStatus.CANNOT_COMPARE:
        headline = f"“{brand_name}” could not be compared reliably."
        undetermined.append(
            Undetermined(
                code=b.comparison_reason_code or "CANNOT_COMPARE",
                reason=b.comparison_note or "The system did not record why the comparison was not made.",
            )
        )
    elif b.is_overcharged:
        headline = (
            f"The billed price per {b.unit_label} ({_money(b.billed_unit_price)}) is above the reference ceiling "
            f"({_money(b.nppa_ceiling_price)}) by {b.deviation_percentage:g}%."
        )
    else:
        headline = (
            f"The billed price per {b.unit_label} ({_money(b.billed_unit_price)}) is within the reference "
            f"ceiling ({_money(b.nppa_ceiling_price)})."
        )

    if b.match_method == "fuzzy_phonetic":
        undetermined.append(
            Undetermined(
                code="FUZZY_NAME_MATCH",
                reason="The medicine was identified by a sound-alike match, so the match itself is not certain.",
            )
        )
    undetermined.append(
        Undetermined(
            code="REFERENCE_IS_SUBSET",
            reason=(
                "The reference list is a curated subset of NPPA Schedule-I; being within or above it is not a "
                "legal finding about this bill."
            ),
        )
    )
    return Explanation(
        finding_type="DAWACHECK_MEDICINE",
        headline=headline,
        evidence=evidence,
        rules=rules,
        trust=TrustState(code=trust_code, label=trust_label, detail=trust_detail),
        undetermined=undetermined,
    )
