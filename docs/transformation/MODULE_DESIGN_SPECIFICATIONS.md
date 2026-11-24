# ArogyaRakshak — Module-Specific Visual & Interaction Specifications

**Design Mandate:** *Six distinct module personalities anchored in one Deep Forest / Warm Ivory design system. Never six copies of the same dashboard.*

---

## 1. KADI — Document Intelligence & Provenance Hub

- **Stitch Reference:** `ee1967ba9bee4c6993547d3a84536a3f`
- **Visual Personality:** *Forensic Archival Laboratory* — clean architectural grid, live 4-stage pipeline rail, calm provenance cards.
- **Accent Pairing:** Secondary Forest `#244C42` + Muted Sage `#91B49C`.
- **Overview (`/platform/kadi`):** Explains RAM-only BYOD processing, PyMuPDF Devanagari quality gate, EasyOCR, Groq/heuristic extraction, cross-script entity resolution, and the Medicine Trust Gate.
- **Workspace (`/app/case/kadi`):**
  - **Upload / Input Flow:** Drag-and-drop + mobile camera scan (`PDF/JPG/PNG/WEBP/BMP/TXT/CSV`, max 10 MB) with mandatory explicit consent checkbox + optional ABDM FHIR Bundle import drawer (`POST /kadi/cases/{id}/abdm/import`).
  - **Processing Experience:** Live SSE (`/stream`) 4-stage rail (*Upload in RAM → OCR & Quality Gate → Entity Extraction → Trust Gate & Graph*). Displays indeterminate scan beam (never fake percentage). Surfaces `pages_skipped` / `partial_reason` honestly via `PartialResultState` (Wave 2 Stream A).
  - **Results & Evidence:** Document Provenance Cards (SHA-256 digest, redacted 1,000-char excerpt with highlighted entity spans, `min_ocr_confidence`), Duplicate Entity Resolution Queue (`MERGE` / `ASK` / `NEW` feedback), and jump-link to Evidence Explorer.
  - **Empty / Error / Mobile:** Empty → guided sample-doc/upload card; Interrupted job (ADR-019) → calm re-upload prompt; Mobile → full-width camera intake button + vertical stage accordion.

---

## 2. BILLNYAY — Hospital Bill Intelligence

- **Stitch Reference:** `95be66a38bab48c5ad5047b862bd2eda`
- **Visual Personality:** *Forensic Financial Ledger* — crisp tabular figures (`JetBrains Mono`), archival paper appeal preview, clinical plausibility split.
- **Accent Pairing:** Deep Forest `#142F2B` + Verified Green `#397A58` (with Critical `#C4544F` solely for overcharges).
- **Overview (`/platform/billnyay`):** Problem statement, interactive synthetic 5-line bill breakdown, CGHS-2024-REVISED scope disclosure (27 curated rows).
- **Workspace (`/app/case/billnyay`):**
  - **Input / Actions:** Top Action Toolbar (*Run CGHS Audit*, *Draft 5-Agent Appeal*, *Clinical Plausibility*, *ICD-10 Audit*, *Log Grievance*).
  - **Results & Visualisations:** Financial Summary Strip (3 cards explicitly labelled *"Estimate vs CGHS-2024-REVISED subset"*), `StackedBarChart` + `WaterfallChart` composition breakdown, sortable `DataTable` of every bill line with expandable ADR-017 `ExplainTrail`, ICD-10 Consistency Panel (`GET /icd-audit`), Clinical Plausibility Panel, and Paper-Style Appeal Letter card with HMAC-SHA256 verification badge + verbatim doctor statement annex.
  - **Empty / Error / Mobile:** No bill entities → upload prompt; Outcome Estimate → `InsufficientEvidenceState` (honest empty dataset); Mobile → card-per-line list with sticky total footer.

---

## 3. DAWACHECK — Medicine Price Intelligence & Trust Gate

- **Stitch Reference:** `275f3364cf8942aca89b2b2b94935a59`
- **Visual Personality:** *Pharmaceutical Analytical Bench* — clean dosage cards, strict unit-scale bars, unmistakable Trust Gate holdouts.
- **Accent Pairing:** AI-Derived Slate Blue `#52769B` + Verified Green `#397A58`.
- **Overview (`/platform/dawacheck`):** Explains ADR-012 per-unit math (the ₹33 strip vs ₹2.30/tablet lesson), Medicine Trust Gate, and 7-formulation NPPA Schedule-I scope.
- **Workspace (`/app/case/dawacheck` — Works Standalone & Case-Linked):**
  - **Input Flow:** Quick Price Check Bar with Medicine Name, Billed ₹, and explicit **Price Basis** segmented selector (`Per Unit`, `Per Strip + tablet count`, `Per Pack`, `Line Total`) + Prescription Shorthand Translator (`OD/BD/TDS/HS/SOS/AC/PC`).
  - **Results & Evidence:** Per-medicine analytical cards with `PriceBar` (paid per-unit vs NPPA cap), Jan Aushadhi generic substitute pills, **Trust Gate Holdout Cards** (`#C28A35`, never price-checked until 2 blind readers settle), Combination Product Refusal (`#89918C`), and `ListenSummary` read-aloud.
  - **Empty / Error / Mobile:** Unmapped drug → honest refusal with *"Absence from the 7-drug subset does not mean exempt"*; Mobile → thumb-friendly Price Basis chips + stacked medicine cards.

---

## 4. DAAVISETU — Pre-Authorisation & Document Readiness

- **Stitch Reference:** `666810eb58214253ae9c0cdf403c47db`
- **Visual Personality:** *Guided Dossier Studio* — structured 3-step horizontal wizard, completeness ring, cryptographic security seal.
- **Accent Pairing:** Secondary Forest `#244C42` + Human-Reviewed Plum `#8066A5`.
- **Overview (`/platform/daavisetu`):** Explains readiness vs approval odds (never predicts approval), institution playbooks, and Annexure-B PDF + client-side encryption.
- **Workspace (`/app/case/daavisetu`):**
  - **3-Step Guided Flow (`StepWizard`):**
    1. **Readiness Checklist:** `DonutChart` completeness ring (`Present` / `Needs Doctor Confirmation` / `Missing`), itemised checklist with provenance badges, *"Request Doctor Confirmation"* trigger, optional institution playbook selector.
    2. **Annexure-B Form & Template Fill:** Auto-filled from Kadi with inline `AI-Derived` tags (`Hospital`, `Diagnosis`, `Procedure`, `Policy ID`, optional `Estimated Cost`), plus optional custom AcroForm PDF template fill (`POST /claim/fill-template`).
    3. **Encrypted Package Builder:** Download Annexure-B PDF (`GET /claim/pdf`) or ZIP (`GET /claim/package`), optional browser-local **PBKDF2 (600,000) → AES-256-GCM** password lock & local unlock utility. Ends at **"Package Ready"** (never "Submitted").
  - **Empty / Error / Mobile:** Structured 422 missing-field recovery inline; Mobile → single-step screen per wizard step with sticky Next/Back bar.

---

## 5. BIMANYAY — Insurance Claim Denial & IRDAI Appeal Studio

- **Stitch Reference:** `fc0c3bba3163434d964cdcc9cadcbe30`
- **Visual Personality:** *Legal-Regulatory Adjudication Studio* — 3-column desktop studio, paper-document appeal drafts, statutory SLA clock.
- **Accent Pairing:** Human-Reviewed Plum `#8066A5` + Needs Attention Amber `#C28A35`.
- **Overview (`/platform/bimanyay`):** IRDAI Master Circular (29 May 2024) 4-category clause audit, 3-tier escalation path, and honest rule-score disclosure.
- **Workspace (`/app/case/bimanyay` — Works Standalone & Case-Linked):**
  - **Top SLA Rail:** 3-tier `TimelineChart` (GRO 15d → Bima Bharosa 15d → Ombudsman 365d).
  - **3-Column Studio (`>= 1280px`):**
    - *Left:* Claim & Denial Dossier form + Denied-Amount Share Bar + Linked Doctor Clinical Statements (`#8066A5`).
    - *Center:* IRDAI Clause Audit Cards showing statutory conflicts (`#C4544F`), legal remedies, verification status (marking `ROOM_RENT` explicitly as `Needs Attention / Unverified primary source`), and *"Rule-based starting estimate: NN / 100"* pill.
    - *Right:* Interactive Trilingual Appeal Draft Studio (`Tier 1 GRO` / `Tier 2 Bima Bharosa` / `Tier 3 Ombudsman Form VI`, EN / HI / MR), Copy/Print/Export, `ListenSummary`, and `ExplainTrail`.
  - **Empty / Error / Mobile:** Mobile collapses 3 columns into 3 clean swipeable/tabbed views (*Dossier*, *Audit*, *Appeals*) with SLA summary pinned at top.

---

## 6. SCHEMESETU — Government Healthcare Scheme Intelligence

- **Stitch Reference:** `4c9fa17dcc6c4e38ad975cb4d31cd6c5`
- **Visual Personality:** *Empathetic Civic Clarity* — warm civic cards, transparent decision-basis flow, zero hidden income assumptions.
- **Accent Pairing:** Verified Green `#397A58` + Needs Attention Amber `#C28A35`.
- **Overview (`/platform/schemesetu`):** Covers PM-JAY (national) & MJPJAY (Maharashtra) with explicit citations and non-determinative income policy.
- **Workspace (`/app/case/schemesetu` — Works Standalone & Case-Linked):**
  - **Input Flow:** State/UT selector (with regional alias feedback, e.g., `"Pune → Maharashtra"`), optional Annual Income & Category clearly labelled *"Not used to decide — neither scheme defines an income ceiling"*, opt-in *"Save income profile to case"* checkbox (`PUT /cases/{id}/income-profile`).
  - **Results & Visualisations:** Two-column Scheme Assessment Cards (**PM-JAY** always `Needs Attention / Verification Needed` with official SECC-2011/ASHA/70+ checklist; **MJPJAY** `Verified / Provisionally Eligible` in Maharashtra with Ration Card/Domicile checklist), interactive **Criterion Reasoning Flow** (`POST /eligibility/reasoning`) with citation verification badges (`Supported`, `Scheme Only`, `Uncheckable`), plus expandable **Income Trend & Transition Guidance** (`POST /eligibility/trend`, `/transition`).
  - **Empty / Error / Mobile:** Mobile stacks scheme cards with collapsible reasoning steps and read-aloud summary.
