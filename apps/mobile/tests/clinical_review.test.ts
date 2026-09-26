import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { extractCaseIdFromPath } from '../src/api/caseAuth';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

const endpoints = read('src', 'api', 'endpoints.ts');
const types = read('src', 'api', 'types.ts');
const reviewCard = read('src', 'components', 'ClinicalReviewCard.tsx');
const workflowCards = read('src', 'components', 'ClinicalWorkflowCards.tsx');
const billNyay = read('src', 'screens', 'BillNyayScreen.tsx');
const bimaNyay = read('src', 'screens', 'BimaNyayScreen.tsx');
const daaviSetu = read('src', 'screens', 'DaaviSetuScreen.tsx');
const dawaCheck = read('src', 'screens', 'DawaCheckScreen.tsx');

describe('ADR-011 mobile clinical review — honesty contracts', () => {
  it('never composes "Verified Doctor"; verification comes from the server label', () => {
    for (const src of [reviewCard, workflowCards, billNyay, bimaNyay]) {
      assert.ok(!/Verified Doctor/i.test(code(src)));
    }
    assert.ok(/rv\.verification_label/.test(reviewCard));
    assert.ok(/verification_label: string/.test(types));
  });

  it('case-holder clinical routes name the case so the case token is auto-attached', () => {
    const paths = endpoints.match(/`\/api\/v1\/kadi\/cases\/\$\{enc\(caseId\)\}\/[a-z-]+/g) ?? [];
    assert.ok(paths.length >= 5, 'expected clinical routes under /kadi/cases/{id}');
    assert.strictEqual(extractCaseIdFromPath('/api/v1/kadi/cases/CASE-9/clinical-reviews'), 'CASE-9');
  });

  it('sharing consent is an explicit patient choice, never defaulted to true', () => {
    assert.ok(/share_with_reviewer_consent: boolean;/.test(types));
    assert.ok(/useState\(false\)/.test(reviewCard));
    assert.ok(/share_with_reviewer_consent: shareConsent/.test(reviewCard));
    assert.ok(/disabled=\{busy \|\| !shareConsent\}/.test(reviewCard));
    assert.ok(!/share_with_reviewer_consent: true/.test(code(endpoints + reviewCard + workflowCards)));
  });

  it('the appeal shows an attached statement or explicitly says none exists', () => {
    assert.ok(/human_clinical_statement_attached \?/.test(billNyay));
    assert.ok(/No statement from a named clinician is attached/.test(billNyay));
    assert.ok(/<StatementView/.test(billNyay));
  });

  it('a statement is shown with COI, limitations and its not-an-insurer-finding notice', () => {
    assert.ok(/Conflict of interest: \{statement\.coi_label\}/.test(reviewCard));
    assert.ok(/Limitations: \{statement\.limitations\}/.test(reviewCard));
    assert.ok(/not an insurer determination/.test(reviewCard));
  });

  it('plausibility is labelled machine-derived and shows its disclaimer', () => {
    assert.ok(/label="Machine-derived"/.test(billNyay));
    assert.ok(/plausibility\.assessment\.disclaimer/.test(billNyay));
  });
});

describe('ADR-011 mobile module integration', () => {
  it('BimaNyay links analyses to the scanned case and offers a clinical review', () => {
    assert.ok(/route\.params\?\.caseId/.test(bimaNyay));
    assert.ok(/getCaseAccessToken\(caseId\)/.test(bimaNyay));
    assert.ok(/<ClinicalReviewCard[\s\S]*?sourceModule="bimanyay"/.test(bimaNyay));
  });

  it('DaaviSetu readiness never claims approval effects', () => {
    assert.ok(/<ReadinessCard caseId=\{caseId\}/.test(daaviSetu));
    assert.ok(!/approval (probability|rate|chance|likelihood)|improve[sd]? (your )?approval/i.test(workflowCards));
  });

  it('DawaCheck routes uncertain readings to human readers, not "doctors"', () => {
    assert.ok(/<TranscriptionCard caseId=\{caseId\}/.test(dawaCheck));
    const transcription = workflowCards.slice(workflowCards.indexOf('export const TranscriptionCard'));
    assert.ok(!/doctor/i.test(transcription));
    assert.ok(/assignTranscription\(caseId, task\.task_id, r\.id, shareConsent\)/.test(transcription));
  });

  it('the safety notice carries the floor disclaimer', () => {
    assert.ok(/evaluation\.disclaimer/.test(workflowCards));
    assert.ok(/<SafetyNotice/.test(billNyay));
  });
});
