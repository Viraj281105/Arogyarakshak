import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { TONE_CLASS, formatTimestamp, humanizeEnum, verificationTone } from '../app/lib/labels';

const read = (...p: string[]) => readFileSync(join(process.cwd(), ...p), 'utf-8');
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

describe('Readable labels (no raw enum leakage)', () => {
  it('maps the statuses the demo shows to plain language', () => {
    assert.strictEqual(humanizeEnum('POTENTIAL_INCONSISTENCY'), 'Potential inconsistency');
    assert.strictEqual(humanizeEnum('IN_REVIEW'), 'Under clinical review');
    assert.strictEqual(humanizeEnum('OCR_UNCERTAIN'), 'Unclear on the document — not yet read by a human');
    assert.strictEqual(humanizeEnum('SOME_NEW_STATUS'), 'Some new status', 'unknown enums still read as words');
    assert.strictEqual(humanizeEnum(null), '');
  });

  it('formats server UTC timestamps without the raw ISO string', () => {
    const out = formatTimestamp('2026-09-27T05:35:20.993958');
    assert.ok(!out.includes('T05:35') && /2026/.test(out));
    assert.strictEqual(formatTimestamp('not a date'), 'not a date');
  });
});

describe('Provenance / verification stay visually distinct', () => {
  it('only a real registry check looks verified', () => {
    assert.strictEqual(verificationTone('EXTERNALLY_VERIFIED'), 'verified');
    assert.notStrictEqual(TONE_CLASS[verificationTone('DEMO_VERIFIED')], TONE_CLASS.verified);
    assert.notStrictEqual(TONE_CLASS[verificationTone('SELF_DECLARED')], TONE_CLASS.verified);
    assert.notStrictEqual(TONE_CLASS[verificationTone('DEMO_VERIFIED')], TONE_CLASS[verificationTone('SELF_DECLARED')]);
  });

  it('machine-derived, human-reviewed and human-authored use different classes', () => {
    const classes = new Set([TONE_CLASS.machine, TONE_CLASS['human-reviewed'], TONE_CLASS['human-authored']]);
    assert.strictEqual(classes.size, 3);
    const css = read('app', 'globals.css');
    for (const c of ['badge-machine', 'badge-human-reviewed', 'badge-human-authored', 'badge-demo', 'badge-self-declared']) {
      assert.ok(css.includes(`.${c}`), c);
    }
  });
});

describe('Demo-hardening UI contracts', () => {
  it('module views get the case only after processing completes; a stalled stream offers Refresh status', () => {
    const page = code(read('app', 'page.tsx'));
    assert.ok(/caseReady = !!caseId && pipelineStep === 4 && !isProcessing/.test(page));
    assert.ok(/caseId=\{readyCaseId\}/.test(page));
    assert.ok(/retryLabel="Refresh status"/.test(page));
    assert.ok(/Processing is taking longer than expected/.test(page));
  });

  it('a failed or unavailable safety check says "Safety check unavailable"', () => {
    const banner = read('app', 'components', 'clinical', 'SafetyEscalationBanner.tsx');
    assert.ok(/Safety check unavailable/.test(banner));
    assert.ok(/evaluation\?\.status === "UNAVAILABLE"/.test(banner));
  });

  it('DawaCheck shows the case medicines with the server trust decision and never a raw state', () => {
    const view = read('app', 'components', 'modules', 'DawaCheckView.tsx');
    assert.ok(/<CaseMedicineTrustPanel/.test(view));
    const panel = read('app', 'components', 'clinical', 'CaseMedicineTrustPanel.tsx');
    assert.ok(/r\.trust\?\.label \?\? humanizeEnum\(state\)/.test(panel));
  });

  it('a NOT_APPLIED reading is never shown as a confirmed reading', () => {
    const panel = code(read('app', 'components', 'clinical', 'TranscriptionPanel.tsx'));
    assert.ok(/task\.final_value && task\.outcome !== "NOT_APPLIED"/.test(panel));
  });

  it('the automated "Judge" score is never presented as an approval', () => {
    const billNyay = code(read('app', 'components', 'modules', 'BillNyayView.tsx'));
    assert.ok(!/Judge-Approved/.test(billNyay));
    assert.ok(/Passed automated quality check/.test(billNyay));
  });

  it('safety rule retirement is four-eyes in the workspace', () => {
    const ws = read('app', 'clinical-review', 'page.tsx');
    assert.ok(/Request retirement/.test(ws) && /Confirm retirement/.test(ws));
  });
});
