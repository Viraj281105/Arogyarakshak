"""Alembic environment (ADR-020).

Runs migrations with a synchronous driver (psycopg2 for PostgreSQL, the stdlib sqlite3
for SQLite) even though the API itself uses asyncpg/aiosqlite: migrations are a one-off
operator step and a sync connection keeps this file simple.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database import Base
import app.models  # noqa: F401 — registers every table on Base.metadata
from app.schema import sync_database_url

config = context.config
if config.config_file_name is not None and not config.attributes.get("skip_logging_config"):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _url() -> str:
    explicit = context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option("sqlalchemy.url")
    if explicit:
        return sync_database_url(explicit)
    from app.config import settings

    return sync_database_url(settings.database_url)


def _configure_kwargs(url: str) -> dict:
    # SQLite cannot ALTER most things in place; batch mode rebuilds the table instead.
    return {"target_metadata": target_metadata, "render_as_batch": url.startswith("sqlite"), "compare_type": True}


def run_migrations_offline() -> None:
    url = _url()
    context.configure(url=url, literal_binds=True, dialect_opts={"paramstyle": "named"}, **_configure_kwargs(url))
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:  # supplied programmatically (app.schema)
        context.configure(connection=connection, **_configure_kwargs(str(connection.engine.url)))
        with context.begin_transaction():
            context.run_migrations()
        return

    url = _url()
    connectable = engine_from_config({"sqlalchemy.url": url}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as conn:
        context.configure(connection=conn, **_configure_kwargs(url))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
