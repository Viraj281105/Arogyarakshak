import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { ACTION_ICONS } from '../app/shell/icons/actionIcons';
import { EVIDENCE_ICONS } from '../app/shell/icons/evidenceIcons';
import { MODULE_ICONS } from '../app/shell/icons/moduleIcons';
import { MODULE_ORDER } from '../app/shell/nav';

const appDir = join(process.cwd(), 'app');

function sources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return name === 'generated' || name === 'shared' ? [] : sources(p);
    return /\.(ts|tsx)$/.test(name) ? [p] : [];
  });
}

describe('icon map (lucide-react, decision D3)', () => {
  test('every check and Kadi documents has a module icon', () => {
    for (const id of [...MODULE_ORDER, 'kadi'] as const) {
      assert.ok(MODULE_ICONS[id], `${id} has no icon`);
    }
  });

  test('evidence icons cover exactly the eight evidence states', () => {
    assert.deepStrictEqual(Object.keys(EVIDENCE_ICONS), [
      'verified', 'provisional', 'unevaluated', 'insufficient-evidence',
      'ai-generated', 'rule-engine', 'user-provided', 'external',
    ]);
    assert.ok(Object.keys(ACTION_ICONS).length >= 10);
  });

  test('lucide icons are imported one file at a time (never the package barrel for values)', () => {
    for (const file of sources(appDir)) {
      const src = readFileSync(file, 'utf8');
      for (const m of src.matchAll(/^import\s+(type\s+)?[^;]*from\s+["']lucide-react(\/[^"']*)?["']/gm)) {
        const isType = Boolean(m[1]);
        const sub = m[2] ?? '';
        assert.ok(isType || sub.startsWith('/icons/'), `${file}: value import from "lucide-react${sub}"`);
      }
    }
  });

  test('nav.ts no longer hand-codes SVG paths', () => {
    const nav = readFileSync(join(appDir, 'shell', 'nav.ts'), 'utf8');
    assert.ok(!/icon:\s*"M/.test(nav));
  });
});
