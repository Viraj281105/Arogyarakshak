"""Optional in-memory LLM response cache (ADR-024). OFF unless LLM_CACHE_ENABLED=true.

Zero-retention rules (ADR-003/010):
- memory only, bounded LRU, short TTL, never persisted, lost on restart;
- keys are SHA-256 digests (``put`` refuses anything else), never raw text;
- only requests whose text is unchanged by ``redact_pii`` are eligible. Keying on the
  *redacted* text of an input that contained identifiers would let two patients' bills that
  differ only in the name share an entry (one patient's extracted name served to another),
  so such inputs bypass the cache instead;
- ``purge()`` empties it; ``app.services.case_purge.purge_case`` calls it on case erasure.
  The cache holds no case id, so purging is all-or-nothing by design.

Residual risk (documented in ADR-024): a cached VALUE is model output and can contain
sensitive content that ``redact_pii`` (direct identifiers only) did not recognise.
"""

import hashlib
import json
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, List, Optional, Tuple

from kadi.privacy.redaction import redact_pii

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def cache_key(model: str, prompt_version: str, system: str, prompt: str,
              temperature: float, max_tokens: int, json_mode: bool) -> str:
    material = json.dumps(
        [model, prompt_version, redact_pii(system or ""), redact_pii(prompt or ""),
         float(temperature), int(max_tokens), bool(json_mode)],
        ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def is_pii_free(*texts: str) -> bool:
    """True when ``redact_pii`` would leave every text unchanged."""
    return all(redact_pii(t or "") == (t or "") for t in texts)


def is_cache_eligible(system: str, prompt: str, temperature: float) -> bool:
    return float(temperature) == 0.0 and is_pii_free(system, prompt)


class ResponseCache:
    def __init__(self, max_entries: int = 256, ttl_s: float = 300.0,
                 clock: Callable[[], float] = time.monotonic):
        self.max_entries = max(1, int(max_entries))
        self.ttl_s = float(ttl_s)
        self._clock = clock
        self._lock = threading.Lock()
        self._data: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if self._clock() >= expires_at:
                del self._data[key]
                return None
            self._data.move_to_end(key)
            return value

    def put(self, key: str, value: Any) -> None:
        if not _DIGEST_RE.match(key or ""):
            raise ValueError("cache keys must be SHA-256 hex digests")
        with self._lock:
            self._data[key] = (self._clock() + self.ttl_s, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_entries:
                self._data.popitem(last=False)

    def purge(self) -> None:
        with self._lock:
            self._data.clear()

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._data)

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
