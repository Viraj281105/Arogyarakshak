# ADR-018: Application service layer and enforced import contracts

## Status
Accepted (2026-10-19)

## Context
The domain packages (`packages/kadi`, `billnyay`, `daavisetu`, `bimanyay`, `schemesetu`,
`dawacheck`) were already clean: no FastAPI, no SQLAlchemy, and domain modules depend only on
Kadi. The coupling problem was inside `apps/api`. Use cases that more than one entry point
needs lived in HTTP route modules, and other code imported those route modules to reach them:

| Caller | Imported from a route module |
|---|---|
| `app.auto_triggers` | `build_case_audit`, `build_case_icd_audit`, `build_case_medicine_benchmarks`, `build_case_eligibility` (lazily, to dodge a circular import) |
| `endpoints/claim_pack.py` | three other route modules |
| `app.case_retention` | `purge_case` from `endpoints/kadi.py` (lazily, "avoids a circular import") |
| `app.clinical.demo_control` | `purge_case`, `create_case_record`, `ingest_document_now`, `processing_status` |
| `app.evaluation.runner`, `scripts/evaluate_latency.py` | BillNyay internals, the latency tracker |
| `app.background` | `app.main` (for test dependency overrides) |

The cycle `endpoints/schemesetu -> app.auto_triggers -> app.background -> app.main ->
endpoints/*` was real; function-level imports hid it. Nothing stopped new code from adding to it.

## Options considered
1. **Leave it, document the rule.** Zero cost; drift continues (it already had).
2. **Hexagonal rewrite** (ports/adapters, repositories per aggregate). Large diff, new
   abstractions for a single-team codebase, high regression risk for no new capability.
3. **A thin application layer plus machine-checked contracts.** Move only the shared use
   cases out of route modules, unchanged, and make the dependency rules a CI failure.

## Decision
Option 3.
- New package `apps/api/app/services/` for use cases shared by more than one entry point:
  `billnyay_audit`, `dawacheck_benchmarks`, `schemesetu_eligibility`, `daavisetu_claims`,
  `case_ingestion`, `case_purge`, `document_jobs` (ADR-019). Code was moved verbatim; route
  modules re-export the old names so existing imports (and tests) keep working.
- `app.background` no longer imports `app.main`; `app.main` registers its
  `dependency_overrides` with `app.background.register_dependency_overrides`.
- `.importlinter` (import-linter 2.1) enforces five contracts, run in CI as `lint-imports`:
  domain packages never import `app`/FastAPI/Starlette/SQLAlchemy; Kadi never imports a domain
  module; domain modules are mutually independent; nothing below the HTTP layer imports
  `app.api` or `app.main`; route modules are mutually independent.
- `apps/api/tests/test_architecture.py` fails if a new `app` module or route module is not
  covered by those contracts, so the rules cannot silently erode.

## Rationale
The smallest change that removes the cycle and makes the boundary enforceable. Moving code
verbatim keeps the behavioural diff at zero (the full suite was unchanged: 1076 passed before
and after the move).

## Consequences
- Where code goes is now decidable: domain rule → `packages/<module>`; shared use case →
  `app/services`; HTTP concerns (auth, consent, status codes) → `app/api/v1/endpoints`.
- Three package directories under `app/api` gained `__init__.py` (they were implicit
  namespace packages, which static import analysis cannot see).
- Tests that monkeypatch the ingestion pipeline now patch `app.services.case_ingestion`.

## Operational cost
One dev dependency (`import-linter`), ~5 s in CI.

## Risks
Re-exports in route modules can tempt new callers to keep importing from routes; the
contracts make that a CI failure for any non-route caller.

## Exceptions
None today. To add one, put it in the contract's `ignore_imports` with a comment explaining
why, and review it like any architecture change (see `docs/architecture/module-boundaries.md`).

## Alternatives rejected
Option 1 (already failing in practice), option 2 (cost and risk without a capability gain).
