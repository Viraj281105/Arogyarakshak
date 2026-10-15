import { describe, it } from 'node:test';
import assert from 'node:assert';
import {
  clearSlaReminders,
  parseIsoDate,
  planSlaReminders,
  syncSlaReminders,
  type NotificationScheduler,
  type PlannedReminder,
} from '../src/services/slaReminders';
import type { GrievanceTimelineEvent } from '../src/api/types';

const ev = (tier: string, deadline_date: string, status: string): GrievanceTimelineEvent => ({
  tier,
  title: tier,
  deadline_date,
  status,
  instructions: 'x',
});

// Local-time "now" so the tests do not depend on the machine's time zone.
const now = new Date(2026, 9, 1, 8, 0, 0); // 1 Oct 2026, 08:00

class FakeScheduler implements NotificationScheduler {
  scheduled: PlannedReminder[] = [];
  cancelled: string[] = [];
  private n = 0;
  async schedule(r: PlannedReminder) {
    this.scheduled.push(r);
    return `p${++this.n}`;
  }
  async cancel(id: string) {
    this.cancelled.push(id);
  }
}

describe('SLA reminder planning', () => {
  it('plans a 3-days-before and an on-the-day reminder at 09:00 local for a future deadline', () => {
    const plan = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now);
    assert.strictEqual(plan.length, 2);
    assert.deepStrictEqual(plan.map((r) => r.kind), ['THREE_DAYS_BEFORE', 'ON_DEADLINE_DAY']);
    assert.strictEqual(plan[0].fireAt.getTime(), new Date(2026, 9, 13, 9, 0).getTime());
    assert.strictEqual(plan[1].fireAt.getTime(), new Date(2026, 9, 16, 9, 0).getTime());
  });

  it('drops reminders that are already in the past', () => {
    const plan = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-03', 'ACTIVE')], now);
    assert.deepStrictEqual(plan.map((r) => r.kind), ['ON_DEADLINE_DAY']);
    assert.strictEqual(planSlaReminders([ev('LEVEL_1_GRO', '2026-09-20', 'ACTIVE')], now).length, 0);
  });

  it('only covers the two short statutory tiers and only open events', () => {
    const plan = planSlaReminders(
      [
        ev('LEVEL_3_OMBUDSMAN', '2027-09-01', 'PENDING'),
        ev('LEVEL_1_GRO', '2026-10-20', 'COMPLETED'),
        ev('LEVEL_1_GRO', '2026-10-20', 'OVERDUE'),
        ev('LEVEL_2_BIMA_BHAROSA', '2026-11-04', 'PENDING'),
      ],
      now,
    );
    assert.ok(plan.length > 0);
    assert.ok(plan.every((r) => r.tier === 'LEVEL_2_BIMA_BHAROSA'));
  });

  it('ignores malformed or impossible dates instead of throwing', () => {
    assert.strictEqual(parseIsoDate('2026-02-30'), null);
    assert.strictEqual(parseIsoDate('16/10/2026'), null);
    assert.deepStrictEqual(planSlaReminders([ev('LEVEL_1_GRO', 'soon', 'ACTIVE')], now), []);
  });

  it('never promises an outcome or gives legal advice', () => {
    const [r] = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now);
    assert.doesNotMatch(r.body, /will (be )?(approve|win|succeed|pay)|guarantee|must/i);
    assert.match(r.body, /2026-10-16/);
  });

  it('gives each reminder a stable id so re-planning is idempotent', () => {
    const a = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now);
    const b = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now);
    assert.deepStrictEqual(a.map((r) => r.id), b.map((r) => r.id));
    assert.strictEqual(new Set(a.map((r) => r.id)).size, a.length);
  });
});

describe('SLA reminder syncing', () => {
  it('schedules new reminders, keeps unchanged ones and cancels ones no longer planned', async () => {
    const s = new FakeScheduler();
    const first = planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now);
    let index = await syncSlaReminders(s, first, {});
    assert.strictEqual(s.scheduled.length, 2);

    // Same plan again: nothing new is scheduled, nothing cancelled.
    index = await syncSlaReminders(s, first, index);
    assert.strictEqual(s.scheduled.length, 2);
    assert.strictEqual(s.cancelled.length, 0);

    // The dispute moved to the next tier: GRO reminders are cancelled, Bima Bharosa ones scheduled.
    const moved = planSlaReminders(
      [ev('LEVEL_1_GRO', '2026-10-16', 'COMPLETED'), ev('LEVEL_2_BIMA_BHAROSA', '2026-10-31', 'ACTIVE')],
      now,
    );
    index = await syncSlaReminders(s, moved, index);
    assert.strictEqual(s.cancelled.length, 2);
    assert.deepStrictEqual(Object.keys(index).sort(), moved.map((r) => r.id).sort());
  });

  it('clears everything (reminders must not outlive a deleted case)', async () => {
    const s = new FakeScheduler();
    const index = await syncSlaReminders(s, planSlaReminders([ev('LEVEL_1_GRO', '2026-10-16', 'ACTIVE')], now), {});
    assert.deepStrictEqual(await clearSlaReminders(s, index), {});
    assert.strictEqual(s.cancelled.length, 2);
  });
});
