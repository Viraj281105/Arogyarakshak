import { test, describe } from 'node:test';
import assert from 'node:assert';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { createElement } from 'react';
import { renderToString } from 'react-dom/server';
import {
  countUpValue,
  readReducedMotion,
  shouldAnimate,
  subscribeReducedMotion,
  type MediaQueryListLike,
} from '../app/motion/useReducedMotion';
import { navigateWithTransition } from '../app/motion/viewTransition';
import CountUp from '../app/motion/CountUp';
import { startSmoothScroll } from '../app/motion/startSmoothScroll';

const appDir = join(__dirname, '..', 'app');
const motionDir = join(appDir, 'motion');
const read = (p: string) => readFileSync(p, 'utf8');
const walk = (dir: string): string[] =>
  readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });

function fakeMq(matches: boolean) {
  const listeners = new Set<() => void>();
  const mq = {
    matches,
    addEventListener: (_t: 'change', cb: () => void) => void listeners.add(cb),
    removeEventListener: (_t: 'change', cb: () => void) => void listeners.delete(cb),
  } satisfies MediaQueryListLike;
  return { mq, listeners, fire: () => listeners.forEach((l) => l()) };
}

describe('useReducedMotion helpers', () => {
  test('subscribe fires the listener on the media query change event and unsubscribe removes it', () => {
    const { mq, listeners, fire } = fakeMq(false);
    let calls = 0;
    const off = subscribeReducedMotion(() => calls++, mq);
    assert.equal(listeners.size, 1);
    fire();
    assert.equal(calls, 1);
    off();
    assert.equal(listeners.size, 0);
    fire();
    assert.equal(calls, 1);
  });

  test('readReducedMotion reflects matches, including after the OS setting flips', () => {
    const f = fakeMq(false);
    assert.equal(readReducedMotion(f.mq), false);
    (f.mq as { matches: boolean }).matches = true;
    f.fire();
    assert.equal(readReducedMotion(f.mq), true);
  });

  test('uses window.matchMedia by default and is safe without a window', () => {
    assert.equal(readReducedMotion(), false);
    const f = fakeMq(true);
    const g = globalThis as unknown as { window?: unknown };
    g.window = { matchMedia: () => f.mq };
    try {
      assert.equal(readReducedMotion(), true);
      const off = subscribeReducedMotion(() => {});
      assert.equal(f.listeners.size, 1);
      off();
    } finally {
      delete g.window;
    }
  });

  test('shouldAnimate truth table', () => {
    assert.equal(shouldAnimate({ reducedMotion: false, supportsScrollTimeline: true }), true);
    assert.equal(shouldAnimate({ reducedMotion: true, supportsScrollTimeline: true }), false);
    assert.equal(shouldAnimate({ reducedMotion: false, supportsScrollTimeline: false }), false);
    assert.equal(shouldAnimate({ reducedMotion: true, supportsScrollTimeline: false }), false);
  });
});

describe('countUpValue', () => {
  test('hits the endpoints, clamps, and never decreases', () => {
    for (const to of [0, 7, 1234.5, 100000]) {
      assert.equal(countUpValue(0, to), 0);
      assert.equal(countUpValue(1, to), to);
      assert.equal(countUpValue(-3, to), 0);
      assert.equal(countUpValue(9, to), to);
      let prev = -Infinity;
      for (let i = 0; i <= 100; i++) {
        const v = countUpValue(i / 100, to);
        assert.ok(v >= prev, `non-monotonic at ${i}`);
        prev = v;
      }
    }
  });
});

describe('CountUp', () => {
  test('server-renders its final formatted value synchronously (no animation needed)', () => {
    const html = renderToString(
      createElement(CountUp, { to: 1234567, format: (n: number) => `Rs ${Math.round(n).toLocaleString('en-IN')}` }),
    );
    assert.ok(html.includes('Rs 12,34,567'), html);
  });
  test('defaults to the plain rounded value when no format is given', () => {
    assert.ok(renderToString(createElement(CountUp, { to: 42 })).includes('>42<'));
  });
});

/** Walks CSS tracking at-rule nesting; returns [declaration-or-keyframes, enclosing preludes]. */
function cssAnimationContexts(css: string): Array<{ what: string; stack: string[] }> {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, '');
  const out: Array<{ what: string; stack: string[] }> = [];
  const stack: string[] = [];
  let buf = '';
  for (const ch of text) {
    if (ch === '{') {
      const prelude = buf.trim();
      if (/^@keyframes/.test(prelude)) out.push({ what: prelude, stack: [...stack] });
      stack.push(prelude);
      buf = '';
    } else if (ch === ';' || ch === '}') {
      const decl = buf.trim();
      if (/^(-\w+-)?animation(-[\w-]+)?\s*:/.test(decl)) out.push({ what: decl, stack: [...stack] });
      buf = '';
      if (ch === '}') stack.pop();
    } else buf += ch;
  }
  return out;
}

describe('motion.css', () => {
  const css = read(join(motionDir, 'motion.css'));

  test('every @keyframes and animation declaration sits inside prefers-reduced-motion: no-preference', () => {
    const ctx = cssAnimationContexts(css);
    assert.ok(ctx.length > 0, 'expected animation rules');
    for (const c of ctx) {
      // `animation: none` inside a `reduce` block is the explicit reduced-motion override.
      if (/^animation\s*:\s*none$/.test(c.what) && c.stack.some((s) => /prefers-reduced-motion:\s*reduce/.test(s))) continue;
      assert.ok(
        c.stack.some((s) => /prefers-reduced-motion:\s*no-preference/.test(s)),
        `ungated: ${c.what} in [${c.stack.join(' > ')}]`,
      );
    }
  });

  test('scroll-linked effects are additionally gated by @supports (animation-timeline: view())', () => {
    for (const c of cssAnimationContexts(css)) {
      if (/^animation\s*:\s*none$/.test(c.what)) continue;
      assert.ok(
        c.stack.some((s) => /@supports\s*\(animation-timeline:\s*view\(\)\)/.test(s)),
        `no @supports gate: ${c.what}`,
      );
    }
  });

  test('provides a reduce override that shows the final state', () => {
    assert.match(css, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
  });

  test('uses motion tokens rather than hardcoded durations', () => {
    assert.match(css, /var\(--motion-duration-/);
    assert.match(css, /var\(--motion-easing-/);
  });
});

describe('motion library confinement', () => {
  test('no file outside app/motion imports motion, framer-motion, lenis or gsap', () => {
    const re = /(?:from\s+|import\s*\(\s*|import\s+|require\(\s*)['"](?:motion|framer-motion|lenis|gsap)(?:\/[^'"]*)?['"]/;
    const offenders = walk(appDir)
      .filter((p) => /\.(tsx?|jsx?|mjs|css)$/.test(p))
      .filter((p) => !relative(appDir, p).startsWith('motion' + sep))
      .filter((p) => re.test(read(p)));
    assert.deepEqual(offenders, []);
  });

  test('the motion package is only imported by Magnetic and the lazy features file', () => {
    const importers = walk(motionDir)
      .filter((p) => /\.tsx?$/.test(p))
      .filter((p) => /from\s+['"]motion\/react['"]/.test(read(p)))
      .map((p) => relative(motionDir, p))
      .sort();
    assert.deepEqual(importers, ['Magnetic.tsx', 'motionFeatures.ts']);
  });
});

describe('progressive enhancement of scroll-linked patterns', () => {
  for (const name of ['Reveal', 'Parallax', 'ScrollScrub']) {
    test(`${name} is JS-free (no client directive, no hooks) so the server output is the final state`, () => {
      const src = read(join(motionDir, `${name}.tsx`));
      assert.ok(!/['"]use client['"]/.test(src));
      assert.ok(!/useState|useEffect|from ['"]motion/.test(src));
    });
  }
});

describe('SmoothScroll (Lenis) accessibility', () => {
  const src = read(join(motionDir, 'SmoothScroll.tsx'));
  test('loads lenis lazily, only after mount', () => {
    assert.match(src, /import\(\s*["']lenis["']\s*\)/);
    assert.ok(!/^import .* from ["']lenis["']/m.test(src));
    assert.match(src, /useEffect/);
  });
  test('respects reduced motion and destroys the instance', () => {
    assert.match(src, /useReducedMotion/);
    assert.match(src, /\.stop\(\)/);
    assert.match(read(join(motionDir, 'startSmoothScroll.ts')), /\.destroy\(\)/);
  });
  test('does not hijack touch scroll and keeps anchor links native-friendly', () => {
    assert.match(src, /anchors:\s*true/);
    assert.ok(!/syncTouch:\s*true/.test(src));
  });
  test('lets wheel events scroll nested scroll containers', () => {
    assert.match(src, /allowNestedScroll:\s*true/);
  });
  test('is not mounted in the root layout; /motion-lab mounts it locally', () => {
    assert.ok(!/SmoothScroll/.test(read(join(appDir, 'layout.tsx'))));
    assert.match(read(join(appDir, '(dev)', 'motion-lab', 'page.dev.tsx')), /<SmoothScroll\s*\/>/);
  });
});

describe('navigateWithTransition', () => {
  const g = globalThis as unknown as { document?: unknown };
  const original = g.document;
  const restore = () => {
    if (original === undefined) delete g.document;
    else g.document = original;
  };

  test('calls go() directly when document.startViewTransition is missing', () => {
    g.document = {};
    let calls = 0;
    try {
      navigateWithTransition(() => calls++);
    } finally {
      restore();
    }
    assert.equal(calls, 1);
  });

  test('calls go() directly when there is no document at all', () => {
    delete g.document;
    let calls = 0;
    try {
      navigateWithTransition(() => calls++);
    } finally {
      restore();
    }
    assert.equal(calls, 1);
  });

  test('wraps go() in startViewTransition when available', () => {
    let started = 0;
    let calls = 0;
    g.document = {
      startViewTransition(cb: () => void) {
        started++;
        assert.equal(calls, 0, 'go must run inside the transition callback');
        cb();
      },
    };
    try {
      navigateWithTransition(() => calls++);
    } finally {
      restore();
    }
    assert.equal(started, 1);
    assert.equal(calls, 1);
  });
});

describe('startSmoothScroll lifecycle', () => {
  const tick = () => new Promise((r) => setTimeout(r, 10));
  function track() {
    const created: Array<{ destroyed: number }> = [];
    class Fake {
      destroyed = 0;
      constructor() {
        created.push(this);
      }
      destroy() {
        this.destroyed++;
      }
    }
    return { created, Fake };
  }

  test('a rejecting loader is swallowed (no unhandled rejection), reported, and stop() is a no-op', async () => {
    const unhandled: unknown[] = [];
    const onUnhandled = (e: unknown) => unhandled.push(e);
    process.on('unhandledRejection', onUnhandled);
    try {
      const errors: unknown[] = [];
      const h = startSmoothScroll<object>(() => Promise.reject(new Error('chunk failed')), {}, (e) => errors.push(e));
      await tick();
      assert.doesNotThrow(() => h.stop());
      await tick();
      assert.equal(errors.length, 1);
      assert.deepEqual(unhandled, []);
    } finally {
      process.off('unhandledRejection', onUnhandled);
    }
  });

  test('an onError that throws still produces no unhandled rejection', async () => {
    const unhandled: unknown[] = [];
    const onUnhandled = (e: unknown) => unhandled.push(e);
    process.on('unhandledRejection', onUnhandled);
    try {
      startSmoothScroll<object>(() => Promise.reject(new Error('x')), {}, () => {
        throw new Error('reporter broke');
      });
      await tick();
      assert.deepEqual(unhandled, []);
    } finally {
      process.off('unhandledRejection', onUnhandled);
    }
  });

  test('stop() before the load resolves prevents instance creation', async () => {
    const { created, Fake } = track();
    let resolve!: (v: { default: typeof Fake }) => void;
    const h = startSmoothScroll<object>(() => new Promise((r) => (resolve = r)), {});
    h.stop();
    resolve({ default: Fake });
    await tick();
    assert.equal(created.length, 0);
  });

  test('a resolving loader creates exactly one instance and stop() destroys it once', async () => {
    const { created, Fake } = track();
    const h = startSmoothScroll<object>(() => Promise.resolve({ default: Fake }), { anchors: true });
    await tick();
    assert.equal(created.length, 1);
    h.stop();
    h.stop();
    assert.equal(created[0].destroyed, 1);
  });
});
