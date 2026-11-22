# Load tests, chaos tests and policy-as-code

Status of everything on this page (2026-11-21): **written and parsed, not run against a live
stack.** k6, OPA, Kyverno, cosign and syft were not available when it was written. No latency,
throughput or capacity figure exists; do not quote one until a run produced it.

## Load tests (k6)

`tests/load/` holds four scripts and a shared `lib.js`:

| Script | What it does | Thresholds (all *proposed, not measured*) |
|---|---|---|
| `health.js` | 20 req/s on `/health/live` and `/health/ready` | 5xx < 0.5 %, 429s < 5 %, p95 < 500 ms, > 600 accepted requests |
| `case_create.js` | ramps `POST /cases` to 5/s | 5xx < 0.5 %, 429s < 5 %, p95 < 1 s, > 100 accepted requests |
| `upload.js` | 2 uploads/s of a synthetic text bill, accept path (`202`) | 5xx < 0.5 %, 429s < 5 %, p95 < 2 s, > 100 accepted requests |
| `sse_stream.js` | 5 VUs: create, upload, follow the SSE stream to its terminal event | 5xx < 0.5 %, 429s < 5 %, p95 end-to-end < 10 s, > 20 accepted requests |

Every script also requires a minimum number of iterations and of 2xx responses
(`accepted_requests`) and caps the share of `429` responses (`rate_limited`). At the default
120 requests per minute per IP the scripts would otherwise return early or collect 429s and
still "pass" having measured nothing; with these thresholds such a run fails.

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
script, **validates the URL first** (`tests/load/validate_base_url.py`: https only, no
credentials, no IP literals or internal names, host must be in the repository variable
`LOAD_TEST_HOSTS`, and must resolve to public addresses only), then runs k6 and uploads the
summary JSON. It never runs on a push, pull request or schedule.

## Chaos tests (pytest)

`tests/chaos/` injects faults into the **real FastAPI app** (TestClient, the SQLite test
database and the API suite's isolation fixtures from `apps/api/tests/conftest.py`). They run in
the normal `python -m pytest` invocation and need no network.

**What "database unavailable" means here:** the database is *stubbed*, not taken down. The tests
override the `get_db` dependency with a session object whose every statement raises an
`OperationalError`. That exercises the application's handling (readiness, the error handler, job
bookkeeping) but is **not** a pool-level outage: connection-pool exhaustion, `pool_pre_ping`
recovery, reconnect timing and a real Postgres restart are untested.

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

- `fixtures/{good,bad}/*.yaml`: the **shared corpus** (14 good, 35 bad). Each bad case is a
  single-defect variant annotated with the one rule it must violate. Python, Rego and Kyverno
  are all held to it.
- `kyverno/*.yaml`: six `ClusterPolicy` objects (run as non-root, no `latest`/untagged images,
  resource limits, read-only root filesystem, no runtime-socket or node `hostPath`, no
  `hostPort`), `Enforce`, scoped to the `arogyarakshak` namespace so cluster add-ons are
  unaffected. They cover `initContainers` and `ephemeralContainers`; the volume expression
  defaults a missing `volumes` list (the migration Job has none); the image expression treats a
  registry port (`localhost:5000/app`) as *not* a tag; `hostPort: 0` is unset.
- `kyverno-tests/`: the `kyverno test` set, **generated** from the fixtures by
  `build_kyverno_tests.py` (a unit test fails when it is stale).
- `rego/workload.rego`, `rego/compose.rego`, `rego/fixtures_test.rego`: the same rules for
  `conftest`/`opa`. Run `python infrastructure/policy/build_opa_data.py --out /tmp/opa-fixtures.json && opa test infrastructure/policy/rego /tmp/opa-fixtures.json -v`
  (the fixtures directory must be loaded: its files become `data.good` / `data.bad`).
- `policy_checks.py`: the **same rules in Python**, the only form executed here. It is run
  against `infrastructure/kubernetes/**` (including each Kustomization's `images:` overlay, so an
  overlay cannot re-point an image at `latest`) and `docker-compose*.yml`, which pass, and
  against the fixtures. `python infrastructure/policy/policy_checks.py [--root DIR]` exits 1 on any
  violation.

Rule details that all three forms share:

- **Compose ports.** A bare container port (`"8000"`) or `"8000:8000"` publishes on every
  interface and is denied. Allowed: `127.0.0.1:`, `[::1]:`, `localhost:` prefixes, and long
  syntax with `host_ip` `127.0.0.1` or `::1`. `${X:-127.0.0.1}` is resolved to its default;
  any `${X}` without a default is unprovable and denied. `[::]:9090:9090` is denied.
- **Host paths** (Kubernetes `hostPath` and compose binds) use one regex, identical in all
  four files (a test asserts it): the runtime sockets (`docker.sock`, `containerd.sock`,
  `crio.sock`), `/`, `/var`, `/var/run` and `/run` (parents expose the sockets), and
  `/var/lib/{docker,containerd,kubelet}`; trailing slashes are tolerated, nothing else is
  normalised (so `..` segments are not resolved).
- **Root.** Pod `runAsNonRoot: true` is required; a pod or container `runAsUser: 0` or a
  container `runAsNonRoot: false` is denied.

Scope notes. "Loopback-only" is a compose rule; its Kubernetes counterpart is "no
`hostPort`". Compose files are local-development stacks, so non-root, read-only root and limits
are enforced for Kubernetes only; the one root container (Tempo in the observability override)
is a commented, tested exception. **Neither Kyverno nor OPA has been executed.** The Rego relies
on `regex.replace` expanding `$1` in its replacement and on `every`; the Kyverno uses `foreach`
with `regex_match`. Both are unverified by an engine. `.github/workflows/policy-test.yml` runs
`opa test` and `kyverno test` report-only (`continue-on-error`) so the first run tells us. **Executed once for real** (2026-11-22) against the official images: OPA 1.22.4 passed 3/3 over 14 good and 35 bad fixtures, and Kyverno CLI v1.19.0 passed all 232 generated tests. The first CI run failed twice before that: OPA could not load a directory of per-case fixtures (now one generated document, `build_opa_data.py`), and the action's default Kyverno CLI predates the tests. **Kyverno 1.20 removed execution of the legacy `kyverno.io/v1` ClusterPolicy type these policies use**, so the CLI is pinned to v1.19.0 and migrating to ValidatingPolicy (CEL, `policies.kyverno.io`) is an open follow-up before upgrading.

## Supply chain

`.github/workflows/supply-chain.yml` runs **only when a semver tag is pushed**
(`v[0-9]+.[0-9]+.[0-9]+*`), never on a pull request or branch push. It builds and pushes
`ghcr.io/<owner>/<repo>/api:<tag>` (lower-case path), generates an SPDX SBOM of that image
digest, signs the digest with keyless cosign (GitHub OIDC, no stored key) and attaches the SBOM
as a signed attestation. Job permissions are exactly `contents: read`, `packages: write`,
`id-token: write`. The build uses no `type=gha` cache. Its first steps fail the run unless the
tag is semver **and** the tagged commit is an ancestor of `origin/main`.

**What the signature proves:** "built by this workflow file from a semver tag whose commit is on
main". It does **not** prove the commit was reviewed.

**Decision: signing writes to the public Rekor transparency log.** The entry exposes the
repository name, the workflow path, the ref and the commit SHA. That is accepted for a
public-facing release; do not use this workflow for a repository that must stay private.

### Repository settings a maintainer must configure (the workflow alone is not enough)

1. Settings > Environments > **`release`**: Required reviewers (at least one person who is not
   the one pushing the tag), "Prevent self-review" on, Deployment branches and tags limited to
   the tag pattern `v[0-9]+.[0-9]+.[0-9]+*`. No secrets are needed.
2. Settings > Rules > Rulesets > a **tag ruleset** targeting `v*`: restrict creations to
   maintainers, block updates, block deletions.
3. Branch protection or a ruleset on **`main`**: pull request required, required status checks,
   no force-push or deletion (the ancestry guard is only as strong as main's protection).
4. Settings > Actions > General: workflow permissions "Read repository contents" by default.
5. Repository **variable** `LOAD_TEST_HOSTS` (for `load-test.yml`): comma-separated allowed
   hostnames.

### Maintainer checklist before the first release

- [ ] **Maintainer must SHA-pin every action in `supply-chain.yml` before the first release.**
      They are pinned by mutable major tags (`actions/checkout@v4`, `docker/*@v3|v6`,
      `anchore/sbom-action@v0`, `sigstore/cosign-installer@v3`) because no commit SHA could be
      looked up offline and none was invented. These actions run in the job that holds
      `packages: write` and `id-token: write`. `.github/dependabot.yml` (github-actions
      ecosystem) then keeps the SHAs current.
- [ ] Do the same for `load-test.yml` and `policy-test.yml` (lower risk: read-only token).
- [ ] Configure the settings above.
- [ ] Run `policy-test.yml` once, review it, then drop its `continue-on-error`.

### Verifying a release image (by digest, never by tag)

Get the digest from the release job summary or `docker buildx imagetools inspect`. The
certificate identity keeps the repository's original case (`Viraj281105/Arogyarakshak`), while
the image path is lower-cased by the workflow: mixing them up makes verification fail.

```bash
IMAGE=ghcr.io/viraj281105/arogyarakshak/api@sha256:<digest>
IDENTITY='^https://github\.com/Viraj281105/Arogyarakshak/\.github/workflows/supply-chain\.yml@refs/tags/v[0-9]+\.[0-9]+\.[0-9]+.*$'
ISSUER=https://token.actions.githubusercontent.com

cosign verify "$IMAGE" --certificate-identity-regexp "$IDENTITY" --certificate-oidc-issuer "$ISSUER"
cosign verify-attestation --type spdxjson "$IMAGE" \
  --certificate-identity-regexp "$IDENTITY" --certificate-oidc-issuer "$ISSUER"
```

It has never run; the first release tag is its first test.
