# ADR-031: The person records actions and outcomes; the system never claims them

## Status
**Accepted (maintainer directive 2026-11-25).**

## Context
Every module ended at a finding or a draft. The product's promise is to help a person understand,
act and follow up. ArogyaRakshak has no connection to any hospital, insurer or authority, so it
cannot know whether anything was sent, received or decided.

## Decision
1. Two Kadi tables, `kadi_case_actions` and `kadi_case_action_events` (migration
   `0004_case_actions`), erased by the same case purge as everything else.
2. The rules live in `packages/kadi/kadi/resolution_tracking.py`: statuses, allowed moves, and
   which moves need a date. A date cannot be in the future; a response cannot predate the send.
3. There is **no `submitted` or `accepted` status**. Every event has provenance `user_recorded`.
4. Free text is passed through `redact_pii` before storage. Limits: 50 actions per case, 100 events
   per action. Evidence references must be digests that belong to the case.
5. Amounts stay distinct: billed (document), identified (analysis), disputed and corrected
   (user-entered).
6. The web shows a result as situation, grouped findings, why it matters, next steps, an editable
   draft and a tracker. It builds the groups from existing module output (`lib/actionPlan.ts`);
   no new model call is involved.

## Consequences
- Records are only as accurate as what the person enters, and are labelled that way.
- No reminders or notifications on the web.
- The web tracker does not yet expose evidence references, next step or amount disputed, which the
  API accepts.
- Mobile has no tracker yet.

## Details
docs/features/action-and-resolution.md.
