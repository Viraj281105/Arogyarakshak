"""
Human resolution of uncertain OCR readings (ADR-011).

This is deliberately NOT a doctor feature: reading handwriting and drug shorthand is
what pharmacists, medical transcriptionists and trained annotators do professionally.

Zero retention (ADR-003) is preserved: no image or crop is ever stored. A task keeps
only the redacted OCR reading, a redacted line of surrounding text with the uncertain
token masked, and a location hint. Reviewers read the original, which stays with the
patient.

Safety rule: a token that may be a medicine, strength, frequency, route or duration is
HIGH risk and needs two independent human readings that agree. Anything else is
STANDARD. A single uncertain reading is never accepted as a medication fact.
"""

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from kadi.redaction import redact_pii

MASK = "▢▢▢"
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.5
MAX_VALUE_CHARS = 200
MAX_TASKS_PER_DOCUMENT = 10


class FieldType(str, Enum):
    MEDICINE_NAME = "MEDICINE_NAME"
    STRENGTH = "STRENGTH"
    FREQUENCY = "FREQUENCY"
    ROUTE = "ROUTE"
    DURATION = "DURATION"
    # Could not tell what it is. Treated as possibly-medication (HIGH risk).
    UNCLASSIFIED = "UNCLASSIFIED"
    # Clearly not medication-related (an amount, a date).
    NON_CLINICAL = "NON_CLINICAL"


class RiskLevel(str, Enum):
    HIGH = "HIGH"
    STANDARD = "STANDARD"


class TaskStatus(str, Enum):
    OPEN = "OPEN"
    AWAITING_SECOND_REVIEW = "AWAITING_SECOND_REVIEW"
    RESOLVED = "RESOLVED"
    HUMAN_ESCALATION_REQUIRED = "HUMAN_ESCALATION_REQUIRED"
    CANCELLED = "CANCELLED"


class ReaderConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


OPEN_TASK_STATES = frozenset({TaskStatus.OPEN.value, TaskStatus.AWAITING_SECOND_REVIEW.value})

_STRENGTH = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|µg|g|gm|ml|iu|units?|%)\b", re.IGNORECASE)
_FREQUENCY = re.compile(
    r"\b(?:od|bd|bid|tds|tid|qds|qid|hs|sos|prn|stat|q\d{1,2}h|once|twice|thrice|daily)\b"
    r"|\b[01]\s*-\s*[01]\s*-\s*[01]\b",
    re.IGNORECASE,
)
_ROUTE = re.compile(
    r"\b(?:oral|po|iv|im|sc|s/c|sl|topical|inhal\w*|nasal|rectal|per\s+oral)\b", re.IGNORECASE
)
_DURATION = re.compile(
    r"(?:\bx\s*\d+\s*(?:days?|d|weeks?|wks?|months?)\b|\bfor\s+\d+\s*(?:days?|weeks?|months?)\b"
    r"|\b\d+\s*(?:days?|weeks?|months?)\b)",
    re.IGNORECASE,
)
_DOSAGE_FORM = re.compile(r"\b(?:tab|tabs|tablet|cap|caps|capsule|inj|injection|syp|syrup|susp|drops?|oint)\b\.?", re.IGNORECASE)
_AMOUNT = re.compile(r"(?:₹|rs\.?|inr)\s*\d", re.IGNORECASE)
_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b")


def infer_field_type(token: str, line: str = "") -> FieldType:
    """Best-effort classification of what an uncertain token represents. When unsure the
    answer is UNCLASSIFIED, which is treated as HIGH risk — never the permissive guess."""
    t = token or ""
    ctx = f"{line} {t}"
    if _STRENGTH.search(t):
        return FieldType.STRENGTH
    if _FREQUENCY.search(t):
        return FieldType.FREQUENCY
    if _DURATION.search(t):
        return FieldType.DURATION
    if _ROUTE.search(t):
        return FieldType.ROUTE
    if (_AMOUNT.search(t) or _DATE.search(t)) and not _DOSAGE_FORM.search(ctx):
        return FieldType.NON_CLINICAL
    if _DOSAGE_FORM.search(ctx) or _STRENGTH.search(ctx) or _FREQUENCY.search(ctx):
        # An unreadable word on a line that looks like a prescription entry is most
        # likely the drug name.
        return FieldType.MEDICINE_NAME
    return FieldType.UNCLASSIFIED


def risk_for_field(field_type: str) -> RiskLevel:
    return RiskLevel.STANDARD if field_type == FieldType.NON_CLINICAL.value else RiskLevel.HIGH


def required_reviews_for(risk: str) -> int:
    return 2 if risk == RiskLevel.HIGH.value else 1


@dataclass(frozen=True)
class OcrSegment:
    text: str
    confidence: float
    bbox: Optional[List[List[float]]] = None


def mask_token(line: str, token: str) -> str:
    if token and token in line:
        return line.replace(token, MASK, 1)
    return f"{line} {MASK}".strip() if line else MASK


# Tokens that carry no information worth a human reading: prescription markers and
# dosage-form abbreviations. A low-confidence "Tab." must never become a task.
_NOISE_TOKENS = frozenset(
    {"rx", "tab", "tabs", "tablet", "cap", "caps", "capsule", "inj", "injection", "syp",
     "syrup", "susp", "drop", "drops", "oint", "sig", "dr", "sos", "od", "bd", "tds"}
)
# Prescriber / identity lines (doctor's name, degrees, registration numbers). These are
# personal data about a third party and are never sent to a reader, even as context.
_IDENTITY_LINE = re.compile(
    r"(?:^|\s)dr\.?\s|\b(?:mbbs|md|ms|dnb|bams|bhms|mch|frcs|mrcp|reg(?:istration)?\.?\s*no)\b",
    re.IGNORECASE,
)
ELIDED_CONTEXT = "…"


def meaningful_tokens(value: str) -> List[str]:
    """Normalized tokens a human reading can actually settle: at least 3 characters and
    not a prescription marker."""
    tokens = normalize_reading(value).split()
    return [t for t in tokens if len(re.sub(r"\W", "", t)) >= 3 and t not in _NOISE_TOKENS]


def looks_like_identity_line(text: str) -> bool:
    return bool(_IDENTITY_LINE.search(text or ""))


def looks_like_medication_line(text: str) -> bool:
    t = text or ""
    return bool(
        _DOSAGE_FORM.search(t) or _STRENGTH.search(t) or _FREQUENCY.search(t)
        or _DURATION.search(t) or _ROUTE.search(t)
    )


def _context_line(text: str) -> str:
    """A neighbouring line is shown only if it looks like part of a medication entry;
    anything else (letterhead, names, addresses) is elided, never forwarded."""
    if not text or looks_like_identity_line(text) or not looks_like_medication_line(text):
        return ELIDED_CONTEXT
    return redact_pii(text)


def select_uncertain_segments(
    segments: Sequence[OcrSegment],
    threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Low-confidence OCR segments that are worth a human reading, as task payloads.

    Skipped: segments with a direct identifier or a prescriber/identity line, pure
    prescription markers ("Rx", "Tab."), tokens too short to settle, and non-clinical
    fields (amounts, dates) that nothing downstream consumes. Context keeps only
    medication-looking neighbour lines, redacted, with the uncertain token masked.
    Callers must still link a payload to an extracted entity before creating a task —
    an unlinked reading has no consumer (see `link_candidate_to_entity`). No cap by
    default: the per-document task cap belongs AFTER linking, otherwise unlinkable
    letterhead noise at the top of a page would use it up before the medicine lines.
    """
    tasks: List[Dict[str, Any]] = []
    for index, seg in enumerate(segments):
        text = (seg.text or "").strip()
        if not text or seg.confidence >= threshold:
            continue
        candidate = redact_pii(text)
        # A segment that carried a direct identifier is identity data, not a clinical
        # token: never worth resolving, and sending even its label to a reviewer would
        # leak that an identifier sat there.
        if candidate != text or looks_like_identity_line(text):
            continue
        if not meaningful_tokens(text):
            continue
        prev_line = segments[index - 1].text if index > 0 else ""
        next_line = segments[index + 1].text if index + 1 < len(segments) else ""
        field_type = infer_field_type(text, f"{prev_line} {next_line}")
        if field_type == FieldType.NON_CLINICAL:
            continue
        context = " ".join(
            x for x in (_context_line(prev_line), mask_token(text, text), _context_line(next_line)) if x
        )
        bbox = None
        if seg.bbox:
            try:
                bbox = [[round(float(x), 1), round(float(y), 1)] for x, y in seg.bbox]
            except (TypeError, ValueError):
                bbox = None
        risk = risk_for_field(field_type.value)
        tasks.append(
            {
                "field_type": field_type.value,
                "risk_level": risk.value,
                "ocr_candidate": candidate[:MAX_VALUE_CHARS],
                "ocr_confidence": round(float(seg.confidence), 3),
                "masked_context": context[:500],
                "location_hint": {"segment_index": index, "bbox": bbox},
                "required_reviews": required_reviews_for(risk.value),
            }
        )
        if limit is not None and len(tasks) >= limit:
            break
    return tasks


def normalize_reading(value: str) -> str:
    """Comparison key for two human readings: case, width, spacing and punctuation
    differences do not count as disagreement ("Dolo 650 mg" == "dolo 650mg")."""
    v = unicodedata.normalize("NFKC", value or "").casefold()
    v = re.sub(r"(\d)\s+(mg|mcg|g|gm|ml|iu|units?)\b", r"\1\2", v)
    v = re.sub(r"[^\w%/]+", " ", v)
    return " ".join(v.split())


def link_candidate_to_entity(candidate: str, entities: Sequence[Tuple[str, str]]) -> Optional[str]:
    """The id of the single extracted entity the uncertain reading is about, by whole
    tokens in either direction: every meaningful token of the reading is in the entity
    name ("Augmntn" -> "Tab Augmntn 625mg"), or every meaningful token of the entity name
    is in the reading (a whole uncertain line "Tab Augmntn 625mg 1-0-1" -> entity
    "Augmntn", whose strength extraction stored separately). Ambiguous (several
    matches) or no match returns None: an unlinked reading has no downstream consumer.

    Whole-token matching matters: a substring test linked a stray "Tab." to every
    medicine and let its "resolution" replace the drug's name.
    """
    wanted = set(meaningful_tokens(candidate))
    if not wanted:
        return None
    reading_tokens = set(normalize_reading(candidate).split())
    matches = []
    for eid, name in entities:
        name_tokens = set(meaningful_tokens(name))
        if wanted <= set(normalize_reading(name).split()) or (name_tokens and name_tokens <= reading_tokens):
            matches.append(eid)
    return matches[0] if len(matches) == 1 else None


_LEADING_FORM_MARKERS = re.compile(
    r"^(?:(?:rx|tab|tabs|tablet|cap|caps|capsule|inj|syp|syrup)\b\.?\s*)+", re.IGNORECASE
)


def substitute_reading(entity_name: str, candidate: str, reading: str) -> Optional[str]:
    """Applies a human reading to an entity name by replacing only the uncertain part.

    Returns None when the substitution cannot be done safely, so the caller leaves the
    entity untouched instead of overwriting a whole medicine name with a fragment.
    A leading dosage-form marker the extraction dropped ("Tab. Pantop" read, entity
    "Pantop 40") is stripped from both the reading and the human value before matching.
    """
    if not entity_name or not candidate or not reading:
        return None
    if normalize_reading(candidate) == normalize_reading(entity_name):
        return reading
    attempts = [(candidate.strip(), reading)]
    bare_candidate = _LEADING_FORM_MARKERS.sub("", candidate.strip())
    bare_reading = _LEADING_FORM_MARKERS.sub("", reading.strip())
    # A reading that is only a marker ("Tab.") must never stand in for the drug name.
    if bare_candidate and bare_candidate != candidate.strip() and bare_reading:
        attempts.append((bare_candidate, bare_reading))
    for cand, value in attempts:
        pattern = re.compile(rf"(?<!\w){re.escape(cand)}(?!\w)", re.IGNORECASE)
        if len(pattern.findall(entity_name)) == 1:
            return pattern.sub(lambda _m, v=value: v, entity_name, count=1)
    return None


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_reading(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = _CONTROL_CHARS.sub("", value).strip()
    if len(cleaned) > MAX_VALUE_CHARS:
        raise ValueError(f"A transcription may be at most {MAX_VALUE_CHARS} characters.")
    return cleaned or None


@dataclass(frozen=True)
class Reading:
    reviewer_id: str
    value: Optional[str]
    unreadable: bool
    confidence: str


@dataclass(frozen=True)
class ConsensusResult:
    status: TaskStatus
    final_value: Optional[str]
    reason: str


def evaluate_consensus(risk_level: str, readings: Sequence[Reading]) -> ConsensusResult:
    """Decides a task's state from its independent human readings."""
    # One reading per reviewer, however many times a client resubmits.
    by_reviewer: Dict[str, Reading] = {}
    for r in readings:
        by_reviewer.setdefault(r.reviewer_id, r)
    distinct = list(by_reviewer.values())

    if not distinct:
        return ConsensusResult(TaskStatus.OPEN, None, "Awaiting a human reading.")

    if any(r.unreadable or not r.value for r in distinct):
        return ConsensusResult(
            TaskStatus.HUMAN_ESCALATION_REQUIRED,
            None,
            "A reviewer could not read this text. Confirm it directly with the prescriber or dispensing pharmacist.",
        )

    required = required_reviews_for(risk_level)
    if len(distinct) < required:
        return ConsensusResult(
            TaskStatus.AWAITING_SECOND_REVIEW,
            None,
            "Possible medication field: a second, independent reading is required before this is accepted.",
        )

    if required == 1:
        only = distinct[0]
        if only.confidence == ReaderConfidence.LOW.value:
            if len(distinct) < 2:
                return ConsensusResult(
                    TaskStatus.AWAITING_SECOND_REVIEW,
                    None,
                    "The reviewer reported low confidence; a second reading is required.",
                )
        else:
            return ConsensusResult(TaskStatus.RESOLVED, only.value, "Resolved by one reviewer.")

    keys = {normalize_reading(r.value or "") for r in distinct}
    if len(keys) == 1:
        return ConsensusResult(
            TaskStatus.RESOLVED,
            distinct[0].value,
            f"{len(distinct)} independent readings agree.",
        )
    return ConsensusResult(
        TaskStatus.HUMAN_ESCALATION_REQUIRED,
        None,
        "Independent readings disagree. Confirm directly with the prescriber or dispensing pharmacist.",
    )
