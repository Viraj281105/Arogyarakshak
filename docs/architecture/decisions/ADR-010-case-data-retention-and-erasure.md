# ADR-010: Case Data Retention & Erasure

## Status
Accepted

## Context
ADR-003 and the README's BYOD claims are true and re-verified for what they actually
cover: raw uploaded documents are never written to disk, held only in RAM during
extraction. But both documents have repeatedly described the resulting database
records — `kadi_cases` and everything derived from it — with language like "linked to a
**temporary** case UUID" and "an **ephemeral** case UUID." That language implies
time-limited existence. It was never true: before this ADR, a `KadiCase` row, its
extracted `KadiEntity` rows, its redacted `document_text` excerpt, and any generated
PDFs (`billnyay_appeals.pdf_bytes`, the compiled appeal letter; `daavisetu_claims`, the
signable pre-authorization form with the patient's real name and policy number)
persisted in the database **indefinitely**, with:
- no time-based expiry or purge job of any kind,
- no `DELETE` route for a case at all — a patient who created a case had no way,
  through this system, to remove their own data once it existed.

An independent adversarial security audit (P1-10, 2026-09-16) flagged this gap: "do not
claim zero retention if generated artifacts/PII remain indefinitely."

## Decision
1. **`DELETE /api/v1/kadi/cases/{case_id}`** (new, ADR-009-authorized — only the case's
   own access-token holder may call it) permanently deletes the case row and every
   record derived from it: `KadiEntity` rows (only once no other case still references
   them — the schema technically allows a shared entity), the case's resolution
   decisions, module insights, `kadi_case_documents` digests, the SchemeSetu income
   profile, the BillNyay appeal (letter text **and** the compiled PDF bytes), and the
   DaaviSetu claim. This is the real erasure mechanism the "temporary"/"ephemeral"
   language always implied but never built.
2. **"Temporary"/"ephemeral" case-UUID language is corrected** in ADR-003 and the
   README to describe what is actually true: a case persists until its owner deletes
   it via the route above, not automatically.
3. **No automatic time-based purge is implemented.** This ADR does not invent a
   retention period (e.g. "30 days") that was never an actual product decision — doing
   so would itself be a fabricated claim. Automatic expiry would need a scheduled job,
   which is new standing infrastructure out of scope for this hardening pass.

## What this does NOT cover — disclosed, not hidden
- **BimaNyay's dispute records** (`bimanyay_cases`, `bimanyay_grievances`,
  `bimanyay_timeline_events`) are a separate data domain, never linked to `kadi_cases`
  by foreign key (BimaNyay generates its own UUID per request, per ADR-005's lifecycle
  division). `DELETE /kadi/cases/{id}` does not and cannot reach them. They have no
  deletion route of their own either — a real, separate gap this ADR does not close.
- **No automatic expiry.** A case a patient never explicitly deletes lives forever.
  Given this project's no-authentication scope decision (ADR-008/009), an abandoned
  case is not silently exposed to a new party (its access token is still required), but
  it is also never cleaned up on its own.
- **Backups, logs, and database-level snapshots**, if any exist in a given deployment,
  are outside this application's control and are not touched by this deletion route —
  it only removes the live rows this application queries.

## Consequences

### Positive
- The "temporary"/"ephemeral" language no longer overstates what the system does — the
  gap between claim and code that the project's own no-fabrication principle exists to
  catch is closed here, the same way it was for FAISS/IndicXlit/IndicSBERT claims
  earlier in this project's history.
- A patient (or, more precisely, whoever holds a case's access token) now has a genuine
  way to request their data be removed, including the compiled documents that carry
  their real name and policy number.

### Negative — explicitly accepted
- No automatic retention limit. If genuine time-based expiry becomes a real product
  requirement, it needs a scheduled job — recorded here as the natural next step, not
  claimed as already done.
- BimaNyay records remain permanently undeletable through this application. A future
  ADR should either link BimaNyay cases to `kadi_cases` or give BimaNyay its own
  deletion route.
