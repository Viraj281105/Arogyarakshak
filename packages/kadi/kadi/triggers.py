"""
Kadi auto-triggering — which module checks a case has enough context for (#32).

Technical Documentation §4.4: once Kadi has enough context it can fire other modules
without a re-upload. This module is the declarative, deterministic half of that: given
how many entities of each type a case holds, whether the patient consented to
cross-module sharing, and whether an income profile exists, it reports for every module
check whether it is READY, NOT_READY (and exactly which context is missing), or
BLOCKED_NO_CONSENT.

Running the checks, and storing their results, is the API's job (apps/api/app/auto_triggers.py).

Only read-only analyses auto-run. The DaaviSetu pre-authorization claim is never run
automatically: it needs policy details only the policyholder can supply and creates a
record the patient signs.
"""

from typing import Dict, Iterable, List, Literal, Optional

from pydantic import BaseModel, Field

ReadinessStatus = Literal["READY", "NOT_READY", "BLOCKED_NO_CONSENT"]


class CheckRequirement(BaseModel):
    module_check: str
    all_of: List[str] = Field(default_factory=list, description="entity types that must each be present")
    any_of: List[str] = Field(default_factory=list, description="at least one of these entity types")
    needs_income_profile: bool = False
    auto_run: bool
    description: str


MODULE_REQUIREMENTS: List[CheckRequirement] = [
    CheckRequirement(
        module_check="billnyay_audit",
        all_of=["billing_item"],
        auto_run=True,
        description="Benchmark billed line items against CGHS rates.",
    ),
    CheckRequirement(
        module_check="billnyay_icd_audit",
        all_of=["diagnosis", "procedure"],
        auto_run=True,
        description="Check billed procedures against the diagnosis's ICD-10 code.",
    ),
    CheckRequirement(
        module_check="dawacheck_benchmark",
        all_of=["medicine"],
        auto_run=True,
        description="Compare medicine prices with NPPA ceiling prices.",
    ),
    CheckRequirement(
        module_check="schemesetu_eligibility",
        any_of=["diagnosis", "procedure"],
        needs_income_profile=True,
        auto_run=True,
        description="Provisional PMJAY/MJPJAY eligibility using the case's saved income profile.",
    ),
    CheckRequirement(
        module_check="daavisetu_claim",
        all_of=["hospital", "diagnosis"],
        auto_run=False,
        description=(
            "Pre-authorization claim form. Never run automatically: it needs policy details "
            "only the policyholder can give and produces a record the patient signs."
        ),
    ),
]

REQUIREMENTS_BY_CHECK: Dict[str, CheckRequirement] = {r.module_check: r for r in MODULE_REQUIREMENTS}


class ContextSnapshot(BaseModel):
    consent_opt_in: bool
    entity_counts: Dict[str, int] = Field(default_factory=dict)
    has_income_profile: bool = False


class ModuleReadiness(BaseModel):
    module_check: str
    status: ReadinessStatus
    auto_run: bool
    missing_context: List[str] = Field(default_factory=list)
    description: str


def count_entity_types(entity_types: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for entity_type in entity_types:
        counts[entity_type] = counts.get(entity_type, 0) + 1
    return counts


def evaluate_readiness(snapshot: ContextSnapshot) -> List[ModuleReadiness]:
    results: List[ModuleReadiness] = []
    for req in MODULE_REQUIREMENTS:
        if not snapshot.consent_opt_in:
            results.append(
                ModuleReadiness(
                    module_check=req.module_check,
                    status="BLOCKED_NO_CONSENT",
                    auto_run=req.auto_run,
                    missing_context=["consent_opt_in"],
                    description=req.description,
                )
            )
            continue

        missing = [t for t in req.all_of if snapshot.entity_counts.get(t, 0) < 1]
        if req.any_of and not any(snapshot.entity_counts.get(t, 0) for t in req.any_of):
            missing.append(" or ".join(req.any_of))
        if req.needs_income_profile and not snapshot.has_income_profile:
            missing.append("income_profile")

        results.append(
            ModuleReadiness(
                module_check=req.module_check,
                status="NOT_READY" if missing else "READY",
                auto_run=req.auto_run,
                missing_context=missing,
                description=req.description,
            )
        )
    return results


def checks_to_run(readiness: Iterable[ModuleReadiness], only: Optional[Iterable[str]] = None) -> List[str]:
    allowed = set(only) if only is not None else None
    return [
        r.module_check
        for r in readiness
        if r.status == "READY" and r.auto_run and (allowed is None or r.module_check in allowed)
    ]
