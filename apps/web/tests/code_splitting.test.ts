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

describe('workspace route (/app) code splitting', () => {
  // app/app/page.tsx is a Server Component; the interactive part lives in HomeWorkspace.
  const page = code(read('components', 'HomeWorkspace.tsx'));

  test('inactive module views are dynamic; the default BillNyay view stays static (it renders at first paint)', () => {
    assertLazy(page, 'BimaNyayView', './modules/BimaNyayView');
    assertLazy(page, 'DaaviSetuView', './modules/DaaviSetuView');
    assertLazy(page, 'SchemeSetuView', './modules/SchemeSetuView');
    assertLazy(page, 'DawaCheckView', './modules/DawaCheckView');
    assert.match(page, /^import \{ BillNyayView \} from "\.\/modules\/BillNyayView";/m);
  });

  test('case-desk components that only render once a case exists are dynamic', () => {
    assertLazy(page, 'AgentStreamVisualizer', './AgentStreamVisualizer');
    assertLazy(page, 'SafetyEscalationBanner', './clinical/SafetyEscalationBanner');
    assertLazy(page, 'EntityResolutionReview', './EntityResolutionReview');
    assertLazy(page, 'ClaimPackPanel', './ClaimPackPanel');
    assertLazy(page, 'CaseTimeline', './CaseTimeline');
  });

  test('demo controls load only in demo mode', () => {
    assertLazy(page, 'DemoControls', './demo/DemoControls');
    assert.match(page, /demoStatus\?\.demo_mode && <DemoControls/);
  });

  test('every dynamic() call has a sized, busy loading placeholder', () => {
    for (const src of [page, code(read('review', 'page.tsx'))]) {
      const calls = src.split('dynamic(').length - 1;
      const withLoading = (src.match(/loading: (moduleLoading|tabLoading|\(\) => <LazyPanel minHeight="[\d.]+rem" \/>)/g) ?? []).length;
      assert.ok(calls > 0);
      assert.equal(withLoading, calls, 'each dynamic() needs loading: <LazyPanel minHeight=...>');
    }
    const lazy = read('components', 'LazyPanel.tsx');
    assert.match(lazy, /aria-busy="true"/);
    assert.match(lazy, /style=\{\{ minHeight \}\}/);
  });
});

describe('static landing sections are Server Components (no client JS)', () => {
  test('hero, journey and reference coverage have no "use client" and are rendered by the server page', () => {
    for (const f of ['LandingHero.tsx', 'CaseJourney.tsx', 'ReferenceCoverage.tsx', 'HeroIllustration.tsx']) {
      assert.ok(!/^\s*["']use client["']/.test(read('components', 'landing', f)), `${f} must stay a Server Component`);
    }
    const serverPage = read('page.tsx');
    assert.ok(!/["']use client["']/.test(serverPage));
    assert.match(serverPage, /<LandingPage hero=\{<LandingHero \/>\} journey=\{<CaseJourney \/>\} coverage=\{<ReferenceCoverage \/>\}/);
    // The workspace moved to /app (Wave 3 M2); its route file is a Server Component too.
    assert.ok(!/["']use client["']/.test(read('app', 'page.tsx')), 'app/app/page.tsx must stay a Server Component');
    assert.ok(!/HomeWorkspace/.test(serverPage), 'the landing route must not ship the workspace');
    const landing = read('components', 'landing', 'Landing.tsx');
    assert.ok(!/import \{ (LandingHero|CaseJourney|ReferenceCoverage) \}/.test(landing), 'Landing must not import them');
  });
});

describe('reviewer workspace code splitting', () => {
  test('the three tabs (shown only after sign-in) are dynamic', () => {
    const page = code(read('review', 'page.tsx'));
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
