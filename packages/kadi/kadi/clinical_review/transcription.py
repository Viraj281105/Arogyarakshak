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

import difflib
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
    # A whole uncertain entry ("Tab Augmntn 625mg 1-0-1") carries a drug-like word as
    # well as a strength: it is a medicine entry, not a strength field.
    if _STRENGTH.search(t) and re.search(r"[^\W\d_]{3,}", _STRENGTH.sub(" ", _DOSAGE_FORM.sub(" ", t))):
        return FieldType.MEDICINE_NAME
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


_UNIT_SUFFIX = re.compile(r"^(\d+(?:\.\d+)?)(?:mg|mcg|g|gm|ml|iu|units?)$")
# Tokens that can never be (part of) a drug's name on their own: markers, frequency and
# unit words. Used to refuse a human reading that would leave an entry with no drug name.
_NON_NAME_TOKENS = _NOISE_TOKENS | frozenset(
    {"mg", "mcg", "g", "gm", "ml", "iu", "unit", "units", "bid", "tid", "qid", "qds", "hs",
     "prn", "stat", "daily", "once", "twice", "thrice", "x", "days", "day"}
)


_DOSING_WORDS = frozenset({"x", "day", "days", "week", "weeks", "wk", "wks", "month", "months"})


def _comparison_tokens(value: str) -> List[str]:
    """Normalized tokens with prescription markers removed ("Tab.", "Rx", "OD"), and the
    dose-pattern / duration fragments of a whole line ("1-0-1", "x 5 days") that never
    name a medicine."""
    return [
        t for t in normalize_reading(value).split()
        if t not in _NOISE_TOKENS and t not in _DOSING_WORDS and not (t.isdigit() and len(t) == 1)
    ]


def _token_eq(a: str, b: str) -> bool:
    """Whole-token equality; a bare number matches the same number with a unit ("40" ==
    "40mg"), because extraction often drops or keeps the unit. Two different units never
    match ("40mcg" != "40mg")."""
    if a == b:
        return True
    ma, mb = _UNIT_SUFFIX.match(a), _UNIT_SUFFIX.match(b)
    return bool((ma and b.isdigit() and ma.group(1) == b) or (mb and a.isdigit() and mb.group(1) == a))


def _tokens_within(needles: Sequence[str], haystack: Sequence[str]) -> bool:
    return bool(needles) and all(any(_token_eq(n, h) for h in haystack) for n in needles)


@dataclass(frozen=True)
class MedicineRef:
    """An extracted medicine as the linker sees it. `dosage` is the strength extraction
    stored separately from the name, when it did."""

    id: str
    name: str
    dosage: Optional[str] = None


def _as_refs(entities: Sequence[Any]) -> List[MedicineRef]:
    refs = []
    for e in entities:
        if isinstance(e, MedicineRef):
            refs.append(e)
        else:
            refs.append(MedicineRef(e[0], e[1] or "", e[2] if len(e) > 2 else None))
    return refs


def token_link_candidates(candidate: str, entities: Sequence[Any]) -> List[str]:
    """Every extracted medicine the uncertain reading names by whole tokens, in either
    direction: every token of the reading is in the medicine's name ("Augmntn" ->
    "Tab Augmntn 625mg"), or every token of the name is in the reading (a whole
    uncertain line "Tab Augmntn 625mg 1-0-1" -> "Augmntn", whose strength extraction
    stored separately). Markers ("Tab.", "Rx") are ignored on both sides; the reading
    must still carry a meaningful token, so a lone marker links to nothing.

    Every token counts, so "Pan-D" does not name "Pan 40" ("d" is missing) but "Pan"
    names both. Whole tokens only — never substrings ("Pan" is not "Pantop"). No
    candidate is preferred over another: two fitting medicines are an ambiguity for a
    human, not a tie for software to break."""
    if not meaningful_tokens(candidate):
        return []
    reading = _comparison_tokens(candidate)
    matches = []
    for ref in _as_refs(entities):
        name = _comparison_tokens(ref.name)
        if not name or not meaningful_tokens(ref.name):
            continue
        if _tokens_within(reading, name) or _tokens_within(name, reading):
            matches.append(ref.id)
    return matches


def link_candidate_to_entity(candidate: str, entities: Sequence[Any]) -> Optional[str]:
    """The id of the single extracted medicine the uncertain reading is about, or None
    when there is no defensible single candidate (none, or several). Callers must treat
    None as "unresolved", never as "nothing to worry about" (see `plan_ocr_uncertainty`).

    Whole-token matching matters: a substring test linked a stray "Tab." to every
    medicine and let its "resolution" replace the drug's name.
    """
    matches = token_link_candidates(candidate, entities)
    return matches[0] if len(matches) == 1 else None


def _similar(a: str, b: str) -> bool:
    if len(a) < 3 or len(b) < 3 or a.isdigit() or b.isdigit():
        return False
    if min(len(a), len(b)) >= 4 and (a.startswith(b[:4]) and b.startswith(a[:4])):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def similar_medicine_candidates(candidate: str, entities: Sequence[Any]) -> List[str]:
    """Medicines an uncertain reading RESEMBLES without naming them token for token —
    typically because the extractor normalised the misread word ("Amoxycilin" read
    uncertainly, extracted as "Amoxicillin"), or because the uncertain part is the
    strength the extractor stored separately ("625mg" -> a medicine with dosage 625mg).

    A resemblance is never a defensible link: the caller must hold these medicines back
    from benchmarking until a human reads the whole entry, not substitute anything."""
    reading = [t for t in meaningful_tokens(candidate) if t not in _NON_NAME_TOKENS]
    if not reading:
        return []
    out = []
    for ref in _as_refs(entities):
        name = [t for t in meaningful_tokens(ref.name) if t not in _NON_NAME_TOKENS]
        dosage = _comparison_tokens(ref.dosage or "")
        if any(_similar(r, n) for r in reading for n in name) or (dosage and _tokens_within(reading, dosage)):
            out.append(ref.id)
    return out


class OcrUncertaintyReason(str, Enum):
    """Why an extracted medicine is held back although no linked task exists for it."""

    # One unclear reading names several medicines ("Pan" with "Pan 40" and "Pan-D").
    AMBIGUOUS = "AMBIGUOUS"
    # An unclear reading resembles this medicine but does not name it token for token
    # (e.g. the extractor normalised a misread word), so it cannot be placed.
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    # Linked unclear reading beyond the per-document task cap: still uncertain.
    OVER_CAP = "OVER_CAP"
    # The document has an unclear medication reading placed nowhere, and this medicine's
    # name is not in the clearly-read OCR text either.
    UNGROUNDED = "UNGROUNDED"


OCR_UNCERTAINTY_EXPLANATIONS: Dict[str, str] = {
    OcrUncertaintyReason.AMBIGUOUS.value: (
        "An unclear OCR reading on the document could belong to more than one medicine, so it was not "
        "attached to any of them automatically."
    ),
    OcrUncertaintyReason.POSSIBLE_MATCH.value: (
        "An unclear OCR reading resembles this medicine but does not match its extracted name; the name may "
        "have been corrected or normalised by the extraction software, which is not a confirmation."
    ),
    OcrUncertaintyReason.OVER_CAP.value: (
        "This medicine's text was read with low confidence, but the per-document limit on automatic "
        "human-reading requests was reached."
    ),
    OcrUncertaintyReason.UNGROUNDED.value: (
        "The document contains an unclear medication reading that matches no extracted medicine, and this "
        "medicine's name was not found in the clearly read text."
    ),
}

OCR_UNCERTAINTY_NEXT_STEP = (
    "Ask for a human reading of the whole entry (two independent readers), or confirm it with the "
    "dispensing pharmacist."
)


@dataclass
class OcrTrustPlan:
    """What to do with a document's uncertain readings. Nothing uncertain is dropped:
    each reading either becomes a linked human-reading task, or holds back the
    medicine(s) it may concern, or (only when it is not medication-related at all) is
    counted as ignored."""

    linked: List[Tuple[Dict[str, Any], str]]
    # entity id -> list of {"reason", "reading", "ocr_confidence"}
    held_back: Dict[str, List[Dict[str, Any]]]
    # Medication-related unclear readings that match no medicine at all.
    unplaced: List[Dict[str, Any]]
    ignored: int = 0


def _grounded(ref: MedicineRef, confident_tokens: Sequence[str]) -> bool:
    name = [t for t in _comparison_tokens(ref.name) if t not in _NON_NAME_TOKENS]
    return _tokens_within(name, confident_tokens)


def plan_ocr_uncertainty(
    payloads: Sequence[Dict[str, Any]],
    medicines: Sequence[Any],
    *,
    document_medicine_ids: Optional[Sequence[str]] = None,
    confident_texts: Sequence[str] = (),
    cap: int = MAX_TASKS_PER_DOCUMENT,
) -> OcrTrustPlan:
    """Decides, for every uncertain reading from `select_uncertain_segments`, how the
    uncertainty is carried forward. The invariant: an uncertain OCR reading of a medicine
    never lets that medicine be treated as a settled fact.

    - exactly one medicine named by whole tokens, within `cap` -> linked task;
    - the same beyond `cap` -> that medicine is held back (OVER_CAP);
    - several medicines named -> all of them held back (AMBIGUOUS);
    - no medicine named but some resembled -> those held back (POSSIBLE_MATCH);
    - nothing named or resembled -> `unplaced`, and every medicine from THIS document
      whose name is not in the clearly read text is held back (UNGROUNDED).
    Only NON_CLINICAL readings are ignored (they never reach here).
    """
    refs = _as_refs(medicines)
    doc_ids = set(document_medicine_ids) if document_medicine_ids is not None else {r.id for r in refs}
    plan = OcrTrustPlan(linked=[], held_back={}, unplaced=[])

    def hold(entity_id: str, reason: OcrUncertaintyReason, payload: Dict[str, Any]) -> None:
        plan.held_back.setdefault(entity_id, []).append(
            {
                "reason": reason.value,
                "reading": payload.get("ocr_candidate"),
                "ocr_confidence": payload.get("ocr_confidence"),
            }
        )

    for payload in payloads:
        if payload.get("risk_level") != RiskLevel.HIGH.value:
            plan.ignored += 1
            continue
        reading = payload.get("ocr_candidate") or ""
        named = token_link_candidates(reading, refs)
        if len(named) == 1:
            if len(plan.linked) < cap:
                plan.linked.append((payload, named[0]))
            else:
                hold(named[0], OcrUncertaintyReason.OVER_CAP, payload)
            continue
        if len(named) > 1:
            for eid in named:
                hold(eid, OcrUncertaintyReason.AMBIGUOUS, payload)
            continue
        resembled = similar_medicine_candidates(reading, refs)
        if resembled:
            for eid in resembled:
                hold(eid, OcrUncertaintyReason.POSSIBLE_MATCH, payload)
            continue
        plan.unplaced.append(payload)

    if plan.unplaced:
        confident = [t for text in confident_texts for t in _comparison_tokens(text)]
        linked_ids = {eid for _, eid in plan.linked}
        for ref in refs:
            if ref.id in doc_ids and ref.id not in linked_ids and ref.id not in plan.held_back and not _grounded(ref, confident):
                for payload in plan.unplaced:
                    hold(ref.id, OcrUncertaintyReason.UNGROUNDED, payload)
    return plan


def merge_ocr_uncertainty(existing: Optional[Dict[str, Any]], held: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """The `ocr_uncertainty` record stored on an entity's meta. Merges with an earlier
    record (a second upload can add reasons; it never clears them)."""
    previous = existing if isinstance(existing, dict) and existing.get("status") == "UNRESOLVED" else {}
    reasons = list(dict.fromkeys([*(previous.get("reasons") or []), *(h["reason"] for h in held)]))
    readings = list(dict.fromkeys([*(previous.get("readings") or []), *(h["reading"] for h in held if h.get("reading"))]))[:5]
    confidences = [c for c in [previous.get("min_ocr_confidence"), *(h.get("ocr_confidence") for h in held)] if c is not None]
    return {
        "status": "UNRESOLVED",
        "reasons": reasons,
        "readings": readings,
        "min_ocr_confidence": min(confidences) if confidences else None,
        "explanation": " ".join(OCR_UNCERTAINTY_EXPLANATIONS[r] for r in reasons if r in OCR_UNCERTAINTY_EXPLANATIONS),
        "next_step": OCR_UNCERTAINTY_NEXT_STEP,
        "provenance": "AI_DERIVED",
    }


_LEADING_FORM_MARKERS = re.compile(
    r"^(?:(?:rx|tab|tabs|tablet|cap|caps|capsule|inj|syp|syrup)\b\.?\s*)+", re.IGNORECASE
)


def _same_tokens(a: Sequence[str], b: Sequence[str]) -> bool:
    return len(a) == len(b) and _tokens_within(a, b) and _tokens_within(b, a)


def _strip_line_fragments(value: str) -> str:
    """A transcribed prescription line without its markers, dose pattern and duration,
    keeping the reader's own spelling: "Tab Augmentin 625mg 1-0-1 x 5 days" ->
    "Augmentin 625mg"."""
    kept = [raw for raw in (value or "").split() if _comparison_tokens(raw) or not normalize_reading(raw)]
    return " ".join(t for t in kept if normalize_reading(t)).strip(" .,-")


def names_a_drug(value: str) -> bool:
    """True when a medicine entry still carries something that can be a drug name — not
    only markers, strengths, units or frequencies ("Tab. 40", "Cap.", "Rx 1-0-1")."""
    return any(
        re.search(r"[^\W\d_]{2,}", t) and t not in _NON_NAME_TOKENS and not _UNIT_SUFFIX.match(t)
        for t in _comparison_tokens(value)
    )


def substitute_reading(entity_name: str, candidate: str, reading: str) -> Optional[str]:
    """Applies a human reading to an entity name by replacing only the uncertain part.

    Returns None when the substitution cannot be done safely, so the caller leaves the
    entity untouched instead of overwriting a whole medicine name with a fragment.
    A leading dosage-form marker the extraction dropped ("Tab. Pantop" read, entity
    "Pantop 40") is stripped from both the reading and the human value before matching.
    A reading that is only a marker is refused, and so is any result that no longer
    names a drug ("Pan 40" + reading "Tab." for "Pan" would give "Tab. 40").
    """
    if not entity_name or not candidate or not reading:
        return None
    bare_reading = _LEADING_FORM_MARKERS.sub("", reading.strip()).strip(" .,-")
    if not re.search(r"\w", bare_reading):
        return None
    result: Optional[str] = None
    if normalize_reading(candidate) == normalize_reading(entity_name):
        result = reading.strip()
    elif _same_tokens(_comparison_tokens(candidate), _comparison_tokens(entity_name)):
        # The uncertain reading was the entry's whole line: its name-bearing tokens are
        # exactly the entry's name, the rest is markers, dose pattern or duration
        # ("Tab Augmntn 625mg 1-0-1 x 5 days" for entry "Augmntn 625mg"). The readers'
        # transcription of that line, minus those same fragments, is the entry.
        result = _strip_line_fragments(reading) or None
    else:
        attempts = [(candidate.strip(), reading.strip())]
        bare_candidate = _LEADING_FORM_MARKERS.sub("", candidate.strip())
        if bare_candidate and bare_candidate != candidate.strip():
            attempts.append((bare_candidate, bare_reading))
        for cand, value in attempts:
            pattern = re.compile(rf"(?<!\w){re.escape(cand)}(?!\w)", re.IGNORECASE)
            if len(pattern.findall(entity_name)) == 1:
                result = pattern.sub(lambda _m, v=value: v, entity_name, count=1)
                break
    if result is None or not names_a_drug(result):
        return None
    return result


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
