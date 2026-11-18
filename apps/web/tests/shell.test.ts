import { describe, mock, test } from 'node:test';
import assert from 'node:assert';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createElement } from 'react';
import { renderToString } from 'react-dom/server';
import { nextHeaderState, type HeaderState } from '../app/shell/headerScroll';
import { isActiveHref, moduleFromHash, moduleHash, NAV_ITEMS, MODULE_ORDER } from '../app/shell/nav';
import { ROUTE_COMMIT_TIMEOUT_MS, routeCommitted, shouldTransition, waitForRouteCommit } from '../app/shell/routeTransition';
import { shellCopy, HTML_LANG } from '../app/shell/shellCopy';
import { PageContainer, PageSection } from '../app/shell/Page';
import { translations } from '../app/translations';
import { common } from '../app/shared/i18n/common';

const webDir = join(__dirname, '..');
const appDir = join(webDir, 'app');
const read = (...p: string[]) => readFileSync(join(appDir, ...p), 'utf8');

describe('nextHeaderState (scroll-aware header)', () => {
  const base = { y: 0, lastY: 0, compact: true, reducedMotion: false, pinned: false };
  const start: HeaderState = { elevated: false, hidden: false };

  test('elevates after 8 px and drops the elevation at the top again', () => {
    assert.deepEqual(nextHeaderState(start, { ...base, y: 4 }), { elevated: false, hidden: false });
    assert.deepEqual(nextHeaderState(start, { ...base, y: 9 }), { elevated: true, hidden: false });
    assert.equal(nextHeaderState({ elevated: true, hidden: false }, { ...base, y: 0, lastY: 30 }).elevated, false);
  });

  test('on small screens hides when scrolling down past 120 px and shows on any upward scroll', () => {
    assert.equal(nextHeaderState(start, { ...base, y: 100, lastY: 60 }).hidden, false, 'not before 120 px');
    assert.equal(nextHeaderState(start, { ...base, y: 200, lastY: 150 }).hidden, true);
    assert.equal(nextHeaderState({ elevated: true, hidden: true }, { ...base, y: 190, lastY: 200 }).hidden, false);
  });

  test('ignores jitter below 6 px (keeps the previous hidden state)', () => {
    assert.equal(nextHeaderState({ elevated: true, hidden: true }, { ...base, y: 400, lastY: 403 }).hidden, true);
    assert.equal(nextHeaderState({ elevated: true, hidden: false }, { ...base, y: 403, lastY: 400 }).hidden, false);
  });

  test('never hides on wide screens, under reduced motion, or while pinned (drawer open / focus inside)', () => {
    const down = { ...base, y: 600, lastY: 500 };
    assert.equal(nextHeaderState(start, { ...down, compact: false }).hidden, false);
    assert.equal(nextHeaderState(start, { ...down, reducedMotion: true }).hidden, false);
    assert.equal(nextHeaderState({ elevated: true, hidden: true }, { ...down, pinned: true }).hidden, false);
  });
});

describe('navigation model', () => {
  test('the five checks map to and from #module-<id> hashes', () => {
    assert.deepEqual(MODULE_ORDER, ['billnyay', 'daavisetu', 'bimanyay', 'schemesetu', 'dawacheck']);
    for (const id of MODULE_ORDER) assert.equal(moduleFromHash(moduleHash(id)), id);
    assert.equal(moduleFromHash('#module-unknown'), null);
    assert.equal(moduleFromHash(''), null);
    assert.equal(moduleFromHash('#intake-dropzone'), null);
  });

  test('isActiveHref matches the route, never a hash link on the home page', () => {
    assert.equal(isActiveHref('/clinical-review', '/clinical-review'), true);
    assert.equal(isActiveHref('/clinical-review', '/'), false);
    assert.equal(isActiveHref('/#intake-dropzone', '/'), false);
    assert.equal(isActiveHref('/', '/'), true);
  });

  test('every nav item has a label in all three languages', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      for (const item of NAV_ITEMS) assert.ok(shellCopy[lang].nav[item.key], `${lang}: nav.${item.key}`);
    }
  });
});

describe('route transitions', () => {
  const click = (over: Partial<Parameters<typeof shouldTransition>[0]> = {}) => ({
    button: 0,
    metaKey: false,
    ctrlKey: false,
    shiftKey: false,
    altKey: false,
    defaultPrevented: false,
    ...over,
  });
  const here = 'http://localhost:3000/';

  test('only plain left clicks to another same-origin page are transitioned', () => {
    assert.equal(shouldTransition(click(), '/clinical-review', here), true);
    assert.equal(shouldTransition(click({ metaKey: true }), '/clinical-review', here), false);
    assert.equal(shouldTransition(click({ ctrlKey: true }), '/clinical-review', here), false);
    assert.equal(shouldTransition(click({ shiftKey: true }), '/clinical-review', here), false);
    assert.equal(shouldTransition(click({ button: 1 }), '/clinical-review', here), false);
    assert.equal(shouldTransition(click({ defaultPrevented: true }), '/clinical-review', here), false);
    assert.equal(shouldTransition(click(), '/clinical-review', here, '_blank'), false);
    assert.equal(shouldTransition(click(), 'https://example.org/', here), false);
    assert.equal(shouldTransition(click(), '/#module-dawacheck', here), false, 'same-page hash links stay native');
    assert.equal(shouldTransition(click(), '/#module-dawacheck', 'http://localhost:3000/clinical-review'), true);
  });

  test('a link to the SAME pathname (search- or hash-only change) never starts a transition', () => {
    // The transition waits for the pathname to change; these links would never change it.
    assert.equal(shouldTransition(click(), '/?module=x', here), false);
    assert.equal(shouldTransition(click(), '/clinical-review?tab=safety', 'http://localhost:3000/clinical-review'), false);
    assert.equal(shouldTransition(click(), '/', here), false);
  });

  test('the wait is capped at 400 ms', () => {
    assert.equal(ROUTE_COMMIT_TIMEOUT_MS, 400);
  });

  test('fake timers: a commit before the cap resolves at once; without a commit it resolves exactly at the cap', async () => {
    mock.timers.enable({ apis: ['setTimeout'] });
    try {
      let early = false;
      const a = waitForRouteCommit().then(() => (early = true));
      mock.timers.tick(100);
      routeCommitted();
      await a;
      assert.equal(early, true);

      let done = false;
      const b = waitForRouteCommit().then(() => (done = true));
      mock.timers.tick(ROUTE_COMMIT_TIMEOUT_MS - 1);
      await Promise.resolve();
      assert.equal(done, false, 'still waiting 1 ms before the cap');
      mock.timers.tick(1);
      await b;
      assert.equal(done, true);
    } finally {
      mock.timers.reset();
    }
  });

  test('a second navigation settles the first one (no transition waits forever)', async () => {
    const first = waitForRouteCommit(5000);
    const second = waitForRouteCommit(5000);
    await first;
    routeCommitted();
    await second;
  });
});

describe('shell copy', () => {
  test('has every key in all three languages and maps <html lang>', () => {
    const keys = (o: object, p = ''): string[] =>
      Object.entries(o).flatMap(([k, v]) => (typeof v === 'object' ? keys(v, `${p}${k}.`) : [`${p}${k}`]));
    const en = keys(shellCopy.en).sort();
    for (const lang of ['hi', 'mr'] as const) assert.deepEqual(keys(shellCopy[lang]).sort(), en);
    for (const lang of ['en', 'hi', 'mr'] as const) {
      for (const k of keys(shellCopy[lang])) {
        const v = k.split('.').reduce<unknown>((o, part) => (o as Record<string, unknown>)[part], shellCopy[lang]);
        assert.ok(typeof v === 'string' && v.trim().length > 0, `${lang}.${k} is empty`);
      }
    }
    assert.deepEqual(HTML_LANG, { en: 'en', hi: 'hi', mr: 'mr' });
  });

  test('page translations reuse the shell strings instead of a second copy', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) {
      assert.equal(shellCopy[lang].appName, common[lang].appName);
      assert.equal(translations[lang].tagline, shellCopy[lang].tagline);
      assert.equal(translations[lang].byodBadge, shellCopy[lang].byodBadge);
      assert.deepEqual(translations[lang].tabs, shellCopy[lang].tabs);
      for (const k of ['disclaimer', 'statutoryNote', 'cghsRef', 'irdaiRef', 'nppaRef'] as const) {
        assert.equal(translations[lang].footer[k], shellCopy[lang].footer[k]);
      }
    }
  });

  test('the shell does not import the full page dictionary (keeps it out of every route)', () => {
    const shellFiles = ['SiteHeader.tsx', 'SiteFooter.tsx', 'MobileNav.tsx', 'ShellProvider.tsx', 'LanguageSwitcher.tsx',
      'ThemeToggle.tsx', 'SkipLink.tsx', 'TransitionLink.tsx', 'shellCopy.ts', 'nav.ts'];
    for (const f of shellFiles) {
      const src = read('shell', f);
      assert.ok(!/translations"/.test(src), `${f} imports translations.ts`);
      assert.ok(!/shared\/i18n\/common/.test(src), `${f} imports the shared i18n dictionary`);
    }
  });
});

describe('layout primitives', () => {
  test('PageContainer and PageSection render without hooks (server-safe)', () => {
    const html = renderToString(
      createElement(PageContainer, null, createElement(PageSection, { labelledBy: 'x', id: 's' }, 'hi')),
    );
    assert.match(html, /class="shell-container"/);
    assert.match(html, /<section[^>]*class="shell-section"[^>]*aria-labelledby="x"/);
  });
});

describe('root layout frame', () => {
  const layout = read('layout.tsx');

  test('renders the skip link, header, a single focusable <main> and the footer around every page', () => {
    assert.match(layout, /<SkipLink/);
    assert.match(layout, /<SiteHeader/);
    assert.match(layout, /<main id="main-content" tabIndex=\{-1\}/);
    assert.match(layout, /<SiteFooter/);
    for (const f of ['page.tsx', 'clinical-review/page.tsx', 'components/StatusPage.tsx', 'not-found.tsx', 'error.tsx']) {
      const src = read(...f.split('/'));
      // StatusPage keeps a <main> only for global-error, which replaces the root layout.
      const mains = (src.match(/<main\b/g) ?? []).length;
      assert.ok(f.endsWith('StatusPage.tsx') ? mains <= 1 : mains === 0, `${f} must not render its own <main>`);
    }
  });

  test('the pages no longer render their own header or footer', () => {
    for (const f of ['page.tsx', 'clinical-review/page.tsx']) {
      const src = read(...f.split('/'));
      assert.ok(!/<Header\b|<Footer\b|className="header-bar"/.test(src), f);
    }
  });

  test('viewport allows safe-area insets and the manifest and SVG icon are linked', () => {
    assert.match(layout, /viewportFit: "cover"/);
    assert.match(layout, /manifest: "\/manifest\.webmanifest"/);
    assert.match(layout, /url: "\/icons\/icon\.svg"/);
  });
});

describe('PWA manifest', () => {
  test('is installable metadata with SVG any + maskable icons, and there is no service worker', () => {
    // A static file, not app/manifest.ts: metadata routes have no client reference manifest,
    // which scripts/measure-baseline.mjs (correctly) refuses to measure.
    const m = JSON.parse(readFileSync(join(webDir, 'public', 'manifest.webmanifest'), 'utf8'));
    assert.equal(m.display, 'standalone');
    assert.equal(m.start_url, '/');
    assert.ok(m.name && m.short_name);
    const icons: Array<{ src: string; type: string; purpose: string }> = m.icons;
    assert.ok(icons.some((i) => i.type === 'image/svg+xml' && i.purpose === 'any'));
    assert.ok(icons.some((i) => i.type === 'image/svg+xml' && i.purpose === 'maskable'));
    for (const i of icons) assert.ok(existsSync(join(webDir, 'public', i.src)), `${i.src} missing`);
    const all = [
      ...['layout.tsx', 'page.tsx'].map((f) => read(f)),
      ...['SiteHeader.tsx', 'ShellProvider.tsx'].map((f) => read('shell', f)),
    ].join('\n');
    assert.ok(!/navigator\.serviceWorker|workbox/i.test(all), 'no service worker (zero retention)');
    for (const f of ['sw.js', 'service-worker.js']) assert.ok(!existsSync(join(webDir, 'public', f)));
  });
});

describe('module tabs keyboard model', () => {
  test('arrow keys wrap, Home/End jump, other keys do nothing', async () => {
    const { nextTabForKey } = await import('../app/components/ModuleTabs');
    const order = MODULE_ORDER;
    assert.equal(nextTabForKey('billnyay', 'ArrowRight', order), 'daavisetu');
    assert.equal(nextTabForKey('dawacheck', 'ArrowRight', order), 'billnyay');
    assert.equal(nextTabForKey('billnyay', 'ArrowLeft', order), 'dawacheck');
    assert.equal(nextTabForKey('bimanyay', 'Home', order), 'billnyay');
    assert.equal(nextTabForKey('bimanyay', 'End', order), 'dawacheck');
    assert.equal(nextTabForKey('bimanyay', 'Enter', order), null);
  });

  test('tabs expose ids, aria-controls and a roving tabindex, and use SVG icons, not emoji', () => {
    const src = read('components', 'ModuleTabs.tsx');
    assert.match(src, /id=\{`tab-\$\{id\}`\}/);
    assert.match(src, /aria-controls=\{active === id \? `panel-\$\{id\}` : undefined\}/);
    assert.match(src, /tabIndex=\{active === id \? 0 : -1\}/);
    assert.ok(!/\p{Extended_Pictographic}/u.test(src), 'no emoji icons');
  });
});

describe('shell layout stability and touch targets (WS4 review)', () => {
  const css = read('shell', 'shell.css');
  const header = read('shell', 'SiteHeader.tsx');
  // Body of the first top-level rule whose line is exactly "<selector> {".
  const rule = (sel: string) => {
    const at = css.indexOf(`\n${sel} {\n`);
    assert.ok(at >= 0, `missing rule ${sel}`);
    const open = css.indexOf('{', at);
    return css.slice(open + 1, css.indexOf('}', open));
  };

  test('html reserves the scrollbar gutter, so locking scroll for the drawer does not shift the page', () => {
    assert.match(rule('html'), /scrollbar-gutter:\s*stable/);
    assert.match(css, /html:has\(dialog\.site-drawer\[open\]\)\s*\{\s*overflow:\s*hidden/);
  });

  test('scroll-padding-top includes the safe-area inset the header pads with', () => {
    assert.match(rule('html'), /scroll-padding-top:\s*calc\(var\(--shell-header-h\)\s*\+\s*env\(safe-area-inset-top\)\s*\+\s*1rem\)/);
  });

  test('the header slot cannot move the other header controls when it fills', () => {
    // Actions are right-anchored and the nav is anchored to the brand (not centred), so a chip
    // appearing in the slot only grows the actions group leftwards.
    assert.match(rule('.site-actions'), /margin-left:\s*auto/);
    assert.ok(!/margin-inline:\s*auto/.test(rule('.site-nav')), '.site-nav must not be centred');
    assert.match(header, /<div className="site-slot">\{slot\}<\/div>\s*<LanguageSwitcher/);
  });

  test('language buttons and footer links are at least 44 px tall', () => {
    assert.match(rule('.site-lang-btn'), /min-height:\s*var\(--min-touch-target\)/);
    assert.match(rule('.site-footer-list a'), /min-height:\s*var\(--min-touch-target\)/);
  });
});

describe('drawer and breakpoint', () => {
  test('the drawer closes when the viewport grows past the compact breakpoint', async () => {
    const { drawerShouldClose } = await import('../app/shell/headerScroll');
    assert.equal(drawerShouldClose({ open: true, compact: false }), true);
    assert.equal(drawerShouldClose({ open: true, compact: true }), false);
    assert.equal(drawerShouldClose({ open: false, compact: false }), false);
    assert.match(read('shell', 'SiteHeader.tsx'), /drawerShouldClose\(/);
  });
});
