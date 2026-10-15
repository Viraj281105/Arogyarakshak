# Mobile SLA reminders (status: planner done, delivery not wired)

`apps/mobile/src/services/slaReminders.ts` turns the BimaNyay timeline (`/api/v1/bimanyay/timeline`)
into local reminders for the two short statutory windows (insurer GRO, Bima Bharosa): one
3 days before and one on the deadline day, 09:00 local. The one-year Ombudsman limit is excluded.

- `planSlaReminders(events, now)` — pure; drops past times, closed tiers and malformed dates.
- `syncSlaReminders(scheduler, plan, current)` — idempotent; cancels reminders that are no longer
  planned (e.g. the dispute moved to the next tier). `clearSlaReminders` removes everything and
  must be called when a case is deleted.
- Wording states the date only; it never predicts an outcome or gives legal advice.

## Not done
The `NotificationScheduler` interface has no production implementation. That needs
`expo-notifications` (install with `npx expo install expo-notifications` so the version matches
SDK 52), a permission prompt, an Android notification channel and a device run.

## Expo SDK (resolved 2026-10-15)
`apps/mobile` stays on Expo SDK 52. A dependabot "bump postcss" commit had changed `expo` to
`~57.0.25`; that was reverted and postcss is kept current with an `overrides` entry.
