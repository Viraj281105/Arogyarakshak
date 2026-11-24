import { test, describe } from 'node:test';
import assert from 'node:assert';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { BRAND_COLORS, compactSvg, emblemPaint, emblemSvg } from '../app/components/brand/geometry';

const webDir = join(__dirname, '..');
const pub = (p: string) => join(webDir, 'public', p);
const read = (p: string) => readFileSync(join(webDir, p), 'utf8');

describe('brand identity (Deep Forest / Warm Ivory)', () => {
  test('uses the official palette values', () => {
    assert.deepStrictEqual(
      [BRAND_COLORS.deepForest, BRAND_COLORS.secondaryForest, BRAND_COLORS.mutedSage, BRAND_COLORS.paleSage, BRAND_COLORS.warmIvory],
      ['#142F2B', '#244C42', '#91B49C', '#D5E7D9', '#F4F1E8'],
    );
  });

  test('every logo variant and icon file exists', () => {
    for (const f of [
      'brand/ar-emblem-primary.svg', 'brand/ar-emblem-dark.svg', 'brand/ar-emblem-mono-dark.svg',
      'brand/ar-emblem-mono-light.svg', 'brand/ar-emblem-compact.svg', 'brand/ar-emblem-compact-dark.svg',
      'brand/ar-wordmark-horizontal.svg', 'brand/ar-wordmark-horizontal-dark.svg',
      'icons/favicon.svg', 'icons/icon.svg', 'icons/icon-maskable.svg',
      'icons/favicon-32.png', 'icons/icon-192.png', 'icons/icon-512.png', 'icons/icon-maskable-512.png', 'icons/apple-touch-icon.png',
    ]) {
      assert.ok(existsSync(pub(f)), `${f} missing (run: npx tsx scripts/brand-assets.ts)`);
      assert.ok(statSync(pub(f)).size > 100, `${f} is empty`);
    }
  });

  test('static SVG files are in sync with geometry.ts (the single source)', () => {
    assert.strictEqual(readFileSync(pub('brand/ar-emblem-primary.svg'), 'utf8').trim(), emblemSvg('light'));
    assert.strictEqual(readFileSync(pub('brand/ar-emblem-mono-dark.svg'), 'utf8').trim(), emblemSvg('mono-dark'));
    assert.strictEqual(readFileSync(pub('brand/ar-emblem-compact.svg'), 'utf8').trim(), compactSvg('light'));
  });

  test('PNG icons have the declared pixel sizes', () => {
    const size = (f: string) => {
      const b = readFileSync(pub(f));
      assert.strictEqual(b.toString('ascii', 1, 4), 'PNG', f);
      return [b.readUInt32BE(16), b.readUInt32BE(20)];
    };
    assert.deepStrictEqual(size('icons/icon-192.png'), [192, 192]);
    assert.deepStrictEqual(size('icons/icon-512.png'), [512, 512]);
    assert.deepStrictEqual(size('icons/icon-maskable-512.png'), [512, 512]);
    assert.deepStrictEqual(size('icons/apple-touch-icon.png'), [180, 180]);
    assert.deepStrictEqual(size('icons/favicon-32.png'), [32, 32]);
  });

  test('manifest lists PNG and maskable icons with brand colours', () => {
    const m = JSON.parse(readFileSync(pub('manifest.webmanifest'), 'utf8'));
    assert.strictEqual(m.theme_color, '#142F2B');
    assert.strictEqual(m.background_color, '#F4F1E8');
    const srcs = m.icons.map((i: { src: string }) => i.src);
    for (const s of ['/icons/icon-192.png', '/icons/icon-512.png', '/icons/icon-maskable-512.png']) assert.ok(srcs.includes(s), s);
  });

  test('emblem files carry an accessible name; tones differ', () => {
    for (const t of ['light', 'dark', 'mono-dark', 'mono-light'] as const) {
      assert.match(emblemSvg(t), /role="img" aria-label="ArogyaRakshak"/);
      assert.match(emblemSvg(t), /<title>ArogyaRakshak<\/title>/);
    }
    assert.notDeepStrictEqual(emblemPaint('light'), emblemPaint('dark'));
  });

  test('brand components are Server-safe (no hooks, no "use client") and every animation honours reduced motion', () => {
    const src = read('app/components/brand/Brand.tsx');
    assert.ok(!src.includes('"use client"'));
    assert.ok(!/\buse(State|Effect|Ref)\b/.test(src));
    assert.match(src, /role="status"/, 'loader is announced');
    const css = read('app/components/brand/brand.css');
    assert.match(css, /@media \(prefers-reduced-motion: reduce\)/);
    assert.match(css, /\[data-motion="reduce"\] \.ar-emblem--reveal/);
    assert.match(read('app/layout.tsx'), /components\/brand\/brand\.css/);
  });

  test('the header and footer use the brand components, not a generic icon', () => {
    assert.match(read('app/shell/SiteHeader.tsx'), /<ArogyaEmblem /);
    assert.match(read('app/shell/SiteFooter.tsx'), /<ArogyaWordmark /);
  });
});

describe('illustration and background library', () => {
  const illo = read('app/components/illustrations/Illustrations.tsx');
  const bg = read('app/components/illustrations/Backgrounds.tsx');
  const css = read('app/components/illustrations/illustrations.css');

  test('15 illustrations and 5 backgrounds are registered', () => {
    const names = [...illo.matchAll(/^  (\w+): \w+Illustration,$/gm)].map((m) => m[1]);
    assert.deepStrictEqual(names, ['anatomy', 'dna', 'heartbeat', 'cell', 'molecule', 'capsule', 'tablets', 'prescription', 'hospital', 'patient', 'record', 'insurance', 'scan', 'ocr', 'evidence']);
    const bgs = [...bg.matchAll(/^  (\w+): \w+Background,$/gm)].map((m) => m[1]);
    assert.deepStrictEqual(bgs, ['network', 'grid', 'botanical', 'waveform', 'documents']);
  });

  test('server-safe and deterministic: no client directive, no hooks, no Math.random', () => {
    for (const src of [illo, bg]) {
      assert.ok(!src.includes('"use client"'));
      assert.ok(!/\buse(State|Effect|Ref)\b/.test(src));
      assert.ok(!src.includes('Math.random'));
    }
  });

  test('decorative by default; backgrounds are always hidden from assistive tech', () => {
    assert.match(illo, /title \? \{ role: "img", "aria-label": title \} : \{ "aria-hidden": true/);
    assert.match(bg, /"aria-hidden": true as const/);
  });

  test('colours come from tokens only (no hex in the illustration CSS except white highlights)', () => {
    const hexes = (css.match(/#[0-9a-fA-F]{3,8}\b/g) ?? []).filter((h) => !/^#(fff|ffffff|000)$/i.test(h));
    assert.deepStrictEqual(hexes, []);
  });

  test('motion is opt-in and stops under reduced motion (OS and in-app)', () => {
    assert.match(css, /@media \(prefers-reduced-motion: no-preference\) \{\n  \.illo--animate/);
    assert.match(css, /\[data-motion="reduce"\] \.illo-bg \*/);
  });

  test('no SVG transform attribute shares an element with an animated class (CSS would replace it)', () => {
    for (const src of [illo, bg]) {
      for (const line of src.split('\n')) {
        if (/transform=/.test(line)) assert.ok(!/illo-(float|pulse|scanbeam|bg-doc|bg-leaf)\b/.test(line), line.trim());
      }
    }
  });

  test('the hospital cross is not red (protected emblem)', () => {
    assert.match(css, /\.illo \.illo-cross \{ stroke: var\(--semantic-verified\)/);
  });
});
