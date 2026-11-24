# ArogyaRakshak — Open Questions, Risks & Design-Engineering Trade-Offs

**Purpose:** Explicitly document every unresolved product decision, technical risk, and conflict between ideal UX ambitions and verified backend/privacy constraints so nothing is hidden or glossed over.

---

## 1. Resolved Design-vs-Engineering Conflicts (Explicit Rulings)

| Potential Conflict | Backend / Architectural Ground Truth | Explicit Ruling in This Blueprint |
|---|---|---|
| **"Document Vault" with original file preview & download** | **ADR-003 (BYOD Zero Document Retention):** Uploaded files are processed in RAM and immediately discarded. | **Do NOT build a Document Vault.** Build **Kadi Document Provenance Cards** showing filename, SHA-256 digest, extracted entities, confidence, and the PII-redacted 1,000-char excerpt. |
| **Longitudinal spending / multi-year savings dashboard** | **ADR-010:** Cases auto-purge after 90 days; no insurer/bank feed exists. | **Do NOT fabricate global savings.** Case Desk displays live case-scoped figures only, explicitly tagged `Estimate` vs `Verified`. |
| **GSAP / Lottie / Rive for rich animations** | Hard **170 KB gzip** per-route web bundle budget; `motion` 14.14.0 already installed and ESLint-confined. | **Use SVG + CSS + `motion` 14.14.0 + View Transitions.** Reject GSAP/Lottie/Rive to keep initial route payloads fast on Indian mobile networks. |
| **Raw Semantic Hexes (`#C28A35`, `#C4544F`, `#89918C`) for badge text on white** | WCAG 2.1 AA requires `>= 4.5:1` for normal text (`#C28A35` on white is ~3.0:1). | **Dual-role semantic tokens:** Use exact brand hexes for icons, borders, and chart fills; use darkened ink-grade shades (`#7A5312`, `#962F2B`, `#4E5651`) for badge text (`>= 6.5:1`). |
| **Secondary Text `#64766C` directly on Warm Ivory `#F4F1E8`** | `#64766C` passes AA (`4.8:1`) on White `#FFFFFF`, but dips to ~`4.3:1` on Warm Ivory `#F4F1E8`. | Use `#64766C` on White cards and `#56675E` (`5.2:1`) for small secondary text directly on Warm Ivory canvas. |
| **Insurer "Submitted / Approved" claim statuses** | DaaviSetu and BimaNyay do not integrate with insurer/TPA portals. | End workflows at **"Package Ready"** or **"Draft Prepared"** with clear user submission instructions. |

---

## 2. Open Product & Engineering Decisions Requiring Maintainer Sign-Off

| # | Open Question | Options & Trade-Offs | Recommended Default |
|---|---|---|---|
| **Q1** | **Outbound Email Provider (`MAIL_TRANSPORT`)** | `ADR-026` password reset & email verification are fully built in the API, but `MAIL_TRANSPORT=disabled` is the only shipped transport (adding SMTP/Resend/SES introduces a new outbound network boundary). | Keep honest *"Email delivery is not enabled in this deployment"* UI on `/forgot-password` & `/verify` until maintainer approves a specific mail provider ADR. |
| **Q2** | **Native-Speaker Hindi & Marathi QA** | Public site copy (`publicCopy.ts`), Wave 3 workspace copy, and BimaNyay HI/MR appeal templates are marked `UNREVIEWED: NEEDS NATIVE-SPEAKER QA`. | Gate full public Hindi/Marathi launch behind native-speaker sign-off; retain the honest *"English-only preview"* notice where translations are pending. |
| **Q3** | **Reference Dataset Expansion** | Currently 27 CGHS rows, 7 NPPA formulations, 5 law provisions, 2 welfare schemes (PM-JAY & MJPJAY), and empty `dispute_outcomes/`. | Keep exact reference counts dynamically bound via `referenceSnapshot.ts` and display clear scope disclaimers so users never assume exhaustive national coverage. |
| **Q4** | **Clinical Reviewer Verification Registry** | `UnavailableRegistryAdapter` means real reviewers cap at `Self-declared — not council-verified` (no NMC/State Medical Council API exists). | Maintain explicit `"Self-declared"` / `"Demo verification only"` badges in `/review` and Evidence Explorer; never imply council verification. |
| **Q5** | **Server-Side Notifications vs Case-Scoped Activity** | No push notification server or user-event inbox table exists in Postgres. | Implement the **Notifications & SLA Feed** as a live client aggregation of real case events (Kadi timeline, pending OCR transcriptions, clinical review updates, BimaNyay SLA deadlines) + local on-device reminders on Expo mobile. |
| **Q6** | **Wiring `kadi.retrieval` (BM25 Index)** | Wave 2 Stream B built a clean, tested in-memory per-case BM25 index (`packages/kadi/kadi/retrieval/`), not yet wired to a live API route. | Keep out of Milestone 1–6 critical path; revisit if a citation-only case search endpoint is added later. |

---

## 3. Technical & Operational Risks

| Risk | Severity | Mitigation |
|---|---|---|
| **Web Bundle Budget Creep (`> 170 KB gzip`)** from new SVG illustrations, Manrope font, or Workspace Sidebar | High | Keep all public pages pure Server Components; code-split `/app/case/evidence`, `/app/case/[module]`, and `ArogyaLogoAnimated` via `next/dynamic`; remove Fraunces & Plus Jakarta Sans once Manrope ships; gate every PR with `npm run check:web-budget`. |
| **Legacy `globals.css` Cascade Collisions** (~4,969 lines of legacy styles competing with new Deep Forest tokens) | Medium | Decompose `globals.css` incrementally by module during Milestones 2–5 and run `tests/tokens_adoption.test.ts` on every PR. |
| **Devanagari OCR Accuracy Unmeasured** (no reference WER/CER corpus yet) | Medium | Surface Wave 2 Stream A's `partial` / `pages_skipped` warnings prominently in `/app/case/kadi` and route low-confidence medicines through the mandatory Trust Gate. |
| **Doc-vs-Code Drift** (`README.md`, `PROJECT_CONTEXT.md`, `docker-compose.yml` still reference pre-ADR-026 no-accounts and removed FAISS) | Low | Schedule documentation cleanup in Milestone 7 so public repo docs match the verified codebase. |
