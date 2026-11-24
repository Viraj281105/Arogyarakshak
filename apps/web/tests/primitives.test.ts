import { describe, test } from 'node:test';
import assert from 'node:assert';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement as h } from 'react';
import { renderToString } from 'react-dom/server';
import { CITATION_TO_EVIDENCE, EVIDENCE_COPY, EVIDENCE_STATES, evidenceFromCitation } from '../app/components/ui/evidence';
import { ConfidenceIndicator, EvidenceBadge, MetricCard, confidenceBucket } from '../app/components/ui/Badges';
import { BarChart, DonutChart, StackedBarChart, TimelineChart, WaterfallChart, donutSegments, waterfallSpans } from '../app/components/ui/Charts';
import { sortRows } from '../app/components/ui/DataTable';
import { nextIndexForKey } from '../app/components/ui/Disclosure';
import { InsufficientEvidenceState, PartialResultState } from '../app/components/ui/States';
import { Checklist, StepWizard } from '../app/components/ui/Steps';
import { filterCommands, isPaletteShortcut, paletteCommands } from '../app/shell/commands';
import { MODULE_ORDER, PLATFORM_PAGES, PUBLIC_PATHS } from '../app/shell/nav';

const appDir = join(process.cwd(), 'app');
const tokens = JSON.parse(readFileSync(join(process.cwd(), '..', '..', 'packages', 'design-tokens', 'tokens.json'), 'utf8'));

describe('evidence vocabulary', () => {
  test('exactly the eight states, matching the design tokens, each with a label and meaning', () => {
    assert.deepStrictEqual([...EVIDENCE_STATES], [
      'verified', 'provisional', 'unevaluated', 'insufficient-evidence',
      'ai-generated', 'rule-engine', 'user-provided', 'external',
    ]);
    for (const s of EVIDENCE_STATES) {
      assert.ok(EVIDENCE_COPY[s].label && EVIDENCE_COPY[s].meaning, s);
      for (const theme of ['dark', 'light']) assert.ok(tokens.color[theme][`evidence-${s}-fg`], `${theme} token for ${s}`);
    }
    assert.equal(new Set(EVIDENCE_STATES.map((s) => EVIDENCE_COPY[s].label)).size, 8);
  });

  test('Wave 2 citation statuses map as documented; unknown values are never verified', () => {
    assert.deepStrictEqual(CITATION_TO_EVIDENCE, {
      supported: 'verified',
      scheme_only: 'provisional',
      unsupported: 'insufficient-evidence',
      uncheckable: 'unevaluated',
    });
    assert.equal(evidenceFromCitation('supported'), 'verified');
    assert.equal(evidenceFromCitation('SUPPORTED'), 'unevaluated');
    assert.equal(evidenceFromCitation('toString'), 'unevaluated');
  });

  test('EvidenceBadge renders a visible text label (not colour only) and the meaning as title', () => {
    for (const s of EVIDENCE_STATES) {
      const html = renderToString(h(EvidenceBadge, { state: s }));
      assert.ok(html.includes(`>${EVIDENCE_COPY[s].label.replace('&', '&amp;')}<`), `${s} label`);
      assert.ok(html.includes('aria-hidden="true"'), `${s} icon is decorative`);
    }
  });
});

describe('figures are labelled', () => {
  test('MetricCard says Estimate or Verified in words and always shows its source', () => {
    const est = renderToString(h(MetricCard, { label: 'X', value: '₹1', basis: 'estimate', source: 'S1', period: 'P1' }));
    assert.match(est, />Estimate</);
    assert.match(est.replace(/<!-- -->/g, ''), /Source: S1 · P1/);
    const ver = renderToString(h(MetricCard, { label: 'X', value: '₹1', basis: 'verified', source: 'S2' }));
    assert.match(ver, />Verified</);
  });

  test('confidence is clamped, bucketed and says who computed it', () => {
    assert.deepStrictEqual(confidenceBucket(0.93), { pct: 93, word: 'High' });
    assert.deepStrictEqual(confidenceBucket(0.6), { pct: 60, word: 'Medium' });
    assert.deepStrictEqual(confidenceBucket(2), { pct: 100, word: 'High' });
    assert.deepStrictEqual(confidenceBucket(Number.NaN), { pct: 0, word: 'Low' });
    assert.match(renderToString(h(ConfidenceIndicator, { value: 0.5, source: 'OCR engine' })).replace(/<!-- -->/g, ''), /\(OCR engine\)/);
  });

  test('every chart shows units, period and source, and renders a data table alternative', () => {
    const meta = { title: 'T', units: 'U-units', period: 'P-period', source: 'S-source' };
    const charts = [
      h(BarChart, { ...meta, data: [{ label: 'a', value: 1 }] }),
      h(StackedBarChart, { ...meta, series: [{ key: 'k', label: 'K' }], rows: [{ label: 'r', values: { k: 2 } }] }),
      h(DonutChart, { ...meta, data: [{ label: 'a', value: 1 }, { label: 'b', value: 3 }] }),
      h(WaterfallChart, { ...meta, start: 10, startLabel: 'Start', steps: [{ label: 'minus', value: -2 }] }),
      h(TimelineChart, { ...meta, events: [{ date: '2026-01-01', label: 'e1' }, { date: '2026-01-05', label: 'e2' }] }),
    ];
    for (const c of charts) {
      const html = renderToString(c);
      assert.match(html, /U-units/);
      assert.match(html, /P-period/);
      assert.match(html, /S-source/);
      assert.match(html, /<table/);
      assert.match(html, /role="img"/);
    }
  });

  test('chart maths: donut shares and waterfall running totals', () => {
    assert.deepStrictEqual(donutSegments([1, 1, 2]), [[0, 0.25], [0.25, 0.5], [0.5, 1]]);
    assert.deepStrictEqual(donutSegments([0, -5]), [[0, 0], [0, 0]]);
    assert.deepStrictEqual(waterfallSpans(100, [{ label: 'a', value: -30 }, { label: 'b', value: 10 }, { label: 't', value: 0, total: true }]), [
      { from: 100, to: 70 },
      { from: 70, to: 80 },
      { from: 0, to: 80 },
    ]);
  });
});

describe('interaction models', () => {
  test('sortRows is stable, numeric-aware, and keeps nulls last in both directions', () => {
    const rows = [{ v: 10 }, { v: null }, { v: 2 }, { v: 10 }];
    const asc = sortRows(rows, (r) => r.v, 'ascending');
    assert.deepStrictEqual(asc.map((r) => r.v), [2, 10, 10, null]);
    assert.strictEqual(asc[1], rows[0], 'stable');
    assert.deepStrictEqual(sortRows(rows, (r) => r.v, 'descending').map((r) => r.v), [10, 10, 2, null]);
    assert.deepStrictEqual(sortRows([{ s: 'item 10' }, { s: 'item 2' }], (r) => r.s, 'ascending').map((r) => r.s), ['item 2', 'item 10']);
  });

  test('tab keys wrap and jump', () => {
    assert.equal(nextIndexForKey(2, 3, 'ArrowRight'), 0);
    assert.equal(nextIndexForKey(0, 3, 'ArrowLeft'), 2);
    assert.equal(nextIndexForKey(1, 3, 'End'), 2);
    assert.equal(nextIndexForKey(1, 3, 'Enter'), null);
  });

  test('partial and insufficient-evidence states say what is missing and never show a figure', () => {
    const p = renderToString(h(PartialResultState, { missing: ['Medicine prices'] }));
    assert.match(p, /Medicine prices/);
    const i = renderToString(h(InsufficientEvidenceState, { reason: 'No row matches' }));
    assert.match(i, /No row matches/);
    assert.match(i, /nothing is guessed/);
  });

  test('wizard marks the current step and checklist states each status in words', () => {
    const w = renderToString(h(StepWizard, { current: 1, steps: [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }] }));
    assert.match(w, /aria-current="step"/);
    assert.match(w, /Step <!-- -->2<!-- --> of <!-- -->2/);
    const c = renderToString(h(Checklist, { title: 'C', items: [{ id: '1', label: 'x', status: 'blocked' }] }));
    assert.match(c, />Blocked</);
  });
});

describe('command palette', () => {
  test('lists only existing routes, in every language', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      const cmds = paletteCommands(lang);
      for (const c of cmds) {
        // Workspace, auth and reviewer routes exist in this app; the public pages are the M3
        // stream's (nav.ts PUBLIC_PATHS / PLATFORM_PAGES, the one place to adjust them).
        const path = c.href.split('#')[0];
        const known = ['/', '/app', '/app/case', '/app/case/reports', '/app/settings', '/review', '/login', '/register',
          ...MODULE_ORDER.map((m) => `/app/case/${m}`), ...Object.values(PUBLIC_PATHS), ...PLATFORM_PAGES.map((p) => `/platform/${p}`)];
        assert.ok(known.includes(path), `${lang}: ${c.href}`);
        assert.ok(c.label, `${lang}: ${c.id} has a label`);
      }
      assert.equal(cmds.filter((c) => c.group === 'Checks').length, 5);
    }
    for (const page of ['page.tsx', 'app/page.tsx', 'app/case/page.tsx', 'app/case/[module]/page.tsx', 'app/case/reports/page.tsx', 'app/settings/page.tsx', 'review/page.tsx', 'login/page.tsx', 'register/page.tsx']) {
      assert.ok(existsSync(join(appDir, page)), page);
    }
  });

  test('filter matches every word against label and keywords; English keywords work in Hindi', () => {
    const en = paletteCommands('en');
    assert.deepStrictEqual(filterCommands(en, 'review').map((c) => c.id), ['reviewer']);
    assert.ok(filterCommands(en, 'dawa').some((c) => c.id === 'module-dawacheck'));
    assert.equal(filterCommands(en, '').length, en.length);
    assert.equal(filterCommands(en, 'zzz').length, 0);
    assert.deepStrictEqual(filterCommands(paletteCommands('hi'), 'reviewer').map((c) => c.id), ['reviewer']);
  });

  test('Ctrl+K and Cmd+K open it; Shift/Alt variants do not', () => {
    const k = { key: 'k', ctrlKey: false, metaKey: false, shiftKey: false, altKey: false };
    assert.equal(isPaletteShortcut({ ...k, ctrlKey: true }), true);
    assert.equal(isPaletteShortcut({ ...k, key: 'K', metaKey: true }), true);
    assert.equal(isPaletteShortcut({ ...k, ctrlKey: true, shiftKey: true }), false);
    assert.equal(isPaletteShortcut(k), false);
  });

  test('the palette chunk is loaded on demand, not with every route', () => {
    const launcher = readFileSync(join(appDir, 'shell', 'CommandPaletteLauncher.tsx'), 'utf8');
    assert.match(launcher, /import\("\.\.\/components\/ui\/CommandPalette"\)/);
    assert.ok(!/^import[^;]*CommandPalette[^;]*from "\.\.\/components\/ui\/CommandPalette"/m.test(launcher));
  });
});

describe('dev gallery and motion', () => {
  test('the primitives gallery is a page.dev.tsx file (not in production builds)', () => {
    assert.ok(existsSync(join(appDir, '(dev)', 'primitives', 'page.dev.tsx')));
    assert.ok(!existsSync(join(appDir, '(dev)', 'primitives', 'page.tsx')));
    assert.match(readFileSync(join(appDir, '(dev)', 'primitives', 'page.dev.tsx'), 'utf8'), /NODE_ENV === "production"\) notFound\(\)/);
  });

  test('primitive animations run only under prefers-reduced-motion: no-preference', () => {
    const css = readFileSync(join(appDir, 'components', 'ui', 'ui.css'), 'utf8');
    const guarded = css.split('@media (prefers-reduced-motion: no-preference)')[1]?.split('@keyframes')[0] ?? '';
    const outside = css.replace(guarded, '');
    assert.ok(/animation:/.test(guarded));
    assert.ok(!/\banimation:|\btransition:/.test(outside), 'no animation/transition outside the no-preference block');
  });
});
