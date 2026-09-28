"""
The single trust decision for an extracted medicine (ADR-011).

Every consumer that turns a medicine entity into something the patient acts on — today
DawaCheck's price benchmark, and the evidence packets reviewers see — asks this one
function whether the entry is a settled fact. Keeping it in one place means no consumer
can quietly fall back to benchmarking uncertain OCR text.

Precedence (first match wins; blocking states always beat settled ones):

1. An open human-reading task for the entry                      -> blocked
2. An escalated task (readers disagreed / could not read)        -> blocked, unless a
   LATER whole-entry reading by two readers settled the entry
3. An agreed reading that could not be placed (`NOT_APPLIED`)    -> blocked
4. OCR uncertainty with no linked task (`ocr_uncertainty`:
   ambiguous, possible match, over the task cap, ungrounded)     -> blocked
5. A placed human reading (`human_transcription.RESOLVED`)       -> trusted,
                                                                    HUMAN_REVIEWED name
6. Otherwise                                                     -> trusted,
                                                                    AI_DERIVED name

States 3 and 4 are cleared only by a reading of the WHOLE entry (a case-holder flag
read by two independent readers); a later partial reading never clears them.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Mapping, Optional

from .transcription import OCR_UNCERTAINTY_NEXT_STEP


class MedicineTrustState(str, Enum):
    AWAITING_HUMAN_READING = "AWAITING_HUMAN_READING"
    READERS_DISAGREED = "READERS_DISAGREED"
    READING_NOT_APPLIED = "READING_NOT_APPLIED"
    OCR_UNCERTAIN = "OCR_UNCERTAIN"
    HUMAN_RESOLVED = "HUMAN_RESOLVED"
    MACHINE_EXTRACTED = "MACHINE_EXTRACTED"


BLOCKED_STATES = frozenset(
    {
        MedicineTrustState.AWAITING_HUMAN_READING,
        MedicineTrustState.READERS_DISAGREED,
        MedicineTrustState.READING_NOT_APPLIED,
        MedicineTrustState.OCR_UNCERTAIN,
    }
)


@dataclass(frozen=True)
class PendingTask:
    """The unresolved (open or escalated) HIGH-risk task linked to the entry, if any."""

    task_id: str
    status: str
    resolved_at: Optional[str] = None


@dataclass(frozen=True)
class MedicineTrustDecision:
    state: MedicineTrustState
    benchmarkable: bool
    name: str
    name_provenance: str
    note: Optional[str] = None
    task_id: Optional[str] = None
    # Kept for API compatibility: the transcription status the client already renders.
    transcription_status: Optional[str] = None
    reasons: List[str] = field(default_factory=list)


def _later(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a and b and str(a) > str(b))


def decide_medicine_trust(
    name: str, meta: Optional[Mapping[str, Any]], pending: Optional[PendingTask] = None
) -> MedicineTrustDecision:
    meta = meta if isinstance(meta, Mapping) else {}
    transcription = meta.get("human_transcription") if isinstance(meta.get("human_transcription"), Mapping) else {}
    uncertainty = meta.get("ocr_uncertainty") if isinstance(meta.get("ocr_uncertainty"), Mapping) else {}
    settled_whole = transcription.get("status") == "RESOLVED" and transcription.get("whole_entry") is True

    if pending is not None and pending.status in ("OPEN", "AWAITING_SECOND_REVIEW"):
        return MedicineTrustDecision(
            state=MedicineTrustState.AWAITING_HUMAN_READING,
            benchmarkable=False,
            name=name,
            name_provenance="AI_DERIVED",
            note=(
                "This medicine's name or strength was read with low confidence and is awaiting independent "
                "human transcription, so it has not been benchmarked. An uncertain reading is never treated "
                "as a medication fact."
            ),
            task_id=pending.task_id,
            transcription_status=pending.status,
        )
    if pending is not None and pending.status == "HUMAN_ESCALATION_REQUIRED":
        if not (settled_whole and _later(transcription.get("resolved_at"), pending.resolved_at)):
            return MedicineTrustDecision(
                state=MedicineTrustState.READERS_DISAGREED,
                benchmarkable=False,
                name=name,
                name_provenance="AI_DERIVED",
                note=(
                    "Human readers could not agree on this medicine's text. Confirm it with the prescriber or "
                    "dispensing pharmacist; it has not been benchmarked."
                ),
                task_id=pending.task_id,
                transcription_status=pending.status,
            )

    if transcription.get("status") == "NOT_APPLIED":
        return MedicineTrustDecision(
            state=MedicineTrustState.READING_NOT_APPLIED,
            benchmarkable=False,
            name=name,
            name_provenance="AI_DERIVED",
            note=(
                f"Independent human readers read this entry as '{transcription.get('human_reading')}', which could "
                "not be matched to the extracted text. It has not been benchmarked — confirm the medicine with "
                "the prescriber or dispensing pharmacist."
            ),
            task_id=transcription.get("task_id"),
            transcription_status="NOT_APPLIED",
        )

    if uncertainty.get("status") == "UNRESOLVED":
        return MedicineTrustDecision(
            state=MedicineTrustState.OCR_UNCERTAIN,
            benchmarkable=False,
            name=name,
            name_provenance="AI_DERIVED",
            note=(
                f"{uncertainty.get('explanation') or 'Part of this entry was read with low confidence.'} "
                f"It has not been benchmarked. {uncertainty.get('next_step') or OCR_UNCERTAINTY_NEXT_STEP}"
            ).strip(),
            transcription_status="OCR_UNCERTAIN",
            reasons=list(uncertainty.get("reasons") or []),
        )

    if transcription.get("status") == "RESOLVED" and transcription.get("value"):
        return MedicineTrustDecision(
            state=MedicineTrustState.HUMAN_RESOLVED,
            benchmarkable=True,
            name=str(transcription["value"]),
            name_provenance="HUMAN_REVIEWED",
            task_id=transcription.get("task_id"),
        )

    return MedicineTrustDecision(
        state=MedicineTrustState.MACHINE_EXTRACTED,
        benchmarkable=True,
        name=name,
        name_provenance="AI_DERIVED",
    )


def display_label(decision: MedicineTrustDecision) -> str:
    """Short, patient-readable label for the state (clients may localise it)."""
    return {
        MedicineTrustState.AWAITING_HUMAN_READING: "Awaiting human reading",
        MedicineTrustState.READERS_DISAGREED: "Readers disagreed — confirm with pharmacist",
        MedicineTrustState.READING_NOT_APPLIED: "Human reading could not be applied",
        MedicineTrustState.OCR_UNCERTAIN: "Unclear on the document — not yet read by a human",
        MedicineTrustState.HUMAN_RESOLVED: "Human-reviewed reading",
        MedicineTrustState.MACHINE_EXTRACTED: "Machine-extracted",
    }[decision.state]


def trust_summary(decision: MedicineTrustDecision) -> Dict[str, Any]:
    return {
        "state": decision.state.value,
        "label": display_label(decision),
        "benchmarkable": decision.benchmarkable,
        "reasons": list(decision.reasons),
    }
