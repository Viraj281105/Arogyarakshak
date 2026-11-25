import { describe, test } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  billnyayPlan,
  bimanyayPlan,
  daavisetuPlan,
  dawacheckPlan,
  english,
  schemesetuPlan,
  type ActionPlanData,
} from '../app/lib/actionPlan';
import { describePriceCheck } from '../app/lib/dawacheck';
import { safeNext } from '../app/components/auth/LoginForm';
import { EVENT_LABEL, STATUS_LABEL } from '../app/components/actions/actionLabels';

const app = (...p: string[]) => readFileSync(join(process.cwd(), 'app', ...p), 'utf8');

const line = (item_name: string, status: string, charged: number, cghs_benchmark: number | null) => ({
  item_name,
  status: status as 'overcharged',
  charged,
  cghs_benchmark,
  deviation_percentage: 0,
  is_deviation: status === 'overcharged',
  benchmarked: cghs_benchmark !== null,
});

const AUDIT = {
  case_id: 'c',
  total_charged: 20000,
  total_benchmark: 9000,
  benchmarked_charged: 15000,
  potential_savings: 6000,
  deviations_count: 1,
  benchmarked_count: 2,
  unmatched_count: 1,
  unmatched_amount: 5000,
  audit_items: [line('Room rent', 'overcharged', 13500, 7500), line('Nursing', 'within_benchmark', 1500, 1500), line('Kit', 'not_benchmarked', 5000, null)],
};

/** Words a plan must never use about the user's own matter. */
const OVERCLAIMS = /\b(illegal|fraud|violat\w* confirmed|guaranteed|you will (get|receive)|will be refunded|you save|savings|submitted|approved)\b/i;

const wording = (plan: ActionPlanData) =>
  [plan.situation, plan.whatNext, ...plan.uncertainties, ...plan.steps.flatMap((s) => [s.title, s.why, s.draft ?? '']), ...plan.findings.map((f) => `${f.observed} ${f.why ?? ''}`)].join('\n');

describe('BillNyay plan', () => {
  const plan = billnyayPlan(AUDIT, english);

  test('speaks of lines to clarify, never of confirmed overcharges or savings', () => {
    assert.match(plan.situation, /1 line\(s\) that may need clarification\. These are not confirmed overcharges/);
    const text = wording(plan).replace(/not confirmed overcharges/g, '').replace(/Nothing here shows that money will be refunded[^\n]*/g, '');
    assert.doesNotMatch(text, OVERCLAIMS);
  });

  test('groups every line and keeps an unmatched one as not assessed', () => {
    assert.deepEqual(plan.findings.map((f) => f.group), ['needs_clarification', 'confirmed', 'unable_to_assess']);
  });

  test('the draft lists only the flagged line, with figures from the audit', () => {
    const draft = plan.steps[0].draft!;
    assert.match(draft, /Room rent: billed ₹13,500; CGHS reference ₹7,500/);
    assert.ok(!draft.includes('Nursing'));
    assert.match(draft, /not alleging wrongdoing/);
  });

  test('distinguishes the amount billed from the amount on lines to clarify', () => {
    assert.deepEqual(plan.amounts?.map((a) => a.value), ['₹20,000', '₹13,500']);
  });

  test('nothing flagged and nothing unmatched suggests no step', () => {
    const clean = billnyayPlan({ ...AUDIT, unmatched_count: 0, audit_items: [AUDIT.audit_items[1]] }, english);
    assert.equal(clean.steps.length, 0);
    assert.match(clean.whatNext, /suggests no step/);
  });
});

describe('BimaNyay plan', () => {
  const result = {
    is_wrongful_denial: true,
    reversal_probability_score: 70,
    primary_dispute_grounds: 'g',
    regulatory_violations: [{ statute_or_circular: 'IRDAI circular', clause_reference: 'Clause 1', violation_summary: 'Summary', legal_remedy: 'Remedy' }],
    level_1_gro_appeal: 'Dear officer,',
    level_2_bimabharosa_text: '',
    level_3_ombudsman_grounds: '',
  };
  const event = { tier: 'LEVEL_1_GRO', title: 'Write to the GRO', deadline_date: '2026-12-01', status: 'PENDING', instructions: 'Server instructions' };

  test("uses the server's own step wording and draft, and promises no outcome", () => {
    const plan = bimanyayPlan(result, [event], english);
    const step = plan.steps.find((s) => s.id === 'grievance-level-1')!;
    assert.equal(step.title, 'Write to the GRO');
    assert.equal(step.why, 'Server instructions');
    assert.equal(step.draft, 'Dear officer,');
    assert.match(plan.situation, /does not mean the insurer will change its decision/);
    assert.ok(plan.uncertainties.some((u) => /not the chance that an appeal succeeds/.test(u)));
  });

  test('says the policy was not read', () => {
    assert.ok(bimanyayPlan(result, [], english).uncertainties.some((u) => /policy wording was not read/.test(u)));
  });
});

describe('DawaCheck plan', () => {
  const base = { brand_name: 'Brand', active_ingredient: 'Drug', reference_entry_count: 7, mrp: 30, nppa_ceiling_price: 2, is_overcharged: null, deviation_percentage: null };

  test('a refused comparison is not assessed and suggests checking the pack', () => {
    const result = { ...base, comparison_status: 'CANNOT_COMPARE' as const };
    const plan = dawacheckPlan(result, describePriceCheck(result), english);
    assert.equal(plan.findings[0].group, 'unable_to_assess');
    assert.deepEqual(plan.steps.map((s) => s.id), ['check-pack']);
  });

  test('above the ceiling asks the pharmacy and never calls MRP the ceiling', () => {
    const result = { ...base, comparison_status: 'COMPARED' as const, billed_unit_price: 3, is_overcharged: true, price_basis: 'PER_UNIT' as const };
    const plan = dawacheckPlan(result, describePriceCheck(result), english);
    assert.deepEqual(plan.steps.map((s) => s.kind), ['ask_pharmacist']);
    assert.ok(plan.uncertainties.some((u) => /not the same thing as the printed MRP/.test(u)));
    assert.match(plan.situation, /not a finding of wrongdoing/);
  });
});

describe('DaaviSetu and SchemeSetu plans', () => {
  test('missing and clinical items become separate steps and the journey ends at the package', () => {
    const plan = daavisetuPlan(
      [
        { item_id: 'a', label: 'Report', status: 'MISSING' },
        { item_id: 'b', label: 'History', status: 'NEEDS_CLINICAL_CONFIRMATION' },
        { item_id: 'c', label: 'Bill', status: 'PRESENT' },
      ],
      english,
    );
    assert.deepEqual(plan.steps.map((s) => s.kind), ['collect_documents', 'confirm_with_doctor']);
    assert.match(plan.whatNext, /stops at a ready package/);
  });

  test('a scheme result is never an eligibility decision and lists what was not checked', () => {
    const plan = schemesetuPlan(
      [
        { scheme_name: 'PM-JAY', estimated_eligibility: 'ambiguous', reason: 'r', claim_guide_steps: ['Call'], criteria_not_evaluated: ['SECC-2011 listing'], sources: [] },
        { scheme_name: 'Other', estimated_eligibility: 'ineligible', reason: 'r', claim_guide_steps: [], criteria_not_evaluated: [], sources: [] },
      ],
      english,
    );
    assert.match(plan.situation, /not an eligibility decision/);
    assert.ok(plan.uncertainties.includes('SECC-2011 listing'));
    assert.equal(plan.steps.length, 1);
  });
});

describe('tracking wording and routing', () => {
  test('no status says submitted, accepted or approved', () => {
    for (const label of [...Object.values(STATUS_LABEL), ...Object.values(EVENT_LABEL)]) {
      assert.doesNotMatch(label, /submit|accept|approv/i);
    }
    assert.match(STATUS_LABEL.resolved, /confirmed by you/);
    assert.match(STATUS_LABEL.sent, /You marked this as sent/);
  });

  test('sign-in returns only to known workspace pages', () => {
    assert.equal(safeNext('/app/case/billnyay'), '/app/case/billnyay');
    for (const bad of ['//evil.example', 'https://evil.example', '/app?x=1', '/login', null]) assert.equal(safeNext(bad), '/app');
  });

  test('every workspace route sits behind the sign-in gate', () => {
    assert.match(app('app', 'layout.tsx'), /<RequireAccount>/);
  });
});
