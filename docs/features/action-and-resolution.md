# From a finding to an outcome

Product journey: **Issue → Evidence → Understanding → Action → Response → Follow-up → Outcome.**
Decision record: ADR-031.

## What a result page shows (web)

1. **Your situation** in plain words.
2. **Findings** grouped as: Requires clarification, Possible discrepancy, Missing documentation,
   Reference comparison, Information confirmed, Unable to assess.
3. **Why it matters.**
4. **Next steps**, in order.
5. **Help me prepare:** an editable draft or checklist. Nothing is sent.
6. **Your progress:** the tracker.

`apps/web/app/lib/actionPlan.ts` builds groups, steps and drafts from the module's existing output.
No extra model call is made. Used by BillNyay, BimaNyay, DawaCheck, SchemeSetu, DaaviSetu and the
case overview.

## Where each statement comes from

| Label | Meaning |
|---|---|
| System generated | Rules or a model produced it from your documents. Check it. |
| Your record | You entered it. ArogyaRakshak did not verify it. |
| Human reviewed | A named reviewer wrote or confirmed it (ADR-011). |
| Verified | Matches a cited source, as defined by the evidence badges. |

## Statuses

`planned`, `draft_prepared`, `sent`, `awaiting_response`, `response_received`,
`further_action_needed`, `resolved`, `partially_resolved`, `unresolved`, `closed`, `withdrawn`.

There is no "submitted" or "accepted". Pre-authorisation ends at "package ready". Allowed moves are
in `packages/kadi/kadi/resolution_tracking.py`. `sent` and `response_received` need the date it
happened; a response cannot predate the send; future dates are refused.

## Amounts

Four different numbers, never merged: **billed** (read from the document), **identified** (above a
reference, from analysis), **disputed** (you entered) and **corrected or refunded** (you entered).
No saving or refund is promised.

## API (owner only)

| Method and path | Does |
|---|---|
| `GET /api/v1/kadi/cases/{case_id}/actions` | List actions with their history |
| `POST /api/v1/kadi/cases/{case_id}/actions` | Start tracking one |
| `POST /api/v1/kadi/cases/{case_id}/actions/{action_id}/events` | Record what happened (409 if impossible) |
| `DELETE /api/v1/kadi/cases/{case_id}/actions/{action_id}` | Remove it |

Free text is redacted before storage. Limits: 50 actions per case, 100 entries per action. All
records are erased with the case (ADR-010).

## Not done

- The web tracker has no fields for evidence reference, next step or amount disputed (the API
  accepts them).
- No reminders.
- No mobile tracker.
- Draft and finding text is translated; text the API sends stays English (docs/localization.md).
