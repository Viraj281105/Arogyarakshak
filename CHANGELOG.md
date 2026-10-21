# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Not-found and error pages, page 10 of the per-page design pass (2026-10-21)

#### Added
- `app/not-found.tsx`: a designed 404 (real 404 status, `noindex`, the saved theme) with links home, to the upload and to the reviewer workspace, and an honest note that a case in progress cannot be reopened from a new page load (its access key lives only in the original tab's memory).
- `app/error.tsx`: route error boundary using Next 16's `retry` prop; shows only the server digest as a log reference, never the error message.
- `app/global-error.tsx`: replaces the root layout when it fails; brings its own document, `globals.css` and the pre-paint theme script.
- `components/StatusPage.tsx`: shared layout with the landing page's paper-bill illustration ("No matching row — so nothing is guessed").
- `tests/status_pages.test.ts`.

### Demo banner and controls, page 9 of the per-page design pass (2026-10-21)

#### Fixed
- The DEMO MODE banner was `position: sticky; top: 0` under a sticky header; on phones it slid beneath the header and covered page content. It now scrolls with the page, and a small "Demo" pill (`DemoPill`) stays in the header of `/` and `/clinical-review`, linking back to the banner (tucked under the emblem below 560 px).
- Safety escalation card: the "Urgent" label ran into the rule title in the text ("URGENTPossible…"); a real space now separates them.

#### Changed
- `DemoBanner`: the server's banner text shown verbatim; "What is simulated?" groups the server's list into Simulated and Real.
- `DemoControls`: operator key as a labelled field ("kept in memory only"), scenario cards with the server's title and module, reset as a destructive outline button, one-time credentials as persona cards (tokens are copy-only, never displayed), a hint while no key is entered. Request, confirmation and one-at-a-time logic unchanged.

### Clinical reviewer workspace redesign, page 8 of the per-page design pass (2026-10-21)

#### Changed
- `/clinical-review`: sticky header (back link, signed-in reviewer, SVG theme toggle), display-type hero, two-column sign-in (credential | registration with a self-declared notice), a profile card with the reviewer ID and verification limits, and descriptive section tabs.
- The "Medical Adjudication Portal" badge is gone — reviewers write attributed statements; nothing on this page adjudicates a claim.
- The one-time credential panel gains a copy button and says no retrievable copy is kept.
- Assigned reviews: queue | open review split view (queue sticky on desktop), a placeholder until a review is chosen, the audit trail as a timeline.
- `types.ts` `panel` inline-style object removed in favour of the shared `case-panel` class; the unused aurora / dot-matrix background CSS removed.

### DawaCheck tab redesign, page 7 of the per-page design pass (2026-10-21)

#### Fixed (unverified or overstated claims)
- Removed the "DPCO 2013 Provision" box that stated charging above the ceiling "is an offence under the Essential Commodities Act" and that pharmacies "must mandatorily display generic bio-equivalents". The project's `law_library.json` marks DPCO Para 14(1) as unverified and no source for the display rule exists in the repo. It is replaced by a "Legal basis" note saying the Order's text has not been verified.
- EN copy: "Verifies pharmacy bill prices against … Schedule-I ceilings" → compares per-unit price against a curated subset; "Compliant with NPPA Cap" / "Overcharged vs Statutory Cap" / "Billed MRP" reworded; the generic-alternative line now says it comes from DawaCheck's reference data.

#### Added
- `modules/dawacheck/PriceBar`: paid-per-unit price against the NPPA ceiling marker on one scale, used by the manual check and by each medicine from the case; it draws a paid bar only when the server made the comparison.
- The manual result now shows where the price basis came from (`basisNote`), which only the case panel showed before.
- `tests/dawacheck_view.test.ts`.

#### Changed
- `DawaCheckView`: labelled fields instead of placeholder-only inputs, `StatePanel` errors with retry, result card coloured by verdict, shorthand translator as a token → meaning list.
- `clinical/CaseMedicineTrustPanel` and `clinical/TranscriptionPanel`: shared panel shell and token styling; logic, wording and requests unchanged.

### SchemeSetu tab redesign, page 6 of the per-page design pass (2026-10-21)

#### Fixed
- The state `<select>` started at `""` with no empty option, so it displayed "Maharashtra" while the check button stayed disabled. It now opens on "Choose your state or union territory" and lists all 28 states and 8 UTs (the engine normalises names itself).
- The pre-check "example" cards claimed MJPJAY covers "1,356 medical/surgical procedures" (no source in the repo) and showed a green "State Scheme" badge. Replaced by a "What SchemeSetu checks" explainer stating only what `schemesetu/thresholds.py` cites, with its source.
- Medical need was required although the engine lists it as an unused input; category defaulted to "General" and was sent as the person's answer. Both are now optional and marked "not used to decide"; category is sent only when chosen.
- EN copy: "Intelligent eligibility assessment across … State healthcare programs" (only MJPJAY is covered) and "Eligible Government Health Schemes" (heading results that are mostly "verification needed") reworded.

#### Changed
- Each result shows its decision basis in three columns — decided by / recorded but not deciding / not checked — plus whether its rule cites an official source or an official restatement; sources are links; errors and the opt-in save use `StatePanel`.

#### Added
- `tests/schemesetu_view.test.ts`.

### BimaNyay tab redesign, page 5 of the per-page design pass (2026-10-21)

#### Fixed (overstated presentation)
- The rule score (a fixed constant per denial category in `bimanyay/clause_auditor.py`, 0.50–0.95) was the headline "Reversal Likelihood Probability: 95%". It is now "Rule-based starting estimate: 95 / 100" with a hatched (not solid) bar and the heuristic disclosure always shown. Regression test: `tests/bimanyay_view.test.ts`.
- Deadlines are computed from the day you press the button (`date_initiated` = today); the tracker now says so ("Counted from today…, assuming you send the step-1 appeal today. Calendar days; holidays are not applied.") and shows "in N days" per deadline.
- EN labels: "Insurance Denial & Grievance Engine" → "Insurance Denial Appeals"; "Wrongful Repudiation Ground Detected" → "Grounds to contest found"; "Statutory & Regulatory Violations" → "Rules this denial may conflict with"; "ACTIVE"/"PENDING" → "Start here"/"Later step".

#### Added
- Each rule conflict now shows its `legal_remedy` (returned by the API but never displayed).
- The form shows the denied share of the claim from the two amounts you entered, and warns if the denied amount exceeds the claim.
- Whether the dispute is linked to your case is stated on the form.

#### Changed
- `BimaNyayView`: grouped form (policy / money / denial) with required marks and an "N fields still empty" hint; errors via `StatePanel` with retry.
- `bimanyay/AppealDrafts`: real `tablist` for the three escalation steps with a line on when to use each; letter on paper; copy reports failure.
- `bimanyay/SlaTimeline`, `DisputeSummary`, `ClinicalSection`: token styling, timeline markers, statement-load errors surfaced.

### DaaviSetu tab redesign, page 4 of the per-page design pass (2026-10-21)

#### Fixed (wrong or overstated labels)
- "Download Form VI / Pre-Auth PDF" -> "Download pre-authorisation PDF": Form VI is the Insurance Ombudsman complaint form; the PDF is a pre-authorisation request laid out after IRDAI Annexure-B (`daavisetu/generator.py`).
- Green "IRDAI Standard Annexure-B" badge -> neutral "Annexure-B layout"; "Network Provider" -> "Hospital"; "Clinical Protocol" -> "Treatment plan"; EN module description no longer claims "conforming to standardized IRDAI claim formats".
- The no-case placeholder that mirrored typed fields under a "Generated Pre-Auth Package" heading is replaced by an empty state.
- Structured API refusals (`{message, missing_fields}`) were shown as raw JSON; `normalizeErrorDetail` now renders the message and the missing fields (test added).

#### Added
- Optional "Estimated cost" field: the API already accepted `estimated_cost`, and without it a document with no bill total ended in a 422 the user could not fix from the UI.

#### Changed
- `DaaviSetuView`: three-step flow (readiness → fill the form → review & download) with required/optional field marks, a disabled-state hint, `StatePanel` errors with retry, a definition-list summary, and copy feedback. Download, encryption and unlock logic unchanged.
- `clinical/PreauthReadinessPanel`: found / needs a doctor / not found meter and legend, per-item status marks; wording and requests unchanged.

### BillNyay tab redesign, page 3 of the per-page design pass (2026-10-21)

#### Changed
- `BillNyayView`: module header, three action tiles (CGHS audit, appeal draft, plausibility) shown only with a case, an empty state that links to the upload, and results ordered audit → appeal → plausibility → clinical review. Audit errors now use `StatePanel` with a retry.
- `billnyay/AuditResults`: the "Forensic Benchmark Coverage" bar (it divided by the whole bill, unmatched lines included, and labelled the result "% Inflation Flagged") is replaced by a composition chart built from each line's status (within / above / usually included elsewhere / not benchmarked) — a line billed below its reference no longer hides another billed above one. The table became a line list with a bar, reference marker, basis and status per line, which also works at 375 px.
- `billnyay/AppealLetterCard`: letter shown as a paper document; disclosures as notices; copy button now confirms and reports clipboard failures.
- `billnyay/PlausibilityCard` and the shared `clinical/ClinicalReviewPanel` shell: token styling, facts as a definition list; no wording or logic changed.

#### Added
- `tests/billnyay_audit_view.test.ts` for the composition (`composeAudit`).

### Case workspace redesign, page 2 of the per-page design pass (2026-10-21)

#### Changed
- `/`: everything that appears once a document is uploaded now lives in one "Your case" workspace (`#case-desk`): title that reflects the real state (reading / read / stopped), the file name, and the add-document and delete-case actions in its header; processing, safety, duplicate questions and the Claim Pack in the main column; the case history beside them.
- `AgentStreamVisualizer`: stage rail driven only by the status stream; the active stage shows an indeterminate bar instead of a made-up 65% width.
- `CaseTimeline`: vertical history with actor markers (software / human reviewer / you) and `<time>` elements; same states (loading, empty, failure, retry).
- `SafetyEscalationBanner`, `EntityResolutionReview`, `ClaimPackPanel`: token-based styling for every state (hardcoded `#ef4444`/`#fca5a5` removed); errors use `StatePanel`. The Claim Pack lists the sections `claim_pack.py` can actually write.
- Client log messages no longer say "multi-agent SSE status stream" or "Kadi layer".

#### Removed
- The unused `.stream-bar` / `.stream-step` styles.

### Landing page redesign, page 1 of the per-page design pass (2026-10-21)

#### Removed (fabricated or unbacked claims from the 2026-10-20 pass)
- `ForensicStoryteller.tsx` (deleted): an invented clinician and MCI registration number, "WASM SHA256" / "100% Client-Side Engine" (documents are uploaded to the API), invented scenario figures and circular clause numbers, and a "Form VI Legal Petition" button that only printed a success message.
- Hero stat grid ("₹14.8 Cr+ reclaimed", "0.00 Bytes retained", "1,840+ NPPA tariffs" — the NPPA reference holds 7 formulations) and the "Client-Side AES-256 Enclave" compliance banner.
- Uploader badges "Max 60MB" (the API limit is 10 MB) and "Devanagari / English OCR" (EasyOCR runs English only); footer badge "DPDP Act 2023 Compliant".

#### Added
- `apps/web/app/components/landing/`: hero with an animated SVG bill illustration, a four-step case journey with a scroll-driven connector, a worked example (made-up bill, real CGHS rows, statuses by the same rule as `services/billnyay_audit.py`), module cards that open the real tab, and a reference-coverage chart.
- `app/lib/referenceSnapshot.ts` + `tests/reference_snapshot.test.ts`: every reference count shown on the page is checked against `billnyay/data/*.json` and `dawacheck/reference_data.py`.
- `app/hooks/useScrollMotion.ts`: scroll reveal and scroll progress; content stays visible without JS and under reduced motion.
- Real drag-and-drop on the dropzone (the copy already said "drag & drop" but there was no drop handler).

#### Changed
- Light theme is now the default unless the OS prefers dark; `useTheme` reads the pre-paint `data-theme` attribute through `useSyncExternalStore`, removing a hydration mismatch on the toggle icon.
- Light `--text-muted` darkened to `#6F7771` (was 3.1:1 on white); new tokens `--font-display` (Fraunces), `--accent-gold`, `--tint-*`, `--chart-*`, `--paper-*`.
- Header shows the real tagline, SVG theme icons, and stays one row at 375 px.

### Design Refinement: Sovereign Editorial & System-Wide Light Mode Overhaul (2026-10-20)

#### Added
- Stitch MCP Design System refinement: updated `assets/14841168233921936765` in project `projects/10088274222863233022` to *ArogyaRakshak Sovereign Editorial & Human Trust* and generated flagship editorial screen `88d1182e3aee4c08a06e1b5762442414`.
- Sovereign Editorial Light & Dark Palettes: Warm ivory canvas (`#F7F6F2`), primary surface (`#FFFFFF`), soft sage wash (`#E9EEE7`), deep forest green (`#244C3A`), graphite text (`#252A27`), secondary text (`#69716B`), muted architectural border (`#E2E5DF`), restrained brass (`#A58A57`), and terracotta status danger (`#B85D43`) in light mode; and deep forest-black (`#151B18`), elevated moss-slate (`#1D2520`), secondary forest shadow (`#252F28`), soft sage accent (`#A7BBA6`), clean linen text (`#F0F1EB`), mineral secondary text (`#B0B8B0`), subtle border (`#354139`), and muted brass (`#C2AD7D`) in dark mode.
- Synchronous blocking `<script>` in `apps/web/app/layout.tsx` to restore `arogyarakshak_theme` from `localStorage` before layout paint, preventing FOUC and keeping themes consistent across all routes.
- Theme switching toggle and `useTheme()` synchronization in `/clinical-review` workspace header (`apps/web/app/clinical-review/page.tsx`).
- High-contrast `.nested-surface-box` class for child cards and citations across all modules in both light and dark themes.

#### Changed
- `apps/web/app/globals.css`: Eliminated neon emerald halos, cyber cyan/indigo gradients, and glowing card borders; replaced futuristic ambient orbs with warm organic forest illumination; refined buttons, tabs, tables, inputs, and modals with true light-mode tokens.
- `apps/web/app/components/Header.tsx`: Replaced fixed green SVG emblem with dynamic `currentColor` rendering (restrained brass in dark mode, crisp clean white in light mode within deep forest badge).
- `apps/web/app/components/DocumentUploader.tsx`: Removed glowing cyan dropzone ring; updated to deep forest and soft sage styling.
- `apps/web/app/components/AgentStreamVisualizer.tsx`: Converted dark hardcoded terminal window to semantic `var(--bg-terminal)` and replaced neon progress bars with forest green and brass.
- `apps/web/app/components/ForensicStoryteller.tsx`: Converted hardcoded dark backgrounds (`rgba(3, 7, 18, 0.7)`) to semantic tokens, resolving black-on-black contrast bugs in light mode.
- `apps/web/app/components/modules/billnyay/AuditResults.tsx`: Converted progress bars to semantic emerald/terracotta tokens and eliminated dark glass leaks.
- `apps/mobile/src/theme/colors.ts` & `apps/mobile/src/screens/HomeScreen.tsx`: Replaced neon colors with Sovereign Editorial tokens (`brandForest`, `brandBrass`, `brandSage`, `statusDanger`).

### Sovereign UI/UX Transformation & Cinematic Scroll Storytelling (2026-10-20)

#### Added
- Stitch MCP design system `ArogyaRakshak Sovereign Health Glass` (`assets/14841168233921936765`) and screen `906bc2f99ad24ea595765a574f7df11e` (*ArogyaRakshak — Sovereign Healthcare Intelligence Landing & Storytelling Experience*).
- `apps/web/app/components/ForensicStoryteller.tsx`: 4-Phase Cinematic Forensic Lifecycle narrative (*Raw Chaos* → *Translucent Lens* → *Benchmark Sync* → *Statutory Remedy*).
- Master Interactive Adjudication Console with multi-scenario switching (Scenarios A, B, C), live line-item discrepancy waterfall, statutory citation box, and recoverable clawback total banners.
- Statutory Foundations & Telemetry Bento Grid: Section 45 Incontestability Rule, MCI/FRCS Clinical Governance Council, IRDAI 2024 1-Hour Cashless Decision Rule, and DawaCheck 85% Jan Aushadhi generic arbitrage.
- Desktop pointer-responsive dynamic specular lighting (`--pointer-x`, `--pointer-y`) on `.interactive-specular` and `.glass-specular` surfaces.
- Visual Discrepancy Waterfall & Benchmark Gauge in `apps/web/app/components/modules/billnyay/AuditResults.tsx`.
- 4-Stage forensic narrative summary chips and statutory precedent tags in `apps/mobile/src/screens/HomeScreen.tsx`.
- Production-grade multi-layer auroral ambient canvas (`.living-bg-container`) and Devanagari ambient watermark (`आरोग्यम् परमं भाग्यम्`).

#### Changed
- `apps/web/app/page.tsx`: Elevated hero section with editorial typography, statutory enclave badge, verified stat micro-grid, and smooth intake scroll link.
- `apps/web/app/components/Header.tsx`: glowing emerald shield emblem, live pulse indicator, quick reviewer console chip, and trilingual language switcher.
- `apps/web/app/components/DocumentUploader.tsx`: radar pulse scanner card, supported format tags (PDF, Devanagari OCR, Max 60MB), and specular border styling.
- `apps/web/app/components/AgentStreamVisualizer.tsx`: glowing terminal log pane, stage micro-badges, and live progress bar.
- `apps/web/app/components/ModuleTabs.tsx`: statutory authority pills (`CGHS`, `Pre-Auth`, `IRDAI`, `PMJAY`, `NPPA`) and glass tab pills.
- `apps/mobile/src/theme/colors.ts` & `Card.tsx`: dark Stitch obsidian palette (`#030712`), elevated card borders, and layered elevation shadows.

### Codebase restructuring and module modularization (2026-10-19)

#### Added
- Modular route packages composing sub-routers: `apps/api/app/api/v1/endpoints/kadi/` (`abdm`, `cases`, `insights`, `loaders`, `resolution`, `schemas`), `clinical_review/` (`registry`, `reviewer`, `case_holder`, `schemas`), and `daavisetu/` (`claims`, `readiness`).
- `apps/api/app/services/billnyay_llm.py` (Groq client adapter and deterministic fallback letters) and `services/billnyay_appeal.py` (appeal/grievance orchestration, signed-PDF generation, and appeal record lookup).
- `apps/api/app/models/` package organizing ORM models by owning domain (`kadi`, `clinical_review`, `billnyay`, `bimanyay`, `daavisetu`, `dawacheck`, `schemesetu`, `safety`, `transcription`), all re-exported by `__init__.py`.
- Modularized Web components: `apps/web/app/clinical-review/components/` (workspace tabs and panels), `components/modules/billnyay/`, `components/modules/bimanyay/`, `components/ModuleTabs.tsx`, and `hooks/useCaseSession.ts`.
- Modularized Mobile components: `apps/mobile/src/screens/camera/` (`styles`, `useScanUpload`, `ScanOverlays`, `PermissionGate`), `screens/billnyay/`, and domain types package in `src/api/types/`.
- Single API base constant across web client: `apps/web/app/lib/apiBase.ts`.
- Restructuring audit report: `docs/architecture/restructuring-2026-10.md`.

#### Changed
- `apps/api/app/clinical/service.py`: streamlined into a thin facade over focused internal services (`case_reviews`, `reviewer_reviews`, `statements`, `facts`, `review_common`).
- Thin HTTP routes: `apps/api/app/api/v1/endpoints/billnyay.py` reduced from 743 to 233 lines by delegating business logic to `app.services`.
- Large production files: all routing, model, and screen files > 500 lines broken down into cohesive units; only 7 files remain > 500 lines (static translation dictionaries, CSS styles, and cohesive domain engines).

#### Removed
- Dead code: removed unwired `packages/kadi/kadi/vector_store.py` (`KadiVectorStore`), unused `apps/mobile/src/hooks/index.ts` barrel, uncalled `document_jobs.job_view`, and unused `httpx` runtime dependency in `apps/api/requirements.txt`.
- Purged 19 unused imports and variables across production modules.

#### Fixed
- Fixed SQLite test fixture isolation in `apps/api/tests/conftest.py` ensuring database file persistence across sessions and preventing premature deletion during async request teardown (commit `3e154d7`).

### Engineering foundation pass (2026-10-19, ADR-018 – ADR-021)

#### Added
- `apps/api/app/services/` application layer and `.importlinter` architecture contracts, run in CI (`lint-imports`) and backed by `test_architecture.py` (ADR-018).
- Alembic migrations (`apps/api/alembic.ini`, `migrations/`), `SCHEMA_MANAGEMENT=migrate|none|create_all`, automatic adoption of databases created by the old `create_all` start-up (ADR-020).
- `kadi_document_jobs`: persisted document processing state; jobs in flight at a restart become `interrupted` and the progress stream tells the user to re-upload (ADR-019).
- `/health/live` and `/health/ready`; `X-Request-ID` on every response; `LOG_FORMAT=json`; hardening headers (`nosniff`, `DENY`, `no-referrer`, `no-store`, CORP).
- OpenAPI contract snapshot (`docs/api/openapi.json`, `scripts/export_openapi.py`, `test_openapi_contract.py`).
- `infrastructure/kubernetes/` (kustomize, single-replica API, hardened pods) with policy tests in `tests/infrastructure/` (ADR-021). Not deployed anywhere.
- `.github/workflows/security.yml`: gitleaks, pip-audit, npm audit, Trivy image report and CycloneDX SBOM.

#### Changed
- `APP_ENV=production` now refuses to start with the default/short signing secret, default database credentials, wildcard CORS, `create_all` or demo mode; `/docs` and `/redoc` are off in production.
- FastAPI 0.115.12 → 0.148.0, Starlette → 1.9.0 (pinned), python-multipart 0.0.12 → 0.0.32, Next.js 16.3.4 → 16.4.2; known advisories on the API and web production dependencies cleared.
- API and web images are multi-stage; uvicorn access log disabled in favour of route-template access logs; compose web bound to 127.0.0.1.
- CI: least-privilege permissions; Alembic upgrade + `alembic check` and a migration round trip on PostgreSQL 16; kustomize render.

#### Fixed
- Logs no longer contain case ids from URLs, submitted validation values or uploaded file names.
- `scripts/evaluate_latency.py` had been reporting PASS with zero samples (every upload was a 401).
- Web image build copied the host's `node_modules` over the Linux install (missing `.dockerignore`).

### "Why am I seeing this?" explanation trail (2026-10-19, ADR-017)

#### Added
- **Deterministic explanation per finding** — `kadi.explanation.Explanation` (evidence + provenance class, exact rule/reference row, trust state, what could not be determined, derived `not_recorded`), built by the owning package next to each decision: `dawacheck.explain`, `billnyay.explain`, `daavisetu.readiness.explain_item`, `bimanyay.tracker`. No LLM call.
- Additive `explanation` field on BillNyay `audit_items[]`, DawaCheck case medicines and manual `/benchmark`, DaaviSetu readiness `items[]` and BimaNyay `timeline_events[]`; same per-case authorization as the findings (ADR-009). Existing fields unchanged.
- Web: collapsed, accessible `ExplainTrail` disclosure under each finding (en; hi/mr labels flagged `NEEDS NATIVE-SPEAKER QA`). Mobile: plain-text `ExplainToggle` on BillNyay lines, case medicines and BimaNyay deadlines.
- `kadi.clinical_review.medicine_trust.name_provenance_class`; DaaviSetu readiness evidence now carries the source document name when recorded.
- Tests: per-builder (incl. the "not recorded" paths), API (`test_explanations_api.py`), web and mobile.

#### Changed
- BillNyay audit: explanations reuse the existing `_match_cghs_key` (no matching change).

### Read-aloud and simple language (2026-10-19)

#### Added
- **On-device read-aloud (ADR-016).** "Listen" / "Stop" on four result summaries (BimaNyay deadlines and appeal, DaaviSetu document check, DawaCheck price result) in English, Hindi and Marathi. Uses only the browser's `speechSynthesis` with voices that report `localService === true`; where no on-device voice exists (common for Marathi) the buttons are replaced by an honest message instead of falling back to a cloud voice. No speech recognition, no third-party TTS, nothing leaves the device. Playback never starts by itself.
- **Simple language** switch: short plain-sentence variant of the same summaries, from curated static strings (no LLM, no runtime translation). Hindi/Marathi strings are flagged `NEEDS NATIVE-SPEAKER QA`.
- `apps/web/app/lib/{speech,listenCopy,listenSummaries}.ts`, `hooks/useListen.ts`, `components/{ListenSummary,SimpleLanguageToggle}.tsx`, `tests/listen.test.ts` (23 tests), `docs/development/accessibility-read-aloud.md`.
- Not verified: actual audio output with a real local voice.

### Claim Pack (2026-10-19)

#### Added
- **Claim Pack (ADR-015)** — `GET /api/v1/kadi/cases/{case_id}/claim-pack`: one in-memory ZIP with a cover sheet, the DaaviSetu documentation checklist, the BimaNyay deadline timeline, the BillNyay audit and appeal draft (only if they exist), DawaCheck rows, the pre-auth form (only if submitted) and a manifest of what is and is not included with provenance classes. Missing parts say "Not available for this case". Web: `ClaimPackPanel` with the optional browser-side password protection from ADR-014. Mobile: not added.

### Phase-4 evaluation harnesses (2026-10-19)

#### Added
- **Evaluation harnesses** (`apps/api/app/evaluation/`, run with `scripts/evaluate_phase4.py`, offline, no Groq key): BMA (bill line → CGHS key), PEA (procedure extraction), billing-anomaly precision/recall/F1, CRMA (claim-rejection mapping), OCR WER/CER utility, DawaCheck price-mapping accuracy.
- Six **SYNTHETIC**, hand-written labelled datasets in `data/evaluation/` (the loader rejects any file not flagged synthetic) and 24 tests with hand-computed expected values.
- `docs/evaluation/phase4-harnesses.md` — measured results, including failures, and limitations. Numbers are development-set figures, not real-world accuracy.

#### Changed
- `billnyay` endpoint: extracted `_match_cghs_key` and the pure `audit_billing_lines` (no behaviour change) so the harness scores production logic.

### Mobile Expo SDK pin (2026-10-15)

#### Fixed
- `apps/mobile`: reverted the accidental `expo ~57` bump from dependabot commit fe4b773 back to SDK 52 (`npm ci` and `npm ls` were failing/invalid; dependabot PR #148 failed mobile CI). The postcss security bump is kept through an `overrides` entry.

### Independent-task pass (2026-10-15)

#### Added
- **Client-side password protection for DaaviSetu downloads (#101, ADR-014)** — optional AES-256-GCM (PBKDF2-SHA256) encryption in the browser; `.arenc` files unlock in the same panel. The password never leaves the device.
- **Mobile SLA reminder planner** (`apps/mobile/src/services/slaReminders.ts`) with tests; delivery via `expo-notifications` is not wired (see `docs/development/mobile-sla-reminders.md`).
- **`docker-compose.demo.yml`** and `docs/development/deployment.md` — local demo deployment (ADR-013, #40).
- Scenario E in `scripts/demo_runtime_smoke.py` (58/58 on SQLite).
- Appeal PDFs carry a quiet provenance footer (page number; states it is not a digital signature certificate).

#### Changed
- `DOCUMENT_SIGNING_SECRET` documented in `.env.example` and the environment reference.

### Diabetes admission demo scenario (2026-09-30)

#### Added
- **Demo Scenario E — diabetes admission, documentation readiness (paperwork only).** A synthetic admission note (`demo/documents/E_diabetes_admission_note.txt`) runs through the real upload pipeline, then DaaviSetu's readiness check with a second demo playbook ("Diabetes-related admission — documentation checklist (demo)": HbA1c report, blood glucose report, renal function report, diabetes treatment history as a doctor-confirmed clinical fact). The note deliberately omits the renal function report so the output names one missing document. No clinical value is interpreted and no approval is predicted. The playbook wording is illustrative and unsourced; it needs clinical-lead review before being presented as realistic.
- `POST /kadi/clinical-demo/scenarios/{A-E}`; the demo seed returns `diabetes_playbook_id` beside `playbook_id`.
- Scenario script `demo/scenarios/E_diabetes_admission_readiness.md`; test `test_scenario_e_diabetes_admission_readiness_with_one_missing_document`.

#### Changed
- Web: Demo controls list the Scenario E playbook ID after a reset; loading Scenario E opens the DaaviSetu tab.

### Release-candidate pass (2026-09-27)

#### Fixed — correctness
- **DawaCheck price basis (ADR-012)**: strip/pack/line totals were compared with per-tablet NPPA ceilings ("Dolo 650: ₹33" → +1,335%). Prices are now resolved to a per-unit price from a declared basis, the bill line ("Strip of 15", "15's", "Qty 10") or a "Rate per tablet" heading — or reported as **Cannot compare reliably** with no percentage. Dosage-form mismatches and contradictions are refused. LLM-normalised medicine names keep their source line's quantity facts (Kadi grounding).
- **BillNyay rate basis (ADR-012)**: per-day/visit/session/shift/bottle CGHS rates were compared with whole line totals (Scenario A's "Room Rent 3 days" showed +200%). Recurring rates now need a stated count; lines without one are not benchmarked, with the reason.
- **Postgres-only 500**: requesting a doctor's fact confirmation (DaaviSetu, Scenario B) violated a foreign key on Postgres (fact rows flushed before their review). Fixed; the SQLite test engine now enforces foreign keys so this class of bug fails in tests.
- The web file picker hid `.txt`/`.csv`, which the API accepts (demo documents could not be chosen).

#### Added
- Demo kit controls: `GET /kadi/clinical-demo/status`, `POST .../reset`, `POST .../scenarios/{A-D}`; web DEMO MODE banner, "What is simulated?" panel, Demo controls (reset, load scenario, one-time persona credentials). Scenario A loads the bill and the discharge summary into one case.
- `APP_ENV` (the API refuses to start with `CLINICAL_DEMO_MODE=true` under `production`) and `DEMO_DOCUMENTS_DIR`; the API image ships the synthetic demo documents.
- Case timeline (`GET /kadi/cases/{id}/timeline`, `kadi.timeline`, web "What has happened to this case") built only from persisted records.
- "Add another document to this case" on the web.
- `scripts/demo_runtime_smoke.py` — Scenarios A–D over HTTP (49 checks); passed on PostgreSQL 16 and on the full docker-compose stack.
- Tests: price basis (package, pipeline, web, mobile), rate basis, demo control (guards, idempotency, concurrent resets), timeline, review transitions (duplicate accept/finalize, reviewer swap, one person as both readers, duplicate ingest), FK enforcement guard.

#### Changed — honesty and UX
- Removed invented example figures (BillNyay totals that did not add up; DawaCheck pack prices with per-pack "ceilings"; a green "✓" DaaviSetu example).
- "PROD" / "v1.0 Production" branding → "PROTOTYPE" / "Release candidate (academic prototype)"; "DPDP Act 2023 Compliant" → design intent; "nothing is stored" / "zero data retained after the session" corrected (extracted details and a redacted excerpt are kept until deletion or the 90-day TTL).
- BillNyay no longer calls CGHS rates a "mandated cap" or cites Supreme Court violations; verdicts read "Above / Within CGHS reference".
- Raw enums/IDs removed from remaining UI paths (fact decisions, confirmation requests, SLA tiers, statement status, DaaviSetu status, case id in the processing header).
- Mobile quick samples declare what their price buys; the manual form requires a basis. Dead `USE_MOCK_DATA` flag removed.
- hi/mr replacements for corrected strings are marked `NEEDS NATIVE-SPEAKER QA`.

### Added
- Human clinical review, safety governance and human OCR resolution layer (ADR-011, `docs/architecture/clinical-review.md`): attributable clinical statements with mandatory conflict-of-interest disclosure and honest verification status; institution-private DaaviSetu preauth readiness playbooks; bounded BillNyay clinical plausibility review; versioned, independently approved clinical safety escalation rules; blind two-reader transcription of uncertain OCR medication text; provenance classes (`AI_DERIVED`, `HUMAN_REVIEWED`, `HUMAN_AUTHORED`, `EXTERNAL_SOURCE`, `PATIENT_PROVIDED`); web reviewer workspace at `/clinical-review`; mobile patient-side cards.

### Fixed (ADR-011 audit)
- OCR transcription tasks no longer flood on letterheads/"Rx"/"Tab.", never forward prescriber names, link only by whole tokens to one medicine, and apply a reading by replacing only the uncertain token.
- A withdrawn, superseded or cancelled clinician statement is removed from the stored signed appeal PDF.
- The insurer-facing appeal PDF no longer carries a "no clinician statement" notice; that notice is patient-facing only.
- Plausibility no longer treats room/nursing lines as interventions and discloses billed items it did not assess.
- Safety rules now check each document's full text at upload; readiness discloses its 1,000-character search scope.
- Only independently verified reviewers are listed publicly; others are assigned by shared ID. Demo reviewers are locked out outside demo mode.
- Safety-rule approvals are tied to a submission round.
- Safety-check failures are shown explicitly. Mobile DaaviSetu now receives its scanned case; mobile screens wait for processing before reading it.

### Fixed (second ADR-011 audit)
- The per-document OCR task cap now counts linked tasks only; letterhead noise at the top of a page could previously use it up so the medicine lines were never flagged.
- A whole uncertain OCR line naming a medicine (e.g. "Tab Augmntn 625mg 1-0-1") now links to that medicine; a leading "Tab."/"Cap." no longer prevents a human reading from being applied.
- A human reading that cannot be placed into the extracted entry is recorded as `NOT_APPLIED`; DawaCheck no longer falls back to benchmarking the uncertain OCR text, and a later partial reading cannot clear that state (a whole-entry flag can).
- A red flag found in a document's full text is no longer lost when the safety rule is re-versioned; it carries forward to the active version while that version still lists the term.
- Plausibility coverage is PARTIAL (not FULL) when a diagnosis could not be assessed.
- Reviewer-facing review responses no longer include the patient's case id.

### Added (demo-hardening pass, 2026-09-27)
- One medicine trust gate (`kadi.clinical_review.medicine_trust`) used by DawaCheck and reviewer evidence; DawaCheck rows carry `trust` (state, label, reasons).
- Uncertain OCR readings that cannot be linked to exactly one medicine are no longer dropped: the medicine(s) they may concern are held back as `ocr_uncertainty` (`AMBIGUOUS`, `POSSIBLE_MATCH`, `OVER_CAP`, `UNGROUNDED`) and are not benchmarked until a whole-entry human reading settles them.
- Deterministic demo kit (`demo/`): synthetic documents, Scenarios A–D with expected output, and a demo-mode-only OCR replay for the Scenario C prescription image (`app/clinical/demo_ocr.py`). Each scenario is an automated test.
- Web DawaCheck shows the case's own medicines with their trust decision and an "Ask for a human reading" action.
- Mobile: processing lifecycle state machine (`services/caseProcessing.ts`) with a 90 s inactivity timeout ("Processing is taking longer than expected." + "Refresh status"), shared active case across tabs, case-medicines card.
- SSE stream emits `idle` at once when nothing is being processed for the case.

### Fixed (demo-hardening pass, 2026-09-27)
- Readings linking to no medicine, to several medicines, or beyond the task cap let the medicine be benchmarked as `AI_DERIVED`; LLM-normalised names ("Amoxycilin" → "Amoxicillin") lost the OCR uncertainty.
- A human reading of only a marker could produce names like "Tab. 40"; results that name no drug are now refused.
- An agreed transcription of a whole uncertain line that is exactly the entry ("Tab Augmntn 625mg 1-0-1 x 5 days") was always `NOT_APPLIED`; it is now placed. A later whole-entry reading overrides an earlier escalation only if it is later; partial readings never clear held-back states.
- Entity resolution auto-merged combination products into their base drug ("Pan-D" into "Pan 40"); a one-sided variant letter is now a conflict for medicines (evaluation unchanged: 0 false merges).
- Plausibility returned PLAUSIBLE when one intervention matched and another is expected for an undocumented diagnosis; now CLINICAL_REVIEW_RECOMMENDED with `conflicting_items`. More administrative lines are excluded; the summary says unassessed diagnoses are not treated as compatible.
- A failing safety evaluation surfaces as `status: UNAVAILABLE` ("Safety check unavailable"), never as "no rules active"; plausibility survives it and recommends review.
- One board member could retire a safety rule alone; retirement is now request + independent confirmation.
- Mobile screens read the case before processing was established (first-render race), BillNyay audited straight after the upload 202, a stale response could overwrite newer state, and tabs did not share the scanned case (DaaviSetu was unreachable for a scanned bill).
- Web module views computed on a half-built case during processing; a dropped/silent stream showed nothing.
- "Judge-Approved Draft" (an automated scorer) relabelled "Passed automated quality check" (web + mobile; Hindi/Marathi rewording needs native-speaker QA). "Audit Completed" after extraction relabelled "Extraction complete".

### Changed
- BillNyay appeals now append finalized clinician statements verbatim (or state that none exists); the Barrister prompt forbids implying a clinician's opinion; the offline appeal template no longer asserts that physician records prove necessity.
- Kadi OCR now returns EasyOCR per-segment confidence; low-confidence readings become human transcription tasks.
- DawaCheck no longer benchmarks a medicine whose uncertain reading is unresolved.

### Added (earlier)
- Comprehensive repository-wide documentation overhaul, including structured `/docs` architecture, ADRs, and contributor manuals.
- Scoped AI coding agent manuals (`AGENTS.md`, `apps/api/AGENTS.md`, `apps/web/AGENTS.md`, `packages/kadi/AGENTS.md`, `.github/AGENTS.md`).
- Architectural specification for `BimaNyay` (insurance claim denial dispute analysis & IRDAI 3-tier grievance escalation engine).
- Architectural roadmap for cross-platform mobile application (`apps/mobile`) in React Native / Expo.
- Dedicated GitHub issue templates (Bug Report, Feature Request) and PR Template.
- Open-source governance files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `.gitattributes`).

### Changed
- **SchemeSetu no longer decides eligibility from income thresholds.** The PMJAY ₹2,50,000 and MJPJAY ₹1,50,000 limits were unverified heuristics; the official sources now cited in `packages/schemesetu/schemesetu/thresholds.py` (PIB releases 2116209 and 2053883; Government of Maharashtra restatements of the GR dated 28 July 2023) define no income ceiling. Income is reported as non-determinative, PMJAY is reported `ambiguous` with verification steps, MJPJAY follows state of residence, and every result cites its sources.
- **API:** `SchemeResult.confidence_score` removed; `non_determinative_factors`, `criteria_provenance` and `sources` added. The income-profile trigger now returns `FIRE` | `NO_CHANGE` | `INSUFFICIENT_EVIDENCE` with `schemes_applicable`, `newly_applicable` and `income_role` (replacing `NO_THRESHOLD_CROSSED`, `*_within_threshold` and `threshold_provenance`). Web and mobile clients render `ambiguous` as "Verification needed" instead of "Not Eligible".

### Removed
- `packages/schemesetu/schemesetu/embeddings.py` (`OfflineEmbedder`): an unwired scaffold that nothing imported. Its fallback built vectors from Python's per-process-salted `hash()`, so they were not reproducible. Domain modules may not ship their own embedding layer; cross-lingual embeddings belong to Kadi's optional IndicSBERT signal (`kadi/resolution/semantic.py`, ADR-006).

---

## [0.2.0] - 2026-08-20

### Added
- **Phase 1 Foundations**:
  - Implemented Kadi core extraction engine (`packages/kadi/kadi/extraction.py`) and vector store indexer (`packages/kadi/kadi/vector_store.py`).
  - Added shared OCR parser (`packages/kadi/kadi/ocr/ocr_parser.py`).
  - Integrated SchemeSetu rule-based eligibility agent (`packages/schemesetu/schemesetu/agent.py`). *(Corrected: this entry originally claimed a RAG agent and an ONNX embedding fallback. Neither existed — `embeddings.py` was an unwired SentenceTransformer scaffold with no ONNX code, since removed.)*
  - Implemented DawaCheck NPPA Schedule-I ceiling price benchmarking (`packages/dawacheck/dawacheck/checker.py`).
  - Implemented DaaviSetu cashless pre-authorization form generator (`packages/daavisetu/daavisetu/generator.py`).
  - Built BillNyay 5-agent auditing chain (`auditor.py`, `clinician.py`, `regulatory.py`, `barrister.py`, `judge.py`).
  - Added real-time Server-Sent Events (SSE) patient document processing status stream (`/api/v1/kadi/cases/{case_id}/stream`).
  - Implemented PostgreSQL database models with pgvector support (`apps/api/app/models.py`).
  - Ingested raw datasets under `data/raw` (CGHS rate PDFs, handwritten prescriptions, invoice OCRs, synthetic claims).
- **CI / Testing**:
  - Configured GitHub Actions CI workflow running PostgreSQL 16 + pgvector (`.github/workflows/ci.yml`).
  - Added unit test suites across all packages and API endpoints (`test_api.py`, `test_agents.py`, `test_ocr.py`, `test_schemesetu.py`, `test_dawacheck.py`, `test_daavisetu.py`).

### Fixed
- Added missing test and serialization dependencies (`httpx`, `aiosqlite`, `python-multipart`) to ensure seamless CI execution.

---

## [0.1.0] - 2026-07-15

### Added
- Initial monorepo scaffolding (`apps/api`, `apps/web`, `packages/kadi`, `packages/billnyay`, `packages/schemesetu`, `packages/dawacheck`, `packages/daavisetu`).
- Docker Compose configuration for multi-container development (PostgreSQL + pgvector, FastAPI, Next.js).
- Technical documentation, SPPU project brief, and atomized task backlog in `docs/`.
