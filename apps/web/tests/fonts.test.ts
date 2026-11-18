import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join } from 'node:path';

const webDir = join(__dirname, '..');
const appDir = join(webDir, 'app');
const tokens = JSON.parse(
  readFileSync(join(webDir, '..', '..', 'packages', 'design-tokens', 'tokens.json'), 'utf8'),
) as { font: Record<string, string> };

const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });

const FAMILIES = ['fraunces', 'plus-jakarta-sans', 'inter', 'jetbrains-mono'];
const GENERIC = ['serif', 'sans-serif', 'monospace', 'system-ui'];

describe('self-hosted fonts', () => {
  test('no fonts.googleapis.com or fonts.gstatic.com reference anywhere under app/ or next.config.ts', () => {
    const files = [...walk(appDir), join(webDir, 'next.config.ts')].filter((p) =>
      /\.(css|tsx?|mjs|js|json)$/.test(p),
    );
    for (const f of files) {
      const text = readFileSync(f, 'utf8');
      assert.ok(!/fonts\.(googleapis|gstatic)\.com/.test(text), `${f} references a Google font host`);
    }
  });

  test('does not use next/font/google', () => {
    for (const f of walk(appDir).filter((p) => /\.tsx?$/.test(p))) {
      assert.ok(!readFileSync(f, 'utf8').includes('next/font/google'), `${f} uses next/font/google`);
    }
  });

  test('@fontsource-variable imports exist for all four families', () => {
    const src = [join(appDir, 'globals.css'), join(appDir, 'layout.tsx')]
      .map((p) => readFileSync(p, 'utf8'))
      .join('\n');
    for (const fam of FAMILIES) {
      assert.ok(src.includes(`@fontsource-variable/${fam}/`), `missing @fontsource-variable/${fam} import`);
      assert.ok(
        existsSync(join(webDir, 'node_modules', '@fontsource-variable', fam, 'package.json')),
        `@fontsource-variable/${fam} not installed`,
      );
    }
  });

  test('each font stack in tokens ends with a generic family', () => {
    for (const [name, stack] of Object.entries(tokens.font)) {
      const last = stack.split(',').pop()!.trim().toLowerCase();
      assert.ok(GENERIC.includes(last), `font.${name} must end with a generic family, got ${last}`);
    }
  });

  test('font stacks keep a Devanagari-capable fallback (Noto Sans Devanagari, Mangal, or system-ui)', () => {
    for (const [name, stack] of Object.entries(tokens.font)) {
      assert.match(stack, /Noto Sans Devanagari|Mangal|system-ui/, `font.${name} lacks a Devanagari fallback`);
    }
  });

  test('stacks put the preloaded next/font face first, then the Fontsource variable family', () => {
    // var(--font-face-*) is set on <html> by app/fonts.ts; without it the var() falls back to
    // the Fontsource family, so the stack still works anywhere the variable is missing.
    assert.match(tokens.font.display, /^var\(--font-face-display, 'Fraunces Variable'\), 'Fraunces Variable',/);
    assert.match(tokens.font.headline, /^var\(--font-face-headline, 'Plus Jakarta Sans Variable'\), 'Plus Jakarta Sans Variable',/);
    assert.match(tokens.font.sans, /^var\(--font-face-sans, 'Inter Variable'\), 'Inter Variable',/);
    assert.match(tokens.font.mono, /^'JetBrains Mono Variable'/);
  });
});

describe('CLS: preloaded latin faces with metric-matched fallbacks (next/font/local)', () => {
  const fonts = readFileSync(join(appDir, 'fonts.ts'), 'utf8');
  const layout = readFileSync(join(appDir, 'layout.tsx'), 'utf8');
  // Fontsource's latin subset range, so ₹ and other latin-ext glyphs still come from the
  // Fontsource faces next in the stack.
  const LATIN =
    'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD';

  test('uses next/font/local only (no network font loader)', () => {
    assert.match(fonts, /from "next\/font\/local"/);
    assert.ok(!/next\/font\/google/.test(fonts));
  });

  test('every src points at an installed @fontsource-variable latin woff2', () => {
    const srcs = [...fonts.matchAll(/path: "([^"]+\.woff2)"/g)].map((m) => m[1]);
    assert.equal(srcs.length, 3, 'expected three hero families');
    for (const s of srcs) {
      assert.match(s, /^\.\.\/node_modules\/@fontsource-variable\/[a-z-]+\/files\/[a-z-]+-latin-(opsz|wght)-normal\.woff2$/);
      assert.ok(existsSync(join(appDir, s)), `${s} does not exist`);
    }
  });

  test('each face is preloaded, swaps, has an adjusted fallback and is limited to the latin range', () => {
    assert.equal((fonts.match(/preload: true/g) ?? []).length, 3);
    assert.equal((fonts.match(/display: "swap"/g) ?? []).length, 3);
    assert.equal((fonts.match(/adjustFontFallback: "Times New Roman"/g) ?? []).length, 1);
    assert.equal((fonts.match(/adjustFontFallback: "Arial"/g) ?? []).length, 2);
    assert.ok(fonts.includes(LATIN), 'latin unicode-range must match Fontsource exactly');
    assert.equal(fonts.split(`declarations: [{ prop: "unicode-range", value: "${LATIN}" }]`).length - 1, 3);
  });

  test('the CSS variables match the token stacks and are applied on <html>', () => {
    for (const v of ['--font-face-display', '--font-face-headline', '--font-face-sans']) {
      assert.ok(fonts.includes(`variable: "${v}"`), `fonts.ts must declare ${v}`);
    }
    assert.match(layout, /<html[^>]*className=\{fontVariables\}/);
  });
});
