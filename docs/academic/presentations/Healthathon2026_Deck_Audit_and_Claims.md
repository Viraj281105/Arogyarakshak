# Health-a-thon 2026 Pitch Deck — Audit, Claims Ledger & Submission Safety Check

**Scope:** Round 1 submission for Health-a-thon 2026 — Track: **Diabetes Care** · Primary user: **Patient/Caregiver** · Use case: **Financial & Administrative Support** ("Insurance, schemes and paperwork made navigable — so cost does not block care.")

**Companion deck:** [`ArogyaRakshak_Healthathon2026_Pitch.pptx`](ArogyaRakshak_Healthathon2026_Pitch.pptx) / `.pdf`
**Audit date:** 2026-09-25 · **Repo commit context:** `viraj-dev`, working tree includes uncommitted ADR-011 clinical-review layer + SEC-01–14 remediation (see `PROJECT_CONTEXT.md` §2, §17)

---

## A. Audit of the existing deck (`ArogyaRakshak_FYP_Presentation.pptx`, 10 slides)

### A1. What's strong (preserve)
- **Visual identity is genuinely good and reusable.** Dark navy (`#0a0e17`)/teal-cyan (`#06b6d4`) system, icon-in-circle motif, card layouts — this *is* the same design language already shipped in `apps/web/app/globals.css` and `apps/mobile/src/theme/`. It reads as a real product, not a generic template. Reuse it, don't replace it.
- **Slide 4** ("From Discharge Documents to Action", UPLOAD→UNDERSTAND→STORE→ASSIST→ACT) is close to the exact workflow language the Health-a-thon brief wants — it just needs re-scoping to a document→evidence→pathway framing without the "STORE" vault step (ArogyaVault is a broader-platform concept not needed for this focused submission).
- **Slide 9** ("Designed for Transparency & Responsible Decision Support") already gestures at the right values (transparency, auditability, privacy, boundaries) — it's underdeveloped relative to what the codebase actually now supports (see B4 below), so it undersells the platform.
- Module-per-workflow framing (slide 3) with a plain-language question per module ("Is my hospital bill correct?" etc.) is effective and worth reusing verbatim for the modules that carry into this submission.

### B2/B3. What's weak / redundant
- 10 slides is 3–4 too many for a 6–8 slide Round-1 cap; several slides (5, 6, 7, 10) either repeat the same journey diagram in a different shape or spend a full slide on a UI vault concept (ArogyaVault) that isn't the differentiator for *this* track.
- Team slide lists 5 names (Viraj Jadhao, Anurag Pawar, Sanjali Paygude, Raj Janvekar, Arya Chandak) — this hackathon's registered core team is only three of those (Viraj, Sanjali, Anurag) plus a newly matched clinical lead. Carrying all 5 forward would misrepresent who is actually on this submission.
- Slide 9's "VALIDATION DIMENSIONS" (OCR accuracy, audit correctness, eligibility correctness, claim completeness…) lists metric *categories* with no numbers — reads as a placeholder rather than evidence. Better to show the real, already-built provenance/status vocabulary (see B4) than a metrics list with nothing behind it.

### C. What violates or risks violating Health-a-thon scope
1. **Slide 1 subtitle: "AI-Assisted Healthcare Decision Support Platform."** The word "Decision" next to "Healthcare" is exactly the ambiguity the brief flags. **Must not carry forward.**
2. **Slide 8 title: "From Documents to Decisions."** Same problem, sharper — "Decisions" is the one word the competition scope explicitly excludes for an assistive tool. **Must not carry forward.**
3. Neither slide is describing clinical decisions in practice (they're audit/eligibility/claim outputs), but a judge skimming titles alone would reasonably flag both. This is a wording risk, not a real functionality risk — the fix is textual, not architectural.
4. The codebase does now contain a genuine clinical-review layer (ADR-011: `packages/kadi/kadi/clinical_review/`, doctor statement attribution, safety escalation rules). **Decision made here:** the new deck does not name or feature this layer. It is real, but explaining it (doctor-authored clinical statements, safety escalation rules) would pull the story toward clinical territory this track explicitly excludes, even though the layer itself is designed to keep AI *out* of clinical authority. Where the deck draws on it, it uses only the general, already-shipped, non-clinical-sounding vocabulary — provenance labels (*Machine-derived / Human-reviewed / External source / Patient-provided*) and status vocabulary (*Present / Missing / Needs review*) — without naming "clinical review," "clinician statements," or "safety rules." This is disclosed here as a deliberate scoping choice, not an oversight.

### D–H. Redundant / preserve / delete / rewrite / missing (summary — see slide-by-slide map in §B for detail)
- **Delete:** ArogyaVault-as-a-slide (folded into one line on the solution slide instead), the separate architecture-diagram slide (too technical for a jury with limited time — the brief is explicit that architecture should support, not replace, the story), the roadmap slide's 3-column NOW/NEXT/FUTURE grid (compressed into slide 7's MVP+impact+future).
- **Preserve:** module question framing, dark/teal visual system, icon-circle motif, "boundaries" line from slide 3.
- **Rewrite:** both flagged headlines (C1–C2); the values slide, replaced by a real evidence-trust slide backed by actual code paths, not a metrics list.
- **Missing from the old deck entirely:** any explicit human-in-the-loop / AI-does-not-decide statement, any mention of a clinical lead, any concrete "what we will and won't claim" boundary list, any diabetes-specific framing at all (the old deck is platform-wide, not track-specific — expected, since it predates this hackathon).

### I. What can become a strong visual
- The **UPLOAD → UNDERSTAND → VERIFY → ACT** spine, used as the deck's one recurring structural device (title bar treatment on slides 3, 5, 7) rather than a single diagram on one slide.
- A **status-chip visual language** (small pill badges: green *Present/Verified*, amber *Needs review/Ambiguous*, grey *Missing*) reused consistently on the solution, product-experience and trust slides — this is not invented styling, it mirrors real UI states already implemented in `apps/web/app/components/modules/SchemeSetuView.tsx` (`ambiguous` → "Verification needed") and `packages/daavisetu/daavisetu/readiness.py` (`PRESENT` / `MISSING` / `NEEDS_CLINICAL_CONFIRMATION`).
- A compact **evidence chain** diagram: Source → Extracted evidence → Rule/criterion → Result → User action, which is a faithful visual translation of how SchemeSetu actually works (`criteria_provenance` + `sources` citations in `packages/schemesetu/schemesetu/agent.py`).

### J. Claims requiring verification
See §D "Claims Ledger" below — every factual/technical claim used in the new deck is listed there with its verification status.

---

## B. Slide-by-slide content map (new 7-slide deck)

| # | Slide | One job | Key visual |
|---|---|---|---|
| 1 | **The Hook** | Make the problem and the platform instantly legible | Patient/caregiver document-maze journey → UNDERSTAND/VERIFY/ACT |
| 2 | **The Problem** | Ground the administrative burden in real, cited numbers | Journey chain: visit → bill/docs → insurance → scheme → paperwork → missing doc → repeat visit |
| 3 | **The Solution** | Position "documents → action," not "documents → decisions" | UPLOAD→UNDERSTAND→VERIFY→ACT with real capabilities under each step |
| 4 | **Existing Foundation** | Show this builds on a real platform, focused for this track | 6 modules, 5 visually foregrounded, DawaCheck backgrounded, arrow into "this hackathon" |
| 5 | **Product Experience** | Make it feel like a real, usable product | Case Administrative Status mockup — clearly labeled prototype |
| 6 | **Trust / Human-in-the-loop** | Make the anti-fabrication philosophy visible, not just claimed | Can/Does-not columns + real provenance-label chips + clinical lead's actual role |
| 7 | **MVP, Impact, Future** | Show what's buildable now and what it leads to | 5-item MVP list, impact chain, closing line |

---

## C. Doctor / clinical lead

Per your instruction, nothing about the clinical lead exists anywhere in the repository, so I could not verify a name independently — I asked in chat rather than inventing one. **Status: name pending from you.** The deck currently uses the placeholder `[Clinical Lead – Doctor]` everywhere the name belongs (slide 1 team line, slide 6 role card) so it's a single find-and-replace once you send it. I have **not** invented a specialty, hospital, or credential anywhere — those fields are left blank/omitted rather than guessed, per your explicit instruction not to force the doctor into a role or credential that isn't confirmed.

---

## D. Claims Ledger — every factual/technical claim used in the deck

| # | Claim as used in deck | Slide | Status | Evidence |
|---|---|---|---|---|
| 1 | ~101 million people in India live with diabetes | 2 | **Verified — external source** | ICMR-INDIAB national study, published in *The Lancet Diabetes & Endocrinology*, 2023 (11.4% weighted prevalence across all 30 states/UTs) |
| 2 | Out-of-pocket spending is 43.4% of India's total health expenditure (₹2,767 per-capita, 2022–23) | 2 | **Verified — external source** | National Health Accounts Estimates for India 2022–23, Union Ministry of Health & Family Welfare (PIB release) |
| 3 | ArogyaRakshak already has 6 modules: Kadi, BillNyay, DaaviSetu, BimaNyay, SchemeSetu, DawaCheck | 4 | **Verified — repo** | `packages/{kadi,billnyay,daavisetu,bimanyay,schemesetu,dawacheck}`, `PROJECT_CONTEXT.md` §3, §7 |
| 4 | OCR + document intelligence exists (PDF via PyMuPDF, images via EasyOCR) | 3, 4 | **Verified — repo** | `packages/kadi/kadi/ocr/ocr_parser.py`; tested (`test_ocr.py`) |
| 5 | Structured entity extraction into a shared case context | 3 | **Verified — repo (partial reliability)** | `packages/kadi/kadi/extraction.py`, `kadi_cases`/`kadi_entities` models. Not claimed in the deck: extraction *accuracy* — the 2026-09-11 internal audit found the non-LLM regex fallback path (used whenever `GROQ_API_KEY` is unset) produces meaningfully wrong totals on some documents. The deck says "understands documents," not "understands them perfectly" — deliberately. |
| 6 | Bill auditing against CGHS benchmark rates | 3, 4, 7 | **Verified — repo** | `packages/billnyay/billnyay/agents/auditor.py`, `cghs_rates.json` (27 cited rates), `POST /api/v1/billnyay/cases/{id}/audit` |
| 7 | Pre-authorization / claim document preparation | 3, 4, 7 | **Verified — repo** | `packages/daavisetu/daavisetu/generator.py` (IRDAI Annexure-B PDF via ReportLab), `POST /api/v1/daavisetu/cases/{id}/claim` |
| 8 | Missing-document / readiness checklist (Present / Missing / Needs review) | 5, 6 | **Verified — repo** | `packages/daavisetu/daavisetu/readiness.py` — real `ItemStatus` enum (`PRESENT`, `MISSING`, `NEEDS_CLINICAL_CONFIRMATION`, …); explicit code comment: "does not predict, estimate or influence the insurer's decision" |
| 9 | Insurance denial analysis + multi-tier appeal drafting (GRO / Bima Bharosa / Ombudsman) | 3, 4, 7 | **Verified — repo** | `packages/bimanyay/bimanyay/` clause auditor, drafter, tracker; cites IRDAI Master Circular (29 May 2024) |
| 10 | Government scheme eligibility (PMJAY/MJPJAY) with cited official sources, "ambiguous" shown as "verification needed" rather than a false negative | 3, 5, 6 | **Verified — repo** | `packages/schemesetu/schemesetu/thresholds.py`, `agent.py` (`criteria_provenance`, `sources`, PIB citations); `apps/web/app/components/modules/SchemeSetuView.tsx` renders `ambiguous` as "Verification needed," never "Not Eligible" |
| 11 | Every output carries a provenance label: Machine-derived / Human-reviewed / Human-authored / External source / Patient-provided | 6 | **Verified — repo** | `apps/web/app/lib/clinical.ts` `PROVENANCE_LABELS`; documented in `CHANGELOG.md` "Unreleased" section. Used in the deck generically — not attributed to the clinical-review feature by name (see §A, item C4) |
| 12 | No persistent storage of uploaded documents (BYOD) | 6 | **Verified — repo** | ADR-003, `scripts/ci_guardrails.py` BYOD invariant scan, `AGENTS.md` §1 |
| 13 | AI does not diagnose, recommend treatment, or make clinical/insurance decisions | 6 | **Verified — repo, by design** | No diagnosis/treatment endpoint exists anywhere in `apps/api/app/api/v1/endpoints/`; every module's stated output is an audit/report/checklist/draft, never a decision. `daavisetu/readiness.py` and `schemesetu/agent.py` docstrings explicitly disclaim prediction of outcomes. |
| 14 | Clinical lead validates workflow assumptions, usability, administrative friction, human-review boundaries | 6 | **Proposed / role description, not yet an activity log** | Provided by you (brief §4); marked in the deck as the lead's intended role for this engagement, not a completed validation |
| 15 | Team: Viraj, Sanjali (Paygude), Anurag (Pawar) + clinical lead | 1, 6 | **Provided by you** | Brief §4; surnames carried from the existing deck's team slide, which you authored |
| 16 | Everything shown beyond the above (UI mockup numbers, sample document names, "2 documents missing" etc.) | 5 | **Fabricated for illustration, explicitly labeled** | Slide 5 carries a visible "Prototype — illustrative workflow" label per the brief's requirement (§8, §13) |

### Claims explicitly avoided (so their absence is a decision, not an oversight)
- No accuracy/performance percentages for OCR, audit correctness, or eligibility matching (none are measured — PROJECT_CONTEXT.md §2 discloses PEA/BMA/CFMA/CRMA/WER harnesses as "not yet built").
- No claim of deployment, real users, hospital partnerships, or funding.
- No claim that the clinical lead has already validated anything — only that this is their role going forward.
- No specialty/hospital/registration for the clinical lead (pending from you).
- No mention of FAISS, IndicXlit, or IndicSBERT as delivered capabilities (per your standing project memory: FAISS/IndicXlit are unwired scaffolds; IndicSBERT is optional and off by default).

---

## E. Submission safety audit

| Check | Result |
|---|---|
| Scope compliant (administrative/financial assistance, not clinical)? | **Pass** — every capability described is document/evidence/pathway/paperwork-facing; both scope-risk phrases from the old deck were removed |
| No diagnosis? | **Pass** — no diagnostic claim anywhere in the deck |
| No treatment recommendation? | **Pass** |
| No clinical decision support? | **Pass** — "AI does not decide for the patient" is stated explicitly on slide 3, and reinforced on slide 6's "does not" column |
| No clinical risk scoring? | **Pass** |
| No autonomous clinical advice? | **Pass** |
| Existing work declared (not presented as built-from-scratch for this hackathon)? | **Pass** — slide 4 exists specifically for this |
| Team information correct? | **Pending** — clinical lead's name not yet supplied; everything else matches your brief |
| 6–8 slides? | **Pass** — 7 slides |
| Under 25 MB? | **Pass** — PPTX 0.42 MB, PDF 0.45 MB |
| No fabricated claims? | **Pass, with one disclosed exception** — slide 5's UI mockup content (sample numbers/filenames) is fabricated *for illustration* and explicitly labeled as such, per the brief's own instruction that a necessary mockup must be clearly marked prototype/proposed |

---

## F. Final recommendation

**DO NOT SUBMIT YET** — one blocking item only: **the clinical lead's name** is a placeholder (`[Clinical Lead – Doctor]`) pending your confirmation. Everything else in the deck (content, scope-safety, claims, length) is submission-ready as of this audit. Once you send the name (and, if you want it, a designation/affiliation), it's a single text swap in two places and the deck is ready to submit.
