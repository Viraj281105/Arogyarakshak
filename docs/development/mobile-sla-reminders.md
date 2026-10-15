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
`expo-notifications`, a permission prompt, an Android notification channel and a device run, and
should not be added until the Expo SDK mismatch below is resolved.

## Known blocker: Expo SDK mismatch
`apps/mobile/package.json` declares `expo ~57.0.25` (changed by the dependabot commit fe4b773),
but the other Expo packages (`expo-camera ~16`, `expo-constants ~17`, …) and CI/README target
SDK 52, and `npm ls` reports the installed `expo@52.0.49` as invalid. Choose one SDK, align every
`expo-*` package, then add `expo-notifications` at the version that SDK expects.
