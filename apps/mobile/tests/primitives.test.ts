import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import {
  CITATION_TO_EVIDENCE,
  EVIDENCE_COPY,
  EVIDENCE_STATES,
  evidenceFromCitation,
  evidenceTokenPrefix,
} from '../src/components/ui/evidence';
import * as webEvidence from '../../web/app/components/ui/evidence';
import {
  checklistSummary,
  confidenceBucket,
  sheetOffset,
  stepCountText,
  stepState,
  toastDuration,
  toastIsAssertive,
  toastReducer,
  TOAST_MAX_VISIBLE,
  type ToastItem,
} from '../src/components/ui/logic';
import { evidenceSwatch } from '../src/components/ui/tones';
import { ACTION_GLYPHS, EVIDENCE_GLYPHS, MODULE_GLYPHS, TINTABLE_ACTIONS } from '../src/icons/glyphs';
import { darkColors, lightColors } from '../src/theme/colors';

const ROOT = process.cwd();
const read = (...p: string[]) => readFileSync(join(ROOT, ...p), 'utf-8');
const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : /\.tsx?$/.test(p) ? [p] : [];
  });

// ---------- evidence vocabulary: same as web ----------

test('mobile evidence vocabulary equals the web one (states, labels, meanings, citation mapping)', () => {
  assert.deepEqual([...EVIDENCE_STATES], [...webEvidence.EVIDENCE_STATES]);
  assert.deepEqual(EVIDENCE_COPY, webEvidence.EVIDENCE_COPY);
  assert.deepEqual(CITATION_TO_EVIDENCE, webEvidence.CITATION_TO_EVIDENCE);
});

test('citation mapping: supported->verified, scheme_only->provisional, unsupported->insufficient, uncheckable->unevaluated', () => {
  assert.equal(evidenceFromCitation('supported'), 'verified');
  assert.equal(evidenceFromCitation('scheme_only'), 'provisional');
  assert.equal(evidenceFromCitation('unsupported'), 'insufficient-evidence');
  assert.equal(evidenceFromCitation('uncheckable'), 'unevaluated');
});

test('unknown citation statuses are never shown as verified', () => {
  for (const s of ['', 'unknown', 'SUPPORTED', 'verified', 'toString', '__proto__', 'constructor', 'hasOwnProperty']) {
    assert.equal(evidenceFromCitation(s), 'unevaluated', s);
    assert.equal(evidenceFromCitation(s), webEvidence.evidenceFromCitation(s), `web parity for ${s}`);
  }
});

test('every evidence state has fg/bg/border tokens in both themes and a distinct text label and glyph', () => {
  assert.equal(evidenceTokenPrefix('insufficient-evidence'), 'evidenceInsufficientEvidence');
  for (const p of [darkColors, lightColors]) {
    for (const s of EVIDENCE_STATES) {
      const sw = evidenceSwatch(p, s);
      assert.match(sw.fg, /^#[0-9A-F]{6}$/i, `${s} fg`);
      assert.match(sw.bg ?? '', /^#[0-9A-F]{6}$/i, `${s} bg`);
      assert.match(sw.border ?? '', /^#[0-9A-F]{6}$/i, `${s} border`);
    }
  }
  const labels = EVIDENCE_STATES.map((s) => EVIDENCE_COPY[s].label);
  assert.equal(new Set(labels).size, 9);
  const glyphs = EVIDENCE_STATES.map((s) => EVIDENCE_GLYPHS[s]);
  assert.equal(new Set(glyphs).size, 9, 'each evidence state has its own glyph');
  for (const g of glyphs) assert.ok(g.length > 0);
});

// ---------- icon map mirrors the web map ----------

const webKeys = (file: string, obj: string) => {
  const src = read('..', 'web', 'app', 'shell', 'icons', file);
  const body = new RegExp(`${obj}[^=]*=\\s*\\{([\\s\\S]*?)\\}`).exec(src)?.[1] ?? '';
  return [...body.matchAll(/^\s*"?([\w-]+)"?\s*:/gm)].map((m) => m[1]);
};

test('module glyph keys equal the web MODULE_ICONS keys', () => {
  const web = webKeys('moduleIcons.ts', 'MODULE_ICONS');
  assert.ok(web.length === 6, `parsed ${web.join(',')}`);
  assert.deepEqual(Object.keys(MODULE_GLYPHS).sort(), web.sort());
});

test('action glyphs cover every web ACTION_ICONS key except the keyboard-only command', () => {
  const web = webKeys('actionIcons.ts', 'ACTION_ICONS');
  assert.ok(web.length >= 14, `parsed ${web.join(',')}`);
  for (const k of web.filter((k) => k !== 'command')) assert.ok(k in ACTION_GLYPHS, `missing action ${k}`);
  for (const k of ['home', 'scan', 'cases', 'tools', 'settings']) assert.ok(k in ACTION_GLYPHS, `mobile tab ${k}`);
  for (const k of TINTABLE_ACTIONS) assert.ok(k in ACTION_GLYPHS);
});

test('evidence glyph keys equal the web EVIDENCE_ICONS keys', () => {
  assert.deepEqual(Object.keys(EVIDENCE_GLYPHS).sort(), webKeys('evidenceIcons.ts', 'EVIDENCE_ICONS').sort());
});

// ---------- pure logic ----------

test('confidenceBucket matches web: clamps and buckets at 0.85 / 0.6', () => {
  assert.deepEqual(confidenceBucket(0.93), { pct: 93, word: 'High' });
  assert.deepEqual(confidenceBucket(0.85), { pct: 85, word: 'High' });
  assert.deepEqual(confidenceBucket(0.6), { pct: 60, word: 'Medium' });
  assert.deepEqual(confidenceBucket(0.59), { pct: 59, word: 'Low' });
  assert.deepEqual(confidenceBucket(2), { pct: 100, word: 'High' });
  assert.deepEqual(confidenceBucket(-1), { pct: 0, word: 'Low' });
  assert.deepEqual(confidenceBucket(Number.NaN), { pct: 0, word: 'Low' });
});

test('steps: state per index and a clamped count', () => {
  assert.deepEqual([0, 1, 2].map((i) => stepState(i, 1)), ['done', 'current', 'upcoming']);
  assert.equal(stepCountText(0, 3), 'Step 1 of 3');
  assert.equal(stepCountText(5, 3), 'Step 3 of 3');
  assert.equal(stepCountText(-2, 3), 'Step 1 of 3');
  assert.equal(stepCountText(0, 0), 'No steps');
  assert.equal(checklistSummary([{ status: 'done' }, { status: 'todo' }, { status: 'done' }]), '2 of 3 done');
});

test('toasts: errors stay until dismissed, others 6 s; at most three; warnings/errors are assertive', () => {
  assert.equal(toastDuration({ message: 'x', tone: 'error' }), 0);
  assert.equal(toastDuration({ message: 'x' }), 6000);
  assert.equal(toastDuration({ message: 'x', tone: 'error', duration: 1000 }), 1000);
  assert.ok(toastIsAssertive('error') && toastIsAssertive('warning'));
  assert.ok(!toastIsAssertive('info') && !toastIsAssertive('success'));
  let s: ToastItem[] = [];
  for (let id = 1; id <= 5; id++) s = toastReducer(s, { type: 'show', id, input: { message: `m${id}` } });
  assert.equal(s.length, TOAST_MAX_VISIBLE);
  assert.deepEqual(s.map((t) => t.id), [3, 4, 5]);
  s = toastReducer(s, { type: 'dismiss', id: 4 });
  assert.deepEqual(s.map((t) => t.id), [3, 5]);
  assert.equal(s[0].tone, 'info');
});

test('bottom sheet does not slide under reduced motion', () => {
  assert.equal(sheetOffset(true, 800), 0);
  assert.equal(sheetOffset(false, 800), 800);
});

// ---------- source contracts ----------

const UI = join(ROOT, 'src', 'components', 'ui');
const uiSources = () => walk(UI).filter((f) => f.endsWith('.tsx')).map((f) => ({ f, src: readFileSync(f, 'utf-8') }));

test('every Pressable in the primitives has a role, a label and a 44pt minimum target', () => {
  let count = 0;
  for (const { f, src } of uiSources()) {
    // Props run to the first `>` that is not part of an arrow function's `=>`.
    for (const m of src.matchAll(/<Pressable\b((?:=>|[^>])*)>/g)) {
      count++;
      const props = m[1];
      assert.match(props, /accessibilityRole=/, `${f}: Pressable without accessibilityRole`);
      assert.match(props, /accessibilityLabel=/, `${f}: Pressable without accessibilityLabel`);
      assert.match(props, /minTouchTarget/, `${f}: Pressable without a 44pt minimum`);
    }
  }
  assert.ok(count >= 2, 'expected the sheet close and toast dismiss buttons');
});

test('animated primitives respect reduced motion (motion layer only, no gesture or animation library)', () => {
  const overlays = read('src', 'components', 'ui', 'Overlays.tsx');
  assert.match(overlays, /useReducedMotion\(\)/);
  assert.match(overlays, /NATIVE_DRIVER/);
  assert.match(read('src', 'components', 'ui', 'States.tsx'), /useReducedMotion\(\)/);
  assert.match(read('src', 'components', 'ui', 'Toast.tsx'), /<Reveal>/);
  for (const { f, src } of uiSources()) {
    assert.doesNotMatch(src, /react-native-(reanimated|gesture-handler|svg)|lucide/, f);
  }
});

test('icon libraries stay out until a budget ruling (measured over budget in Wave 3 M2)', () => {
  const pkg = JSON.parse(read('package.json'));
  const deps = { ...pkg.dependencies, ...pkg.devDependencies };
  for (const name of ['react-native-svg', 'lucide-react-native']) {
    assert.ok(!(name in deps), `${name} was measured over the 2,600,000 B budget; see performance-budgets.md`);
  }
});

test('the primitives gallery is dev-only: loaded only through a __DEV__ conditional require in App.tsx', () => {
  const app = read('App.tsx');
  assert.match(app, /=\s*__DEV__\s*\?\s*require\('\.\/src\/dev\/PrimitivesGallery'\)/);
  assert.doesNotMatch(app, /import[^;]*dev\/PrimitivesGallery/);
  for (const f of walk(join(ROOT, 'src'))) {
    if (f.includes(join('src', 'dev'))) continue;
    assert.doesNotMatch(readFileSync(f, 'utf-8'), /dev\/PrimitivesGallery/, `${f} must not import the gallery`);
  }
});

test('Button no longer draws white on a coloured fill', () => {
  const src = read('src', 'components', 'Button.tsx');
  assert.match(src, /buttonSwatch\(/);
  assert.doesNotMatch(src, /colors\.brandCyan/);
  assert.doesNotMatch(src, /#fff/i);
});
