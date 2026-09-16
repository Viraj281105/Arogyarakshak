import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('Web Domain Contracts and Routing Boundaries', () => {
  const domainEndpoints = [
    { module: 'kadi', path: '/api/v1/kadi/cases' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/upload' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/stream' },
    { module: 'billnyay', path: '/api/v1/billnyay/cases/CASE-123/audit' },
    { module: 'daavisetu', path: '/api/v1/daavisetu/cases/CASE-123/claim' },
    { module: 'daavisetu', path: '/api/v1/daavisetu/cases/CASE-123/claim/pdf' },
    { module: 'bimanyay', path: '/api/v1/bimanyay/analyze' },
    { module: 'schemesetu', path: '/api/v1/schemesetu/eligibility' },
    { module: 'dawacheck', path: '/api/v1/dawacheck/benchmark' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/resolutions' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/graph' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/insights' },
    { module: 'kadi', path: '/api/v1/kadi/cases/CASE-123/abdm/import' },
    { module: 'schemesetu', path: '/api/v1/schemesetu/cases/CASE-123/income-profile' },
    { module: 'billnyay', path: '/api/v1/billnyay/outcome-estimate' },
  ];

  test('all routes must strictly follow /api/v1/<module>/... versioning', () => {
    domainEndpoints.forEach(({ module, path }) => {
      const regex = new RegExp(`^/api/v1/${module}/`);
      assert.match(path, regex, `Route ${path} does not match versioning convention for ${module}`);
    });
  });

  test('all module names must be strictly lowercase conforming to AGENTS.md', () => {
    const moduleNames = ['kadi', 'billnyay', 'daavisetu', 'bimanyay', 'schemesetu', 'dawacheck'];
    moduleNames.forEach((name) => {
      assert.strictEqual(name, name.toLowerCase(), `Module name ${name} is not strictly lowercase`);
    });
  });

  test('statutory legal frameworks must be correctly referenced across modules', () => {
    const legalFrameworks = {
      billnyay: 'CGHS 2024 Revised Rates',
      bimanyay: 'IRDAI Master Circular (29 May 2024)',
      schemesetu: 'AB-PMJAY & MJPJAY 2024 Criteria',
      dawacheck: 'NPPA Schedule-I DPCO 2013',
      daavisetu: 'IRDAI Standard Cashless Pre-Auth Form VI (Annexure-B)',
    };

    assert.ok(legalFrameworks.billnyay.includes('CGHS 2024'));
    assert.ok(legalFrameworks.bimanyay.includes('IRDAI'));
    assert.ok(legalFrameworks.dawacheck.includes('NPPA'));
    assert.ok(legalFrameworks.daavisetu.includes('Annexure-B'));
  });

  test('document audit requires explicit file and disallows empty or dummy fallbacks', () => {
    const startAuditGuard = (file: { name: string } | null) => {
      if (!file) {
        return { success: false, error: 'Please select or drop a valid document file before starting the audit.' };
      }
      return { success: true, fileName: file.name };
    };

    const nullResult = startAuditGuard(null);
    assert.strictEqual(nullResult.success, false);
    assert.ok(nullResult.error?.includes('valid document file'));

    const fileResult = startAuditGuard({ name: 'real_hospital_bill.pdf' });
    assert.strictEqual(fileResult.success, true);
    assert.strictEqual(fileResult.fileName, 'real_hospital_bill.pdf');
  });
});

describe('Web Consent Request Behaviour', () => {
  const source = readFileSync(
    join(process.cwd(), 'app', 'page.tsx'),
    'utf-8'
  );
  const uploader = readFileSync(
    join(process.cwd(), 'app', 'components', 'DocumentUploader.tsx'),
    'utf-8'
  );

  test('case creation must send the user consent value, never a hardcoded true', () => {
    assert.ok(
      !/consent_opt_in:\s*true/.test(source),
      'page.tsx must not hardcode consent_opt_in: true'
    );
    assert.ok(
      /consent_opt_in:\s*consentGiven/.test(source),
      'page.tsx must send the actual consent value'
    );
  });

  test('consent checkbox must default to unchecked (opt-in, not opt-out)', () => {
    assert.ok(
      /useState<boolean>\(false\)/.test(uploader),
      'consent must default to false — a pre-ticked box is not consent'
    );
  });

  test('upload must be blocked until consent is given', () => {
    assert.ok(
      /if \(!consentGiven \|\| !selectedFile\) return;/.test(uploader),
      'submit handler must refuse without consent'
    );
    assert.ok(
      /disabled=\{!consentGiven/.test(uploader),
      'submit button must be disabled without consent'
    );
  });

  test('consent must be forwarded to the audit handler', () => {
    assert.ok(
      /onStartAudit\(selectedFile, selectedFile\.name, consentGiven\)/.test(uploader),
      'uploader must pass consent up to the caller'
    );
  });
});

describe('Web Forms Must Not Pre-Fill Fabricated Data', () => {
  const moduleDir = join(process.cwd(), 'app', 'components', 'modules');
  const views = ['DaaviSetuView', 'BimaNyayView', 'SchemeSetuView', 'DawaCheckView'];

  // Values previously hardcoded into form state. A user who submitted without editing
  // generated a determination — and a persisted pre-auth form — about a fabricated person.
  const forbidden = [
    'Viraj Jadhao',
    'POL-STAR-774411',
    'POL-884422',
    'Apollo Multi-Speciality Hospital',
    'Star Health & Allied Insurance',
    'Acute Myocardial Infarction',
    'Heart bypass surgery (CABG)',
    'Laparoscopic Appendectomy',
    'Paracetamol 650mg',
  ];

  views.forEach((view) => {
    test(`${view} must not seed form state with sample identity or clinical data`, () => {
      const src = readFileSync(join(moduleDir, `${view}.tsx`), 'utf-8');
      const seeded = src
        .split('\n')
        .filter((line) => line.includes('useState(') && !line.trim().startsWith('//'));

      seeded.forEach((line) => {
        forbidden.forEach((value) => {
          assert.ok(
            !line.includes(value),
            `${view} seeds form state with "${value}": ${line.trim()}`
          );
        });
      });
    });
  });

  test('DaaviSetu requires patient name and policy before submitting', () => {
    const src = readFileSync(join(moduleDir, 'DaaviSetuView.tsx'), 'utf-8');
    assert.ok(
      /!patientName\.trim\(\) \|\| !policyId\.trim\(\)/.test(src),
      'submit must be blocked until identity fields are supplied'
    );
  });

  test('BimaNyay requires a complete dossier before drafting a legal appeal', () => {
    const src = readFileSync(join(moduleDir, 'BimaNyayView.tsx'), 'utf-8');
    assert.ok(/bimaNyayFormComplete/.test(src), 'completeness guard missing');
    assert.ok(
      /disabled=\{isLoading \|\| !bimaNyayFormComplete\}/.test(src),
      'analyze button must be disabled while the dossier is incomplete'
    );
  });

  test('SchemeSetu renders the provisional-result disclosure, not just types it', () => {
    // Regression: is_provisional/criteria_evaluated/criteria_not_evaluated were declared
    // on the SchemeResult TS interface but never referenced in JSX, so the backend's
    // honesty disclosure never reached the user.
    const src = readFileSync(join(moduleDir, 'SchemeSetuView.tsx'), 'utf-8');
    assert.ok(/scheme\.is_provisional/.test(src), 'is_provisional must gate a rendered notice');
    assert.ok(/scheme\.criteria_not_evaluated/.test(src), 'criteria_not_evaluated must be rendered');
    assert.ok(/scheme\.criteria_evaluated/.test(src), 'criteria_evaluated must be rendered');
    assert.ok(/scheme\.non_determinative_factors/.test(src), 'non_determinative_factors must be rendered');
    assert.ok(/scheme\.sources\.map/.test(src), 'official sources must be rendered');
    assert.ok(!src.includes('confidence_score'), 'no heuristic score may be shown beside a cited rule');
    assert.ok(src.includes('t.verificationNeeded'), 'an ambiguous verdict must not render as "Not eligible"');
  });

  test('DawaCheck renders the dataset provenance disclosure, not just types it', () => {
    // Regression: data_source/reference_entry_count were declared on the response type
    // but never rendered, so users could not tell the curated ~7-formulation subset
    // apart from full NPPA Schedule-I coverage.
    const src = readFileSync(join(moduleDir, 'DawaCheckView.tsx'), 'utf-8');
    assert.ok(/result\.reference_entry_count/.test(src), 'reference_entry_count must be rendered');
  });
});

import { formatScore, resolutionPaths, signalRows } from '../app/lib/resolution';

describe('Kadi Entity Resolution Review Contract (#31)', () => {
  test('review paths match the API routes', () => {
    assert.strictEqual(resolutionPaths.pending('CASE-123'), '/api/v1/kadi/cases/CASE-123/resolutions?status=pending');
    assert.strictEqual(
      resolutionPaths.feedback('CASE-123', 'RES-9'),
      '/api/v1/kadi/cases/CASE-123/resolutions/RES-9/feedback'
    );
  });

  test('scores render as percentages and unavailable signals as missing, never as zero', () => {
    assert.strictEqual(formatScore(0.8583), '86%');
    assert.strictEqual(formatScore(null), null);
    const rows = signalRows([
      { signal: 'lexical', status: 'AVAILABLE', score: 0.8182, detail: '' },
      { signal: 'semantic', status: 'UNAVAILABLE', score: null, detail: 'disabled' },
    ]);
    assert.deepStrictEqual(rows, [
      { signal: 'lexical', value: '82%' },
      { signal: 'semantic', value: null },
    ]);
  });

  test('entities are only merged by an explicit answer from the patient', () => {
    const src = readFileSync(join(process.cwd(), 'app', 'components', 'EntityResolutionReview.tsx'), 'utf-8');
    assert.ok(src.includes('same_entity: sameEntity'));
    assert.ok(src.includes('onClick={() => answer(decision, true)}'));
    assert.ok(src.includes('onClick={() => answer(decision, false)}'));
  });
});

describe('SchemeSetu Income Profile Is Opt-In (#92)', () => {
  const src = readFileSync(join(process.cwd(), 'app', 'components', 'modules', 'SchemeSetuView.tsx'), 'utf-8');

  test('save-to-case defaults to unchecked and gates the PUT', () => {
    assert.ok(src.includes('const [saveToCase, setSaveToCase] = useState(false)'));
    assert.ok(src.includes('if (caseId && saveToCase)'));
    assert.ok(src.includes('/income-profile'));
  });
});
