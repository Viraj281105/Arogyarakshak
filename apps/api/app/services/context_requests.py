"""Instrumentation hook for module requests for case context (#112).

``note_context_request`` is called by the service functions that read a case's stored
context. It records one ``ContextRequestEvent`` and returns nothing: the caller's result is
identical whatever it does.

``CONTEXT_REUSE_ENABLED`` (environment, default true) is a *measurement* switch, not a
behaviour switch. When ``false`` every request is counted as ``fresh`` and the OCR and
extraction work a module would have to repeat without a shared context is added to the
``repeat`` work counter (one unit of each per document the case holds). The module is still
served from the stored context: nothing is re-run, so results never change and no document
is needed again (zero retention). It is read at call time so a test can flip it.
"""

import os

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCaseDocument
from app.telemetry import context_metrics as cm

_OFF = {"0", "false", "no", "off"}


def reuse_enabled() -> bool:
    return os.environ.get("CONTEXT_REUSE_ENABLED", "true").strip().lower() not in _OFF


async def note_context_request(
    db: AsyncSession, case_id: str, *, module: str, context: str, items: int
) -> None:
    """``items``: how many stored items answered the request (0 = nothing to reuse)."""
    try:
        if reuse_enabled():
            outcome = "reused" if items > 0 else "fresh"
        else:
            outcome = "fresh"
            documents = (
                await db.execute(select(func.count()).select_from(KadiCaseDocument).where(KadiCaseDocument.case_id == case_id))
            ).scalar_one()
            for kind in ("ocr", "extraction"):
                cm.record_context_work(kind, "repeat", int(documents))
        cm.record_context_request(cm.ContextRequestEvent(module, context, outcome, items))
    except Exception:  # never let instrumentation fail the module call
        import logging

        logging.getLogger("arogyarakshak.telemetry").debug("context request not noted", exc_info=True)
