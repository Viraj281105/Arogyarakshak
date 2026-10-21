# Engineering foundation pass — assessment and results (2026-10-19)

Branch `arch/engineering-foundation` (from `viraj-dev` = `main` @ `b8068d3`). Scope: the
platform under the product, ahead of the UI redesign. No visual change was made.

## 1. Starting point (measured)

Working tree clean; the four recent feature efforts (evaluation harnesses #155, Claim Pack
#154, read-aloud #156, explanation trail #157) were already merged; no other worktree was
active (`.claude/worktrees/read-aloud-…` is an ignored leftover directory and was not touched).

| Check | Baseline result |
|---|---|
| `python -m pytest` (packages + apps/api/tests) | 1076 passed, 6 skipped |
| `scripts/ci_guardrails.py` | 8/8 |
| CI Ruff gate (`E9,F63,F7,F82`) | clean (full Ruff rule set: 1,788 findings — not a gate, not addressed) |
| web: lint / `tsc` / tests | 0 / 0 / 133 passed |
| mobile: `tsc` / tests | 0 / 126 passed |
| Docker engine | not available on this machine (images could not be built locally) |

## 2. What the inventory found

Already sound: domain packages free of web/ORM imports and independent of each other; per-
case authorization (ADR-009); retention sweep and erasure (ADR-010); non-root images;
localhost-only ports; deterministic explanations (ADR-017); a real evaluation harness.

Structural problems, in priority order:

1. **Route modules used as a library.** Auto-triggers, the Claim Pack, the retention sweep, the
   demo kit and the evaluation harness imported HTTP route modules for business logic, with
   function-level imports hiding an import cycle through `app.main`. No rule prevented more.
2. **No schema migrations.** `create_all` at start-up can never add a column to an existing
   table; failures were logged and swallowed.
3. **Silent loss of in-flight processing.** A restart mid-processing left a case looking idle.
   The single-process requirement behind the in-memory progress stream and rate limiter was
   recorded only in code comments.
4. **Known-vulnerable dependencies** on the upload path (python-multipart 0.0.12, Starlette
   0.46.2) and a critical Next.js advisory (16.3.4).
5. **Sensitive data in logs**: raw URLs with case ids in error logs and uvicorn's access log;
   Pydantic validation errors (including submitted values) logged verbatim; uploaded file
   names (which can identify a patient) logged at INFO.
6. **Production profile was advisory**: insecure signing secret, default DB credentials and
   wildcard CORS produced warnings only.
7. **Health checks conflated liveness and readiness** (`/health` never touched the DB).
8. **The latency harness had silently stopped measuring** (401 on every upload since case
   tokens were introduced) and reported `PASS: all 0 run(s)`.
9. Web image build context included host `node_modules` (copied over the Linux install).

## 3. What changed

| Area | Change | Evidence |
|---|---|---|
| Modularization | `apps/api/app/services/` (7 modules) extracted verbatim from route modules; route modules re-export; `app.background` no longer imports `app.main` (ADR-018) | suite unchanged at 1076 passed after the move |
| Architecture enforcement | `.importlinter` (5 contracts) + `test_architecture.py` (contracts cover every module) | 5/5 kept; mutation: re-introducing the old imports breaks 2 contracts |
| Migrations | Alembic, `0001_baseline` + `0002_document_jobs`, `SCHEMA_MANAGEMENT`, legacy `create_all` databases adopted not recreated (ADR-020) | `test_migrations.py` (models == migrations, round trip, legacy adoption with data kept, DB CHECK constraint); mutation: an unmigrated column fails; live: fresh DB migrated at start-up |
| Processing reliability | `kadi_document_jobs`, start-up reconciliation to `interrupted`, SSE reports it, single-process rule codified (ADR-019) | `test_document_jobs.py` (9 tests) |
| API contract | `docs/api/openapi.json` + `test_openapi_contract.py` (removed operations flagged separately), `scripts/export_openapi.py`, `docs/api/compatibility.md` | caught a test that leaked a probe route into the app after the FastAPI upgrade |
| Security | production profile refuses insecure defaults; `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Cache-Control: no-store`, CORP on every response; docs UIs off in production; logs use route templates, no input values, no file names; uvicorn access log off | `test_platform_foundation.py` (14 tests); live log inspection |
| Dependencies | FastAPI 0.148.0, Starlette 1.9.0 (pinned), python-multipart 0.0.32, Next.js 16.4.2 (+ transitive fixes) | pip-audit: 14 → 0; web `npm audit --omit=dev`: 3 (1 critical) → 0; full suites green |
| Observability | `X-Request-ID` (reused if well-formed), JSON logs (`LOG_FORMAT=json`), one access line per request, `/health/live` vs `/health/ready` | tests + live run |
| Containers | API image multi-stage (no gcc in runtime), HEALTHCHECK, graceful-shutdown timeout, migrations shipped; web image multi-stage + `.dockerignore`; compose web on 127.0.0.1 | `docker compose config` both files; **images not built locally** (no Docker engine) — CI builds them |
| Kubernetes | kustomize base + example overlay + migration Job, single API replica, hardened pods, Pod Security restricted, NetworkPolicy (ADR-021) | `kubectl kustomize` renders; `tests/infrastructure` (8 policy tests); **never applied to a cluster** |
| CI | least-privilege permissions; `lint-imports`; Alembic upgrade + `alembic check` on PostgreSQL 16; migration round trip on PostgreSQL; kustomize render; demo compose validation; new `security.yml` (gitleaks, pip-audit, npm audit, Trivy + SBOM) | workflow YAML parsed; **not yet run on GitHub** |
| Performance | latency harness fixed (sends the token, fails on zero samples); new baseline p50 0.026 s / p95 0.035 s (offline, text fixtures) | `docs/evaluation/latency.md` |
| Docs | ADR-018…021, module boundaries, service catalog, migrations, Kubernetes, runbook, supply chain, compatibility | — |

## 4. Final results

| Check | Result |
|---|---|
| `python -m pytest` | **1119 passed, 7 skipped** (the extra skip is the PostgreSQL migration variant; CI runs it) |
| `lint-imports` | 5 kept, 0 broken |
| `scripts/ci_guardrails.py` / CI Ruff gate | 8/8 / clean |
| web lint / `tsc` / tests / build | 0 / 0 / 133 passed / OK (Next.js 16.4.2) |
| mobile `tsc` / tests | 0 / 126 passed |
| pip-audit (API) / `npm audit --omit=dev` (web) | 0 / 0 |
| Live run (SQLite, demo mode, `SCHEMA_MANAGEMENT=migrate`) | fresh DB migrated to `0002_document_jobs`; `/health/ready` 200; web upload → SSE → extraction → auto-triggers → CGHS audit rendered; console clean; app logs carry route templates only |

## 5. Not done, not verified, and why

- **Container images were not built or run locally** (Docker engine unavailable). CI builds them.
- **Kubernetes manifests were never applied to a cluster**; none exists. Resource numbers are assumptions.
- **Alembic on PostgreSQL is verified only by the new CI steps**, which have not run yet.
  `alembic check` with `compare_type` could flag dialect type differences on PostgreSQL that
  SQLite does not; if so, that is a real finding to resolve in a revision.
- **Backup/restore has not been exercised** (procedure in `docs/operations/runbook.md`).
- **No metrics backend or tracing** (Prometheus/OpenTelemetry): one process and no collector
  in scope; request ids + structured logs are the correlation mechanism. FastAPI 0.148 pulls
  `opentelemetry-api` transitively; nothing in this codebase configures it.
- **Mobile dependencies**: 56 advisories remain (accepted risk pending the Expo SDK upgrade).
- **No authentication layer** (ADR-008) — unchanged; it remains the gate for any public deployment.
- Full Ruff rule set, SAST, image signing, Actions pinned by SHA: not addressed.
- Uploaded file names are still stored in entity metadata (`source_file`), by product design
  (explanation trail); only their logging was removed.
