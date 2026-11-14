import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

const appDir = join(__dirname, '..', 'app');
const globals = readFileSync(join(appDir, 'globals.css'), 'utf8');
const tokens = readFileSync(join(appDir, 'generated', 'tokens.css'), 'utf8');

const declared = (css: string): Set<string> =>
  new Set([...css.matchAll(/(^|[;{\s])(--[\w-]+)\s*:/g)].map((m) => m[2]));

// Custom properties set at runtime (inline style={{ "--x": ... }} or el.style.setProperty),
// so they are legitimately consumed via var() without any stylesheet declaration.
const RUNTIME_SET = new Set([
  '--i', // style={{ "--i": i }} in landing components (stagger index)
  '--row', // style={{ "--row": i }} in HeroIllustration / StatusPage
  '--journey-progress', // useScrollProgress(ref, "--journey-progress") in CaseJourney.tsx
  '--hero-progress', // useScrollProgress(ref, "--hero-progress") in LandingHero.tsx
]);

describe('globals.css adopts generated design tokens', () => {
  test('imports ./generated/tokens.css before any other rule that is not an @import', () => {
    const stripped = globals.replace(/\/\*[\s\S]*?\*\//g, '');
    assert.match(stripped, /@import\s+["']\.\/generated\/tokens\.css["'];/);
    const firstNonImport = stripped.search(/^(?!\s*@import)\s*[^\s@]/m);
    const importAt = stripped.search(/@import\s+["']\.\/generated\/tokens\.css["']/);
    assert.ok(importAt >= 0 && importAt < firstNonImport, 'tokens import must precede all rules');
  });

  test('contains no hand-written custom property that tokens.css also defines', () => {
    const own = declared(globals);
    const dupes = [...declared(tokens)].filter((v) => own.has(v));
    assert.deepStrictEqual(dupes, []);
  });

  test('every var(--x) used in globals.css is defined in tokens.css or globals.css', () => {
    const defined = new Set([...declared(tokens), ...declared(globals), ...RUNTIME_SET]);
    const used = new Set([...globals.matchAll(/var\(\s*(--[\w-]+)/g)].map((m) => m[1]));
    const missing = [...used].filter((v) => !defined.has(v));
    assert.deepStrictEqual(missing, []);
  });
});
