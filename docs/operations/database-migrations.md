# Database migrations (Alembic)

Decision: ADR-020. Code: `apps/api/alembic.ini`, `apps/api/migrations/`, `apps/api/app/schema.py`.

## Everyday commands (from `apps/api`, venv active)

```bash
alembic upgrade head            # apply all pending revisions (uses DATABASE_URL via app.config)
alembic current                 # revision the database is at
alembic history                 # all revisions
alembic check                   # fails if app/models/ has changes with no revision
alembic -x url=sqlite:///scratch.db upgrade head   # one-off target
```

## Changing the schema

1. Edit `app/models/`.
2. `alembic revision --autogenerate -m "short description"` and **read the generated file**:
   autogenerate misses renames (it emits drop + add — data loss), server defaults and some
   constraint changes.
3. For anything that is not purely additive, write a backward-compatible sequence: add the new
   column nullable → backfill → switch code → make it required / drop the old one in a later
   release.
4. `python -m pytest apps/api/tests/test_migrations.py` — fails if the models and migrations
   disagree (SQLite locally; CI also checks PostgreSQL 16).
5. Commit the model change and the revision together.

## Start-up behaviour (`SCHEMA_MANAGEMENT`)

| Value | What the API does | Use for |
|---|---|---|
| `migrate` (default) | Upgrades to head. A database created by the old `create_all` start-up (tables, no `alembic_version`) is stamped at `0001_baseline`, then upgraded. Logs a warning when it does that. | local, docker compose, the single-replica demo |
| `none` | Changes nothing. `/health/ready` is 503 until the database is at head. | production / Kubernetes (run the migration Job first) |
| `create_all` | Legacy `create_all`, never alters existing tables. Refused with `APP_ENV=production`. | throwaway local databases |

## Existing local databases

A docker volume created before Alembic is adopted automatically by `migrate`. If its tables
predate columns that existed before `0001_baseline`, those columns were already missing under
`create_all`; the safe fix is `docker compose down -v` **only if the data is disposable** (demo
data is — reload a scenario), otherwise add the missing columns in a new revision.

## Rollback

Every revision has a `downgrade()`, but a downgrade that drops a table drops its data. Treat
downgrade as a schema tool, not a recovery tool: to recover data, restore a backup
(`docs/operations/runbook.md#backup-and-restore`). Roll application code back to a version
whose models match the database revision.
