# Module boundaries and where code belongs

Enforced by `.importlinter` (run `PYTHONPATH=apps/api lint-imports` from the repo root; CI runs it)
and `apps/api/tests/test_architecture.py`. Background: ADR-018.

## Layers

```text
apps/web, apps/mobile          ── HTTP/JSON only (docs/api/openapi.json). Never import backend code.
        │
apps/api/app/main.py           ── entrypoint: middleware, exception handlers, health probes, lifespan
apps/api/app/api/v1/endpoints  ── HTTP layer: auth (case token / reviewer / institution), consent,
        │                         request validation, status codes. Thin. Never imported by anything
        │                         below it, and route modules never import each other.
apps/api/app/services          ── application use cases shared by >1 entry point (routes, auto-
        │                         triggers, Claim Pack, retention sweep, demo kit, evaluation).
apps/api/app/{models,database,config,schema,observability,clinical,...}
        │                      ── persistence, configuration, cross-cutting infrastructure
packages/<module>              ── domain rules: pure Python + Pydantic. No FastAPI, Starlette,
        │                         SQLAlchemy or `app` imports.
packages/kadi                  ── shared intelligence layer. Never imports a domain module.
```

Domain modules (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`) do not import
each other. Cross-module work happens through Kadi (shared models and case context) or in the
API layer (`app/services`, `app/auto_triggers`, `app/claim_pack`).

## Where does my change go?

| You are adding… | Put it in |
|---|---|
| A rule, calculation, reference-data lookup, prompt or agent | `packages/<module>/` (+ unit tests there) |
| OCR, extraction, redaction, entity resolution, explanations, case graph | `packages/kadi/` |
| A use case that loads rows, calls a package and shapes the result, needed by more than one caller | `apps/api/app/services/` |
| A new route | `apps/api/app/api/v1/endpoints/<module>.py`, calling a package or a service |
| A table or column | `apps/api/app/models/<owning module>.py` (export it from `app/models/__init__.py`) **and** an Alembic revision (`docs/operations/database-migrations.md`) |
| A setting | `apps/api/app/config.py` (`Settings`) + `docs/configuration/environment-variables.md` + `.env.example` |
| A new top-level `app` module | add it to the `no-route-imports-below-http` contract (the architecture test tells you) |

## Known exceptions

- `kadi.resolution.semantic` and `kadi.extraction` read `KADI_SEMANTIC_MATCHING` /
  `GROQ_*` from the environment directly (a package cannot depend on `app.config`). The API
  passes the Groq settings explicitly where it calls extraction.
- Route modules re-export names that moved to `app/services` (marked `# noqa: F401 —
  re-exported`) so older imports keep working. New code imports from `app.services`.

## Exceptions process

An import contract exception goes in that contract's `ignore_imports` in `.importlinter`,
with a comment stating why, and is reviewed like any other architecture change (PR
description says which contract and why the alternative was worse). Do not delete a contract
to get a green build.
