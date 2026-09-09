# ArogyaRakshak — Research Contribution Note
*Prepared to support IndiaAI Fellowship nomination*

---

## Context

ArogyaRakshak — patient-facing healthcare billing, government scheme eligibility, and medicine pricing transparency platform. Full technical scope in `ArogyaRakshak_Technical_Documentation.md`. This note isolates the one component of the build that constitutes a genuine research contribution, for fellowship framing purposes — it does not change project scope.

## The Research Question

**Does combining phonetic transliteration matching with cross-lingual semantic embeddings improve entity resolution accuracy over either signal alone, for trilingual (English/Hindi/Marathi) medical billing and prescription documents?**

This sits inside Kadi, ArogyaRakshak's shared context layer (Technical Documentation §4.3) — already committed, already scoped, not new work being added for the sake of the application.

## Why This Is a Genuine Gap, Not Just an Engineering Task

- **IndicXlit** (AI4Bharat) solves same-word-different-script matching well — brand names, proper nouns (क्रोसिन ↔ Crocin).
- **IndicSBERT** (L3Cube) solves translated-concept matching well — बुखार ↔ Fever.
- No published system combines both specifically for **medical entity linking in a bill-auditing context**, where OCR noise, transliteration variance, and medical terminology synonymy all compound in the same pipeline. That combination — and whether it actually outperforms using either signal alone — is the open question.

## Evaluation Plan

1. Build the labeled entity-pair dataset already planned (Task Backlog, Phase 4) — pairs of entity mentions marked same/different across documents and scripts.
2. Ablation study: string-similarity-only vs. transliteration-only vs. embedding-only vs. combined confidence score.
3. Report precision, recall, and F1 for entity match/no-match classification across all four configurations.
4. The ablation comparison itself is the contribution — most systems in this space report one signal or the other, not a controlled comparison for this specific language and domain combination.

## What This Deliberately Does Not Change

- No new modules, no new infrastructure — this is Kadi's entity resolution pipeline, already in the technical documentation, evaluated and written up rather than just shipped.
- Keeps the fellowship application additive to the FYP timeline instead of competing with it.

---

## Application Checklist
*(per IndiaAI FutureSkills guidelines, verified July 2026 — reconfirm on the official portal before submitting, as dates and terms can shift year to year)*

- [ ] **Confirm PES Modern College of Engineering's nomination eligibility with Deepali Maam directly** — this is an institute-nominated fellowship, not an open individual application. Some guidance describes eligible institutes broadly, others specify top-NIRF-ranked engineering colleges — don't assume either way.
- [ ] Confirm personal eligibility: 80%+ aggregate through last completed semester, at least 3 completed AI-related courses
- [ ] Latest semester marksheet (PDF, 20KB–2MB)
- [ ] Endorsement letter — Project Guide
- [ ] Endorsement letter — Institute Head
- [ ] Passport-size photo (JPG/JPEG/PNG, 20KB–500KB)
- [ ] Track actual application window on the IndiaAI portal (fellowship.indiaai.gov.in) — typically opens Aug–Sep, closes Oct–Nov, results Jan–Feb, but confirm current-year dates directly rather than relying on last year's pattern
- [ ] Funding structure: ₹50,000 on meeting eligibility criteria, ₹50,000 more on submitting final-semester grades (min. 80%) plus a guide-endorsed project progress report — not a lump sum, budget accordingly
- [ ] Note: cannot be held alongside another central government fellowship/scholarship at the same time — shouldn't apply to you, but confirm it doesn't
