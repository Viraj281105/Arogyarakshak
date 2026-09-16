"""
Kadi entity resolution — signal combination and merge / ask-user / new-entity branching (#31).

Implements Technical Documentation §4.3: a new entity mention is scored against the
entities already in the same case and of the same type (blocking), then

    high confidence   -> MERGE  (fold the mention into the existing entity)
    medium confidence -> ASK    (keep both, ask the user whether they are the same)
    low confidence    -> NEW    (create a new entity)

Signals (each in [0, 1], or UNAVAILABLE / NOT_APPLICABLE):

- lexical  — ``similarity.string_similarity``; for cross-script pairs it runs on the
             phonetically normalized romanizations (rule-based, not IndicXlit)
- phonetic — ``phonetic.phonetic_similarity`` over core Indic phonetic keys
- semantic — ``semantic.semantic_similarities`` (IndicSBERT; optional, off by default)

Combination is a weighted noisy-OR, ``1 - Π(1 - w_i · s_i)`` over AVAILABLE signals: one
strong signal is enough, several moderate signals accumulate, and an unavailable signal
neither helps nor hurts. The weights and default thresholds below are **uncalibrated
defaults chosen by reasoning, not fitted to data**. Thresholds can be recalibrated from
user feedback (``calibration.py``).

Deterministic safety rules override the score:

1. ``billing_item`` / ``document_text`` (and any other type outside
   RESOLVABLE_ENTITY_TYPES) are never resolved — two identical bill lines are evidence of
   double billing, not a duplicate to hide.
2. A conflicting quantity (650 mg vs 500 mg), dosage form (tablet vs injection), variant
   letter (Hepatitis A vs B), laterality (left vs right) or opposite clinical prefix
   (hyper-/hypo-thyroidism) makes the pair NEW: these are distinct entities, and asking
   the user about them would only add noise.
3. MERGE needs lexical or phonetic support (>= STRUCTURAL_SUPPORT_FLOOR), and the
   lexical + phonetic confidence on its own must reach the merge threshold. Embedding
   similarity is topical, not identity — the first real IndicSBERT evaluation merged the
   look-alike drugs Prednisone / Prednisolone — so semantic similarity can move a pair to
   ASK but never into MERGE.
4. When more than one existing entity clears the merge threshold, the choice is ambiguous
   and goes to ASK.
"""

from typing import Dict, FrozenSet, Iterable, List, Literal, Optional, Sequence, Tuple

from pydantic import BaseModel, Field, model_validator

from kadi.resolution.phonetic import normalized_stopwords, phonetic_normalize, phonetic_similarity
from kadi.resolution.semantic import (
    DISABLED_REASON,
    SemanticEncoder,
    SemanticSimilarity,
    semantic_similarities,
)
from kadi.resolution.similarity import (
    FACILITY_STOPWORDS,
    GENERIC_STOPWORDS,
    dosage_form_conflict,
    laterality_conflict,
    numeric_conflict,
    opposing_prefix_conflict,
    string_similarity,
    variant_conflict,
)
from kadi.resolution.transliteration import detect_script, romanize_devanagari
from kadi.resolution.types import SignalName, SignalScore

RESOLVABLE_ENTITY_TYPES: FrozenSet[str] = frozenset({"hospital", "diagnosis", "procedure", "medicine"})

DEFAULT_MERGE_THRESHOLD = 0.90
DEFAULT_ASK_THRESHOLD = 0.70

SIGNAL_WEIGHTS: Dict[str, float] = {"lexical": 0.9, "phonetic": 0.7, "semantic": 0.5}
ALL_SIGNALS: FrozenSet[str] = frozenset(SIGNAL_WEIGHTS)

STRUCTURAL_SUPPORT_FLOOR = 0.75
SEMANTIC_ONLY_ASK_FLOOR = 0.80

FACILITY_DEVANAGARI_STOPWORDS: FrozenSet[str] = frozenset(
    {"हॉस्पिटल", "हास्पिटल", "अस्पताल", "रुग्णालय", "क्लिनिक", "दवाखाना", "इस्पितळ"}
)

Action = Literal["MERGE", "ASK", "NEW"]


def stopwords_for(entity_type: str) -> FrozenSet[str]:
    if entity_type == "hospital":
        return GENERIC_STOPWORDS | FACILITY_STOPWORDS | FACILITY_DEVANAGARI_STOPWORDS
    return GENERIC_STOPWORDS


class ResolutionThresholds(BaseModel):
    merge: float = Field(DEFAULT_MERGE_THRESHOLD, ge=0.0, le=1.0)
    ask: float = Field(DEFAULT_ASK_THRESHOLD, ge=0.0, le=1.0)
    source: Literal["default_uncalibrated", "feedback_calibrated"] = "default_uncalibrated"
    calibration_id: Optional[str] = None

    @model_validator(mode="after")
    def _ask_not_above_merge(self) -> "ResolutionThresholds":
        if self.ask > self.merge:
            raise ValueError("ask threshold must not exceed merge threshold")
        return self


class EntityMention(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    entity_type: str


class CandidateEntity(BaseModel):
    id: str
    name: str = Field(..., min_length=1, max_length=512)
    entity_type: str
    # Other surface forms already confirmed as this entity (earlier merged mentions), e.g.
    # the Devanagari spelling seen on a prescription.
    aliases: List[str] = Field(default_factory=list)


class PairScore(BaseModel):
    confidence: float
    signals: List[SignalScore]
    conflicts: List[str]
    compared_text: str
    cross_script: bool


class ResolutionDecision(BaseModel):
    action: Action
    confidence: float
    matched_candidate_id: Optional[str] = None
    matched_text: Optional[str] = None
    signals: List[SignalScore] = Field(default_factory=list)
    conflicts: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    thresholds: ResolutionThresholds
    candidates_considered: int = 0


def combine_signals(signals: Iterable[SignalScore]) -> float:
    """Weighted noisy-OR over AVAILABLE signals."""
    remaining = 1.0
    for signal in signals:
        if signal.status == "AVAILABLE" and signal.score is not None:
            remaining *= 1.0 - SIGNAL_WEIGHTS[signal.signal] * signal.score
    return round(1.0 - remaining, 4)


def _conflicts(a: str, b: str) -> List[str]:
    ra, rb = romanize_devanagari(a), romanize_devanagari(b)
    found = []
    if numeric_conflict(ra, rb):
        found.append("quantity_conflict")
    if dosage_form_conflict(ra, rb):
        found.append("dosage_form_conflict")
    if variant_conflict(ra, rb):
        found.append("variant_conflict")
    if laterality_conflict(ra, rb):
        found.append("laterality_conflict")
    if opposing_prefix_conflict(ra, rb):
        found.append("opposing_prefix_conflict")
    return found


def score_pair(
    a: str,
    b: str,
    entity_type: str,
    *,
    semantic: Optional[SemanticSimilarity] = None,
    enabled_signals: FrozenSet[str] = ALL_SIGNALS,
) -> PairScore:
    stops = stopwords_for(entity_type)
    cross_script = detect_script(a) != detect_script(b)
    signals: List[SignalScore] = []

    if "lexical" in enabled_signals:
        if cross_script:
            sim = string_similarity(
                phonetic_normalize(a), phonetic_normalize(b), normalized_stopwords(stops), fuzzy_stopwords=True
            )
            detail = "cross-script: compared rule-based romanizations"
        else:
            sim = string_similarity(a, b, stops)
            detail = "same script"
        if sim.normalized_a and sim.normalized_b:
            signals.append(SignalScore(signal="lexical", status="AVAILABLE", score=sim.score, detail=detail))
        else:
            signals.append(SignalScore(signal="lexical", status="NOT_APPLICABLE", detail="empty after normalization"))

    if "phonetic" in enabled_signals:
        ph = phonetic_similarity(a, b, stops, fuzzy_stopwords=cross_script)
        if ph.score is None:
            signals.append(SignalScore(signal="phonetic", status="NOT_APPLICABLE", detail="no identifying token"))
        else:
            signals.append(
                SignalScore(signal="phonetic", status="AVAILABLE", score=ph.score, detail=f"{ph.key_a} | {ph.key_b}")
            )

    if "semantic" in enabled_signals:
        if semantic is None:
            signals.append(SignalScore(signal="semantic", status="UNAVAILABLE", detail=DISABLED_REASON))
        else:
            signals.append(
                SignalScore(signal="semantic", status=semantic.status, score=semantic.score, detail=semantic.reason)
            )

    return PairScore(
        confidence=combine_signals(signals),
        signals=signals,
        conflicts=_conflicts(a, b),
        compared_text=b,
        cross_script=cross_script,
    )


def _signal(score: PairScore, name: SignalName) -> Optional[float]:
    for s in score.signals:
        if s.signal == name and s.status == "AVAILABLE":
            return s.score
    return None


def resolve_mention(
    mention: EntityMention,
    candidates: Sequence[CandidateEntity],
    thresholds: Optional[ResolutionThresholds] = None,
    encoder: Optional[SemanticEncoder] = None,
    enabled_signals: FrozenSet[str] = ALL_SIGNALS,
) -> ResolutionDecision:
    thresholds = thresholds or ResolutionThresholds()

    if mention.entity_type not in RESOLVABLE_ENTITY_TYPES:
        return ResolutionDecision(
            action="NEW",
            confidence=0.0,
            thresholds=thresholds,
            reasons=[f"entity type '{mention.entity_type}' is never auto-resolved"],
        )

    pool = [c for c in candidates if c.entity_type == mention.entity_type]
    if not pool:
        return ResolutionDecision(
            action="NEW",
            confidence=0.0,
            thresholds=thresholds,
            reasons=["no existing entity of the same type in this case"],
        )

    comparisons: List[Tuple[CandidateEntity, str]] = []
    for cand in pool:
        for text in dict.fromkeys([cand.name, *cand.aliases]):
            if text and text.strip():
                comparisons.append((cand, text))

    if "semantic" in enabled_signals:
        semantic_scores: List[Optional[SemanticSimilarity]] = list(
            semantic_similarities(mention.name, [t for _, t in comparisons], encoder)
        )
    else:
        semantic_scores = [None] * len(comparisons)

    best: Dict[str, Tuple[CandidateEntity, PairScore]] = {}
    for (cand, text), sem in zip(comparisons, semantic_scores):
        pair = score_pair(mention.name, text, mention.entity_type, semantic=sem, enabled_signals=enabled_signals)
        # On equal confidence prefer a same-script comparison: a confirmed alias written the
        # same way is more direct evidence than a transliterated match.
        rank = (pair.confidence, not pair.cross_script)
        if cand.id not in best or rank > (best[cand.id][1].confidence, not best[cand.id][1].cross_script):
            best[cand.id] = (cand, pair)

    ranked = sorted(best.values(), key=lambda item: item[1].confidence, reverse=True)
    top_candidate, top = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else None

    structural = max(
        (v for v in (_signal(top, "lexical"), _signal(top, "phonetic")) if v is not None),
        default=0.0,
    )
    semantic_score = _signal(top, "semantic")
    non_semantic_confidence = combine_signals(s for s in top.signals if s.signal != "semantic")

    def decide(action: Action, *reasons: str) -> ResolutionDecision:
        matched = action != "NEW"
        return ResolutionDecision(
            action=action,
            confidence=top.confidence,
            matched_candidate_id=top_candidate.id if matched else None,
            matched_text=top.compared_text if matched else None,
            signals=top.signals,
            conflicts=top.conflicts,
            reasons=list(reasons),
            thresholds=thresholds,
            candidates_considered=len(ranked),
        )

    if top.conflicts:
        # A conflicting strength, form, variant, side or opposite prefix is deterministic
        # evidence of two different entities, however alike the names look.
        return decide("NEW", "distinct entity despite a similar name: " + ", ".join(top.conflicts))

    if top.confidence >= thresholds.merge:
        if structural < STRUCTURAL_SUPPORT_FLOOR:
            return decide("ASK", "merge requires lexical or phonetic support; semantic similarity alone is not identity")
        if non_semantic_confidence < thresholds.merge:
            return decide(
                "ASK", "only semantic similarity lifted this pair into the merge band; it can ask, never merge"
            )
        if runner_up is not None and runner_up.confidence >= thresholds.merge:
            return decide("ASK", "more than one existing entity matches above the merge threshold")
        return decide("MERGE", "confidence at or above the merge threshold")

    if (
        semantic_score is not None
        and semantic_score >= SEMANTIC_ONLY_ASK_FLOOR
        and structural < STRUCTURAL_SUPPORT_FLOOR
    ):
        return decide("ASK", "strong cross-lingual semantic similarity without lexical or phonetic support")

    if top.confidence >= thresholds.ask:
        return decide("ASK", "confidence between the ask and merge thresholds")

    return decide("NEW", f"best candidate confidence {top.confidence:.2f} is below the ask threshold")
