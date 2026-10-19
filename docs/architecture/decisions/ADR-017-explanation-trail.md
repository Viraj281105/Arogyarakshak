# ADR-017: A deterministic "Why am I seeing this?" explanation trail

## Status
Accepted (2026-10-19)

## Context
ArogyaRakshak's principles — no fabrication, readiness-not-approval, honest "cannot
determine" states (ADR-011, ADR-012) — were enforced in code but invisible to a user or a
judge looking at a finding. A finding such as "overcharged by 43%" or "deadline 2026-01-16"
gave no way to see which document line, which reference row or which statutory period
produced it, how much the system trusted its input, or what it could not establish.

## Decision
1. **One shared, structured model.** `kadi.explanation.Explanation` (Pydantic) holds: the
   source evidence (each item with a *provenance class* — `OCR_EXTRACTED`, `LLM_NORMALISED`,
   `HUMAN_REVIEWED`, `USER_ENTERED`, `REFERENCE_DATA`, `RULE_COMPUTED`, `NOT_RECORDED` — plus
   the document name when recorded), the exact rule/reference row applied, a trust state,
   what could not be determined (code + reason) and `not_recorded`. It lives in Kadi
   because provenance and trust are Kadi-layer concepts.
2. **Built by the owning package, next to the decision, from the same values.**
   `dawacheck.explain`, `billnyay.explain`, `daavisetu.readiness.explain_item`,
   `bimanyay.tracker._explain_deadline`. No builder calls an LLM; the model states
   `generated_by` so clients can say so. DawaCheck's builder is a separate module that only
   reads `MedicineBenchmark` fields, leaving `checker.py` / `reference_data.py` untouched.
3. **"Not recorded" is structural.** A value the system did not record is `null`; `not_recorded`
   is *derived* in the model validator from those nulls (and from OCR-derived evidence
   without a document name), so no builder can substitute a plausible guess. Examples of
   honestly unrecorded data today: the CGHS procedure code (the bundled table has none),
   the NPPA notification/serial of a reference row, a per-line OCR confidence, the source
   document of a keyword match (document text is stored joined), a reviewer's
   verification label.
4. **Delivered additively on the existing authorised responses**, not through a new
   endpoint: `explanation` on each BillNyay `audit_items[]`, each DawaCheck case medicine and
   manual `/benchmark` response, each DaaviSetu readiness `items[]`, and each BimaNyay
   `timeline_events[]`. Per-case authorization (`X-Case-Access-Token`, ADR-009) and consent
   gates are therefore unchanged and an explanation can never be fetched by a route that
   the finding itself is not. Existing fields are untouched.
5. **Provenance is claimed no further than it is recorded.** `LLM_NORMALISED` is used only
   when the recorded OCR-uncertainty reasons include `POSSIBLE_MATCH` (the extractor's name
   differs from the OCR reading); whether an LLM rewrote a given name is not otherwise
   stored, so the UI says "read from your document" rather than inventing a claim either way.
6. **Packages gain a dependency on `kadi.explanation`** (pure Pydantic; importing `kadi`
   costs ~0.4 s because `kadi/__init__` loads the extractor). The module packages remain
   free of each other. Not added to `pyproject.toml` because `kadi` is installed from the
   monorepo (`pip install -e packages/kadi`), as CI already does.

## Consequences
- A reviewer can open any finding and see evidence → rule → trust → gaps, and the gaps are
  data (`undetermined`, `not_recorded`), usable in tests and in the Claim Pack.
- Explanation text from the server is English; only the fixed UI labels are trilingual
  (hi/mr are first drafts, `NEEDS NATIVE-SPEAKER QA`).
- BimaNyay's explanation discloses real simplifications in the tracker: the clock starts at
  the entered date (not the insurer's receipt/rejection date), calendar days are used, tier 2
  is placed straight after tier 1, and an unreadable start date falls back to today.
  These are surfaced, not fixed here.
- Explanations are not persisted; they are recomputed with each response, so they can never
  disagree with the decision beside them.
- Not covered: SchemeSetu eligibility reasoning (it already returns a reasoning trace) and
  BillNyay appeal-letter content.
