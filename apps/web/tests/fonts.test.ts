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

  test('stacks name the Fontsource variable family first', () => {
    assert.match(tokens.font.display, /^'Fraunces Variable'/);
    assert.match(tokens.font.headline, /^'Plus Jakarta Sans Variable'/);
    assert.match(tokens.font.sans, /^'Inter Variable'/);
    assert.match(tokens.font.mono, /^'JetBrains Mono Variable'/);
  });
});
