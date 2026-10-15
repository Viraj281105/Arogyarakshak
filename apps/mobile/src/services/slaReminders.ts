// Statutory-deadline reminders for BimaNyay disputes (PROJECT_CONTEXT P1 "Mobile Push SLA Alerts").
//
// This module is deliberately free of native dependencies: it turns the server's timeline events
// into a reminder plan and syncs that plan through a NotificationScheduler interface. The Expo
// adapter that implements the interface (expo-notifications) is a separate, device-tested step -
// see docs/development/mobile-sla-reminders.md.
//
// Wording rule: a reminder states the date and the next step from the timeline. It never says a
// claim will succeed, never gives legal advice, and never says the insurer "must" do anything beyond
// what the server's own instructions already say.

import type { GrievanceTimelineEvent } from '../api/types';

export type ReminderKind = 'THREE_DAYS_BEFORE' | 'ON_DEADLINE_DAY';

export interface PlannedReminder {
  /** Stable id (tier + kind + deadline), so re-planning replaces rather than duplicates. */
  id: string;
  tier: string;
  kind: ReminderKind;
  /** Local wall-clock time the notification should fire. */
  fireAt: Date;
  title: string;
  body: string;
}

export interface NotificationScheduler {
  /** Schedule a local notification at `fireAt`; resolves to the platform's identifier. */
  schedule(reminder: PlannedReminder): Promise<string>;
  /** Cancel a notification previously returned by schedule(). */
  cancel(platformId: string): Promise<void>;
}

/** Tiers worth a push reminder: the two short statutory windows (the one-year Ombudsman limit is excluded). */
export const REMINDER_TIERS = ['LEVEL_1_GRO', 'LEVEL_2_BIMA_BHAROSA'] as const;

const REMINDER_HOUR_LOCAL = 9;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Parse a YYYY-MM-DD string as a local calendar date; null when it is not a real date. */
export function parseIsoDate(value: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const date = new Date(y, mo - 1, d, REMINDER_HOUR_LOCAL, 0, 0, 0);
  if (date.getFullYear() !== y || date.getMonth() !== mo - 1 || date.getDate() !== d) return null;
  return date;
}

function whenLabel(tier: string): string {
  return tier === 'LEVEL_1_GRO' ? "your insurer's grievance officer reply window" : 'the Bima Bharosa escalation window';
}

/**
 * Plan reminders for events that are still ahead of the person: status ACTIVE or PENDING, tier in
 * REMINDER_TIERS, deadline date in the future. Reminders already in the past are dropped.
 */
export function planSlaReminders(events: GrievanceTimelineEvent[], now: Date = new Date()): PlannedReminder[] {
  const plan: PlannedReminder[] = [];
  for (const event of events) {
    if (!(REMINDER_TIERS as readonly string[]).includes(event.tier)) continue;
    if (event.status !== 'ACTIVE' && event.status !== 'PENDING') continue;
    const deadlineDay = parseIsoDate(event.deadline_date);
    if (!deadlineDay) continue;

    const candidates: Array<[ReminderKind, Date, string]> = [
      [
        'THREE_DAYS_BEFORE',
        new Date(deadlineDay.getTime() - 3 * DAY_MS),
        `${whenLabel(event.tier)} ends in 3 days (${event.deadline_date}).`,
      ],
      ['ON_DEADLINE_DAY', deadlineDay, `${whenLabel(event.tier)} ends today (${event.deadline_date}).`],
    ];
    for (const [kind, fireAt, headline] of candidates) {
      if (fireAt.getTime() <= now.getTime()) continue;
      plan.push({
        id: `${event.tier}:${kind}:${event.deadline_date}`,
        tier: event.tier,
        kind,
        fireAt,
        title: 'ArogyaRakshak deadline reminder',
        body: `${headline} Open the app for the next step.`,
      });
    }
  }
  return plan.sort((a, b) => a.fireAt.getTime() - b.fireAt.getTime());
}

/** Platform ids of what is currently scheduled, keyed by PlannedReminder.id. */
export type ScheduledIndex = Record<string, string>;

/**
 * Make the scheduler match `plan`: cancel anything scheduled that is no longer planned, schedule
 * anything planned that is missing, leave the rest alone. Returns the new index to persist.
 */
export async function syncSlaReminders(
  scheduler: NotificationScheduler,
  plan: PlannedReminder[],
  current: ScheduledIndex,
): Promise<ScheduledIndex> {
  const wanted = new Set(plan.map((r) => r.id));
  const next: ScheduledIndex = {};
  for (const [id, platformId] of Object.entries(current)) {
    if (wanted.has(id)) next[id] = platformId;
    else await scheduler.cancel(platformId);
  }
  for (const reminder of plan) {
    if (next[reminder.id]) continue;
    next[reminder.id] = await scheduler.schedule(reminder);
  }
  return next;
}

/** Cancel everything (e.g. when the case is deleted - reminders must not outlive the case data). */
export async function clearSlaReminders(scheduler: NotificationScheduler, current: ScheduledIndex): Promise<ScheduledIndex> {
  for (const platformId of Object.values(current)) await scheduler.cancel(platformId);
  return {};
}
