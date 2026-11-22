# Wave 2, stream E (platform): handoff

Branch `wave2/e-platform`. Owns: `tests/load/**`, `tests/chaos/**`, `infrastructure/policy/**`,
`.github/workflows/{load-test,supply-chain}.yml`, ADR-025, `docs/operations/load-and-chaos.md`,
plus new tests under `tests/infrastructure/`. No application source was changed.

## What shipped
- **k6 scripts** (`tests/load/`): `health.js`, `case_create.js`, `upload.js`, `sse_stream.js`,
  `lib.js`. Thresholds come from the SLO table in `docs/operations/observability.md` and are
  labelled *proposed, not measured*. Request-latency thresholds have no SLO behind them and are
  marked as placeholders. `load-test.yml` is `workflow_dispatch` only.
- **Chaos tests** (`tests/chaos/`, 39 tests: 36 pass, 3 `xfail(strict=True)`): database
  unavailable, LLM timeout / 5xx / open circuit, OCR crash, over-limit and malformed uploads,
  disk-full-like failures. They use the real app, the SQLite test database and the API suite's
  fixtures re-exported through `chaos_harness.py` (no second `conftest.py`, which collides with
  `packages/kadi/tests/conftest.py`).
- **Policy as code** (`infrastructure/policy/`): six Kyverno ClusterPolicies, Rego for
  Kubernetes and compose (+ opa unit tests), and `policy_checks.py`, a Python implementation of
  the same rules that `tests/infrastructure/test_policy_as_code.py` runs against the repo's own
  manifests and compose files (they pass) and against bad examples (each rule rejects one).
- **Supply chain** (`.github/workflows/supply-chain.yml`): semver tags only
  (`v[0-9]+.[0-9]+.[0-9]+*`), job in `environment: release`, fails unless the tagged commit is an
  ancestor of `origin/main`; build and push to GHCR (no gha cache), SPDX SBOM, keyless cosign
  signature and SBOM attestation. Signing writes to the PUBLIC Rekor log (decision, documented).
  The signature means "built by this workflow from a semver tag on main", not "reviewed".
  Exact `cosign verify` / `verify-attestation` commands (by digest, anchored identity, the
  case trap) and the required repository settings are in `docs/operations/load-and-chaos.md`.
- `.github/dependabot.yml` (new; none existed): github-actions ecosystem.
- `.github/workflows/policy-test.yml` (new, report-only): `opa test` and `kyverno test`.
- **Load guard**: `load-test.yml` validates `base_url` with `tests/load/validate_base_url.py`
  (https, no credentials, no IP literals/internal names, host in `vars.LOAD_TEST_HOSTS`, public
  DNS answers only); unit-tested in `tests/infrastructure/test_load_validator.py`.
- **ADR-025** (PROPOSED): in-process bounded queue vs Postgres `SKIP LOCKED` vs Redis. Proposes
  not adopting a durable queue until load is measured and ADR-003 is revisited.
- `docs/operations/load-and-chaos.md`.

## Defects found (reproduced, not fixed; none trivial and isolated)
1. Unhandled 500 lacks `X-Request-ID` and the hardening headers, and logs `req=-`
   (`test_an_unhandled_500_carries_the_request_id_and_hardening_headers`).
2. 500 and 429 payloads have no `message` key, contrary to AGENTS.md 4.2
   (`test_every_error_payload_has_detail_and_message`). The 500 shape is pinned by
   `apps/api/tests/test_api.py`; decide to add `message` or fix the docs.
3. ENOSPC while spooling a large multipart body is returned as 400 instead of a 5xx
   (`test_a_full_disk_while_spooling_is_a_server_error_not_a_client_error`).
Observation, no test: the unhandled-exception log line includes the exception text.

**Fixes applied to application code: none.**

## Wiring the integrator must add
- Nothing is required for the tests: `testpaths` already includes `tests`, and the new files are
  collected by the normal `python -m pytest` run.
- `ci.yml` is not edited by this stream. Optional: add `lint-imports`-style step
  `python infrastructure/policy/policy_checks.py` (already covered by the pytest run).
- The three `xfail` tests are strict: whoever fixes a defect must remove its marker.
- **MAINTAINER CHECKLIST before the first release: maintainer must SHA-pin every action in
  `supply-chain.yml` before the first release** (they are mutable major tags; no SHA could be
  looked up offline and none was invented), configure the `release` environment, the `v*` tag
  ruleset and main's protection, and set the repository variable `LOAD_TEST_HOSTS`. Details in
  `docs/operations/load-and-chaos.md`. Then run `policy-test.yml` once and drop its
  `continue-on-error`.
- `docs/security/supply-chain.md` still says image signing is "not yet in place"; update it when
  the first signed release exists (outside this stream's ownership).
- No new environment variables, dependencies or database changes.

## Test evidence
Full suite, one invocation from `D:\wt\w2e` (PYTHONPATH set to the worktree):

```
1671 passed, 9 skipped, 3 xfailed, 32 warnings in 301.15s (0:05:01)
```

Also: ruff E9/F63/F7/F82 passed, `lint-imports` 5 kept 0 broken, `ci_guardrails.py` passed,
root `npm test` 61 pass 0 fail.

**The database-outage chaos tests STUB the database**: they override `get_db` with a session whose
statements raise `OperationalError`. They are not a pool-level outage (pool exhaustion,
`pool_pre_ping` recovery, a real Postgres restart are untested).

## Not executed (state plainly)
k6 (so no script has run and **no latency or capacity figure exists**), `opa test` and conftest,
Kyverno, cosign and syft, and the three new workflows. Their syntax was checked only by: PyYAML,
`node --check` on the k6 scripts, and structure tests. The Rego and Kyverno patterns were written
from the documented syntax and are unverified by an engine.

## Decisions
- Policy engines agree through one shared fixture corpus (`infrastructure/policy/fixtures`),
  one host-path regex string asserted identical in Python, both Rego files and Kyverno, and a
  generated `kyverno-tests/` set. A bare compose port (`"8000"`) is now denied.
- Policies scoped to namespace `arogyarakshak` and `Enforce`; loopback-only is a compose rule,
  `hostPort` is its Kubernetes counterpart.
- Compose files are exempt from run-as-non-root, read-only root and limits (dev stacks); Tempo's
  root user stays a commented exception.
- Load scripts need a raised `RATE_LIMIT_PER_MINUTE` (k6 is one IP); `docker-compose.yml` does not
  pass that variable, so the doc runs uvicorn directly.
- Action versions are mutable major tags (matching `ci.yml`); the structure test accepts them only
  while the "mutable" note and the SHA-pin checklist exist, it does not call them pinned.
- `tests/chaos/**` and the shared test-DB path now belong to stream G; not edited in this round.
