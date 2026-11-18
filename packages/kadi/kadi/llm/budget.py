"""Per-case token budget (ADR-024).

One ``TokenBudget`` per pipeline run for one case (BillNyay creates it in ``llm_client()``),
shared by every agent call in that run. It holds counts only — no case id, no text.
"""

import math
import threading
from typing import Optional

from kadi.llm.errors import BudgetExceeded


def estimate_tokens(system: str, prompt: str, max_tokens: int) -> int:
    """Conservative reservation: ~4 characters per token for the input (rounded up) plus
    the full completion allowance."""
    chars = len(system or "") + len(prompt or "")
    return math.ceil(chars / 4) + max(0, int(max_tokens))


class TokenBudget:
    def __init__(self, limit: int):
        self.limit = max(0, int(limit))  # 0 = unlimited
        self._used = 0
        self._lock = threading.Lock()

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> Optional[int]:
        if not self.limit:
            return None
        with self._lock:
            return max(0, self.limit - self._used)

    def ensure_fits(self, estimate: int) -> None:
        """Raises BudgetExceeded when ``estimate`` more tokens would exceed the limit."""
        if not self.limit:
            return
        with self._lock:
            if self._used + estimate > self.limit:
                raise BudgetExceeded("token budget exhausted for this case")

    def charge(self, tokens: int) -> None:
        with self._lock:
            self._used += max(0, int(tokens))
