# ADR-015: Claim Pack — one cross-module, in-memory ZIP for the person helping

- **Status:** Accepted (2026-10-19)
- **Context:** A patient is usually helped by someone else (caregiver, insurance agent, hospital
  desk). The results sit in separate module screens, and the existing DaaviSetu claim package
  (#81) covers only pre-authorization.
- **Decision:** `GET /api/v1/kadi/cases/{case_id}/claim-pack` returns a ZIP assembled in memory
  (`apps/api/app/claim_pack.py`, route in `endpoints/claim_pack.py`). It lives under `/kadi`
  because it is cross-module case context (AGENTS.md "Kadi Layer Exclusivity"). It requires the
  per-case access token (ADR-009) and cross-module consent (ADR-007/011).
  Contents: `README.txt` cover sheet, `01` documentation checklist (the DaaviSetu readiness
  engine and its wording; generic baseline only), `02` BimaNyay deadlines (stored grievance
  tracker for the case), `03` BillNyay audit, `04` appeal draft, `05` DawaCheck rows,
  `preauth_form.pdf` (only if the person already submitted claim details), `manifest.txt` and
  `manifest.json`.
- **Rules:**
  - Read-only. No LLM call, no network call, no row written. The BillNyay audit and DawaCheck
    rows are the existing deterministic functions over stored entities; an appeal is included
    only if one was already drafted. DawaCheck's staged brand mappings are rolled back.
  - Original uploaded files are not an input (they are not retained, ADR-003), so they cannot be
    in the pack. The manifest says so.
  - A section without data is still listed and says "Not available for this case"; nothing is
    estimated or filled in. No approval prediction, no clinical interpretation.
  - The manifest lists every section with `included`, a summary and provenance classes
    (`OCR_EXTRACTED`, `HUMAN_REVIEWED`, `RULE_COMPUTED`, `USER_ENTERED`, `AI_DRAFTED`).
  - Web: `ClaimPackPanel` offers the opt-in browser-side password protection from ADR-014
    (`.arenc`); the password never leaves the browser.
- **Consequences:** The checklist uses the generic baseline, not an institution's private
  playbook (as in #81). The BillNyay audit is recomputed rather than read from the stored
  insight summary, because the insight keeps only counts. Mobile has no Claim Pack control yet.
