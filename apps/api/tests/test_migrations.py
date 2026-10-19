"""Alembic migrations stay equal to the models and upgrade real databases (ADR-020).

Runs on a throwaway SQLite file. Set MIGRATION_TEST_DATABASE_URL to an EMPTY PostgreSQL
database to run the same checks there (CI does); the test downgrades it back to empty.
"""

import os
from datetime import datetime

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, pool, text

import app.models  # noqa: F401 — registers every table
from app.database import Base
from app.schema import (
    BASELINE_REVISION,
    alembic_config,
    current_revision,
    head_revision,
    sync_database_url,
    upgrade_to_head,
)


def _sqlite_url(tmp_path) -> str:
    return "sqlite:///" + (tmp_path / "migrations.db").as_posix()


def _urls(tmp_path):
    urls = [_sqlite_url(tmp_path)]
    if os.environ.get("MIGRATION_TEST_DATABASE_URL"):
        urls.append(os.environ["MIGRATION_TEST_DATABASE_URL"])
    return urls


def _diff_against_models(url: str):
    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    try:
        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn, opts={"compare_type": True})
            return compare_metadata(ctx, Base.metadata)
    finally:
        engine.dispose()


def _downgrade_to_base(url: str) -> None:
    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    try:
        with engine.begin() as conn:
            cfg = alembic_config()
            cfg.attributes["connection"] = conn
            command.downgrade(cfg, "base")
    finally:
        engine.dispose()


def test_single_linear_history():
    script = ScriptDirectory.from_config(alembic_config())
    assert len(script.get_heads()) == 1, "migration history has branched; add a merge revision"
    revisions = list(script.walk_revisions())
    assert revisions[-1].revision == BASELINE_REVISION


@pytest.mark.parametrize("which", ["sqlite", "postgres"])
def test_upgrade_to_head_matches_models_exactly(tmp_path, which):
    urls = _urls(tmp_path)
    if which == "postgres":
        if len(urls) < 2:
            pytest.skip("MIGRATION_TEST_DATABASE_URL not set")
        url = urls[1]
    else:
        url = urls[0]
    try:
        assert upgrade_to_head(url) == head_revision()
        diff = _diff_against_models(url)
        assert diff == [], (
            "app/models/ and the migrations disagree. Generate a revision: "
            f"cd apps/api && alembic revision --autogenerate -m '...'.\n{diff}"
        )
    finally:
        _downgrade_to_base(url)

    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    with engine.connect() as conn:
        left = set(inspect(conn).get_table_names()) - {"alembic_version"}
    engine.dispose()
    assert left == set(), f"downgrade to base left tables behind: {sorted(left)}"


def test_create_all_database_is_stamped_and_upgraded_without_data_loss(tmp_path):
    """A database made by the pre-Alembic start-up has every table except the ones added
    by later revisions, and no alembic_version. It must be adopted, not recreated."""
    url = _sqlite_url(tmp_path)
    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    legacy_tables = [t for name, t in Base.metadata.tables.items() if name != "kadi_document_jobs"]
    Base.metadata.create_all(engine, tables=legacy_tables)
    with engine.begin() as conn:
        conn.execute(
            text("INSERT INTO kadi_cases (id, status, consent_opt_in, total_charged, created_at) "
                 "VALUES ('CASE-legacy', 'active', 1, 10.0, :now)"),
            {"now": datetime.utcnow()},
        )
    engine.dispose()

    assert upgrade_to_head(url) == head_revision()
    assert current_revision(url) == head_revision()

    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM kadi_cases WHERE id = 'CASE-legacy'")).scalar() == 1
        assert "kadi_document_jobs" in inspect(conn).get_table_names()
    engine.dispose()
    assert _diff_against_models(url) == []


def test_upgrade_is_idempotent(tmp_path):
    url = _sqlite_url(tmp_path)
    first = upgrade_to_head(url)
    assert upgrade_to_head(url) == first


def test_document_job_state_is_constrained_in_the_database(tmp_path):
    """The CHECK constraint is a real invariant, not just an ORM convention."""
    url = _sqlite_url(tmp_path)
    upgrade_to_head(url)
    engine = create_engine(sync_database_url(url), poolclass=pool.NullPool)
    now = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO kadi_cases (id, status, consent_opt_in, total_charged, created_at) "
                          "VALUES ('CASE-x', 'active', 0, 0, :now)"), {"now": now})
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO kadi_document_jobs (id, case_id, sha256, state, pipeline_version, created_at, updated_at) "
                     "VALUES ('JOB-1', 'CASE-x', :d, 'done-ish', 'v', :now, :now)"),
                {"d": "0" * 64, "now": now},
            )
    engine.dispose()


def test_sync_url_conversion():
    assert sync_database_url("postgresql+asyncpg://u:p@h:5432/d") == "postgresql+psycopg2://u:p@h:5432/d"
    assert sync_database_url("postgresql://u:p@h/d") == "postgresql+psycopg2://u:p@h/d"
    assert sync_database_url("sqlite+aiosqlite:///x.db") == "sqlite:///x.db"
