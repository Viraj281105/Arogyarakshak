import { describe, test, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  ACTIVE_CASE_KEY,
  GUEST_CASES_KEY,
  MAX_GUEST_CASES,
  activeCaseRef,
  addGuestCase,
  caseHeaders,
  clearAllCases,
  parseGuestCases,
  removeGuestCase,
  setActiveCase,
  type StorageLike,
} from '../app/lib/caseStore';
import {
  getAccountState,
  markSignedIn,
  markSignedOut,
  noteUnauthorized,
  refreshAccount,
  requestCredentials,
  resetAccountStateForTests,
} from '../app/lib/session';
import { drawableEdges, edgesOf, radialLayout, type GraphNode } from '../app/components/workspace/graphLayout';
import { filterTimeline } from '../app/components/workspace/TimelineExplorer';
import { fillCopy, shortCaseId, humanizeKey } from '../app/components/workspace/workspaceFormat';
import { caseCopy } from '../app/components/workspace/caseCopy';
import { deskCopy } from '../app/components/workspace/deskCopy';
import { overviewCopy } from '../app/components/workspace/overviewCopy';
import { timelineCopy } from '../app/components/workspace/timelineCopy';
import { graphCopy } from '../app/components/workspace/graphCopy';
import { reportsCopy } from '../app/components/workspace/reportsCopy';
import { settingsCopy } from '../app/components/workspace/settingsCopy';

const COPY_FILES = ['caseCopy', 'deskCopy', 'overviewCopy', 'timelineCopy', 'graphCopy', 'reportsCopy', 'settingsCopy'];
import { authCopy } from '../app/components/auth/authCopy';
import { safeNext } from '../app/components/auth/LoginForm';
import { storedConfidence } from '../app/components/workspace/DocumentsKept';

function memoryStorage(): StorageLike & { data: Map<string, string> } {
  const data = new Map<string, string>();
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v), removeItem: (k) => void data.delete(k) };
}

describe('guest case store (decision D2)', () => {
  test('adds, de-duplicates, caps and removes guest cases', () => {
    const s = memoryStorage();
    addGuestCase({ id: 'A', token: 'ta' }, s);
    addGuestCase({ id: 'B', token: 'tb' }, s);
    addGuestCase({ id: 'A', token: 'ta' }, s);
    assert.deepEqual(parseGuestCases(s.getItem(GUEST_CASES_KEY)).map((g) => g.id), ['A', 'B']);
    for (let i = 0; i < MAX_GUEST_CASES + 5; i++) addGuestCase({ id: `X${i}`, token: 't' }, s);
    assert.equal(parseGuestCases(s.getItem(GUEST_CASES_KEY)).length, MAX_GUEST_CASES);
    removeGuestCase('X0', s);
    clearAllCases(s);
    assert.equal(s.getItem(GUEST_CASES_KEY), null);
  });

  test('malformed storage is ignored, never thrown', () => {
    assert.deepEqual(parseGuestCases('not json'), []);
    assert.deepEqual(parseGuestCases('{"a":1}'), []);
    assert.deepEqual(parseGuestCases('[{"id":"A"},{"id":"B","token":"t"}]').map((g) => g.id), ['B']);
  });

  test('the active case resolves its token from the guest list; an owned case has none', () => {
    const s = memoryStorage();
    addGuestCase({ id: 'G', token: 'secret' }, s);
    setActiveCase({ id: 'G', owned: false }, s);
    assert.deepEqual(activeCaseRef(s), { id: 'G', token: 'secret', owned: false });
    assert.deepEqual(caseHeaders(activeCaseRef(s)), { 'X-Case-Access-Token': 'secret' });
    setActiveCase({ id: 'O', owned: true }, s);
    assert.deepEqual(activeCaseRef(s), { id: 'O', token: null, owned: true });
    assert.deepEqual(caseHeaders(activeCaseRef(s)), {});
    // Removing a guest case that is open closes it too.
    setActiveCase({ id: 'G', owned: false }, s);
    removeGuestCase('G', s);
    assert.equal(s.getItem(ACTIVE_CASE_KEY), null);
    // A guest case whose token is gone cannot be opened.
    setActiveCase({ id: 'missing', owned: false }, s);
    assert.equal(activeCaseRef(s), null);
  });

  test('the store uses sessionStorage only, never localStorage, and tokens never go in a URL', () => {
    const src = readFileSync(join(process.cwd(), 'app', 'lib', 'caseStore.ts'), 'utf8');
    assert.match(src, /window\.sessionStorage/);
    assert.ok(!/localStorage/.test(src.replace(/\/\/.*$/gm, '')));
    const api = readFileSync(join(process.cwd(), 'app', 'lib', 'caseApi.ts'), 'utf8');
    // The only query-string credential is the guest case token on the SSE stream (ADR-009).
    const queryTokens = api.match(/\?access_token=/g) ?? [];
    assert.equal(queryTokens.length, 1);
    assert.match(api, /new EventSource\(base, \{ withCredentials: true \}\)/);
  });
});

describe('account session state', () => {
  beforeEach(() => resetAccountStateForTests());
  const user = { id: 'u', email: 'a@example.com', email_verified: false, email_verified_at: null, created_at: '2026-11-24T00:00:00' };

  test('credentials travel unless the API said there is no session or could not be reached', async () => {
    assert.equal(requestCredentials(), 'include');
    const unauthorized = (async () => new Response('{}', { status: 401 })) as unknown as typeof fetch;
    await refreshAccount(unauthorized);
    assert.equal(getAccountState().status, 'signed-out');
    assert.equal(requestCredentials(), 'same-origin');
    const down = (async () => {
      throw new TypeError('Failed to fetch');
    }) as unknown as typeof fetch;
    await refreshAccount(down);
    assert.equal(getAccountState().status, 'unreachable');
    markSignedIn(user);
    assert.equal(requestCredentials(), 'include');
  });

  test('GET /auth/me is sent with credentials and a 200 signs in', async () => {
    let seen: RequestInit | undefined;
    const ok = (async (_u: string, init: RequestInit) => {
      seen = init;
      return new Response(JSON.stringify(user), { status: 200 });
    }) as unknown as typeof fetch;
    await refreshAccount(ok);
    assert.equal(seen?.credentials, 'include');
    assert.equal(getAccountState().user?.email, 'a@example.com');
  });

  test('a 401 from a case route while signed in means the session ended; auth routes are answers', () => {
    markSignedIn(user);
    noteUnauthorized('/api/v1/kadi/auth/login');
    assert.equal(getAccountState().status, 'signed-in');
    noteUnauthorized('/api/v1/kadi/cases/X');
    assert.equal(getAccountState().status, 'expired');
    markSignedOut();
    assert.equal(getAccountState().status, 'signed-out');
  });
});

describe('evidence graph layout', () => {
  const node = (id: string, kind: string, label = id): GraphNode => ({ id, kind, label, attributes: {}, aliases: [], source_files: [] });
  test('the stay is the hub and every other node sits on the ring; only real edges are drawn', () => {
    const nodes = [node('m1', 'medicine'), node('S', 'hospital_stay'), node('h', 'hospital'), node('b', 'billing_item')];
    const placed = radialLayout(nodes, 600);
    assert.equal(placed[0].node.id, 'S');
    assert.deepEqual([placed[0].x, placed[0].y], [300, 300]);
    assert.deepEqual(placed.slice(1).map((p) => p.node.kind), ['hospital', 'medicine', 'billing_item']);
    for (const p of placed.slice(1)) assert.ok(Math.abs(Math.hypot(p.x - 300, p.y - 300) - 228) < 0.5);
    const edges = [
      { source: 'S', target: 'm1', relation: 'RECORDED_MEDICINE', evidence: [] },
      { source: 'S', target: 'ghost', relation: 'X', evidence: [] },
    ];
    assert.equal(drawableEdges(edges, placed).length, 1);
    assert.equal(edgesOf('m1', edges).length, 1);
    assert.deepEqual(radialLayout([], 600), []);
  });
});

describe('timeline explorer', () => {
  const ev = (kind: string, at: string) => ({ at, kind, label: kind, detail: null, actor: 'MACHINE' as const });
  test('filters by kind and reverses without mutating the input', () => {
    const events = [ev('document', '1'), ev('module', '2'), ev('document', '3')];
    assert.deepEqual(filterTimeline(events, new Set(), false).map((e) => e.at), ['1', '2', '3']);
    assert.deepEqual(filterTimeline(events, new Set(['document']), true).map((e) => e.at), ['3', '1']);
    assert.deepEqual(events.map((e) => e.at), ['1', '2', '3']);
  });
});

describe('workspace and account copy', () => {
  function keys(o: unknown, prefix = ''): string[] {
    if (!o || typeof o !== 'object') return [prefix];
    return Object.entries(o as Record<string, unknown>).flatMap(([k, v]) => keys(v, prefix ? `${prefix}.${k}` : k));
  }
  function placeholders(o: unknown): string[] {
    return keys(o).map((k) => {
      const v = k.split('.').reduce<unknown>((acc, part) => (acc as Record<string, unknown>)[part], o);
      return `${k}:${(String(v).match(/\{\w+\}/g) ?? []).sort().join(',')}`;
    });
  }
  test('hi and mr have every key and the same placeholders as en', () => {
    for (const dict of [caseCopy, deskCopy, overviewCopy, timelineCopy, graphCopy, reportsCopy, settingsCopy, authCopy] as const) {
      for (const lang of ['hi', 'mr'] as const) {
        assert.deepEqual(keys(dict[lang]), keys(dict.en), `${lang} keys`);
        assert.deepEqual(placeholders(dict[lang]), placeholders(dict.en), `${lang} placeholders`);
      }
    }
  });

  test('hi and mr stubs are marked UNREVIEWED for native-speaker QA', () => {
    for (const f of [...COPY_FILES.map((n) => ['components', 'workspace', `${n}.ts`]), ['components', 'auth', 'authCopy.ts']]) {
      assert.match(readFileSync(join(process.cwd(), 'app', ...f), 'utf8'), /UNREVIEWED[\s\S]*NEEDS NATIVE-SPEAKER QA/);
    }
  });

  test('email copy never pretends a message was sent', () => {
    for (const lang of ['en', 'hi', 'mr'] as const) assert.ok(authCopy[lang].emailUnavailable.length > 0);
    assert.ok(!/check your inbox/i.test(JSON.stringify(authCopy.en)));
    assert.match(authCopy.en.emailUnavailable, /cannot send email/);
  });

  test('helpers', () => {
    assert.equal(fillCopy('Case {id} of {n}', { id: 'X', n: 2 }), 'Case X of 2');
    assert.equal(shortCaseId('CASE-1234567890'), '12345678');
    assert.equal(humanizeKey('billing_item'), 'Billing item');
    assert.equal(storedConfidence({ meta: { ocr_uncertainty: { min_ocr_confidence: 0.42 } } }), 0.42);
    assert.equal(storedConfidence({ meta: {} }), null);
  });
});

describe('sign-in redirect', () => {
  test('only internal workspace paths are allowed after sign-in', () => {
    assert.equal(safeNext('/app/settings'), '/app/settings');
    assert.equal(safeNext('https://evil.example'), '/app');
    assert.equal(safeNext('//evil.example'), '/app');
    assert.equal(safeNext(null), '/app');
  });
});
