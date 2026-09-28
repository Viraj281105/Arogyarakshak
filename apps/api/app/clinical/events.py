"""
Statement-change notifications (ADR-011).

Packages that embed clinician statements (e.g. BillNyay's signed appeal PDF) register a
listener here and are told whenever the set of current statements for a case/module
changes — finalized, superseded, withdrawn, or the review cancelled. This keeps the
shared review layer from importing any module while guaranteeing no stored document
keeps presenting a statement that is no longer current.
"""

from typing import Awaitable, Callable, List

from sqlalchemy.ext.asyncio import AsyncSession

StatementListener = Callable[[AsyncSession, str, str], Awaitable[None]]
_listeners: List[StatementListener] = []


def on_statements_changed(fn: StatementListener) -> StatementListener:
    if fn not in _listeners:
        _listeners.append(fn)
    return fn


async def notify_statements_changed(db: AsyncSession, case_id: str, source_module: str) -> None:
    # Listeners query current statements; pending status changes must be visible to them.
    await db.flush()
    for listener in _listeners:
        await listener(db, case_id, source_module)
