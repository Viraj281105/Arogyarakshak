# Load tests, chaos tests and policy-as-code

Status of everything on this page (2026-11-21): **written and parsed, not run against a live
stack.** k6, OPA, Kyverno, cosign and syft were not available when it was written. No latency,
throughput or capacity figure exists; do not quote one until a run produced it.

## Load tests (k6)

`tests/load/` holds four scripts and a shared `lib.js`:

| Script | What it does | Thresholds (all *proposed, not measured*) |
|---|---|---|
| `health.js` | 20 req/s on `/health/live` and `/health/ready` | 5xx < 0.5 %, p95 < 500 ms |
| `case_create.js` | ramps `POST /cases` to 5/s | 5xx < 0.5 %, p95 < 1 s |
| `upload.js` | 2 uploads/s of a synthetic text bill, accept path (`202`) | 5xx < 0.5 %, p95 < 2 s |
| `sse_stream.js` | 5 VUs: create, upload, follow the SSE stream to its terminal event | 5xx < 0.5 %, p95 end-to-end < 10 s |

Where the numbers come from: the availability SLO (99.5 % of requests not 5xx) and the case
latency SLO (95 % of documents within 10 s) are from the SLO table in
[`observability.md`](observability.md), which itself says they are proposed targets, not
results. **There is no request-latency SLO** in that table: the 500 ms, 1 s and 2 s figures are
engineering placeholders, labelled as such in the scripts, to be replaced once a baseline run
exists. A 429 is counted separately (`rate_limited_responses`) and is not a server error.

### Running them

Use a throw-away stack, never a shared or production one. The API limits each client IP to 120
requests per minute (`RATE_LIMIT_PER_MINUTE`, `app/rate_limit.py`) and k6 is one IP, so raise it
for the run. `docker-compose.yml` does not pass that variable through, so the simplest way is
to run the API directly:

```bash
cd apps/api
RATE_LIMIT_PER_MINUTE=100000 uvicorn app.main:app --host 127.0.0.1 --port 8000   # one process (ADR-019)
k6 run tests/load/health.js                     # from the repository root, in another shell
BASE_URL=http://127.0.0.1:8000 k6 run tests/load/sse_stream.js
```

The scripts send synthetic text only and no `GROQ_API_KEY` should be set, so extraction uses
the offline heuristic and nothing leaves the machine. With a key set, the run would also
measure Groq, which is a different (and billable) experiment.

CI: `.github/workflows/load-test.yml` is `workflow_dispatch` only. It asks for a base URL and a
script, runs k6 and uploads the summary JSON. It never runs on a push, pull request or schedule.

## Chaos tests (pytest)

`tests/chaos/` injects faults into the **real FastAPI app** (TestClient, the SQLite test
database and the API suite's isolation fixtures from `apps/api/tests/conftest.py`). They run in
the normal `python -m pytest` invocation and need no network.

| Module | Fault | Asserted |
|---|---|---|
| `test_chaos_database.py` | every statement fails like a lost Postgres connection, message carries a fake DSN and password | `/health/live` stays 200; `/health/ready` 503 with booleans only; recovery without restart; 500 payload generic with a 12-character `error_id`; mid-pipeline failure recorded `failed`; job-bookkeeping failure does not fail the upload |
| `test_chaos_llm.py` | provider timeout, 5xx, socket errors, open circuit | document still completes on the offline fallback; the open circuit stops calling the transport; the API key never reaches a response or a log; no network attempt |
| `test_chaos_ocr.py` | parser raises `RuntimeError`, `MemoryError`, `ValueError`, `OSError(ENOSPC)` with document-like text in the message | job recorded `failed` with the `error_id`; the stream and the response carry a generic message and no exception or document text; the case accepts a corrected upload afterwards; a failed job is not shown as idle after a "restart" |
| `test_chaos_upload.py` | over-limit, exact-limit, empty, bad type, missing file, temp-file creation failing (disk full) | 413/400/415/422 with `{detail, message}`; no job row for a rejected document; small uploads unaffected by a full disk (documents are memory-only, ADR-003); no write-mode `open()` during processing |

Documented behaviour these tests pin: `/health/ready` is the only probe that touches the
database; liveness never does, so a database outage does not restart-loop the container.

### Known defects (reproduced as `xfail(strict=True)`)

Each is a test that fails today for the stated reason. When someone fixes the defect the test
turns into an unexpected pass and must lose its `xfail`.

1. **An unhandled 500 has no `X-Request-ID` and no hardening headers** (`nosniff`,
   `Cache-Control: no-store`), and its log line shows `req=-`. Starlette's outermost
   `ServerErrorMiddleware` answers it outside `RequestContextMiddleware`.
   `test_an_unhandled_500_carries_the_request_id_and_hardening_headers`.
2. **The 500 and 429 payloads have no `message` key**, although AGENTS.md section 4.2 and the
   docstring in `app/main.py` describe `{detail, message}`. 500 returns `{detail, error_id}`,
   429 returns `{detail, retry_after_seconds}`. The 500 shape is pinned by an existing test, so
   the decision is whether to add `message` or to correct the documentation.
   `test_every_error_payload_has_detail_and_message`.
3. **A server-side disk-full while Starlette spools a large multipart body is reported as `400
   There was an error parsing the body`**, a client error, so a 5xx alert never fires.
   `test_a_full_disk_while_spooling_is_a_server_error_not_a_client_error`.

Also observed and **not** turned into a test: the unhandled-exception handler logs the
exception text (with `exc_info`) server-side, so an exception message that quotes a connection
string or document text reaches the log. Responses, SSE events and job rows are clean. Whether
log text is acceptable is a privacy decision (ADR-023 scrubs telemetry, not the application log).

## Policy as code

`infrastructure/policy/`:

- `kyverno/*.yaml`: six `ClusterPolicy` objects (run as non-root, no `latest`/untagged images,
  resource limits, read-only root filesystem, no Docker socket hostPath, no `hostPort`),
  `Enforce`, scoped to the `arogyarakshak` namespace so cluster add-ons are unaffected.
- `rego/workload.rego` and `rego/compose.rego` (+ `workload_test.rego`): the same rules for
  `conftest`/`opa`, for rendered Kubernetes manifests and for the compose files (image tags,
  loopback-only published ports, no Docker socket).
- `policy_checks.py`: the **same rules implemented in Python**. `tests/infrastructure/
  test_policy_as_code.py` runs it against `infrastructure/kubernetes/**` and `docker-compose*.yml`
  (they pass), proves each rule rejects a bad example, validates the Kyverno and Rego structure
  and checks that all three forms cover the same rule names. `python
  infrastructure/policy/policy_checks.py` runs it by hand.

Scope notes. The "loopback-only" rule is a compose rule (every published port binds
`127.0.0.1`); its Kubernetes counterpart is "no `hostPort`". The compose files are
local-development stacks, so run-as-non-root, read-only root filesystem and limits are enforced
for Kubernetes only; the one root container (Tempo in the observability override) is a
commented, tested exception. Neither Kyverno nor OPA has been executed: the Kyverno patterns
use documented syntax and the Rego is written for `rego.v1`, but only the Python implementation
is exercised. Run `opa test infrastructure/policy/rego` and `kyverno test` before relying on
them in a cluster.

## Supply chain

`.github/workflows/supply-chain.yml` runs **only on a pushed tag `v*`**, never on a pull request
or branch push: it builds and pushes `ghcr.io/<owner>/<repo>/api:<tag>`, generates an SPDX SBOM
of that image digest (Syft via `anchore/sbom-action`), signs the digest with keyless cosign
(GitHub OIDC; no stored key) and attaches the SBOM as a signed attestation. `id-token: write` is
granted only to that job. It has never run; the first release tag is its first test. The
verification command is in the workflow header.
