# Product evolution: final report (2026-11-25)

Branch `wave3/transformation`, base commit `4b37e4e`. **Merged to `main` on 2026-11-25 by PR #180.**

## A. Summary
The existing app now follows one path from an issue to a recorded outcome, requires sign-in, ships a
synthetic demo account, can send account email through Gmail once configured, and has English, Hindi
and Marathi web interfaces. Automated quality gates pass. It is not production-ready: translations are
unreviewed, no screen reader was used, email was never sent, and mobile is behind the web.

## B. Product
- Public promise and "Understand your healthcare. Know your next step." in the public copy.
- Result pages: situation, grouped findings, why it matters, next steps, editable draft, progress tracker.
- Tracker statuses are the person's own record; there is no "submitted" state. Pre-authorisation ends at "package ready".
- Mobile home screen: removed an invented "Active Dossier" with a rupee figure and unsupported claims.

## C. Localisation
- Every marked web string has a Hindi and a Marathi entry; a test fails on missing keys, changed placeholders or lost figures.
- **Machine translation, not reviewed.** Public pages and Settings say so.
- Mobile (added after the first version of this report): remaining screens, cards and messages
  translated, guarded by a scan test; checked in the Expo web export, not on a device.
- Still English: text sent by the API (errors, timeline events, rule explanations, safety disclaimers,
  price-basis phrases), document content and some official names. Details: `docs/localization.md`.
- All web routes are now rendered per request because the language comes from a cookie.

## D. Authentication
- Server-enforced, deny by default (ADR-029); cases open only for their owner; `?access_token=` removed.
- Old guest cases can only be claimed into an account.
- Judgement call to confirm: `/review` opens without a patient account because it needs a reviewer credential and shows nothing without one.
- Fixed: with the old default `CORS_ORIGINS=*`, nobody could sign in outside Docker. The default is now
  `http://localhost:3000`; production refuses an unset or wildcard list.

## E. Demo account
Aarav Sharma, `demo@arogyarakshak.in`, synthetic, labelled in the web app, demo mode only, refused in
production, password generated per run. Guide: `docs/DEMO_GUIDE.md`. The credentials generated for
testing were deleted.

## F. Accessibility
- axe-core: 168 page loads, 0 violations after fixes; no overflow at 320 to 1440 px; keyboard walk clean after fixes.
- **NVDA + Chrome: NOT TESTED** (not installed, no human listener). Mobile screen readers: NOT TESTED.
- Record and a script for a person: `docs/accessibility/audit-2026-11-25.md`.

## G. Resolution workflow
API, rules and web tracker done (ADR-031, `docs/features/action-and-resolution.md`). Missing: web fields
for evidence, next step and disputed amount; reminders; mobile tracker.

## H. Email
Gmail API transport implemented and tested with a fake client; **never run against Google**. You need a
dedicated mailbox, a Google Cloud OAuth client with `gmail.send`, a refresh token, and `MAIL_TRANSPORT`,
`GMAIL_SENDER`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`, `WEB_APP_BASE_URL`
(`docs/configuration/email-gmail.md`). Enter these yourself. Kubernetes manifests do not pass them yet.

## I. Business model
`docs/BUSINESS_MODEL.md`: a proposal with no market research and no payments in the product.

## J. Modified files
270 files before this report, listed at the end. The mobile localisation added `translations/tr.ts`,
`translations/ui.ts`, `tests/i18n.test.ts`, `tests/i18nScan.ts` and changed further mobile sources
(`git status` has the current list). New dependency: `expo-sharing ~13.0.1` (npm, mobile).

## K. Testing
| Check | Result |
|---|---|
| Backend `pytest`, PostgreSQL migration tests on | PASS 2,546, 8 skipped (docstring-only change afterwards) |
| Ruff gate, import contracts 6/6, guardrails, evaluation regression | PASS |
| PostgreSQL upgrade, drift check, downgrade; demo smoke | PASS; 60/60 |
| Web type-check, lint, tests, build, bundle budget | PASS, 343/343 |
| Mobile type-check, tests, Android export and budget | PASS, 226/226, 2.50 MB of 2.6 MB |
| Root tests, generated-copy check | PASS 79/79, 3/3 |
| Signed-in browser walk | PASS 13/13 |
| Static analysis | 0 errors (`docs/architecture/code-analysis/`) |
| NVDA, live Gmail, live Groq | NOT TESTED |
| Mobile on a device or emulator | NOT TESTED |
| GitHub CI, Docker image build, k6 load, Kubernetes apply | NOT RUN |
| Stitch visual comparison, native-speaker review | NOT DONE (need a person) |

First failures, fixed and rerun: 10 chaos tests (test client signed in during the simulated outage).
Security review was a self-review of the new authorisation, tracking and mail code plus a secret scan;
no independent reviewer.

## L. Risks
1. Breaking change: no guest use; third-party clients of the old token flow would break (none known).
2. Without Gmail configured, a forgotten password cannot be recovered.
3. A wrong Hindi or Marathi qualifier could make a result sound more certain than it is.
4. Screen-reader users: unverified.
5. About 1.3 KB headroom under the web bundle budget.
6. A very large single change set (about 290 files) is hard to review; consider splitting the pull request.

## M. Readiness
| Use | Verdict |
|---|---|
| Development | Ready |
| Supervised demo with synthetic data | Ready; say translations are unreviewed |
| Pull request | Ready to open when you ask; CI not yet run |
| Production | **Not ready**: items in C, F, H, L |

## Changed files (M modified, A added)

```text
M .env.example
M .gitignore
M .importlinter
M PROJECT_CONTEXT.md
M README.md
M apps/api/app/account_auth.py
M apps/api/app/api/v1/api.py
M apps/api/app/api/v1/endpoints/accounts.py
M apps/api/app/api/v1/endpoints/bimanyay.py
M apps/api/app/api/v1/endpoints/clinical_demo.py
M apps/api/app/api/v1/endpoints/kadi/__init__.py
A apps/api/app/api/v1/endpoints/kadi/actions.py
M apps/api/app/api/v1/endpoints/kadi/cases.py
A apps/api/app/auth_gate.py
M apps/api/app/case_auth.py
A apps/api/app/clinical/demo_account.py
M apps/api/app/clinical/demo_control.py
M apps/api/app/config.py
M apps/api/app/models/__init__.py
M apps/api/app/models/kadi.py
M apps/api/app/services/accounts.py
A apps/api/app/services/case_actions.py
M apps/api/app/services/case_purge.py
M apps/api/app/services/mail.py
A apps/api/app/services/mail_gmail.py
A apps/api/migrations/versions/0004_case_actions.py
M apps/api/tests/account_helpers.py
M apps/api/tests/auth_test_client.py
M apps/api/tests/clinical_helpers.py
M apps/api/tests/conftest.py
M apps/api/tests/test_account_hardening.py
M apps/api/tests/test_accounts.py
M apps/api/tests/test_api.py
M apps/api/tests/test_appeal_pdf_lifecycle.py
M apps/api/tests/test_bimanyay_case_lifecycle.py
A apps/api/tests/test_case_actions.py
M apps/api/tests/test_case_authorization.py
M apps/api/tests/test_case_deletion.py
M apps/api/tests/test_case_ownership.py
M apps/api/tests/test_case_retention.py
M apps/api/tests/test_claim_pack.py
M apps/api/tests/test_clinical_security.py
A apps/api/tests/test_demo_account.py
M apps/api/tests/test_demo_control.py
M apps/api/tests/test_event_loop_concurrency.py
A apps/api/tests/test_mail_gmail.py
A apps/api/tests/test_mandatory_sign_in.py
M apps/api/tests/test_platform_foundation.py
M apps/api/tests/test_rate_limiting.py
M apps/api/tests/test_sse_stream.py
M apps/mobile/App.tsx
M apps/mobile/package-lock.json
M apps/mobile/package.json
M apps/mobile/src/api/caseAuth.ts
M apps/mobile/src/api/client.ts
A apps/mobile/src/api/download.ts
M apps/mobile/src/api/endpoints.ts
A apps/mobile/src/api/session.ts
M apps/mobile/src/api/types/core.ts
M apps/mobile/src/components/Header.tsx
M apps/mobile/src/hooks/useLanguage.ts
M apps/mobile/src/hooks/useSSEStream.ts
M apps/mobile/src/screens/DaaviSetuScreen.tsx
M apps/mobile/src/screens/HomeScreen.tsx
A apps/mobile/src/screens/SignInScreen.tsx
M apps/mobile/src/screens/billnyay/AppealCard.tsx
A apps/mobile/src/services/languageStore.ts
A apps/mobile/src/services/secureValue.ts
M apps/mobile/src/shared/api-client/accounts.ts
M apps/mobile/src/shared/api-client/generated/schema.d.ts
M apps/mobile/src/translations/strings.ts
M apps/mobile/tests/api_client_delegation.test.ts
M apps/mobile/tests/billnyay_appeal_and_claim_package.test.ts
M apps/mobile/tests/case_auth.test.ts
M apps/mobile/tests/case_token_persistence_and_pdf_download.test.ts
M apps/mobile/tests/clinical_review.test.ts
A apps/mobile/tests/session.test.ts
M apps/web/AGENTS.md
M apps/web/app/about/page.tsx
M apps/web/app/app/case/page.tsx
M apps/web/app/app/case/reports/page.tsx
M apps/web/app/app/layout.tsx
M apps/web/app/app/page.tsx
M apps/web/app/app/settings/page.tsx
M apps/web/app/components/AgentStreamVisualizer.tsx
M apps/web/app/components/CaseTimeline.tsx
M apps/web/app/components/ClaimPackPanel.tsx
M apps/web/app/components/DocumentUploader.tsx
M apps/web/app/components/EntityResolutionReview.tsx
M apps/web/app/components/ModuleTabs.tsx
M apps/web/app/components/StatusPage.tsx
A apps/web/app/components/actions/ActionPlan.tsx
A apps/web/app/components/actions/ActionTracker.tsx
A apps/web/app/components/actions/LazyModulePlan.tsx
A apps/web/app/components/actions/ModulePlans.tsx
A apps/web/app/components/actions/actionLabels.ts
A apps/web/app/components/actions/actions.css
M apps/web/app/components/auth/AuthShared.tsx
M apps/web/app/components/auth/AuthSplit.tsx
A apps/web/app/components/auth/DemoAccountNote.tsx
M apps/web/app/components/auth/LoginForm.tsx
A apps/web/app/components/auth/RequireAccount.tsx
M apps/web/app/components/auth/authCopy.ts
M apps/web/app/components/clinical/AssignReviewer.tsx
M apps/web/app/components/clinical/Attribution.tsx
M apps/web/app/components/clinical/CaseMedicineTrustPanel.tsx
M apps/web/app/components/clinical/ClinicalReviewPanel.tsx
M apps/web/app/components/clinical/PreauthReadinessPanel.tsx
M apps/web/app/components/clinical/SafetyEscalationBanner.tsx
M apps/web/app/components/clinical/TranscriptionPanel.tsx
M apps/web/app/components/demo/DemoBanner.tsx
M apps/web/app/components/demo/DemoControls.tsx
M apps/web/app/components/landing/CaseJourney.tsx
M apps/web/app/components/landing/HeroIllustration.tsx
M apps/web/app/components/landing/LandingHero.tsx
M apps/web/app/components/landing/LandingSections.tsx
M apps/web/app/components/landing/ReferenceCoverage.tsx
M apps/web/app/components/landing/WorkedExample.tsx
M apps/web/app/components/modules/BillNyayView.tsx
M apps/web/app/components/modules/BimaNyayView.tsx
M apps/web/app/components/modules/DaaviSetuView.tsx
M apps/web/app/components/modules/DawaCheckView.tsx
M apps/web/app/components/modules/SchemeSetuView.tsx
M apps/web/app/components/modules/billnyay/AppealLetterCard.tsx
M apps/web/app/components/modules/billnyay/AuditResults.tsx
M apps/web/app/components/modules/billnyay/PlausibilityCard.tsx
M apps/web/app/components/modules/bimanyay/AppealDrafts.tsx
M apps/web/app/components/modules/bimanyay/ClinicalSection.tsx
M apps/web/app/components/modules/bimanyay/DisputeSummary.tsx
M apps/web/app/components/modules/bimanyay/SlaTimeline.tsx
M apps/web/app/components/modules/dawacheck/PriceBar.tsx
M apps/web/app/components/public/PublicLanguageNotice.tsx
M apps/web/app/components/public/PublicParts.tsx
M apps/web/app/components/public/copy/en.ts
M apps/web/app/components/public/copy/types.ts
M apps/web/app/components/public/public.css
M apps/web/app/components/public/publicCopy.ts
M apps/web/app/components/public/publicNav.ts
M apps/web/app/components/ui/Badges.tsx
M apps/web/app/components/ui/Charts.tsx
M apps/web/app/components/ui/CommandPalette.tsx
M apps/web/app/components/ui/States.tsx
M apps/web/app/components/ui/Steps.tsx
M apps/web/app/components/ui/Toast.tsx
M apps/web/app/components/ui/evidence.ts
M apps/web/app/components/workspace/CaseDesk.tsx
M apps/web/app/components/workspace/CaseOverview.tsx
M apps/web/app/components/workspace/DocumentsKept.tsx
M apps/web/app/components/workspace/EvidenceGraph.tsx
M apps/web/app/components/workspace/ModuleWorkspace.tsx
M apps/web/app/components/workspace/ReportsViewer.tsx
M apps/web/app/components/workspace/SettingsPage.tsx
M apps/web/app/components/workspace/caseCopy.ts
M apps/web/app/components/workspace/deskCopy.ts
M apps/web/app/components/workspace/settingsCopy.ts
M apps/web/app/components/workspace/workspaceFormat.ts
M apps/web/app/error.tsx
M apps/web/app/forgot-password/page.tsx
M apps/web/app/global-error.tsx
M apps/web/app/globals.css
M apps/web/app/help/page.tsx
M apps/web/app/hooks/useApi.ts
M apps/web/app/how-it-works/page.tsx
A apps/web/app/i18n/T.tsx
A apps/web/app/i18n/format.ts
A apps/web/app/i18n/load.ts
A apps/web/app/i18n/locales/hi.ts
A apps/web/app/i18n/locales/mr.ts
A apps/web/app/i18n/server.ts
A apps/web/app/i18n/useT.ts
M apps/web/app/layout.tsx
A apps/web/app/lib/actionPlan.ts
A apps/web/app/lib/actionsApi.ts
M apps/web/app/lib/apiClient.ts
M apps/web/app/lib/caseApi.ts
M apps/web/app/lib/caseStore.ts
M apps/web/app/lib/claimPack.ts
M apps/web/app/lib/clinical.ts
M apps/web/app/lib/dawacheck.ts
M apps/web/app/lib/demo.ts
M apps/web/app/lib/labels.ts
M apps/web/app/lib/packageCrypto.ts
M apps/web/app/lib/session.ts
M apps/web/app/login/page.tsx
M apps/web/app/not-found.tsx
M apps/web/app/page.tsx
M apps/web/app/platform/[module]/page.tsx
M apps/web/app/platform/page.tsx
M apps/web/app/register/page.tsx
M apps/web/app/reset-password/page.tsx
M apps/web/app/review/components/EvidencePanel.tsx
M apps/web/app/review/components/FactConfirmations.tsx
M apps/web/app/review/components/ReviewSummary.tsx
M apps/web/app/review/components/ReviewsTab.tsx
M apps/web/app/review/components/SafetyTab.tsx
M apps/web/app/review/components/SignInPanel.tsx
M apps/web/app/review/components/StatementEditor.tsx
M apps/web/app/review/components/TranscriptionTab.tsx
M apps/web/app/review/layout.tsx
M apps/web/app/review/page.tsx
M apps/web/app/review/types.ts
M apps/web/app/security/page.tsx
M apps/web/app/shared/api-client/accounts.ts
M apps/web/app/shared/api-client/generated/schema.d.ts
M apps/web/app/shell/AccountMenu.tsx
M apps/web/app/shell/ShellProvider.tsx
M apps/web/app/shell/SiteFooter.tsx
M apps/web/app/shell/SiteHeader.tsx
M apps/web/app/shell/shell.css
M apps/web/app/verify/page.tsx
A apps/web/scripts/i18n-keys.ts
A apps/web/tests/action_plan.test.ts
M apps/web/tests/clinical_review.test.ts
M apps/web/tests/demo_hardening.test.ts
A apps/web/tests/i18n.test.ts
M apps/web/tests/primitives.test.ts
M apps/web/tests/public_site.test.ts
M apps/web/tests/schemesetu_view.test.ts
M apps/web/tests/workspace.test.ts
M demo/README.md
M docker-compose.yml
A docs/BUSINESS_MODEL.md
A docs/DEMO_GUIDE.md
M docs/JUDGE_DEMO.md
M docs/README.md
A docs/accessibility/audit-2026-11-25.md
M docs/api/accounts.md
M docs/api/compatibility.md
M docs/api/openapi.json
M docs/api/overview.md
M docs/architecture/clinical-review.md
M docs/architecture/code-analysis/README.md
A docs/architecture/code-analysis/api/README.md
A docs/architecture/code-analysis/api/analysis/findings.json
A docs/architecture/code-analysis/api/analysis/module-graph.json
A docs/architecture/code-analysis/api/analysis/overview.json
A docs/architecture/code-analysis/api/analysis/review.json
M docs/architecture/code-analysis/kadi/analysis.previous/findings.json
M docs/architecture/code-analysis/kadi/analysis.previous/module-graph.json
M docs/architecture/code-analysis/kadi/analysis.previous/overview.json
M docs/architecture/code-analysis/kadi/analysis.previous/review.json
M docs/architecture/code-analysis/kadi/analysis/findings.json
M docs/architecture/code-analysis/kadi/analysis/module-graph.json
M docs/architecture/code-analysis/kadi/analysis/overview.json
M docs/architecture/code-analysis/kadi/analysis/review.json
A docs/architecture/decisions/ADR-029-mandatory-sign-in.md
A docs/architecture/decisions/ADR-030-gmail-account-email.md
A docs/architecture/decisions/ADR-031-action-and-resolution-records.md
M docs/architecture/service-catalog.md
A docs/configuration/email-gmail.md
M docs/configuration/environment-variables.md
M docs/development/deployment.md
M docs/development/troubleshooting.md
A docs/features/action-and-resolution.md
A docs/localization.md
A docs/superpowers/plans/2026-11-25-product-evolution.md
M docs/transformation/IMPLEMENTATION_STATUS.md
M packages/api-client/src/accounts.ts
M packages/api-client/src/generated/schema.d.ts
A packages/kadi/kadi/resolution_tracking.py
A packages/kadi/tests/test_resolution_tracking.py
A scripts/demo_account.py
M scripts/demo_runtime_smoke.py
M scripts/evaluate_latency.py
M tests/chaos/chaos_harness.py
M tests/infrastructure/test_load_and_supply_chain.py
M tests/load/case_create.js
M tests/load/lib.js
M tests/load/sse_stream.js
M tests/load/upload.js
```
