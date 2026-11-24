# ArogyaRakshak — Product Vision & Transformation Charter

**Status:** Approved Planning Blueprint (Pre-Implementation)  
**Target Release:** ArogyaRakshak Next-Generation Experience (Post-Wave 3 M3/M4)  
**Visual Identity:** ArogyaRakshak — Deep Forest / Warm Ivory (Light-First Sovereign Editorial)  
**Stitch Project Reference:** `projects/847521722700511340` (*ArogyaRakshak — Deep Forest / Warm Ivory Transformation*) · Design System `assets/8789632704855580659`

---

## 1. Executive Thesis

ArogyaRakshak (**आरोग्यरक्षक** — *Healthcare Protector*) is an **evidence-first healthcare intelligence and patient financial protection platform for India**. It exists for a high-stakes human moment: a family standing at a hospital billing desk, staring at an opaque ₹2,00,000 discharge bill, holding a puzzling insurance repudiation letter, or wondering whether a prescribed medicine costs ten times its regulated ceiling.

Conventional healthcare AI products fail Indian patients in four ways that ArogyaRakshak was architected to refuse:
1. **False certainty:** Turning low-confidence OCR or LLM guesses into unchallenged "facts."
2. **Unit-blind price math:** Comparing a 15-tablet strip price against a per-tablet NPPA ceiling to fabricate sensational overcharge percentages.
3. **Manufactured authority:** Displaying green "verified" badges or doctor-sounding appeal letters that no clinician ever reviewed.
4. **Silent data hoarding:** Retaining raw sensitive medical documents on disk indefinitely.

The **Complete Product Transformation** elevates ArogyaRakshak from an engineering-led academic release candidate into a **category-defining, deeply trustworthy, visually distinctive healthcare intelligence product** — without compromising a single backend invariant, privacy guarantee, or clinical-honesty rule.

---

## 2. Verified Current State (Ground-Truth Repository Audit)

Verified directly against branch `wave3/m3m4-integration` (`apps/api`, `apps/web`, `apps/mobile`, `packages/*`):

| Dimension | Verified Reality in Code | Transformation Implication |
|---|---|---|
| **Core Backend** | FastAPI `0.148.0`, SQLAlchemy `2.0.38` async, PostgreSQL 16 (28 tables across 10 ORM modules, 3 Alembic migrations), 123 routes (`/api/v1/*` + ops). | Preserve 100% of domain logic, DB schemas, and API contracts. Zero unnecessary backend rewrites. |
| **Six Domain Packages** | Pure Python, DB-agnostic, CI-enforced via 6 `import-linter` contracts: **Kadi**, **BillNyay**, **DawaCheck**, **DaaviSetu**, **BimaNyay**, **SchemeSetu**. | Each module receives a bespoke visual workspace tailored to its real inputs, outputs, and limitations. |
| **Identity & Access** | **ADR-026 implemented** (`kadi_users`, `kadi_sessions`, `kadi_account_tokens`, scrypt `N=2^15 r=8 p=3`, `__Host-arogya_session` cookie / Mobile Bearer, 12 account endpoints) alongside **ADR-009 guest tokens**. `MAIL_TRANSPORT=disabled` (no outbound email provider yet). | Full public-to-authenticated journey is supported. Password reset/email verification UIs must honestly disclose `MAIL_TRANSPORT=disabled` until an email provider is chosen. |
| **Privacy & Retention** | **ADR-003 BYOD Zero Document Retention**: uploaded files are processed in RAM and immediately discarded. Only SHA-256 digest, extracted entities, and redacted 1,000-char excerpt persist for `CASE_TTL_DAYS=90` (ADR-010). | Never build a "Document Vault" storing raw originals or longitudinal multi-year spending analytics. Build a transparent **Case Documents & Provenance** surface instead. |
| **Human-in-the-Loop** | Blind dual-reader OCR transcription, Kadi Medicine Trust Gate, Conflict-declared Doctor Clinical Review (`/review`), verbatim immutable statements, four-eyes Safety Rules governance (ADR-011). | Elevate human review and provenance (`Verified`, `AI-Derived`, `Human-Reviewed`, `Needs Attention`, `Critical`, `Not Assessed`) as first-class visual storytelling elements. |
| **Frontend Stack** | Next.js `16.4.6` App Router, React `19.2.4`, TypeScript 5, **Vanilla CSS** (no Tailwind), `motion` `14.14.0`, `lenis`, `lucide-react` `1.71.0`, self-hosted `@fontsource-variable` fonts, hand-built SVG charts. Strict **170 KB gzip** route bundle budget. | Rebrand `packages/design-tokens/tokens.json` from Navy/Teal to **Deep Forest / Warm Ivory** (Light-first), adopt Manrope + Inter, promote unused `ui/Charts.tsx` & `EvidenceGraph` into signature experiences, keep public pages zero-bloat Server Components. |
| **Doc-vs-Code Drift Found** | `README.md` and older docstrings still claim "no user accounts" and "FastAPI 0.115"; `docker-compose.yml` still mentions removed FAISS scaffold; `PROJECT_CONTEXT.md` cites 5 import-linter contracts instead of 6. | Transformation docs establish a single verified truth; doc hygiene backlog item included in roadmap. |

---

## 3. Product Pillars & Non-Negotiable Principles

1. **Public Clarity Before Login:** Every visitor lands on a rich, calm, self-explanatory public experience (`/`, `/platform`, `/platform/<module>`, `/how-it-works`, `/security`, `/about`, `/help`) before ever being asked to authenticate. Guest mode remains first-class for urgent hospital-desk use.
2. **Evidence-First Honesty:** Every number, benchmark, and clause carries an explicit provenance badge, a deterministic *"Why am I seeing this?"* Explanation Trail (ADR-017), and an honest *"What could not be determined"* disclosure.
3. **Calm Sovereign Aesthetics (Deep Forest / Warm Ivory):** Patients interacting with ArogyaRakshak are often stressed. We replace cold clinical navy/teal and neon AI clichés with a warm, archival-editorial **Light-First** canvas (`#F4F1E8`), crisp white working surfaces (`#FFFFFF`), and authoritative Deep Forest (`#142F2B`) accents.
4. **Six Distinct Module Personalities, One Cohesive System:** Kadi, BillNyay, DawaCheck, DaaviSetu, BimaNyay, and SchemeSetu solve fundamentally different problems and must never look like six clones of the same template.
5. **Accessible, Multilingual & Mobile-Native by Design:** WCAG 2.1 AA contrast across every token pair, trilingual architecture (English, Hindi, Marathi with explicit QA gating), Web Speech read-aloud, Simple Language toggle, `prefers-reduced-motion` + in-app motion toggle, and an intentionally crafted mobile experience for hospital billing desks.

---

## 4. Target Personas & Primary Outcomes

| Persona | Context | Core Need | Success Outcome |
|---|---|---|---|
| **Patient / Family Caregiver** | At hospital discharge desk or holding a denial letter (often on mobile, stressed, low bandwidth) | Immediate clarity on whether a bill, medicine price, or denial is fair — in plain language (EN/HI/MR) | Uploads bill/prescription in <30s (guest or account), understands flagged items with provenance, downloads signed appeal or pre-auth dossier |
| **Returning Account Holder** | Managing an ongoing hospitalisation or multi-tier IRDAI insurance dispute over weeks | Persistent access to owned cases across devices, SLA deadline tracking, ability to claim guest cases & permanently erase data | Manages cases from Case Desk, tracks 15/15/365-day BimaNyay SLAs, controls privacy & deletion |
| **Clinical Reviewer (Doctor) / OCR Reader** | Independent volunteer/partner clinician or pharmacist reviewing uncertain OCR or clinical plausibility conflicts | Distraction-free queue, redacted evidence, conflict-of-interest gate, immutable statement authoring | Settles uncertain medicines via blind dual-reading; authors verbatim clinical statements that auto-re-sign appeal PDFs |
| **Hospital / Institutional Coordinator** | Preparing pre-authorisation packages using institution playbooks (DaaviSetu) | Clear readiness checklist distinguishing missing paperwork from facts needing doctor confirmation | Generates complete Annexure-B PDF and AES-256-GCM encrypted claim package |

---

## 5. North-Star Product Transformation Goals

- **Visual Signature:** Original botanical-medical protective shield emblem, bespoke scientific SVG illustration library, and calm purposeful motion families.
- **Flagship Differentiator:** The **Evidence Explorer** — an interactive visual relationship graph linking Source Documents → Extracted Entities → Statutory/Reference Rules → Computed Findings → Human Clinical Statements.
- **Engineering Discipline:** Zero framework migrations, zero regressions to the 170 KB gzip web bundle budget, 100% WCAG AA automated contrast verification, and full preservation of all 2,363+ backend tests, 290+ web tests, and 215+ mobile tests.
