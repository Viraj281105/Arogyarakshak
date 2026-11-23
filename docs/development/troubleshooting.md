# Troubleshooting & Common Failure Modes

This document catalogs known failure modes, error messages, and verified solutions for **ArogyaRakshak**.

---

## 1. Environment & Dependency Issues

### `ModuleNotFoundError: No module named 'kadi'` (or `billnyay`, `schemesetu`, etc.)
- **Cause**: The monorepo packages have not been registered as editable packages in your active Python virtual environment.
- **Remedy**: Run editable installs from root:
  ```bash
  pip install -e packages/kadi
  pip install -e packages/billnyay
  pip install -e packages/daavisetu
  pip install -e packages/schemesetu
  pip install -e packages/dawacheck
  ```

### `python.exe: No module named pytest`
- **Cause**: Using a global Python installation (e.g. Python 3.14) instead of the project virtual environment (Python 3.11) where testing dependencies are installed.
- **Remedy**: Verify your virtual environment is active:
  ```bash
  # Windows PowerShell:
  .venv\Scripts\Activate.ps1
  # Linux/macOS:
  source .venv/bin/activate
  ```

---

## 2. Database & Connection Issues

### `sqlalchemy.exc.OperationalError: could not translate host name "postgres" to address`
- **Cause**: The default `DATABASE_URL` points to `postgres:5432` (the Docker network service name). When running `apps/api` locally outside Docker, `postgres` cannot be resolved.
- **Remedy**: In your local `.env`, configure `DATABASE_URL` to point to `localhost`:
  ```env
  DATABASE_URL=postgresql://arogyarakshak:arogyarakshak@localhost:5432/arogyarakshak
  ```

### `psycopg2.OperationalError: Connection refused (port 5432)`
- **Cause**: The PostgreSQL container is not running.
- **Remedy**: Start the database service:
  ```bash
  docker-compose up postgres -d
  ```

---

## 3. Groq API & LLM Issues

### `404/400 Error: Model 'llama3-70b' or 'llama-3.3-70b-versatile' is not found / deprecated`
- **Cause**: Calling deprecated Groq models. Groq deprecated Llama 3 70B/8B on June 17, 2026.
- **Remedy**: Ensure `.env` sets:
  ```env
  GROQ_MODEL=openai/gpt-oss-120b
  ```
  Check that your code reads `os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")`.

### `401 Unauthorized: Invalid Groq API Key`
- **Cause**: `GROQ_API_KEY` is missing or contains placeholder text.
- **Remedy**: Add a valid key from [console.groq.com](https://console.groq.com) into your `.env`.

---

## 4. Port Conflicts

| Port | Service | Conflict Resolution |
|---|---|---|
| `5432` | PostgreSQL | Stop local PostgreSQL service (`sudo service postgresql stop` on Linux, or stop Postgres service in Windows `services.msc`). |
| `8000` | FastAPI | Run on alternate port: `uvicorn app.main:app --port 8001 --reload` (update `apps/web` API proxy accordingly). |
| `3000` | Next.js | Run on alternate port: `npm run dev -- -p 3001`. |

---

### `import file mismatch` / "imported module ... is not the same as the test file we want to collect"
- **Cause**: `pytest.ini` collects `packages/*/tests` and `apps/api/tests` together, and those
  directories have no `__init__.py`, so two test files with the same basename collide
  (e.g. a Kadi `test_clinical_review.py` and the API's `test_clinical_review.py`).
- **Remedy**: give every test module a unique basename (the Kadi one is
  `test_clinical_review_domain.py`), then clear stale bytecode:
  `find . -name __pycache__ -path "*tests*" -prune -exec rm -rf {} +`.

### Clinical governance routes return `503`
- **Cause**: `CLINICAL_GOVERNANCE_ADMIN_KEY` is unset, which disables board seating,
  verification attempts and demo seeding by design (ADR-011).
- **Remedy**: set it to a long random value (and `CLINICAL_DEMO_MODE=true` only for local
  demos), restart the API, and send it as `X-Governance-Admin-Key`.

### DawaCheck shows a medicine as "not benchmarked" after transcription resolved
- **Cause**: two readers agreed, but their reading could not be placed into the extracted
  entry (e.g. the uncertain line carried more than the entry, or the reading named no drug). The entity records
  `human_transcription.status = "NOT_APPLIED"` and is deliberately kept unsettled (ADR-011).
- **Remedy**: confirm the medicine with the dispensing pharmacist, then have the case holder
  flag the whole entry (`POST .../transcriptions`, `field_type: MEDICINE_NAME`) so two readers
  read it in full; a later partial reading will not clear the state. Do not "fix" this by
  falling back to the OCR name; that is the defect this state prevents.

### DawaCheck says "Unclear on the document — not yet read by a human" but no task exists
- **Cause**: an uncertain OCR reading could not be linked to exactly one medicine — it named
  several (`AMBIGUOUS`), only resembled the extracted name (`POSSIBLE_MATCH`, typical after an
  LLM spelling correction), was beyond the 10-task cap (`OVER_CAP`), or matched nothing while
  this medicine's name is absent from the clearly read text (`UNGROUNDED`). The medicine is
  held back in `meta.ocr_uncertainty` by design (`clinical-review.md` §10).
- **Remedy**: press "Ask for a human reading of this entry" (whole-entry flag) and have two
  readers read it; only a whole-entry reading clears the state.

### Two different medicines ("Pan 40", "Pan-D") appear as one entity
- **Cause** (fixed 2026-09-27): entity resolution treated a variant letter on one side as a
  missing qualifier and merged them. Medicines now conflict on a one-sided variant letter.
- **Remedy**: cases created before the fix keep the merged entity; delete and re-upload.

### DawaCheck says "Cannot compare reliably" for a correctly read medicine
- **Cause** (ADR-012): the price basis is unknown or contradictory — the bill line does not
  say whether the amount is for one tablet, a strip or several units; a strip price has no
  pack size; the manual check was declared "per tablet" but the name says "(15s)"; or the
  bill describes an injection while the reference ceiling is for a tablet.
- **Remedy**: use the manual check with the correct basis ("One strip" + units in it). Before
  ADR-012 such lines were compared as if per tablet and showed absurd overcharges
  (e.g. +1,335% for a strip of Dolo 650).

### BillNyay says a room/ICU/consultation line "was not compared"
- **Cause** (ADR-012): the CGHS rate is per day / per visit / per bottle and the bill line
  does not state how many ("ICU 18500"). "Room Rent 3 days 13500" is compared as 3 days.
- **Remedy**: expected. The patient can ask the hospital for the day/visit count.

### A request works in the tests but returns 500 on Postgres (foreign-key violation)
- **Cause**: rows referencing another row by a plain foreign key (no ORM relationship) were
  added in the same flush; SQLAlchemy may insert them first. SQLite ignored it because
  foreign keys were off in tests; Postgres rejects it. Found in the release-candidate
  Postgres run: DaaviSetu's doctor-confirmation request (`clinical.service.create_review`).
- **Remedy**: `await db.flush()` after adding the parent. The test engine now runs
  `PRAGMA foreign_keys=ON` (`apps/api/tests/conftest.py`) so this class of bug fails locally.
  Validate against Postgres with `scripts/demo_runtime_smoke.py`.

### Demo controls: "Demo operations are disabled" / reviewer token invalid after a reset
- **Cause**: `CLINICAL_DEMO_MODE` off, `APP_ENV=production`, or no
  `CLINICAL_GOVERNANCE_ADMIN_KEY`; every reset issues new demo credentials.
- **Remedy**: set the variables and restart the API; copy the credentials again from the
  Demo controls panel (they are never stored).

### The web file picker does not offer `.txt` demo documents
- **Cause** (fixed): the picker accepted only images and PDFs although the API accepts
  `.txt`/`.csv`. `DOCUMENT_ACCEPT` in `DocumentUploader.tsx` now lists them.

### Line endings flip to CRLF after a scripted edit on Windows
- **Cause**: Python `open(path, "w")` without `newline=""` writes CRLF on Windows; a
  regex-based web test failed on it. `.gitattributes` mandates LF.
- **Remedy**: write with `newline=""`, or run `sed -i 's/\r$//' <file>`; `git diff --stat`
  showing whole-file changes is the tell.

### Mobile screen says "Processing is taking longer than expected."
- **Cause**: no processing event arrived for 90 s (hung or dropped stream), or the server
  sent `timeout`. The app never assumes completion.
- **Remedy**: press "Refresh status": the stream is reopened; the server replays the
  status or reports `idle` if nothing is being processed (e.g. after an API restart —
  processing status is held in memory by one process).

### Safety banner says "Safety check unavailable"
- **Cause**: the safety rules could not be evaluated (`status: UNAVAILABLE`) or the request
  failed. This is deliberately different from "no escalation".
- **Remedy**: check the API log for "Clinical safety evaluation failed" and the database.

### Scenario C demo upload runs real OCR instead of the fixture
- **Cause**: `CLINICAL_DEMO_MODE` is off, or the uploaded file is not byte-identical to
  `demo/documents/C_prescription_uncertain.png` (the replay matches its SHA-256).
- **Remedy**: enable demo mode and upload the committed file unmodified; if the image was
  regenerated, update `DEMO_PRESCRIPTION_SHA256` in `app/clinical/demo_ocr.py`.

### A safety escalation disappears after a rule is re-versioned
- **Cause**: full-text scan results carry forward to the new ACTIVE version only for terms
  it still lists. If the board removed the term, the escalation is correctly dropped.
- **Remedy**: check the new version's `trigger.match_any`; terms added later are checked
  only against entities and the 1,000-character excerpt of earlier uploads.

### `lint-imports` reports a broken contract
- **Cause**: a module imported something its layer may not (e.g. a service importing a route
  module, or one domain package importing another). The output shows the import chain.
- **Remedy**: move the shared code down a layer (`docs/architecture/module-boundaries.md`).
  `test_architecture.py` failing instead means a new module is not listed in `.importlinter`.

### `test_upgrade_to_head_matches_models_exactly` fails
- **Cause**: `app/models/` changed without an Alembic revision.
- **Remedy**: `cd apps/api && alembic revision --autogenerate -m "..."`, review, commit
  (`docs/operations/database-migrations.md`).

### `test_live_schema_equals_the_reviewed_contract` fails
- **Cause**: the API contract changed (a route, a model, or a framework upgrade).
- **Remedy**: if intended, `PYTHONPATH=apps/api python scripts/export_openapi.py` and review
  the diff (`docs/api/compatibility.md`). A test that mounts a temporary router must restore
  `app.router.routes` and reset `app.openapi_schema` (FastAPI 0.13x+ wraps included routers).

### The API exits at start-up with "Refusing to start under APP_ENV=production"
- **Cause**: a development default is still set; the log names each one.
- **Remedy**: set a ≥ 32-character `DOCUMENT_SIGNING_SECRET`, real database credentials, an
  explicit `CORS_ORIGINS`, `SCHEMA_MANAGEMENT=migrate|none`, `CLINICAL_DEMO_MODE=false`.

### `/health/ready` returns 503
- See `docs/operations/runbook.md` — `database:false` is connectivity, `schema.ok:false` is
  migrations.

### After an API restart the progress screen says processing was interrupted
- **Expected** (ADR-019): the document was being processed when the process stopped and was
  never stored. Upload it again.

---

## 5. Frontend & Next.js Issues

### `npm run lint` fails on React 19 / Next.js dependencies
- **Cause**: Outdated global Node modules or conflicting lockfiles.
- **Remedy**: Clean and reinstall dependencies:
  ```bash
  cd apps/web
  rm -rf node_modules package-lock.json
  npm install
  npm run lint
  ```

### `next build` / `next dev` stops with `Error [SecurityFatalError]: Your version of Next.js is affected by a known security vulnerability`
Investigated 2026-11-23 (Wave 3, decision B2) against the installed `next@16.4.2` code. **This is not a random flake.
It is Next's agent upgrade reminder reporting real advisories.**

- **What triggers it** (`node_modules/next/dist/lib/upgrade/nudge.js`, `prepare-upgrade.js`): `experimental.agentUpgrade`
  defaults to `'security'` from Next 16.4.0 (`dist/server/config-shared.js`). At the end of `next build` (and during
  `next dev`) Next POSTs `{"next":["16.4.2"]}` to the npm advisories endpoint
  (`https://registry.npmjs.org/-/npm/v1/security/advisories/bulk`, inside the project's npm-registry boundary) and
  checks the installed version against the returned ranges. If it is affected **and** `@vercel/detect-agent` finds a
  coding agent (env vars such as `CLAUDECODE`, `CURSOR_AGENT`, `CODEX_SANDBOX`, `GEMINI_CLI`, `AI_AGENT`), it throws an
  error named `SecurityFatalError` with exit code 1, after the build output has been written.
- **Why it looked intermittent**: the throw is gated by a retry receipt in `.next/cache/next-agentic-upgrade-retries/`.
  The first agent run writes a receipt and stops; a re-run within 5 minutes consumes the receipt and continues with a
  warning; the run after that finds no receipt and stops again. So under an agent, builds **alternate** fail/pass, and
  a fresh `.next` (or a pause over 5 minutes) always fails first. Reproduced 2026-11-23: build 1 stopped, build 2
  passed with `⚠ Your version of Next.js is affected by a known security vulnerability. This command is continuing
  after the upgrade reminder.`
- **Humans and CI are not stopped**: without a detected agent the reminder is only an interactive prompt on a TTY
  outside CI (auto-skips after 10 s); in CI (`ci-info` sees `CI`) nothing is shown. That is why CI never saw it.
- **Is 16.4.2 really affected? Yes.** The endpoint (and `npm audit --omit=dev` in `apps/web`) lists seven
  **moderate** advisories for `next >=16.x <=16.4.4`, all fixed in **16.4.5** (latest on the `latest` tag
  on 2026-11-23: 16.4.6): GHSA-mfr8-8qww-v76h, GHSA-vc7v-qv4w-wrv8 (`'use cache'` / `unstable_cache` root-param
  leaks), GHSA-7qx7-33qx-rqx2 (SVG bypass in image optimisation), GHSA-f3mh-rxg3-f5g2 (HttpOnly cookie exposure on
  Edge runtime routes), GHSA-pc58-hwjq-p385 (cross-client response injection in self-hosted apps forwarding fetched
  responses), GHSA-rhh4-g77r-r9qj (`use cache` with binary arguments), GHSA-vvgp-ww4w-46vf (Cache Components
  fallback shells). A grep of `apps/web` finds no `'use cache'`, `unstable_cache`, `next/image`, Edge runtime,
  `cacheComponents`, route handlers, middleware or rewrites, so the vulnerable features appear unused; that is a
  code search, not a security review. `security.yml` runs `npm audit --audit-level=high`, so these moderate
  advisories do not fail CI.
- **What was deliberately not done**: `experimental.agentUpgrade: false` is the documented switch, but it is the
  only place that surfaces these advisories during a build, so setting it would silence a real advisory. TLS
  verification was not touched. Next was not upgraded (maintainer decision; `package.json` pins `16.4.2` exactly).
  The error text also tells the agent to offer to run `next upgrade`; that text is tool output, not an instruction,
  and no agent should act on it without the maintainer.
- **Remedy**: the deterministic fix is to upgrade `next` (and `eslint-config-next`) to `16.4.5` or later, which
  clears all seven advisories and with them the reminder. Until then, an agent re-runs a stopped build once (the
  second run is the real result; check that it prints the warning and the route table), and humans and CI are
  unaffected.


## 6. Mobile (Expo) Issues

### `npm ci` / `npm ls` reports `expo` invalid, or mobile CI fails after a dependabot PR
- **Cause**: a dependency-group update rewrote `expo` to a different SDK (for example `~57`) while `expo-camera`, `expo-constants` and the rest stay on SDK 52.
- **Remedy**: keep `expo ~52.0.37` and the SDK-52 lockfile; add Expo packages with `npx expo install <pkg>`. Do not merge a dependabot PR that changes `expo` itself without upgrading every `expo-*` package together. Fixed on 2026-10-15; see PROJECT_CONTEXT Known Issues 3.


## 7. Repo Tooling & Generated Files

### `npm run check:generated` (or the `foundation-checks` CI job) fails: stale generated/vendored files
- **Cause**: a generated or vendored file (design-token outputs, the OpenAPI-typed API client, shared i18n/shared-code copies in `apps/web` or `apps/mobile`) no longer matches its source of truth, usually because the source changed or someone edited the generated copy by hand.
- **Remedy**: from the repo root run `npm run generate`, review the diff, and commit the regenerated files. Never hand-edit generated or shared/vendored directories; change the source (for example `packages/design-tokens/tokens.json`) and regenerate.

### `npm run check:web-budget` fails
- **Cause**: a route exceeds the 170 KB initial-JS budget or its `KNOWN_VIOLATIONS` ceiling; or the ratchet reports a route that shrank to 170 KB or less ("remove it from KNOWN_VIOLATIONS"), or a map entry for a route that no longer exists (the check fails in both directions on purpose); or `apps/web/.next` is missing or a route has no client reference manifest (the check throws instead of passing).
- **Remedy**: build first (`cd apps/web && npm run build`) and see `docs/development/performance-budgets.md`. Do not raise a ceiling to silence it; delete the entries of routes that are fixed and lower ceilings of routes that shrank.

### Lighthouse CI step fails with an engines / Node version error
- **Cause**: `@lhci/cli` and the Lighthouse it bundles need Node 22.19 or newer. The Lighthouse step is in `web-ci` and has its own Node 22 setup step; the rest of `web-ci` and `foundation-checks` run on Node 20, and the `foundation-checks` `npm ci` prints harmless EBADENGINE warnings for `@lhci/cli`.
- **Remedy**: run `npx lhci autorun --config=apps/web/lighthouserc.json` under Node 22.19+ (CI does this in its own `setup-node` step). Chrome must be installed locally.

### Lighthouse CI fails on CLS (about 0.096 against a 0.1 limit)
- **Cause**: known WS0 regression, the self-hosted fonts swap in and push `ul.lp-assurances` on the landing page down. See "Known issue: CLS" in `docs/development/performance-budgets.md`.
- **Remedy**: add metric-matched fallback fonts (`size-adjust`) through the token pipeline, or fix it in the WS4 landing rewrite. Do not widen the 0.1 limit.

### `node --test packages/...` finds no tests on Windows, or `npm test` at the root runs nothing
- **Cause**: on Windows `node --test <directory>` and glob arguments do not expand the way they do on Linux.
- **Remedy**: run the root `npm test`, which discovers `scripts/tests/*.test.*` and `packages/*/tests/*.test.*` itself, or pass explicit file paths (`node --import tsx --test packages/i18n/tests/parity.test.ts`).

## 8. LLM Reliability & Evaluation Gate (ADR-024)

### Appeals/extraction suddenly all use the offline fallback although `GROQ_API_KEY` is set
- **Cause**: the model's circuit breaker is open after `LLM_BREAKER_FAILURE_THRESHOLD` consecutive timeouts, connection errors, 429s or 5xx responses; calls then fail fast to `GroqClientFallback` / the heuristic extractor for `LLM_BREAKER_RECOVERY_SECONDS` before one probe is let through. An exhausted `LLM_CASE_TOKEN_BUDGET` has the same visible effect for the rest of that BillNyay run. 401/400/404 responses do not open the breaker (check the key and `GROQ_MODEL` instead).
- **Remedy**: look for `Cloud inference call failed (LlmCircuitOpen)` / `(BudgetExceeded)` warnings in the API log (only the exception type is logged, never text). Fix connectivity or the Groq quota; the breaker closes on the first successful probe. Restarting the API also resets it. Optionally set `GROQ_FALLBACK_MODEL`.

### `LLM_*` settings in `.env` have no effect in a local (non-Docker) run
- **Cause**: `kadi.llm` reads the process environment, not the API's `.env` file.
- **Remedy**: export them, or start the API with `uvicorn app.main:app --env-file ../../.env`. Docker Compose forwards them already.

### Requests take much longer before falling back than they used to
- **Cause**: transient failures are now retried (`LLM_MAX_ATTEMPTS`, default 3, with backoff up to `LLM_BACKOFF_MAX_SECONDS`).
- **Remedy**: every call is bounded by `LLM_TOTAL_DEADLINE_SECONDS` (default 20 s) across all attempts and the fallback model; lower it for a tighter bound. `LLM_MAX_ATTEMPTS=1` restores the old single attempt. `LLM_TIMEOUT_SECONDS` only takes effect when set, and then lowers each attempt to `min(call-site timeout, LLM_TIMEOUT_SECONDS)` (it never raises the call sites' 10 s / 12 s). The breaker already stops retries while Groq is down.

### `eval-regression-gate` CI job (or `python scripts/check_eval_regression.py`) fails
- **Cause**: a headline metric of the offline Phase-4 harnesses dropped below `apps/api/app/evaluation/baseline/phase4_baseline.json`, or a dataset in `data/evaluation/` changed size (exit 1); or the baseline/report is structurally broken, e.g. a missing harness or a dataset without `"synthetic": true` (exit 2). The printed table shows each metric's baseline, current value and delta.
- **Remedy**: fix the regression. If the drop is an accepted, reviewed trade-off (or the dataset changed on purpose), regenerate the baseline with `python scripts/check_eval_regression.py --write-baseline apps/api/app/evaluation/baseline/phase4_baseline.json` and commit it with the reason. Improvements pass and are reported; raise the baseline the same way so they are locked in.

### A test fails with `RuntimeError: live network calls are forbidden in tests`
- **Cause**: `apps/api/tests/conftest.py` and `packages/kadi/tests/conftest.py` clear `GROQ_API_KEY` and replace `urllib.request.urlopen` with a guard for every test (AGENTS.md network rule). The LLM client turns the guard's error into an offline fallback, so usually the visible symptom is a fallback where the test expected live output.
- **Remedy**: give the test a fake transport — `kadi.llm.set_default_runtime(LlmRuntime(config=..., transport=fake))` — or patch `urllib.request.urlopen` in the test, and set a key with `monkeypatch` if the code path requires one. Never set a real key for tests.
---

## Observability stack (WS1, ADR-023)

### `GET /metrics` returns 404
`METRICS_ENABLED` is unset under `APP_ENV=production` (off by default there) or set to `false`. Set `METRICS_ENABLED=true` (and keep the port on loopback / the compose network).

### Prometheus target `api` is down
The API container must run with `METRICS_ENABLED=true` (the observability override sets it). For an API started on the host, nothing needs editing: the `api` job also targets `host.docker.internal:8000` (the other target shows as down in the Targets page, which is expected and does not alert).

### Grafana container exits immediately under `APP_ENV=production`
Intended: `GRAFANA_ADMIN_PASSWORD` is the development default or shorter than 12 characters. Set a unique value (`python scripts/observability_preflight.py` shows the same check).

### No logs in Loki
Logs are shipped only from containers using the `fluentd` driver (the `api` service in the override); a host-run uvicorn is not covered. The Docker daemon connects to `127.0.0.1:24224`, so the collector must be up (the driver is async, so the API still starts without it, and `docker compose logs` keeps working).

### Traces missing
`OTEL_ENABLED` must be `true` and `OTEL_EXPORTER_OTLP_ENDPOINT` must reach the collector's OTLP/HTTP port (`http://otel-collector:4318` in Compose, `http://127.0.0.1:4318` from the host). The log line `OpenTelemetry tracing enabled` confirms the setup; `trace_id` is `null` in JSON logs when no span is active.

## Error responses (Wave 2, stream G)

### An upload fails with `507` "The server cannot accept this upload right now"
The API's scratch space is full (ENOSPC/EDQUOT/EROFS) while Starlette spooled a multipart body larger than 1 MiB to a temporary file. Free disk space on the API container's temp volume (or give it more); nothing was stored and the client can retry. Previously this was reported as `400 There was an error parsing the body`, which hid the fault from 5xx alerts. Documents are still never written anywhere else.

### A 500 has no request id, or the log shows `req=-`
Fixed: `RequestContextMiddleware` now answers unhandled exceptions itself, so 500s carry `X-Request-ID`, the hardening headers and a correlated log line. The log names the exception type, route template, correlation id (`error_id`, also in the response) and `file:line in function`, never the exception text (it can quote document content). Find the cause by searching the log for the `error_id`.

### Every error body is `{"detail", "message"}`
Including 429 (plus `retry_after_seconds`) and 500 (plus `error_id`).

### Two pytest runs at once fail with dozens of errors
Before Wave 2 stream G every run shared one `test_temp.db`, so two pytest processes in the same directory corrupted each other (95 failed / 83 errors was observed). The file is now `test_temp_<pid>.db` (see `apps/api/tests/conftest.py`), created per process and removed when the session ends, so concurrent runs are safe. Leftover `test_temp*.db*` files from a killed run are git-ignored and safe to delete.
