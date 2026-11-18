import { describe, test } from 'node:test';
import assert from 'node:assert';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

// WS4: components that are not on screen at first paint load through next/dynamic, so they
// stay out of the route's initial JS (scripts/build-checks/web-bundle-budget.mjs).
const appDir = join(__dirname, '..', 'app');
const read = (...p: string[]) => readFileSync(join(appDir, ...p), 'utf8');
const code = (src: string) => src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');

function assertLazy(src: string, name: string, from: string) {
  const staticImport = new RegExp(`^import[^;]*\\b${name}\\b[^;]*from\\s+["']${from.replace(/[./]/g, '\\$&')}["']`, 'm');
  assert.ok(!staticImport.test(src), `${name} must not be imported statically`);
  const lazy = new RegExp(`dynamic\\(\\s*\\(\\)\\s*=>\\s*import\\(["']${from.replace(/[./]/g, '\\$&')}["']\\)`);
  assert.ok(lazy.test(src), `${name} must be loaded with next/dynamic from ${from}`);
}

describe('home route code splitting', () => {
  const page = code(read('page.tsx'));

  test('inactive module views are dynamic; the default BillNyay view stays static (it renders at first paint)', () => {
    assertLazy(page, 'BimaNyayView', './components/modules/BimaNyayView');
    assertLazy(page, 'DaaviSetuView', './components/modules/DaaviSetuView');
    assertLazy(page, 'SchemeSetuView', './components/modules/SchemeSetuView');
    assertLazy(page, 'DawaCheckView', './components/modules/DawaCheckView');
    assert.match(page, /^import \{ BillNyayView \} from "\.\/components\/modules\/BillNyayView";/m);
  });

  test('case-desk components that only render once a case exists are dynamic', () => {
    assertLazy(page, 'AgentStreamVisualizer', './components/AgentStreamVisualizer');
    assertLazy(page, 'SafetyEscalationBanner', './components/clinical/SafetyEscalationBanner');
    assertLazy(page, 'EntityResolutionReview', './components/EntityResolutionReview');
    assertLazy(page, 'ClaimPackPanel', './components/ClaimPackPanel');
    assertLazy(page, 'CaseTimeline', './components/CaseTimeline');
  });

  test('demo controls load only in demo mode', () => {
    assertLazy(page, 'DemoControls', './components/demo/DemoControls');
    assert.match(page, /demoStatus\?\.demo_mode && <DemoControls/);
  });
});

describe('reviewer workspace code splitting', () => {
  test('the three tabs (shown only after sign-in) are dynamic', () => {
    const page = code(read('clinical-review', 'page.tsx'));
    assertLazy(page, 'ReviewsTab', './components/ReviewsTab');
    assertLazy(page, 'TranscriptionTab', './components/TranscriptionTab');
    assertLazy(page, 'SafetyTab', './components/SafetyTab');
  });
});

describe('dev-only motion lab is not part of production builds', () => {
  test('the gallery is a page.dev.tsx file and next.config only adds that extension in development', () => {
    assert.ok(existsSync(join(appDir, '(dev)', 'motion-lab', 'page.dev.tsx')));
    assert.ok(!existsSync(join(appDir, '(dev)', 'motion-lab', 'page.tsx')));
    const cfg = readFileSync(join(__dirname, '..', 'next.config.ts'), 'utf8');
    assert.match(cfg, /pageExtensions/);
    assert.match(cfg, /NODE_ENV\s*===\s*["']development["']/);
    assert.match(cfg, /["']dev\.tsx["']/);
  });
});

describe('status pages do not pull next/link into every route', () => {
  test('StatusPage, not-found, error and global-error use plain anchors', () => {
    for (const f of [['components', 'StatusPage.tsx'], ['not-found.tsx'], ['error.tsx'], ['global-error.tsx']]) {
      assert.ok(!/from "next\/link"/.test(read(...f)), `${f.join('/')} imports next/link`);
    }
  });
});
