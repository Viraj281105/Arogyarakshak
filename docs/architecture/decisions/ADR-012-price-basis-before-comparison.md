# ADR-012: Establish the Price Basis Before Any Price Comparison

## Status
Accepted (2026-09-27, release-candidate pass)

## Context
Both price-comparing modules compared an amount with a reference that is defined per unit:

- **DawaCheck**: NPPA ceiling prices are per dosage unit (one tablet, capsule or vial).
  A medicine entity's `cost` was the whole bill-line amount — often a strip or pack total —
  and the manual form sent whatever the user typed. "Dolo 650: ₹33" (a strip of 15) was
  reported as **+1,335%** against the ₹2.30 per-tablet ceiling; the mobile quick sample
  "Dolo 650mg Tablet (15s) ₹33.5" produced **+1,356%**.
- **BillNyay**: CGHS reference rates are per day (room, ICU), per visit (consultation), per
  session (dialysis), per shift (PPE) or per bottle (IV infusion). "Room Rent (Private
  Ward) 3 days ₹13,500" was compared with one day's ₹4,500 and reported as **+200%** — in
  the judge demo's own Scenario A bill.

These are not rounding issues: they are fabricated findings a patient might act on.

## Decision
1. **Price basis is explicit.** `dawacheck.price_basis` models `PER_UNIT`, `PER_STRIP`,
   `PER_PACK`, `LINE_TOTAL` and `UNKNOWN`; CGHS entries carry a `billing_unit`
   (`per_day`, `per_visit`, `per_session`, `per_shift`, `per_bottle`, `per_service`).
2. **A basis comes from a statement, never an assumption.** Sources, in order: the
   person's declaration (manual DawaCheck check); the bill line itself ("Strip of 15",
   "15's", "1x15", "Qty 10", "3 days", "x 2"); a document-wide heading ("Rate per
   tablet/capsule"). Dosing schedules ("1-0-1 x 5 days") and strengths ("650") are never
   read as quantities.
3. **Convert or refuse.** A strip/pack price is converted to a unit price only with a
   stated, whole, positive unit count; a recurring CGHS rate is applied only to a stated
   count. Otherwise the result is `CANNOT_COMPARE` / `not_benchmarked` with a plain
   reason, and **no percentage and no "within/above" verdict** is produced
   (`is_overcharged` and `deviation_percentage` are `null`).
4. **Contradictions are refused too.** A declared per-unit price whose name states a pack,
   a quantity next to a pack size, two pack sizes, or a dosage form different from the
   reference (tablet vs injection) → `CANNOT_COMPARE`.
5. **Kadi records, DawaCheck interprets.** At upload, while the text is in memory, Kadi
   grounds each extracted medicine to its single source line
   (`kadi.line_items.ground_medicine_source_lines`) so an LLM-normalised name ("Pan 40")
   keeps what its line said; DawaCheck stores only the derived `price_facts` and a short
   matched snippet — never the raw line (ADR-003).
6. **The trust gate still comes first.** Price basis is consulted only for medicines the
   medicine trust gate (ADR-011) has cleared.
7. The only default is the legacy manual-API contract ("MRP per unit") for a caller that
   sends no basis and whose name states no pack; it is labelled `basis_source =
   API_DEFAULT`. The web and mobile forms always send an explicit basis.

## Consequences
- More lines are honestly "not compared" (e.g. "ICU ₹18,500" with no day count). That is
  the intended trade: a missing comparison is recoverable, a false 1,300% is not.
- API responses gained fields (`comparison_status`, `price_basis`, `price_basis_label`,
  `basis_source`, `basis_evidence`, `billed_unit_price`, `unit_label`,
  `comparison_reason_code`, `comparison_note`; BillNyay `benchmark_basis`,
  `not_benchmarked_reason`). `is_overcharged` / `deviation_percentage` became nullable;
  both clients treat a missing or `CANNOT_COMPARE` comparison as not compared.
- Tablet and capsule are distinct forms (NPPA ceilings differ); a document-wide
  "tablet/capsule" heading covers both.
- Regression tests: `packages/dawacheck/tests/test_price_basis.py`,
  `packages/billnyay/tests/test_rate_basis.py`,
  `apps/api/tests/test_dawacheck_price_basis_pipeline.py`, the BillNyay audit tests in
  `test_api.py`, and Scenario C's per-tablet assertions.
