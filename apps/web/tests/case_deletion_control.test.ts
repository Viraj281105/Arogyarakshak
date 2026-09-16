import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

describe('SEC-03: web UI exposes explicit case deletion, not just server-side expiry', () => {
  const pageSrc = readFileSync(join(process.cwd(), 'app', 'page.tsx'), 'utf-8');

  it('calls DELETE /api/v1/kadi/cases/{caseId} with the case access token header', () => {
    assert.ok(
      /method:\s*"DELETE"/.test(pageSrc),
      'handleDeleteCase must issue a real DELETE request'
    );
    assert.ok(
      /\/api\/v1\/kadi\/cases\/\$\{caseId\}`,\s*\{\s*method:\s*"DELETE"/.test(pageSrc),
      'must target the case-scoped deletion route with this case\'s id'
    );
    assert.ok(
      /"X-Case-Access-Token":\s*caseToken/.test(pageSrc),
      'the delete request must carry the real per-case access token, not rely on the id alone'
    );
  });

  it('asks for confirmation before deleting (destructive, irreversible action)', () => {
    assert.ok(
      /window\.confirm\(/.test(pageSrc),
      'deleting a case is irreversible and must be confirmed before the request fires'
    );
  });

  it('clears local case state after a successful deletion, not just on the server', () => {
    const deleteFnMatch = pageSrc.match(/const handleDeleteCase = async \(\) => \{[\s\S]*?\n  \};/);
    assert.ok(deleteFnMatch, 'handleDeleteCase function not found');
    assert.ok(/setCaseId\(""\)/.test(deleteFnMatch![0]), 'must clear caseId after deletion');
    assert.ok(/setCaseToken\(""\)/.test(deleteFnMatch![0]), 'must clear caseToken after deletion');
  });

  it('the delete control only renders once a case actually exists', () => {
    assert.ok(
      /\{caseId && \(\s*<div[\s\S]*?handleDeleteCase/.test(pageSrc),
      'the delete button must be gated on an active caseId, not always rendered'
    );
  });
});
