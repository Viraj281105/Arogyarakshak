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
  // Fontsource's latin and latin-ext subset ranges, copied verbatim.
  const LATIN =
    'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD';
  const LATIN_EXT =
    'U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF';
  const count = (needle: string) => fonts.split(needle).length - 1;

  test('uses next/font/local only (no network font loader)', () => {
    assert.match(fonts, /from "next\/font\/local"/);
    assert.ok(!/next\/font\/google/.test(fonts));
  });

  test('every src points at an installed @fontsource-variable latin or latin-ext woff2', () => {
    const srcs = [...fonts.matchAll(/path: "([^"]+\.woff2)"/g)].map((m) => m[1]);
    assert.equal(srcs.length, 6, 'latin + latin-ext for three hero families');
    assert.equal(srcs.filter((s) => /-latin-(opsz|wght)-normal/.test(s)).length, 3);
    assert.equal(srcs.filter((s) => /-latin-ext-(opsz|wght)-normal/.test(s)).length, 3);
    for (const s of srcs) {
      assert.match(s, /^\.\.\/node_modules\/@fontsource-variable\/[a-z-]+\/files\/[a-z-]+-latin(-ext)?-(opsz|wght)-normal\.woff2$/);
      assert.ok(existsSync(join(appDir, s)), `${s} does not exist`);
    }
  });

  test('latin faces are preloaded with an adjusted fallback; latin-ext faces load on demand without one', () => {
    assert.equal(count('preload: true'), 3);
    assert.equal(count('preload: false'), 3);
    assert.equal(count('display: "swap"'), 6);
    assert.equal(count('adjustFontFallback: "Times New Roman"'), 1);
    assert.equal(count('adjustFontFallback: "Arial"'), 2);
    assert.equal(count('adjustFontFallback: false'), 3);
    assert.equal(count(`{ prop: "unicode-range", value: "${LATIN}" }`), 3);
    assert.equal(count(`{ prop: "unicode-range", value: "${LATIN_EXT}" }`), 3);
  });

  test('each latin-ext face joins its latin face in ONE family, so ₹ and ā come from the brand font, not the local fallback', () => {
    // The generated "<family> Fallback" face has no unicode-range; if ₹ were only in a family
    // AFTER it in the stack, the fallback (local Arial / Times) would draw it.
    for (const fam of ['arogyaFraunces', 'arogyaJakarta', 'arogyaInter']) {
      assert.equal(count(`{ prop: "font-family", value: "${fam}" }`), 2, `${fam} must name both faces`);
    }
  });

  test('the CSS variables match the token stacks and are applied on <html>', () => {
    for (const v of ['--font-face-display', '--font-face-headline', '--font-face-sans']) {
      assert.ok(fonts.includes(`variable: "${v}"`), `fonts.ts must declare ${v}`);
    }
    assert.match(layout, /<html[^>]*className=\{fontVariables\}/);
  });
});
