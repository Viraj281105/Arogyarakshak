import { describe, test } from 'node:test';
import assert from 'node:assert';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { localisedPublicCopy, publicCopy } from '../app/components/public/publicCopy';
import { PUBLIC_LANGUAGE_NOTICE, PUBLIC_MODULE_IDS, PUBLIC_ROUTES, allPublicPaths } from '../app/components/public/publicNav';
import { PUBLIC_FOOTER_LINKS } from '../app/components/public/publicRoutes';
import { filterFaq, normalise } from '../app/components/public/faqFilter';
import { EVIDENCE_STATES } from '../app/components/ui/evidence';
import { CGHS_TOTAL_ROWS, NPPA_REFERENCE_FORMULATIONS } from '../app/lib/referenceSnapshot';

// Wave 3 M3 public site: routes are Server Components with their own metadata, copy is honest
// and stays out of client bundles, styles use tokens only.
const appDir = join(__dirname, '..', 'app');
const read = (...p: string[]) => readFileSync(join(appDir, ...p), 'utf8');
const isClient = (src: string) => /^\s*["']use client["']/.test(src);

const ROUTE_FILES = ['platform/page.tsx', 'platform/[module]/page.tsx', 'how-it-works/page.tsx', 'security/page.tsx', 'about/page.tsx', 'help/page.tsx'];
const en = publicCopy();

describe('public routes', () => {
  test('exist, are Server Components and declare their own title and description', () => {
    for (const f of ROUTE_FILES) {
      assert.ok(existsSync(join(appDir, f)), f);
      const src = read(...f.split('/'));
      assert.ok(!isClient(src), `${f} must be a Server Component`);
      assert.match(src, /export (const metadata: Metadata|async function generateMetadata)/, `${f} needs metadata`);
      assert.ok(!/<main\b/.test(src), `${f} must not render its own <main>`);
    }
    const landing = read('page.tsx');
    assert.ok(!isClient(landing));
    assert.match(landing, /export async function generateMetadata/);
  });

  test('module pages are statically generated for exactly the six capabilities, 404 otherwise', () => {
    const src = read('platform', '[module]', 'page.tsx');
    assert.match(src, /export const dynamicParams = false/);
    // The page imports public.css, which tsx cannot load, so check the source and the id list it maps.
    assert.match(src, /return PUBLIC_MODULE_IDS\.map\(\(module\) => \(\{ module \}\)\)/);
    assert.deepEqual([...PUBLIC_MODULE_IDS], ['kadi', 'billnyay', 'daavisetu', 'bimanyay', 'schemesetu', 'dawacheck']);
  });

  test('the exact route list handed to M4', () => {
    assert.deepEqual(allPublicPaths(), [
      '/platform', '/platform/kadi', '/platform/billnyay', '/platform/daavisetu', '/platform/bimanyay',
      '/platform/schemesetu', '/platform/dawacheck', '/how-it-works', '/security', '/about', '/help',
    ]);
  });

  test('titles and descriptions are unique per page', () => {
    const metas = [en.landing.meta, en.platform.meta, en.howItWorks.meta, en.security.meta, en.about.meta, en.help.meta, ...PUBLIC_MODULE_IDS.map((id) => en.modules[id].meta)];
    assert.equal(new Set(metas.map((m) => m.title)).size, metas.length);
    assert.equal(new Set(metas.map((m) => m.description)).size, metas.length);
    for (const m of metas) assert.ok(m.description.length >= 50 && m.description.length <= 200, m.title);
  });

  test('the footer links every public route (labels from the small nav module, not the page copy)', () => {
    const footer = read('shell', 'SiteFooter.tsx');
    assert.match(footer, /PUBLIC_FOOTER_LINKS/);
    assert.ok(!/publicCopy|copy\/en|publicNav/.test(footer), 'footer must import only the tiny route module');
    assert.deepEqual(PUBLIC_FOOTER_LINKS.map(([href]) => href), Object.values(PUBLIC_ROUTES));
    for (const [, label] of PUBLIC_FOOTER_LINKS) assert.ok(label.length > 0);
  });
});

describe('public copy honesty', () => {
  const all = JSON.stringify(en);

  test('Hindi and Marathi are marked as machine translation, never presented as reviewed', async () => {
    assert.equal(en.translation, 'source');
    for (const lang of ['hi', 'mr'] as const) {
      const copy = await localisedPublicCopy(lang);
      assert.equal(copy.translation, 'machine');
      assert.notEqual(copy.landing.lede, en.landing.lede, `${lang} landing text is translated`);
      assert.equal(copy.landing.primaryCta.href, en.landing.primaryCta.href, 'addresses are never translated');
      assert.deepEqual(copy.faq.map((f) => f.id), en.faq.map((f) => f.id));
    }
    assert.match(read('components', 'public', 'publicCopy.ts'), /UNREVIEWED/);
    assert.match(read('components', 'public', 'publicNav.ts'), /NEEDS NATIVE-SPEAKER QA/);
    assert.match(read('components', 'public', 'publicRoutes.ts'), /UNREVIEWED/);
    assert.ok(PUBLIC_LANGUAGE_NOTICE.hi && PUBLIC_LANGUAGE_NOTICE.mr);
  });

  test('no testimonials, user counts, accuracy or savings claims, partner logos', () => {
    for (const re of [/testimonial/i, /trusted by/i, /\b\d[\d,]*\+? (users|patients|families|hospitals)\b/i, /\d+(\.\d+)?\s?% (accura|success|approv)/i, /accuracy of/i, /saved ₹/i, /savings of/i, /partner/i]) {
      assert.ok(!re.test(all), `copy matches ${re}`);
    }
  });

  test('reference counts come from the snapshot (kept equal to the data files by reference_snapshot.test)', () => {
    assert.match(all, new RegExp(`${CGHS_TOTAL_ROWS} rows`));
    assert.match(all, new RegExp(`${NPPA_REFERENCE_FORMULATIONS} formulations`));
  });

  test('every module page has a synthetic example, limitations and dated reference data', () => {
    for (const id of PUBLIC_MODULE_IDS) {
      const m = en.modules[id];
      assert.equal(m.id, id);
      assert.ok(m.example.rows.length >= 3, id);
      assert.match(m.example.intro, /made-up/i, `${id} example must say it is made up`);
      assert.ok(m.limitations.length >= 3, id);
      assert.ok(m.references.length >= 1, id);
      for (const r of m.references) assert.ok(r.date && r.location, `${id} reference needs a date statement and a location`);
      for (const s of m.evidence) assert.ok((EVIDENCE_STATES as readonly string[]).includes(s));
      for (const row of m.example.rows) if (row.evidence) assert.ok((EVIDENCE_STATES as readonly string[]).includes(row.evidence));
    }
    assert.equal(en.common.synthetic, 'Synthetic example');
    assert.match(read('platform', '[module]', 'page.tsx'), /c\.common\.synthetic/);
  });

  test('DaaviSetu never claims submission; security page states the email and Groq limitations', () => {
    assert.ok(!/(was|been|is) submitted/i.test(JSON.stringify(en.modules.daavisetu)));
    const sec = JSON.stringify(en.security);
    assert.match(sec, /no email is sent/i);
    assert.match(sec, /Groq/);
    assert.match(sec, /scrypt/);
    assert.match(sec, /90 days/);
  });

  test('landing FAQ excerpt ids exist; FAQ ids are unique', () => {
    const ids = en.faq.map((f) => f.id);
    assert.equal(new Set(ids).size, ids.length);
    for (const id of en.landing.faq.ids) assert.ok(ids.includes(id), id);
  });
});

describe('client code stays small', () => {
  const publicDir = join(appDir, 'components', 'public');
  const clientFiles = [
    ...readdirSync(publicDir).filter((f) => f.endsWith('.tsx')).map((f) => join(publicDir, f)),
    ...readdirSync(join(appDir, 'components', 'landing')).map((f) => join(appDir, 'components', 'landing', f)),
  ].filter((f) => isClient(readFileSync(f, 'utf8')));

  test('no client component imports the page copy (it is passed as props)', () => {
    assert.ok(clientFiles.length >= 3);
    for (const f of clientFiles) {
      const src = readFileSync(f, 'utf8');
      assert.ok(!/import (?!type)[^;]*from ["'][^"']*(publicCopy|copy\/en|copy\/modules)["']/.test(src), `${f} imports page copy`);
      assert.ok(!/from ["'][^"']*translations["']/.test(src), `${f} imports the full translations dictionary`);
    }
  });

  test('the new landing sections are Server Components', () => {
    assert.ok(!isClient(read('components', 'landing', 'LandingSections.tsx')));
    assert.ok(!isClient(read('components', 'public', 'PublicParts.tsx')));
  });
});

describe('public.css', () => {
  const css = read('components', 'public', 'public.css');
  const tokens = read('generated', 'tokens.css');
  const declared = (s: string) => new Set([...s.matchAll(/(^|[;{\s])(--[\w-]+)\s*:/g)].map((m) => m[2]));
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g, '');

  test('uses tokens only: no hex, rgb() or hsl() colours', () => {
    assert.ok(!/#[0-9a-fA-F]{3,8}\b/.test(stripped), 'hex colour');
    assert.ok(!/\b(rgba?|hsla?)\(/.test(stripped), 'rgb/hsl colour');
  });

  test('every var() is defined in tokens.css or public.css (shell vars excepted)', () => {
    const defined = new Set([...declared(tokens), ...declared(css)]);
    const used = [...new Set([...css.matchAll(/var\(\s*(--[\w-]+)/g)].map((m) => m[1]))];
    assert.deepEqual(used.filter((v) => !defined.has(v)), []);
  });

  test('animations live only inside a prefers-reduced-motion: no-preference block', () => {
    const guard = stripped.indexOf('@media (prefers-reduced-motion: no-preference)');
    assert.ok(guard > 0);
    const before = stripped.slice(0, guard);
    assert.ok(!/animation|@keyframes|transition/.test(before), 'motion outside the guard');
  });
});

describe('help search', () => {
  const items = en.faq;
  test('matches every word in question, answer or keywords; topic narrows; empty keeps all', () => {
    assert.equal(filterFaq(items, '', null).length, items.length);
    assert.ok(filterFaq(items, 'delete', null).some((f) => f.id === 'delete-case'));
    assert.ok(filterFaq(items, 'groq', null).some((f) => f.id === 'data-sent'));
    assert.ok(filterFaq(items, 'PM-JAY', null).some((f) => f.id === 'pmjay'));
    assert.ok(filterFaq(items, 'pre auth', null).length > 0);
    assert.ok(filterFaq(items, 'delete', 'accounts').every((f) => f.topic === 'accounts'));
    assert.deepEqual(filterFaq(items, 'zzzz-nothing', null), []);
    assert.equal(normalise('  Pré-Auth!  '), 'pre auth');
  });
});

describe('public pages draw icons without client components', () => {
  test('no public page or landing server section imports lucide-react or the client icon maps', () => {
    const files = [...ROUTE_FILES, 'page.tsx', 'components/landing/LandingSections.tsx', 'components/public/PublicParts.tsx'];
    for (const f of files) {
      const src = read(...f.split('/')).replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
      assert.ok(!/lucide-react|shell\/icons\/|ui\/Badges/.test(src), `${f} pulls a client icon component into a server page`);
    }
  });

  test('static icon geometry equals the lucide icons the shell maps use', async () => {
    const { PUBLIC_ICON_NODES } = await import('../app/components/public/publicIcons');
    const names: Record<string, string> = {
      kadi: 'file-text', billnyay: 'receipt-text', daavisetu: 'clipboard-check', bimanyay: 'shield-check', schemesetu: 'landmark', dawacheck: 'pill',
      verified: 'badge-check', provisional: 'hourglass', unevaluated: 'circle-dashed', 'insufficient-evidence': 'file-question-mark',
      'ai-generated': 'sparkles', 'rule-engine': 'scale', 'user-provided': 'user-round', external: 'book-open',
    };
    const moduleMap = read('shell', 'icons', 'moduleIcons.ts') + read('shell', 'icons', 'evidenceIcons.ts');
    for (const [key, file] of Object.entries(names)) {
      assert.ok(moduleMap.includes(`lucide-react/icons/${file}"`), `${file} is not in the shell icon maps`);
      const src = readFileSync(join(__dirname, '..', 'node_modules', 'lucide-react', 'dist', 'esm', 'icons', `${file}.mjs`), 'utf8');
      const ds = [...src.matchAll(/(\w+): "([^"]*)"/g)].filter((m) => m[1] !== 'key' && m[1] !== 'name').map((m) => m[2]);
      const ours = (PUBLIC_ICON_NODES as Record<string, ReadonlyArray<readonly [string, Record<string, string>]>>)[key].flatMap(([, a]) => Object.values(a));
      assert.deepEqual(ours, ds, key);
    }
  });
});
