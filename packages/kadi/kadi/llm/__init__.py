"""Kadi resilient LLM client (WS2, ADR-024).

The one place that performs Groq chat calls: timeouts, jittered retries, a per-model
circuit breaker, an optional fallback model (GROQ_FALLBACK_MODEL), a per-case token budget,
an opt-in in-memory response cache, an observer hook (no text) and opt-in shadow runs.
"""

from kadi.llm.budget import TokenBudget, estimate_tokens
from kadi.llm.client import (
    LlmRequest,
    LlmResponse,
    LlmRuntime,
    ResilientLlmClient,
    default_runtime,
    purge_default_cache,
    reset_default_runtime,
    set_default_runtime,
)
from kadi.llm.config import LlmConfig
from kadi.llm.errors import (
    BudgetExceeded,
    LlmCircuitOpen,
    LlmClientError,
    LlmConnectionError,
    LlmError,
    LlmNotConfigured,
    LlmRateLimited,
    LlmResponseError,
    LlmServerError,
    LlmTimeout,
)
from kadi.llm.observer import (
    CIRCUIT_STATES,
    OUTCOMES,
    LlmCallEvent,
    clear_llm_observers,
    register_llm_observer,
)
from kadi.llm.prompts import (
    PromptVersion,
    get_prompt_version,
    register_prompt_version,
    registered_prompt_versions,
)

__all__ = [
    "BudgetExceeded", "CIRCUIT_STATES", "LlmCallEvent", "LlmCircuitOpen", "LlmClientError",
    "LlmConfig", "LlmConnectionError", "LlmError", "LlmNotConfigured", "LlmRateLimited",
    "LlmRequest", "LlmResponse", "LlmResponseError", "LlmRuntime", "LlmServerError",
    "LlmTimeout", "OUTCOMES", "PromptVersion", "ResilientLlmClient", "TokenBudget",
    "clear_llm_observers", "default_runtime", "estimate_tokens", "get_prompt_version",
    "purge_default_cache", "register_llm_observer", "register_prompt_version",
    "registered_prompt_versions", "reset_default_runtime", "set_default_runtime",
]
