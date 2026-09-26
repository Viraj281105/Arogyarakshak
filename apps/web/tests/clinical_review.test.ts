import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { clinicalPaths, isCurrentOpinion, reviewerHeaders, PROVENANCE_LABELS } from '../app/lib/clinical';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');
// Explanatory comments legitimately name what the code must never do; check code only.
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
const clinicalDir = join(process.cwd(), 'app', 'components', 'clinical');
const clinicalSources = readdirSync(clinicalDir).map((f) => read('app', 'components', 'clinical', f));
const workspace = read('app', 'clinical-review', 'page.tsx');
const libSrc = read('app', 'lib', 'clinical.ts');
const billNyay = read('app', 'components', 'modules', 'BillNyayView.tsx');
const bimaNyay = read('app', 'components', 'modules', 'BimaNyayView.tsx');
const daaviSetu = read('app', 'components', 'modules', 'DaaviSetuView.tsx');
const dawaCheck = read('app', 'components', 'modules', 'DawaCheckView.tsx');
const page = read('app', 'page.tsx');

describe('ADR-011 clinical review — web honesty contracts', () => {
  it('never composes "Verified Doctor" anywhere in the clinical UI', () => {
    for (const src of [...clinicalSources, workspace, libSrc, billNyay, bimaNyay]) {
      assert.ok(!/Verified Doctor/i.test(code(src)));
    }
  });

  it('shows verification only through the server-provided verification_label', () => {
    const attribution = read('app', 'components', 'clinical', 'Attribution.tsx');
    assert.ok(/reviewer\.verification_label/.test(attribution));
  });

  it('only a FINALIZED statement counts as a current opinion', () => {
    assert.strictEqual(isCurrentOpinion({ status: 'FINALIZED' }), true);
    for (const s of ['DRAFT', 'UNDER_REVIEW', 'SUPERSEDED', 'WITHDRAWN'] as const) {
      assert.strictEqual(isCurrentOpinion({ status: s }), false);
    }
  });

  it('labels every provenance class', () => {
    for (const key of ['AI_DERIVED', 'HUMAN_REVIEWED', 'HUMAN_AUTHORED', 'EXTERNAL_SOURCE', 'PATIENT_PROVIDED'] as const) {
      assert.ok(PROVENANCE_LABELS[key]);
    }
  });

  it('reviewer credentials travel only in the X-Reviewer-Token header', () => {
    assert.deepStrictEqual(reviewerHeaders('abc'), { 'X-Reviewer-Token': 'abc' });
    assert.deepStrictEqual(reviewerHeaders(''), {});
    assert.ok(!/reviewer_token=/.test(libSrc), 'no query-string reviewer tokens');
  });

  it('case-holder routes sit under /cases/{id} so the case token is attached', () => {
    assert.strictEqual(clinicalPaths.caseReviews('CASE-1'), '/api/v1/kadi/cases/CASE-1/clinical-reviews');
    assert.strictEqual(clinicalPaths.safety('CASE-1'), '/api/v1/kadi/cases/CASE-1/safety-escalations');
    assert.strictEqual(clinicalPaths.plausibility('CASE-1'), '/api/v1/billnyay/cases/CASE-1/clinical-plausibility');
  });
});

describe('Consent and human confirmation are explicit', () => {
  it('requesting a review needs the patient to tick the sharing consent', () => {
    const panel = read('app', 'components', 'clinical', 'ClinicalReviewPanel.tsx');
    assert.ok(/share_with_reviewer_consent: shareConsent/.test(panel));
    assert.ok(/disabled=\{busy \|\| !shareConsent\}/.test(panel));
  });

  it('finalization sends the confirmation only when the reviewer ticked it themselves', () => {
    const fn = workspace.match(/const finalizeStatement[\s\S]*?\n {2}\);?\n/);
    assert.ok(fn, 'finalizeStatement not found');
    assert.ok(/confirmation: confirmTicked/.test(fn![0]));
    assert.ok(/confirmTicked \? detail!\.finalization_confirmation_text : ""/.test(fn![0]));
    assert.ok(/disabled=\{!confirmTicked\}/.test(workspace));
  });

  it('the reviewer credential is kept in memory, never in browser storage', () => {
    assert.ok(!/localStorage|sessionStorage/.test(code(workspace)));
  });

  it('COI must be declared before accepting', () => {
    assert.ok(/disabled=\{!coi\.category\}/.test(workspace));
  });
});

describe('Module integration', () => {
  it('BillNyay offers the review panel only for a real case and discloses a missing statement', () => {
    assert.ok(/\{caseId && \(\s*<ClinicalReviewPanel/.test(billNyay));
    assert.ok(/human_clinical_statement_attached \?/.test(billNyay));
    assert.ok(/No statement from a named clinician is attached/.test(billNyay));
  });

  it('BillNyay shows the plausibility disclaimer, not a necessity verdict', () => {
    assert.ok(/assessment\.disclaimer/.test(billNyay));
    assert.ok(!/medically necessary/i.test(billNyay));
  });

  it('BimaNyay surfaces the clinical-interpretation trigger and the verbatim annex', () => {
    assert.ok(/requires_clinical_interpretation/.test(bimaNyay));
    assert.ok(/clinical-statements/.test(bimaNyay));
  });

  it('DaaviSetu readiness never claims approval effects', () => {
    const readiness = read('app', 'components', 'clinical', 'PreauthReadinessPanel.tsx');
    assert.ok(/<PreauthReadinessPanel/.test(daaviSetu));
    assert.ok(!/approval (probability|rate|chance|likelihood)|improve[sd]? (your )?approval/i.test(readiness));
  });

  it('DawaCheck transcription is presented as human reading, not a doctor feature', () => {
    const transcription = read('app', 'components', 'clinical', 'TranscriptionPanel.tsx');
    assert.ok(/<TranscriptionPanel/.test(dawaCheck));
    assert.ok(!/doctor/i.test(transcription.replace(/not to "doctors"/, '')));
    assert.ok(/share_with_reviewer_consent: shareConsent/.test(transcription));
  });

  it('the safety banner always carries the floor disclaimer and the source', () => {
    const banner = read('app', 'components', 'clinical', 'SafetyEscalationBanner.tsx');
    assert.ok(/evaluation\.disclaimer/.test(banner));
    assert.ok(/esc\.source\.name/.test(banner));
    assert.ok(/<SafetyEscalationBanner/.test(page));
  });
});
