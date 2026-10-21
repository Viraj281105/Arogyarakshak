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

## 4. Measured results and verification

### 4.1 Production source and test line counts

Measured using the exact rules defined in §1:

| Area | Production source | Tests (counted separately) |
|---|---|---|
| **Backend** | 177 files, 26,915 lines | 95 files, 15,245 lines |
| **Web** | 67 files, 10,488 lines | 13 files, 1,485 lines |
| **Mobile** | 68 files, 7,679 lines | 12 files, 1,677 lines |

### 4.2 Resolution of oversized production files (> 500 lines)

Every oversized route, service facade, model, component, and screen from §2 was modularized:

| Baseline lines | File | Final state | Actions & modules created |
|---|---|---|---|
| 800 | `apps/api/app/api/v1/endpoints/kadi.py` | Split into package | `apps/api/app/api/v1/endpoints/kadi/` (`__init__.py`, `cases.py` [332], `resolution.py` [194], `abdm.py` [149], `schemas.py` [143], `insights.py` [118], `loaders.py` [42]) |
| 743 | `apps/api/app/api/v1/endpoints/billnyay.py` | 233 lines | Extracted `services/billnyay_llm.py` (243) and `services/billnyay_appeal.py` (295) |
| 710 | `apps/api/app/clinical/service.py` | 57 lines | Thin facade delegating to `case_reviews.py` (257), `statements.py` (274), `reviewer_reviews.py` (150), `facts.py` (98), `review_common.py` (21) |
| 668 | `apps/api/app/models.py` | Split into package | `apps/api/app/models/` (`kadi.py` [195], `clinical_review.py` [150], `daavisetu.py` [106], `safety.py` [88], `bimanyay.py` [73], `transcription.py` [70], `billnyay.py` [35], `schemesetu.py` [29], `dawacheck.py` [25], re-exported by `__init__.py` [83]) |
| 630 | `apps/api/app/api/v1/endpoints/clinical_review.py` | Split into package | `apps/api/app/api/v1/endpoints/clinical_review/` (`reviewer.py` [206], `registry.py` [187], `case_holder.py` [180], `schemas.py` [78], `__init__.py` [24]) |
| 522 | `apps/api/app/api/v1/endpoints/daavisetu.py` | Split into package | `apps/api/app/api/v1/endpoints/daavisetu/` (`readiness.py` [217], `claims.py` [213], `__init__.py` [18]) |
| 1003 | `apps/web/app/clinical-review/page.tsx` | 128 lines | Extracted components to `apps/web/app/clinical-review/components/` (`ReviewsTab.tsx` [220], `SafetyTab.tsx` [215], `StatementEditor.tsx` [188], `TranscriptionTab.tsx` [103], `ReviewSummary.tsx` [96], `SignInPanel.tsx` [92], `FactConfirmations.tsx` [75], `EvidencePanel.tsx` [56]) |
| 632 | `apps/web/app/components/modules/BillNyayView.tsx` | 195 lines | Extracted `modules/billnyay/` (`AuditResults.tsx` [169], `AppealLetterCard.tsx` [128], `types.ts` [84], `PlausibilityCard.tsx` [78]) |
| 546 | `apps/web/app/page.tsx` | 227 lines | Extracted `hooks/useCaseSession.ts` (301) and `components/ModuleTabs.tsx` (34) |
| 528 | `apps/web/app/components/modules/BimaNyayView.tsx` | 195 lines | Extracted `modules/bimanyay/` (`SlaTimeline.tsx` [111], `ClinicalSection.tsx` [102], `AppealDrafts.tsx` [81], `DisputeSummary.tsx` [63], `types.ts` [55]) |
| 546 | `apps/mobile/src/screens/CameraScanScreen.tsx` | 143 lines | Extracted `screens/camera/` (`styles.ts` [135], `useScanUpload.ts` [130], `ScanOverlays.tsx` [113], `PermissionGate.tsx` [57]) |
| 515 | `apps/mobile/src/api/types.ts` | Split into package | `apps/mobile/src/api/types/` (`clinical.ts` [158], `billnyay.ts` [79], `dawacheck.ts` [70], `core.ts` [69], `bimanyay.ts` [65], `schemesetu.ts` [52], `daavisetu.ts` [28], re-exported by `index.ts` [11]) |

### 4.3 Files retained > 500 lines

Only 7 production files exceed 500 lines, each retained with deliberate justification:
1. `apps/mobile/src/translations/strings.ts` (785 lines): static trilingual string dictionary (retained per §3).
2. `apps/web/app/globals.css` (755 lines): CSS design tokens and layout primitives (retained per §3, no visual changes).
3. `apps/web/app/translations.ts` (719 lines): static trilingual string dictionary (retained per §3).
4. `packages/kadi/kadi/clinical_review/transcription.py` (648 lines): cohesive clinical transcription domain logic.
5. `apps/web/app/lib/listenCopy.ts` (516 lines): static read-aloud copy dictionaries.
6. `packages/daavisetu/daavisetu/readiness.py` (503 lines): pre-claim documentation readiness domain logic.
7. `apps/api/app/clinical/transcription_service.py` (502 lines): database persistence and audit service for transcription tasks.

### 4.4 Duplication and dead code resolution

- **D1 (Denial extraction):** Unified in `apps/api/app/services/billnyay_appeal.py`.
- **D2 (Signed-PDF compilation):** Unified in `apps/api/app/services/billnyay_appeal.py`.
- **D3 (Appeal loading):** Unified in `apps/api/app/services/billnyay_appeal.py`.
- **D4 (API_BASE):** Unified into single definition at `apps/web/app/lib/apiBase.ts`.
- **X1 (Vector store scaffold):** Removed dead `packages/kadi/kadi/vector_store.py` (56 lines).
- **X2 (Mobile hooks barrel):** Removed unused `apps/mobile/src/hooks/index.ts`.
- **X3 (Uncalled job view):** Removed `document_jobs.job_view`.
- **X4 (Unused imports/variables):** Cleaned 19 unused items flagged by Ruff.
- **X5 (Runtime dependency):** Removed unused `httpx` from `apps/api/requirements.txt`.

### 4.5 Engineering baseline verification

- **GitHub Actions CI (PR #158, commit `3e154d7`):** 11/11 passing runs across API dependencies (pip-audit), API image scan + SBOM, architectural invariants guard, backend suite (Python 3.11, PostgreSQL 16), CI quality gate, Docker container build, mobile client suite, mobile dependencies, secret scan (gitleaks), web client suite, and web production dependencies (npm audit).
- **Backend test suite:** 1,119 passed, 7 skipped.
- **Architecture contracts (`lint-imports`):** 5/5 kept (no cycles, no route imports below HTTP layer).
- **CI Guardrails (`scripts/ci_guardrails.py`):** 8/8 checks passed.
- **Web client:** 133 tests passed, ESLint clean (0 errors), Next.js build OK.
- **Mobile client:** 126 tests passed, TypeScript clean (0 errors).
- **Reviewer workspace browser verification:** Verified in live browser against migrated SQLite backend with seeded demo credentials. Sign-in, error states on invalid credentials, 3-tab navigation, safety governance rule display, and reviewer registration verified end-to-end.

