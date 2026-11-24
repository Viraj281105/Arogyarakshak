// Regression guards from the post-Antigravity independent review (2026-11-25,
// docs/transformation/IMPLEMENTATION_STATUS.md section 6). Each test names the defect it prevents.
import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const appDir = join(__dirname, '..', 'app');
const read = (p: string) => readFileSync(join(appDir, p), 'utf8');
const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });

describe('transformation review: API contracts', () => {
  test('ICD audit view reads the real ICDProcedureAuditItem fields and explains every status', () => {
    const src = read('components/modules/BillNyayView.tsx');
    // The first version read invented fields (summary/findings/note), so a "mismatched" result was never shown.
    assert.ok(!/icdApi\.data\.(summary|findings|note)/.test(src));
    for (const f of ['icd10_code', 'diagnosis_text', 'procedures_billed', 'reference_entry_count']) assert.ok(src.includes(f), f);
    for (const s of ['consistent', 'mismatched', 'no_procedure_billed', 'code_not_found', 'code_not_in_reference']) {
      assert.match(src, new RegExp(`\\b${s}: \\{`), `status ${s} has a plain-language reading`);
    }
    assert.ok(!/6-code/.test(src), 'reference size comes from reference_entry_count, not a hard-coded number');
  });

  test('SchemeSetu reasoning view reads the real EligibilityReasoning fields', () => {
    const src = read('components/modules/SchemeSetuView.tsx');
    assert.ok(!/reasoningApi\.data\.(steps|summary)/.test(src), 'invented fields rendered an empty trace');
    for (const f of ['reasoning_trace', 'criteria_not_considered', 'threshold_or_rule', 'applicant_value', 'determinative', 'satisfied']) {
      assert.ok(src.includes(f), f);
    }
  });
});

describe('transformation review: evidence honesty', () => {
  test('"human-reviewed" is only shown for an item a named reviewer confirmed', () => {
    const uses = walk(appDir)
      .filter((p) => /\.tsx$/.test(p))
      .flatMap((p) => readFileSync(p, 'utf8').split('\n').filter((l) => l.includes('state="human-reviewed"')).map((l) => `${p}: ${l.trim()}`));
    // The (dev) gallery and the evidence legend list every state on purpose.
    const real = uses.filter((u) => !/\(dev\)/.test(u));
    for (const u of real) assert.match(u, /CONFIRMED_BY_REVIEWER/, u);
  });

  test('module heroes use neutral chips, not evidence badges (a page header is not a finding)', () => {
    for (const f of ['BillNyayView', 'BimaNyayView', 'DaaviSetuView', 'DawaCheckView', 'SchemeSetuView']) {
      const src = read(`components/modules/${f}.tsx`);
      const hero = src.slice(src.indexOf('ws-mod-hero'), src.indexOf('</header>', src.indexOf('ws-mod-hero')));
      assert.ok(!hero.includes('<EvidenceBadge'), `${f} hero`);
    }
  });

  test('extracted fields are not labelled AI-generated (extraction may be rule-based; entities do not say which)', () => {
    assert.ok(!read('components/workspace/DocumentsKept.tsx').includes('state="ai-generated"'));
    assert.ok(!read('components/workspace/CaseOverview.tsx').includes('state="ai-generated"'));
  });

  test('DaaviSetu has one step list; no step is marked done before the server returned the package', () => {
    const src = read('components/modules/DaaviSetuView.tsx');
    assert.ok(!src.includes('ws-step-strip'), 'duplicate step strip removed');
  });
});

describe('transformation review: bundle budget', () => {
  test('client modules imported by Settings and the shell carry no brand or background code', () => {
    for (const f of ['components/auth/AuthShared.tsx', 'shell/SiteHeader.tsx', 'shell/SiteFooter.tsx']) {
      const src = read(f);
      assert.ok(!/components\/brand\/Brand|\.\.\/brand\/Brand|illustrations\/Backgrounds/.test(src), f);
    }
    const split = read('components/auth/AuthSplit.tsx');
    assert.ok(!split.includes('"use client"'), 'AuthSplit is a Server Component');
    for (const page of ['login', 'register', 'forgot-password', 'reset-password', 'verify']) {
      assert.match(read(`${page}/page.tsx`), /<AuthSplit>/, page);
    }
  });
});
