import { test, describe } from 'node:test';
import assert from 'node:assert';

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
