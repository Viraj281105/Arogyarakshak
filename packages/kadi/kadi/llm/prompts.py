"""Prompt/model versioning (ADR-024).

A ``PromptVersion`` names a prompt and its version. It is part of the cache key and of
shadow-run statistics, so a prompt edit never serves stale cached output and shadow
agreement is reported per prompt version. Names are code-defined labels, never user text.
"""

import hashlib
import re
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

_NAME_RE = re.compile(r"^[a-z0-9_.]{1,64}$")
_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,40}$")


@dataclass(frozen=True)
class PromptVersion:
    name: str
    version: str

    def __post_init__(self):
        if not _NAME_RE.match(self.name or ""):
            raise ValueError("prompt name must match ^[a-z0-9_.]{1,64}$")
        if not _VERSION_RE.match(self.version or ""):
            raise ValueError("prompt version must match ^[A-Za-z0-9_.-]{1,40}$")

    @property
    def label(self) -> str:
        return f"{self.name}@{self.version}"

    @classmethod
    def from_template(cls, name: str, template: str) -> "PromptVersion":
        """Version = first 12 hex chars of SHA-256(template): editing a constant prompt
        changes its version automatically."""
        return cls(name, hashlib.sha256(template.encode("utf-8")).hexdigest()[:12])


_lock = threading.Lock()
_registry: Dict[str, PromptVersion] = {}


def register_prompt_version(pv: PromptVersion) -> PromptVersion:
    """Registers ``pv`` (idempotent). A different version under the same name is an error:
    two live versions of one prompt in one process would make metrics ambiguous."""
    with _lock:
        existing = _registry.get(pv.name)
        if existing is not None and existing != pv:
            raise ValueError(f"prompt {pv.name!r} is already registered as {existing.version!r}")
        _registry[pv.name] = pv
    return pv


def get_prompt_version(name: str) -> Optional[PromptVersion]:
    with _lock:
        return _registry.get(name)


def registered_prompt_versions() -> List[PromptVersion]:
    with _lock:
        return sorted(_registry.values(), key=lambda p: p.name)
