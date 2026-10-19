# Codebase restructuring — audit, target structure and results (2026-10-19)

Second pass on branch `arch/engineering-foundation` (PR #158), after the foundation pass
(`engineering-foundation-2026-10.md`). Goal: physical structure and maintainability —
cohesive, appropriately sized modules; thin routes and components; less duplication; dead
code removed. No visual change, no API contract change, no Expo SDK upgrade.

## 1. Measurement method

The same script, unchanged, produced the baseline and final numbers. It was run from outside
the repository; its rules are reproduced here so anyone can re-measure.

| Area | Counted (production source) | Tests counted separately |
|---|---|---|
| backend | `apps/api/app/**/*.py`, `packages/*/<pkg>/**/*.py`, `scripts/*.py` | `apps/api/tests`, `packages/*/tests`, `packages/kadi/kadi/ocr/tests`, `tests/` |
| web | `apps/web/app/**/*.{ts,tsx,css,mjs}` | `apps/web/tests` |
| mobile | `apps/mobile/src/**/*.{ts,tsx}`, `apps/mobile/App.tsx` | `apps/mobile/tests` |

Excluded everywhere: `node_modules`, `.next`, `dist`, `build`, `.expo`, `__pycache__`, tool
caches, `.venv`, `*.egg-info`, lockfiles, Alembic revision files (`apps/api/migrations`,
generated then reviewed), `docs/api/openapi.json` (generated), reference-data JSON,
`.claude/` worktrees. Lines are physical lines (blank + comment lines included), no
reformatting. A path segment named `tests` moves a file to the test count.

## 2. Baseline findings

### Largest production files (> 500 lines)

| Lines | File | Responsibilities found |
|---|---|---|
| 800 | `apps/api/app/api/v1/endpoints/kadi.py` | 5 unrelated route groups (case lifecycle + upload/SSE, latency metrics, entity-resolution review/calibration, case graph + insights, ABDM import) and all their schemas |
| 743 | `apps/api/app/api/v1/endpoints/billnyay.py` | HTTP routes **plus** a Groq HTTP client, ~130 lines of canned fallback letters (3 languages), and a 140-line 5-agent orchestration inside one handler |
| 710 | `apps/api/app/clinical/service.py` | case-holder review lifecycle, reviewer actions, statement lifecycle, fact confirmations |
| 668 | `apps/api/app/models.py` | every table of every module in one file |
| 648 | `packages/kadi/kadi/clinical_review/transcription.py` | transcription domain (see §4 — retained) |
| 630 | `apps/api/app/api/v1/endpoints/clinical_review.py` | reviewer registry, case-holder routes and reviewer routes |
| 522 | `apps/api/app/api/v1/endpoints/daavisetu.py` | claim/PDF/template routes and institution/playbook/readiness routes |
| 503 | `packages/daavisetu/daavisetu/readiness.py` | readiness domain (see §4) |
| 502 | `apps/api/app/clinical/transcription_service.py` | transcription persistence (see §4) |
| 1003 | `apps/web/app/clinical-review/page.tsx` | entire reviewer workspace: session, registration, queue, review detail, statement editor, transcription |
| 755 | `apps/web/app/globals.css` | styling — out of scope (no visual change) |
| 719 | `apps/web/app/translations.ts` | string data |
| 632 | `apps/web/app/components/modules/BillNyayView.tsx` | audit fetch + table + appeal drafting + PDF/verify + plausibility |
| 546 | `apps/web/app/page.tsx` | page layout **plus** case creation, upload and SSE handling with its own API base (×3) |
| 528 | `apps/web/app/components/modules/BimaNyayView.tsx` | denial analysis form + results + timeline |
| 516 | `apps/web/app/lib/listenCopy.ts` | string data |
| 785 | `apps/mobile/src/translations/strings.ts` | string data |
| 546 | `apps/mobile/src/screens/CameraScanScreen.tsx` | camera, upload, SSE lifecycle and result rendering |
| 515 | `apps/mobile/src/api/types.ts` | every module's API types in one file |

### Duplication

| # | Where | What |
|---|---|---|
| D1 | `billnyay.py` `draft_appeal` / `draft_grievance` | load case document text → choose LLM client → run Auditor → build the "not specified" placeholder denial |
| D2 | `billnyay.py` `draft_appeal` / `refresh_appeal_annex` | compile PDF → SHA-256 → HMAC sign → store |
| D3 | `billnyay.py` `download_appeal_pdf` / `verify_appeal_pdf` | load appeal record or 409 with the same message |
| D4 | `apps/web/app/page.tsx` (×3) and `hooks/useApi.ts` | `process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"` defined four times |

### Dead code and dependencies (each confirmed by search for imports, dynamic loading, framework registration, entry points and tests)

| # | Item | Evidence |
|---|---|---|
| X1 | `packages/kadi/kadi/vector_store.py` (`KadiVectorStore`) | imported only by `kadi/__init__` (so every `import kadi` loaded it); no caller anywhere; documented as an unwired scaffold |
| X2 | `apps/mobile/src/hooks/index.ts` | barrel imported by nothing (import-graph analysis from `App.tsx`) |
| X3 | `document_jobs.job_view` | written in the foundation pass, never called |
| X4 | unused imports / variables in production modules (Ruff F401/F841) | 19 in `billnyay` agents/tools, `daavisetu.generator`, `dawacheck.metaphone`, `latency_metrics`, `rate_limit`, the BillNyay route |
| X5 | `httpx` in `apps/api/requirements.txt` | no production import; only the test client uses it (CI installs it with the test tools) |

Retained after checking: `RegistryVerificationAdapter` (a documented Protocol), Pydantic
validators flagged by vulture, `apps/mobile/src/services/slaReminders.ts` (tested, documented
as "planner, no push delivery yet"), package `__init__` re-exports (public API), every web and
mobile dependency (all imported; `react-native-screens` is a required navigation peer).

### Cycles and boundary violations

- Python: 0 import-contract violations after the foundation pass (5/5 kept). The foundation
  pass removed the one real cycle (`schemesetu route → auto_triggers → background → app.main →
  routes`).
- Web and mobile: 0 import cycles, 0 unreachable web files (import-graph analysis).

## 3. Target structure

```text
apps/api/app/
  api/v1/endpoints/
    kadi/            __init__ (router composition) · schemas · cases · resolution · insights · abdm
    clinical_review/ __init__ · schemas · registry · case_holder · reviewer
    daavisetu/       __init__ · claims · readiness
    billnyay.py      thin routes only
    …                (other route modules unchanged — already small)
  services/
    billnyay_llm.py     Groq HTTP client + deterministic offline fallbacks (infrastructure adapter)
    billnyay_appeal.py  appeal/grievance orchestration; shared denial extraction (D1), signed-PDF rendering (D2), appeal lookup (D3)
    …                   (existing services)
  clinical/
    service.py       facade (stable import path) over:
    reviews.py · reviewer_actions.py · statements.py · facts.py
  models/            __init__ (re-exports every model) · kadi · clinical · billnyay · bimanyay · daavisetu · schemesetu · dawacheck

apps/web/app/
  lib/apiBase.ts                 single API base (D4)
  hooks/useCaseUpload.ts         case creation, upload, SSE (out of page.tsx)
  clinical-review/components/…   sections of the reviewer workspace; page.tsx composes them
  components/modules/billnyay/…  audit table, appeal panel (BillNyayView composes)
  components/modules/bimanyay/…  form, results (BimaNyayView composes)

apps/mobile/src/
  api/types/        one file per domain, index re-exports (import path unchanged)
  screens/camera/   processing hook + result view (CameraScanScreen composes)
```

Rules: route packages compose sub-routers and re-export the names other code and tests
already import; no new generic `utils` modules; data dictionaries (translations, read-aloud
copy) and CSS stay as they are.
