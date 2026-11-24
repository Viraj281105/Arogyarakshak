import { describe, it } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const read = (f: string) => readFileSync(join(process.cwd(), f), 'utf-8');

describe('SEC-03: web UI exposes explicit case deletion, not just server-side expiry', () => {
  // Wave 3 M4: the request lives in lib/caseApi; the case frame and settings render the control.
  const api = read('app/lib/caseApi.ts');
  const provider = read('app/components/workspace/CaseProvider.tsx');
  const frame = read('app/components/workspace/CaseFrame.tsx');
  const settings = read('app/components/workspace/SettingsPage.tsx');

  it('calls DELETE /api/v1/kadi/cases/{caseId} with the case header (token for a guest case, cookie for an owned one)', () => {
    assert.match(api, /export async function deleteCase\(ref: CaseRef\)[\s\S]*?apiFetch\(casePath\(ref\.id\), \{ method: "DELETE", headers: caseHeaders\(ref\) \}\)/);
    const store = read('app/lib/caseStore.ts');
    assert.match(store, /ref\?\.token \? \{ "X-Case-Access-Token": ref\.token \} : \{\}/);
  });

  it('asks for confirmation before deleting (destructive, irreversible action)', () => {
    for (const src of [frame, settings]) {
      assert.match(src, /<ConfirmationDialog[\s\S]*?destructive/);
      assert.ok(!/window\.confirm\(/.test(src));
    }
  });

  it('clears local case state after a successful deletion, not just on the server', () => {
    const fn = provider.match(/const removeCase = useCallback\(async \(\) => \{[\s\S]*?\n  \}, \[ref\]\);/);
    assert.ok(fn, 'removeCase not found');
    assert.match(fn![0], /await deleteCase\(ref\)/);
    assert.match(fn![0], /removeGuestCase\(ref\.id\)/);
    assert.match(fn![0], /clearActiveCase\(\)/);
  });

  it('the delete control only renders once a case actually exists', () => {
    assert.match(frame, /\{ref && !cs\.problem && \(\s*<div className="ws-case-actions">/);
  });
});
