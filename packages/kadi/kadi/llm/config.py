"""Settings for the resilient LLM client, read from the environment (ADR-024).

Kadi must not import ``apps/api`` (dependency direction apps -> packages), so this is a
small frozen dataclass of its own rather than a field on the API's pydantic Settings. The
API key and the primary model are NOT read here: call sites pass the API's own
``settings.groq_api_key`` / ``settings.groq_model`` (GROQ_MODEL, ADR-004) in.

Every default keeps the pre-WS2 behaviour except retries/breaker: no fallback model, no
cache, no shadow runs, no token budget.
"""

import logging
import os
from dataclasses import dataclass
from typing import Mapping, Optional

logger = logging.getLogger("arogyarakshak.kadi.llm")

# ADR-004: Groq deprecated these. They are refused as a fallback or shadow model even if
# someone sets them in the environment. (This file's basename is on the CI model-grounding
# scanner's skip list, which is what lets the names appear here as literals.)
DEPRECATED_GROQ_MODELS = frozenset({
    "llama3-70b",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
    "llama3-8b-8192",
})


def _str(env: Mapping[str, str], name: str) -> str:
    return (env.get(name) or "").strip()


def _bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = _str(env, name).lower()
    if not raw:
        return default
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    logger.warning("%s=%r is not a boolean; using %s.", name, raw, default)
    return default


def _num(env: Mapping[str, str], name: str, default, cast, lo=None, hi=None):
    raw = _str(env, name)
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        logger.warning("%s=%r is not a valid number; using %s.", name, raw, default)
        return default
    if lo is not None and value < lo:
        value = cast(lo)
    if hi is not None and value > hi:
        value = cast(hi)
    return value


def _model(env: Mapping[str, str], name: str) -> str:
    model = _str(env, name)
    if model in DEPRECATED_GROQ_MODELS:
        logger.warning("%s names a deprecated Groq model (ADR-004); ignoring it.", name)
        return ""
    return model


def _positive(env: Mapping[str, str], name: str, default: float, hi: float) -> float:
    """A strictly positive number; zero, negative or unparsable values are refused
    (warning + default) rather than clamped, so 'disable' can never be expressed by 0."""
    raw = _str(env, name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        value = -1.0
    if not value > 0:
        logger.warning("%s=%r must be a number > 0; using %s.", name, raw, default)
        return default
    return min(value, hi)


# Used when neither the call site nor LLM_TIMEOUT_SECONDS gives a per-attempt timeout.
DEFAULT_TIMEOUT_S = 12.0


@dataclass(frozen=True)
class LlmConfig:
    fallback_model: str = ""
    # Per-attempt timeout ceiling. None (LLM_TIMEOUT_SECONDS unset) = the call site's own
    # timeout applies; when set, the effective timeout is min(call site, this).
    timeout_s: Optional[float] = None
    # Overall wall-clock budget for one complete() across all attempts, backoff sleeps and
    # the fallback model. Always > 0.
    total_deadline_s: float = 20.0
    max_attempts: int = 3
    backoff_base_s: float = 0.5
    backoff_max_s: float = 8.0
    retry_after_max_s: float = 30.0
    breaker_failure_threshold: int = 5
    breaker_recovery_s: float = 30.0
    case_token_budget: int = 0  # 0 = unlimited
    cache_enabled: bool = False
    cache_max_entries: int = 256
    cache_ttl_s: float = 300.0
    shadow_enabled: bool = False
    shadow_model: str = ""
    shadow_sample_rate: float = 0.1
    shadow_max_runs: int = 50

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "LlmConfig":
        env = os.environ if env is None else env
        d = cls()
        return cls(
            fallback_model=_model(env, "GROQ_FALLBACK_MODEL"),
            timeout_s=_num(env, "LLM_TIMEOUT_SECONDS", d.timeout_s, float, lo=0.1, hi=120),
            total_deadline_s=_positive(env, "LLM_TOTAL_DEADLINE_SECONDS", d.total_deadline_s, hi=600),
            max_attempts=_num(env, "LLM_MAX_ATTEMPTS", d.max_attempts, int, lo=1, hi=10),
            backoff_base_s=_num(env, "LLM_BACKOFF_BASE_SECONDS", d.backoff_base_s, float, lo=0, hi=60),
            backoff_max_s=_num(env, "LLM_BACKOFF_MAX_SECONDS", d.backoff_max_s, float, lo=0, hi=120),
            retry_after_max_s=_num(env, "LLM_RETRY_AFTER_MAX_SECONDS", d.retry_after_max_s, float, lo=0, hi=600),
            breaker_failure_threshold=_num(env, "LLM_BREAKER_FAILURE_THRESHOLD", d.breaker_failure_threshold, int, lo=1),
            breaker_recovery_s=_num(env, "LLM_BREAKER_RECOVERY_SECONDS", d.breaker_recovery_s, float, lo=0),
            case_token_budget=_num(env, "LLM_CASE_TOKEN_BUDGET", d.case_token_budget, int, lo=0),
            cache_enabled=_bool(env, "LLM_CACHE_ENABLED", d.cache_enabled),
            cache_max_entries=_num(env, "LLM_CACHE_MAX_ENTRIES", d.cache_max_entries, int, lo=1, hi=10_000),
            cache_ttl_s=_num(env, "LLM_CACHE_TTL_SECONDS", d.cache_ttl_s, float, lo=1, hi=3600),
            shadow_enabled=_bool(env, "LLM_SHADOW_ENABLED", d.shadow_enabled),
            shadow_model=_model(env, "LLM_SHADOW_MODEL"),
            shadow_sample_rate=_num(env, "LLM_SHADOW_SAMPLE_RATE", d.shadow_sample_rate, float, lo=0, hi=1),
            shadow_max_runs=_num(env, "LLM_SHADOW_MAX_RUNS", d.shadow_max_runs, int, lo=0, hi=10_000),
        )

    def attempt_timeout(self, call_site_timeout_s: Optional[float]) -> float:
        """min(call site, LLM_TIMEOUT_SECONDS) over whichever are set; default 12 s."""
        candidates = [t for t in (call_site_timeout_s, self.timeout_s) if t is not None]
        return min(candidates) if candidates else DEFAULT_TIMEOUT_S

    def fallback_for(self, primary: str) -> Optional[str]:
        """The fallback model to try after ``primary`` failed, or None."""
        if not self.fallback_model or self.fallback_model == primary:
            return None
        return self.fallback_model
