# ADR-011: Human Clinical Review, Safety Governance & Human OCR Resolution

## Status
Accepted — implemented 2026-09-23. Full design and walkthrough: [`docs/architecture/clinical-review.md`](../clinical-review.md).

## Context
Some findings ArogyaRakshak produces need professional clinical judgment: whether a billed
intervention fits the documented diagnosis, whether a denial of "not medically necessary"
is sound, whether a clinical fact a pre-authorization depends on is actually documented.
Until now the only "Clinician" in the system was an LLM agent (`billnyay.agents.clinician`)
writing general reasoning, and the offline appeal template asserted that "the treating
physician's records evidence the necessity" of the charges — an implied clinical opinion
nobody gave.

A hostile product review of five doctor-integration concepts killed the naive versions
("AI drafts, doctor clicks approve"; a public insurer-gaming playbook marketplace; a
medical-necessity predictor; doctors inventing a safety system; doctors transcribing
handwriting). This ADR records the redesigned versions that were built.

Constraints that shaped the design:
- **No user accounts** (ADR-008/009). Authorization is a per-case bearer token.
- **Consent** is one boolean per case (`consent.py`); ADR-007 federation is not built.
- **Zero document retention** (ADR-003): no stored images, not even crops.
- **No registry integration**: no NMC / State Medical Council / Pharmacy Council API is
  available to this project.
- Table names must carry a module prefix (`scripts/ci_guardrails.py`); Kadi owns
  cross-module case context (ADR-002).

## Decision

1. **One shared layer, owned by Kadi.** DB-agnostic rules in
   `packages/kadi/kadi/clinical_review/`; persistence and HTTP in `apps/api/app/clinical/`
   and three endpoint files mounted under `/api/v1/kadi`. All shared tables are `kadi_*`;
   DaaviSetu playbooks are `daavisetu_*`. BillNyay, BimaNyay, DaaviSetu and DawaCheck
   consume the layer; none re-implements it.

2. **Credentials without accounts.** Reviewers and institutions register and receive a
   bearer credential shown once (SHA-256 hash stored), accepted only as a header
   (`X-Reviewer-Token`, `X-Institution-Token`). A reviewer credential grants nothing by
   itself: the case holder *delegates* a single review or transcription task to a named
   reviewer, and only that task's frozen evidence becomes visible. Operator-only actions
   (safety-board seating, verification attempts, demo seeding) need
   `CLINICAL_GOVERNANCE_ADMIN_KEY`; when it is unset they are disabled (503), never open.

3. **Verification is never overstated.** Self-registration yields at most
   `SELF_DECLARED`. `EXTERNALLY_VERIFIED` is reachable only through a
   `RegistryVerificationAdapter`; the only shipped adapter reports
   `EXTERNAL_VERIFICATION_UNAVAILABLE`. `DEMO_VERIFIED` exists only with
   `CLINICAL_DEMO_MODE=true`. Every client renders the server's `verification_label`
   verbatim; no surface says "Verified Doctor".

4. **Consent is per request.** Sharing with a human reviewer needs the case's stored
   `consent_opt_in` **and** `share_with_reviewer_consent: true` on that request.
   Cancelling a review revokes the reviewer's access immediately.

5. **COI before evidence.** A reviewer sees only a minimal COI context (hospital, insurer)
   until they accept with a mandatory conflict-of-interest category; the COI is frozen
   into every statement and shown wherever the statement is shown.

6. **Statements are human-authored, confirmed and immutable.** DRAFT → UNDER_REVIEW →
   FINALIZED → SUPERSEDED | WITHDRAWN. Finalizing needs the author's own credential and
   the exact confirmation sentence; no server path supplies either. A finalized statement
   stores a reviewer snapshot and a SHA-256 content hash; changes create a new version.
   Appeals append finalized statements **verbatim** through a deterministic formatter
   (`kadi.clinical_review.annex`) — never through the LLM — and state explicitly when none
   exists. The Barrister prompt forbids implying any clinician's opinion, and the offline
   template no longer asserts one.

7. **Plausibility, not necessity.** BillNyay's check reports PLAUSIBLE /
   INSUFFICIENT_INFORMATION / POTENTIAL_INCONSISTENCY / CLINICAL_REVIEW_RECOMMENDED from
   the existing curated ICD-10 table, names that table as project-curated, cites
   guidelines only from a registered record (none exists, so none is cited), and routes
   uncertainty to human review.

8. **Readiness, not approval.** DaaviSetu checks documentation completeness against a
   generic baseline plus optional institution-private playbooks (versioned, immutable
   once ACTIVE, expiry-enforced, never visible across institutions). Labels that assert
   claimant facts are rejected. Clinical facts stay NEEDS_CLINICAL_CONFIRMATION until a
   named doctor decides them.

9. **Safety rules are adopted, approved and versioned.** Rules adapt a named published
   protocol (source, version, section, limitations), need independent approval by a
   seated board member other than the proposer (approval bound to the submitted content
   hash), are immutable once approved, and supersede by version. Escalations are not
   consent-gated. Every surface carries: "This safety layer is a decision-support floor,
   not a substitute for professional clinical assessment."

10. **OCR resolution is not a doctor feature.** Kadi now keeps EasyOCR's per-segment
    confidence; low-confidence segments become transcription tasks holding only redacted
    text and a location hint. Possible-medication fields need two independent, blind
    readings that agree; disagreement or "unreadable" escalates to humans. DawaCheck
    never benchmarks an unresolved reading and marks a resolved name `HUMAN_REVIEWED`.

11. **Provenance survives.** `AI_DERIVED`, `HUMAN_REVIEWED`, `HUMAN_AUTHORED`,
    `EXTERNAL_SOURCE`, `PATIENT_PROVIDED` travel on evidence items, statements, fact
    decisions and transcriptions, and are exposed together by
    `GET /kadi/cases/{id}/clinical-context`.

12. **Erasure.** `purge_case` deletes all case-scoped clinical records (reviews,
    statements, fact decisions, transcription tasks/assignments/readings, case audit
    events); global reviewers, rules and playbooks are kept.

## Consequences
- The claim this makes true: ArogyaRakshak distinguishes machine-derived evidence from
  accountable human judgment, routes cases to named human review with consent and COI,
  keeps immutable history, and puts human judgment into dispute packages without letting
  AI impersonate or manufacture professional authority.
- Not claimed: registry verification, identity proofing of reviewers or case holders,
  medical-necessity determination, approval or outcome prediction, comprehensive safety
  coverage, federated consent.
- Anyone can self-register as "a doctor". That is disclosed (SELF_DECLARED label) rather
  than prevented; real verification needs a registry integration (see Future work in the
  architecture doc).
- Keyword safety triggers do not understand negation and will over-escalate; this is
  disclosed on every escalation.
- Clinical UI copy is English-only pending native-speaker review of Hindi/Marathi
  medico-legal wording.
- No migrations tool exists; the new tables are created by `create_all`. No existing table
  was altered.
