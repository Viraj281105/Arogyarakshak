"""
Kadi entity resolution (Phase 3: #28 string similarity, #89 cross-script phonetics,
#30 optional IndicSBERT semantic signal, #31 merge/ask/new branching, #88 feedback
calibration).

DB-agnostic: pure functions and pydantic models. Persistence lives in apps/api.
"""

from kadi.resolution.calibration import (
    CalibrationResult,
    LabeledOutcome,
    calibrate_thresholds,
)
from kadi.resolution.phonetic import indic_phonetic_key, phonetic_normalize, phonetic_similarity, soundex
from kadi.resolution.resolver import (
    RESOLVABLE_ENTITY_TYPES,
    CandidateEntity,
    EntityMention,
    ResolutionDecision,
    ResolutionThresholds,
    combine_signals,
    resolve_mention,
    score_pair,
)
from kadi.resolution.semantic import (
    IndicSBERTEncoder,
    get_default_semantic_encoder,
    semantic_matching_enabled,
    semantic_similarities,
)
from kadi.resolution.similarity import string_similarity
from kadi.resolution.transliteration import detect_script, romanize_devanagari
from kadi.resolution.types import SignalScore

__all__ = [
    "CalibrationResult",
    "CandidateEntity",
    "EntityMention",
    "IndicSBERTEncoder",
    "LabeledOutcome",
    "RESOLVABLE_ENTITY_TYPES",
    "ResolutionDecision",
    "ResolutionThresholds",
    "SignalScore",
    "calibrate_thresholds",
    "combine_signals",
    "detect_script",
    "get_default_semantic_encoder",
    "indic_phonetic_key",
    "phonetic_normalize",
    "phonetic_similarity",
    "resolve_mention",
    "romanize_devanagari",
    "score_pair",
    "semantic_matching_enabled",
    "semantic_similarities",
    "soundex",
    "string_similarity",
]
