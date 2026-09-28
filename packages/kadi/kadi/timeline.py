"""
Kadi — case timeline: what has actually happened to a case, in plain language.

Every entry is built from a record that already exists (a stored document digest, an
append-only audit event, a module insight, an appeal row) and carries that record's own
timestamp — so the timeline can never show a step before it happened, and never shows a
step that did not happen. What is merely true *now* (how many medicines can be
price-checked) is reported separately as current state, not as a past event.

Pure and DB-agnostic: the API gathers the rows, this module only labels and orders them.
Labels never contain clinical text, document content or reviewer credentials.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional, Sequence

MACHINE = "MACHINE"
HUMAN = "HUMAN"
PATIENT = "PATIENT"


@dataclass(frozen=True)
class TimelineEvent:
    at: datetime
    kind: str
    label: str
    detail: Optional[str] = None
    actor: str = MACHINE  # MACHINE | HUMAN | PATIENT


@dataclass
class TimelineInput:
    documents: Sequence[Mapping[str, Any]] = ()  # {"at", "extension", "source"}
    entity_counts: Mapping[str, int] = field(default_factory=dict)
    held_back_medicines: int = 0
    audit_events: Sequence[Mapping[str, Any]] = ()  # {"at", "event_type", "actor_type", "details"}
    module_insights: Sequence[Mapping[str, Any]] = ()  # {"at", "module_check", "status", "summary"}
    safety_matches: Sequence[Mapping[str, Any]] = ()  # {"at", "rule_title"}
    appeal_at: Optional[datetime] = None
    claim_package_at: Optional[datetime] = None
    live_status: Optional[Mapping[str, Any]] = None  # last in-memory processing event


_DOC_KIND = {".txt": "Text document", ".csv": "Text document", ".pdf": "PDF"}

# Audit event -> (label, actor). Only events a patient benefits from seeing are listed;
# drafting keystrokes (STATEMENT_EDITED) are folded away.
_AUDIT_LABELS: Dict[str, "tuple[str, str]"] = {
    "TRANSCRIPTION_REQUESTED": ("Unclear reading sent for independent human reading", MACHINE),
    "TRANSCRIPTION_ASSIGNED": ("A reader was assigned to an unclear reading", PATIENT),
    "TRANSCRIPTION_SUBMITTED": ("A reader submitted a blind reading", HUMAN),
    "TRANSCRIPTION_CONFIRMED": ("Two independent readers agreed", HUMAN),
    "TRANSCRIPTION_REJECTED": ("Readers disagreed or could not read it — confirm with the pharmacist", HUMAN),
    "TRANSCRIPTION_CANCELLED": ("A reading request was cancelled", PATIENT),
    "REVIEW_REQUESTED": ("Clinical review requested", PATIENT),
    "REVIEWER_ASSIGNED": ("Reviewer assigned", PATIENT),
    "COI_DECLARED": ("Reviewer declared any conflict of interest", HUMAN),
    "REVIEW_ACCEPTED": ("Reviewer accepted the review", HUMAN),
    "REVIEW_DECLINED": ("Reviewer declined the review", HUMAN),
    "REVIEW_CANCELLED": ("Clinical review cancelled", PATIENT),
    "EVIDENCE_ACCESSED": ("Reviewer opened the shared evidence", HUMAN),
    "STATEMENT_CREATED": ("Reviewer started a statement (private draft)", HUMAN),
    "STATEMENT_SUBMITTED": ("Statement locked for finalization", HUMAN),
    "STATEMENT_FINALIZED": ("Doctor-authored statement finalized and signed", HUMAN),
    "STATEMENT_SUPERSEDED": ("An earlier statement was superseded by a newer version", HUMAN),
    "STATEMENT_WITHDRAWN": ("The reviewer withdrew their statement", HUMAN),
    "FACT_DECIDED": ("A doctor recorded a decision on a clinical fact", HUMAN),
}

_MODULE_LABELS = {
    "billnyay_audit": "BillNyay bill audit",
    "billnyay_icd_audit": "BillNyay diagnosis–procedure check",
    "dawacheck_benchmark": "DawaCheck medicine price check",
    "schemesetu_eligibility": "SchemeSetu scheme eligibility",
    "daavisetu_claim": "DaaviSetu pre-authorization",
    "bimanyay_analysis": "BimaNyay denial analysis",
}

# In-flight processing stages (in-memory, per API process) -> readable stage names.
LIVE_STAGE_LABELS = {
    "upload_received": "Document received",
    "ocr_start": "Reading the document",
    "demo_fixture": "Demo fixture replayed (synthetic document)",
    "extraction_start": "Extracting information",
    "database_write": "Saving the extracted information",
    "entity_resolution": "Matching with information already in the case",
    "transcription_flags": "Flagging unclear readings for human readers",
    "module_checks": "Running automatic module checks",
    "completed": "Processing complete",
    "duplicate": "Already processed — nothing added",
    "failed": "Processing failed",
    "timeout": "Processing status timed out",
    "idle": "Nothing in progress",
}


def _plural(n: int, one: str, many: Optional[str] = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _extraction_detail(counts: Mapping[str, int], held_back: int) -> str:
    parts = []
    for key, one in (("billing_item", "bill line"), ("medicine", "medicine"), ("procedure", "procedure"), ("diagnosis", "diagnosis")):
        n = int(counts.get(key, 0) or 0)
        if n:
            parts.append(_plural(n, one, "diagnoses" if key == "diagnosis" else None))
    text = ", ".join(parts) if parts else "No bill lines, medicines, procedures or diagnoses were found"
    return text + "."


def _module_detail(check: str, summary: Mapping[str, Any]) -> Optional[str]:
    if check == "dawacheck_benchmark":
        total = summary.get("medicines", 0)
        done = summary.get("benchmarked", 0)
        unclear = summary.get("price_basis_unclear", 0)
        text = f"{done} of {total} medicine(s) compared with the NPPA ceiling"
        if unclear:
            text += f"; {unclear} not compared because the price basis (per tablet / strip / pack) is not stated"
        return text + "."
    if check == "billnyay_audit":
        if "benchmarked_count" in summary:
            return f"{summary.get('benchmarked_count', 0)} bill line(s) compared with CGHS rates."
    return None


def build_case_timeline(data: TimelineInput) -> Dict[str, Any]:
    events: List[TimelineEvent] = []

    docs = sorted(data.documents, key=lambda d: d["at"])
    for d in docs:
        kind = _DOC_KIND.get(str(d.get("extension") or "").lower(), "Image")
        events.append(
            TimelineEvent(
                d["at"], "document", "Document received and read",
                f"{kind} processed in memory; the file itself was not kept.", PATIENT,
            )
        )
    if docs:
        events.append(
            TimelineEvent(
                docs[-1]["at"], "extraction", "Information extracted",
                _extraction_detail(data.entity_counts, data.held_back_medicines), MACHINE,
            )
        )

    drafting_seen = False
    for ev in sorted(data.audit_events, key=lambda e: e["at"]):
        et = ev.get("event_type")
        if et == "STATEMENT_EDITED":
            continue
        if et == "STATEMENT_CREATED":
            if drafting_seen:
                continue
            drafting_seen = True
        mapped = _AUDIT_LABELS.get(str(et))
        if not mapped:
            continue
        label, actor = mapped
        details = ev.get("details") or {}
        detail = None
        if et == "TRANSCRIPTION_CONFIRMED":
            detail = (
                "The agreed reading was applied to the medicine; it can now be price-checked."
                if details.get("applied_to_entity")
                else "The agreed reading could not be matched to the extracted entry, so the medicine stays held back."
            )
        elif et == "TRANSCRIPTION_REQUESTED" and "held_back_entities" in details:
            # The upload-time summary: unclear readings that could not be tied to exactly
            # one medicine hold those medicines back (no reader task is created for them).
            label = "Unclear readings could not be tied to one medicine — those medicines are held back"
            held = int(details.get("held_back_entities") or 0)
            detail = (
                f"{_plural(held, 'medicine')} will not be price-checked until a human reads the whole entry."
                if held
                else None
            )
        if et == "TRANSCRIPTION_REQUESTED" and ev.get("actor_type") not in (None, "SYSTEM"):
            actor = PATIENT
        events.append(TimelineEvent(ev["at"], "review" if et.startswith(("REVIEW", "STATEMENT", "COI", "EVIDENCE", "FACT")) else "reading", label, detail, actor))

    for ins in sorted(data.module_insights, key=lambda i: i["at"]):
        check = str(ins.get("module_check"))
        name = _MODULE_LABELS.get(check, check.replace("_", " ").capitalize())
        status = str(ins.get("status") or "")
        if status == "COMPLETED":
            events.append(TimelineEvent(ins["at"], "module", f"Automatic check ran: {name}", _module_detail(check, ins.get("summary") or {})))
        elif status:
            events.append(TimelineEvent(ins["at"], "module", f"Automatic check could not run: {name}", None))

    for m in sorted(data.safety_matches, key=lambda s: s["at"]):
        events.append(
            TimelineEvent(
                m["at"], "safety", "Safety rule matched words in the document",
                f"{m.get('rule_title') or 'A safety rule'} — see the safety notice above.",
            )
        )

    if data.appeal_at:
        events.append(TimelineEvent(data.appeal_at, "appeal", "Appeal letter prepared", "Machine-drafted; any doctor-authored statement is attached verbatim, never rewritten.", PATIENT))
    if data.claim_package_at:
        events.append(TimelineEvent(data.claim_package_at, "claim", "Pre-authorization package prepared", None, PATIENT))

    events.sort(key=lambda e: e.at)

    live = dict(data.live_status or {})
    live_status = str(live.get("status") or "")
    in_progress = None
    failure = None
    if live_status == "failed":
        failure = {
            "stage": LIVE_STAGE_LABELS["failed"],
            "message": live.get("log") or "Document processing failed.",
            "recovery": "Upload the document again. If it keeps failing, try a clearer scan or a PDF/text export.",
        }
    elif live_status and live_status not in ("completed", "duplicate", "idle", "timeout"):
        in_progress = {"stage": LIVE_STAGE_LABELS.get(live_status, "Processing"), "message": live.get("log")}

    return {
        "events": [
            {"at": e.at.isoformat(), "kind": e.kind, "label": e.label, "detail": e.detail, "actor": e.actor} for e in events
        ],
        "in_progress": in_progress,
        "failure": failure,
    }
