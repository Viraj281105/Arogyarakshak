"""Opt-in shadow runs: a candidate model/prompt next to production (WS2, ADR-024).

OFF by default (``LLM_SHADOW_ENABLED``). After a successful production call the runner may
send the same request to the candidate model and record **numbers only** — runs, skips,
errors, exact matches and an agreement score — per (kind, candidate model, candidate prompt
version). No prompt or response text is stored, logged or emitted.

Guards:
- only inputs unchanged by ``redact_pii`` are shadowed (the "same redacted input" rule:
  for such inputs the redacted text *is* the input); others are counted as ``skipped_pii``;
- a sampled fraction only (``sample_rate``) and at most ``max_runs`` per process (cost bound);
- candidate calls never use the cache, the fallback model or the production budget;
- they run on one background worker thread so production latency is unaffected (tests
  inject an inline executor).
"""

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any, Callable, Dict, Optional, Tuple

from kadi.llm.cache import is_pii_free
from kadi.llm.prompts import PromptVersion

logger = logging.getLogger("arogyarakshak.kadi.llm")

_COUNTERS = ("runs", "errors", "exact_matches", "skipped_pii", "skipped_sampled", "skipped_cap",
             "candidate_invalid_json")


def agreement(production: str, candidate: str, json_mode: bool) -> Tuple[bool, float, Optional[bool]]:
    """(exact match, agreement score in [0, 1], candidate-JSON-valid or None for prose).

    JSON: share of top-level keys (union) whose values are equal; prose: token Jaccard."""
    if json_mode:
        try:
            a = json.loads(production)
        except ValueError:
            a = None
        try:
            b = json.loads(candidate)
            valid = True
        except ValueError:
            b, valid = None, False
        if a is None or b is None:
            return False, 0.0, valid
        if isinstance(a, dict) and isinstance(b, dict):
            keys = set(a) | set(b)
            if not keys:
                return True, 1.0, valid
            same = sum(1 for k in keys if k in a and k in b and a[k] == b[k])
            return a == b, same / len(keys), valid
        return a == b, 1.0 if a == b else 0.0, valid
    ta, tb = set(production.lower().split()), set(candidate.lower().split())
    union = ta | tb
    score = 1.0 if not union else len(ta & tb) / len(union)
    return production.strip() == candidate.strip(), score, None


class ShadowRunner:
    def __init__(self, runtime, model: str, sample_rate: float = 0.1, max_runs: int = 50,
                 executor: Optional[Callable[[Callable[[], None]], Any]] = None):
        self.runtime = runtime
        self.model = model
        self.sample_rate = max(0.0, min(1.0, float(sample_rate)))
        self.max_runs = max(0, int(max_runs))
        self._executor = executor
        self._pool: Optional[ThreadPoolExecutor] = None
        self._lock = threading.Lock()
        self._started = 0
        self._candidate_prompts: Dict[str, Tuple[PromptVersion, str]] = {}
        self._stats: Dict[str, Dict[str, float]] = {}

    def set_candidate_prompt(self, kind: str, version: PromptVersion, system: str) -> None:
        """Registers (in code, never from env/user input) a candidate system prompt for a kind."""
        with self._lock:
            self._candidate_prompts[kind] = (version, system)

    def _bucket(self, kind: str) -> Tuple[str, Optional[Tuple[PromptVersion, str]]]:
        candidate = self._candidate_prompts.get(kind)
        label = candidate[0].label if candidate else "same-prompt"
        return f"{kind}|{self.model}|{label}", candidate

    def _count(self, bucket: str, name: str, value: float = 1) -> None:
        stats = self._stats.setdefault(bucket, {**{c: 0 for c in _COUNTERS}, "agreement_sum": 0.0})
        stats[name] += value

    def submit(self, api_key: str, request, production_response) -> None:
        with self._lock:
            bucket, candidate = self._bucket(request.kind)
            if self._started >= self.max_runs:
                self._count(bucket, "skipped_cap")
                return
            if not is_pii_free(request.system, request.prompt):
                self._count(bucket, "skipped_pii")
                return
            if self.runtime.random() >= self.sample_rate:
                self._count(bucket, "skipped_sampled")
                return
            self._started += 1

        def job() -> None:
            self._run(api_key, request, production_response.text, bucket, candidate)

        if self._executor is not None:
            self._executor(job)
            return
        with self._lock:
            if self._pool is None:
                self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="llm-shadow")
            pool = self._pool
        pool.submit(job)

    def _run(self, api_key, request, production_text: str, bucket: str, candidate) -> None:
        from kadi.llm.client import ResilientLlmClient  # local: client imports this module lazily

        system = candidate[1] if candidate else request.system
        version = candidate[0] if candidate else request.prompt_version
        kind = (request.kind + ".shadow")[:64]
        shadow_request = replace(request, system=system, prompt_version=version, kind=kind, budget=None)
        try:
            resp = ResilientLlmClient(api_key=api_key, model=self.model, runtime=self.runtime).complete_shadow(shadow_request)
        except Exception as exc:  # noqa: BLE001
            logger.info("Shadow LLM run failed (%s).", type(exc).__name__)
            with self._lock:
                self._count(bucket, "runs")
                self._count(bucket, "errors")
            return
        exact, score, valid = agreement(production_text, resp.text, request.json_mode)
        with self._lock:
            self._count(bucket, "runs")
            self._count(bucket, "exact_matches", int(exact))
            self._count(bucket, "agreement_sum", score)
            if valid is False:
                self._count(bucket, "candidate_invalid_json")

    def snapshot(self) -> Dict[str, Dict[str, float]]:
        """Per bucket counters plus ``mean_agreement`` over successful runs. Numbers only."""
        with self._lock:
            out = {}
            for bucket, s in self._stats.items():
                ok = s["runs"] - s["errors"]
                out[bucket] = {**s, "mean_agreement": (s["agreement_sum"] / ok) if ok else None}
            return out

    def shutdown(self) -> None:
        with self._lock:
            pool, self._pool = self._pool, None
        if pool is not None:
            pool.shutdown(wait=True)
