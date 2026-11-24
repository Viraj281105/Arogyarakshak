"""Compatibility alias for :mod:`kadi.privacy.redaction` (moved by ADR-027).

The implementation moved into the dependency-free ``kadi.privacy`` package so ``kadi.llm``
can use it without importing the ``kadi`` root modules back (which formed a package-level
cycle). This path keeps ``from kadi.redaction import redact_pii`` working unchanged for
``apps/api``, ``kadi.clinical_review`` and the documentation. New code inside ``kadi`` that
sits below the root modules (for example ``kadi.llm``) must import from ``kadi.privacy``.
"""

from kadi.privacy.redaction import REDACTION_MARK, contains_direct_identifier, redact_pii

__all__ = ["REDACTION_MARK", "contains_direct_identifier", "redact_pii"]
