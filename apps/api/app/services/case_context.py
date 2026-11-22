"""The one reader of a case's stored context (#112).

Every module, and Kadi's own consumers, read a case's stored entities through
``load_case_entities``, which runs the shared query and records exactly one
``ContextRequestEvent``. ``tests/test_architecture.py`` fails when ``KadiEntity`` is selected
anywhere else (bar a short, reasoned allow-list), so a read that forgets to be instrumented is
a red test, and ``module``/``context`` are ``Literal`` types so a typo is caught by the same
suite instead of mapping silently to ``other``.

The hook only observes: it issues no SQL of its own, never raises into the caller, and does
not change what is returned.
"""

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KadiCase, KadiEntity
from app.telemetry import context_metrics as cm


async def load_case_entities(
    db: AsyncSession,
    case_id: str,
    types: Optional[Sequence[str]] = None,
    *,
    module: cm.Module,
    context: cm.ContextKind,
) -> List[KadiEntity]:
    """The case's stored entities, optionally restricted to ``types`` (None = all)."""
    query = select(KadiEntity).join(KadiCase.entities).where(KadiCase.id == case_id)
    if types is not None:
        query = query.where(KadiEntity.type.in_(list(types)))
    entities = list((await db.execute(query)).scalars().all())
    cm.record_context_request(
        cm.ContextRequestEvent(module, context, "served" if entities else "empty", len(entities))
    )
    return entities
