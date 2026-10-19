"""Database schema management (ADR-020).

Alembic migrations in ``apps/api/migrations`` are the source of truth for the schema.
``SCHEMA_MANAGEMENT`` (app.config) decides what the API does at start-up:

- ``migrate`` (default): upgrade the database to the latest revision. A database created
  by the old ``create_all`` start-up (tables present, no ``alembic_version``) is stamped
  at the baseline revision first, then upgraded.
- ``none``: touch nothing; an operator runs ``alembic upgrade head`` as a release step
  (recommended for production). Readiness reports a database behind the code.
- ``create_all``: the legacy ``Base.metadata.create_all``. Never adds a column to an
  existing table; kept for throwaway local databases only and refused in production.
"""

import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, pool
from sqlalchemy.engine import make_url

logger = logging.getLogger("arogyarakshak.api.schema")

API_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = API_DIR / "alembic.ini"
MIGRATIONS_DIR = API_DIR / "migrations"

# The schema exactly as the pre-Alembic create_all start-up produced it.
BASELINE_REVISION = "0001_baseline"


def sync_database_url(url: str) -> str:
    """The same database through a synchronous driver (migrations run synchronously)."""
    parsed = make_url(url)
    backend = parsed.get_backend_name()
    if backend == "postgresql":
        parsed = parsed.set(drivername="postgresql+psycopg2")
    elif backend == "sqlite":
        parsed = parsed.set(drivername="sqlite")
    return parsed.render_as_string(hide_password=False)


def alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(MIGRATIONS_DIR))
    cfg.attributes["skip_logging_config"] = True
    return cfg


def head_revision() -> str:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    assert head, "no Alembic revisions found"
    return head


def upgrade_to_head(database_url: str) -> str:
    """Brings the database to the latest revision and returns it. Synchronous: call it
    through a worker thread from async code."""
    engine = create_engine(sync_database_url(database_url), poolclass=pool.NullPool)
    try:
        with engine.begin() as conn:
            tables = set(inspect(conn).get_table_names())
            cfg = alembic_config()
            cfg.attributes["connection"] = conn
            if "alembic_version" not in tables and "kadi_cases" in tables:
                logger.warning(
                    "Database has ArogyaRakshak tables but no migration history (created by the "
                    "old create_all start-up). Stamping it at %s, then upgrading. If it predates "
                    "that schema, columns added since were never created — see "
                    "docs/operations/database-migrations.md.",
                    BASELINE_REVISION,
                )
                command.stamp(cfg, BASELINE_REVISION)
            command.upgrade(cfg, "head")
            return MigrationContext.configure(conn).get_current_revision() or ""
    finally:
        engine.dispose()


def current_revision(database_url: str) -> Optional[str]:
    engine = create_engine(sync_database_url(database_url), poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()
