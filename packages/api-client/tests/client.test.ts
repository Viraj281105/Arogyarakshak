import test from "node:test";
import assert from "node:assert/strict";
import { createClient, normalizeErrorDetail, type ApiError } from "../src/index";

type Call = { url: string; init: RequestInit & { headers: Record<string, string> } };

function stub(responder: (call: Call) => Response | Promise<Response>) {
  const calls: Call[] = [];
  const fetchImpl = (async (url: string, init: Call["init"]) => {
    const call = { url, init };
    calls.push(call);
    return responder(call);
  }) as unknown as typeof fetch;
  return { calls, fetchImpl };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

async function rejection(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (e) {
    return e as ApiError;
  }
  assert.fail("expected rejection");
}

const abortOnSignal = ({ init }: Call) =>
  new Promise<Response>((_, reject) => {
    init.signal!.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  });

test("422 array detail becomes 'field: msg; field: msg'", async () => {
  const { fetchImpl } = stub(() =>
    json(
      {
        detail: [
          { loc: ["body", "name"], msg: "field required", type: "x" },
          { loc: ["query", "age"], msg: "bad", type: "y" },
        ],
      },
      422,
    ),
  );
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.equal(err.status, 422);
  assert.equal(err.statusCode, 422);
  assert.equal(err.detail, "name: field required; query.age: bad");
});

test("string detail passes through", async () => {
  const { fetchImpl } = stub(() => json({ detail: "Case not found" }, 404));
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.equal(err.status, 404);
  assert.equal(err.detail, "Case not found");
  assert.match(err.message ?? "", /HTTP Error 404/);
});

test("object detail is JSON-stringified", async () => {
  const { fetchImpl } = stub(() => json({ detail: { code: "X", n: 1 } }, 400));
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.equal(err.detail, JSON.stringify({ code: "X", n: 1 }));
});

test("error body without detail falls back to message, then raw JSON; non-JSON uses the text", async () => {
  const c = (r: () => Response) => createClient({ baseUrl: "http://api", fetchImpl: stub(r).fetchImpl });
  assert.equal((await rejection(c(() => json({ message: "m" }, 500)).request("/x"))).detail, "m");
  assert.equal((await rejection(c(() => json({ a: 1 }, 500)).request("/x"))).detail, '{"a":1}');
  assert.equal((await rejection(c(() => new Response("plain failure", { status: 502 })).request("/x"))).detail, "plain failure");
});

test("normalizeErrorDetail covers every shape", () => {
  assert.equal(normalizeErrorDetail("s"), "s");
  assert.equal(normalizeErrorDetail([]), "Request validation failed.");
  assert.equal(normalizeErrorDetail(["a", { z: 1 }]), 'a; {"z":1}');
  assert.equal(normalizeErrorDetail([{ msg: "m" }]), "m");
  assert.equal(normalizeErrorDetail(null), "An error occurred.");
  assert.equal(normalizeErrorDetail(undefined), "An error occurred.");
});

test("timeout rejects with ApiError status 0 after timeoutMs", async () => {
  const { fetchImpl } = stub(abortOnSignal);
  const t0 = Date.now();
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl, timeoutMs: 40 }).request("/slow"));
  assert.ok(Date.now() - t0 >= 30);
  assert.equal(err.status, 0);
  assert.equal(err.statusCode, 0);
  assert.match(err.message ?? "", /timed out after 40ms/);
  assert.ok(!(err instanceof Error));
});

test("per-request timeoutMs overrides the client default", async () => {
  const { fetchImpl } = stub(abortOnSignal);
  const err = await rejection(
    createClient({ baseUrl: "http://api", fetchImpl, timeoutMs: 5000 }).request("/slow", { timeoutMs: 20 }),
  );
  assert.match(err.message ?? "", /timed out after 20ms/);
});

test("an AbortError that is not our timeout still rejects with ApiError status 0", async () => {
  const { fetchImpl } = stub(() => {
    throw new DOMException("aborted", "AbortError");
  });
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.equal(err.status, 0);
  assert.equal(typeof err.detail, "string");
});

test("network failure rejects with ApiError status 0, not a TypeError", async () => {
  const { fetchImpl } = stub(() => {
    throw new TypeError("Failed to fetch");
  });
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.ok(!(err instanceof TypeError));
  assert.equal(err.status, 0);
  assert.equal(err.message, "Failed to fetch");
  assert.equal(err.detail, "Failed to fetch");
});

test("a non-Error rejection from fetch still becomes an ApiError", async () => {
  const { fetchImpl } = stub(() => Promise.reject("boom") as Promise<Response>);
  const err = await rejection(createClient({ baseUrl: "http://api", fetchImpl }).request("/x"));
  assert.equal(err.status, 0);
  assert.equal(err.message, "Network request failed");
});

test("headersFor is called with the request path and its headers are merged; explicit headers win", async () => {
  const seen: string[] = [];
  const { calls, fetchImpl } = stub(() => json({}));
  const client = createClient({
    baseUrl: "http://api",
    fetchImpl,
    headersFor: (path) => {
      seen.push(path);
      return { "X-Case-Access-Token": "tok", "X-Other": "from-hook" };
    },
  });
  await client.request("/api/v1/kadi/cases/abc", { headers: { "X-Other": "explicit" } });
  assert.deepEqual(seen, ["/api/v1/kadi/cases/abc"]);
  assert.equal(calls[0].url, "http://api/api/v1/kadi/cases/abc");
  assert.equal(calls[0].init.headers["X-Case-Access-Token"], "tok");
  assert.equal(calls[0].init.headers["X-Other"], "explicit");
  assert.equal(calls[0].init.headers["Accept"], "application/json");
});

test("headersFor is path-specific: a path it has nothing for gets no extra header", async () => {
  const { calls, fetchImpl } = stub(() => json({}));
  const client = createClient({
    baseUrl: "http://api",
    fetchImpl,
    headersFor: (path) => (path.startsWith("/api/v1/kadi/cases/") ? { "X-Case-Access-Token": "tok" } : {}),
  });
  await client.request("/health");
  assert.equal(calls[0].init.headers["X-Case-Access-Token"], undefined);
});

test("JSON string bodies get a JSON content-type; FormData bodies do not; an explicit one is kept", async () => {
  const { calls, fetchImpl } = stub(() => json({}));
  const client = createClient({ baseUrl: "http://api", fetchImpl });
  await client.request("/a", { method: "POST", body: JSON.stringify({ a: 1 }) });
  await client.request("/b", { method: "POST", body: new FormData() });
  await client.request("/c", { method: "POST", body: "x", headers: { "content-type": "text/plain" } });
  await client.request("/d");
  assert.equal(calls[0].init.headers["Content-Type"], "application/json");
  assert.equal(calls[1].init.headers["Content-Type"], undefined);
  assert.equal(calls[2].init.headers["Content-Type"], undefined);
  assert.equal(calls[2].init.headers["content-type"], "text/plain");
  assert.equal(calls[3].init.headers["Content-Type"], undefined);
});

test("success parses JSON; 204 returns undefined", async () => {
  const ok = createClient({ baseUrl: "http://api", fetchImpl: stub(() => json({ id: "1" })).fetchImpl });
  assert.deepEqual(await ok.request("/x"), { id: "1" });
  const empty = createClient({
    baseUrl: "http://api",
    fetchImpl: stub(() => new Response(null, { status: 204 })).fetchImpl,
  });
  assert.equal(await empty.request("/x"), undefined);
});

test("a 200 with an unparseable body rejects with an ApiError", async () => {
  const c = createClient({
    baseUrl: "http://api",
    fetchImpl: stub(() => new Response("not json", { status: 200 })).fetchImpl,
  });
  const err = await rejection(c.request("/x"));
  assert.equal(err.status, 200);
  assert.equal(typeof err.detail, "string");
});

test("the timer is cleared on success so it cannot abort later", async () => {
  const { fetchImpl } = stub(() => json({}));
  const c = createClient({ baseUrl: "http://api", fetchImpl, timeoutMs: 20 });
  await c.request("/x");
  await new Promise((r) => setTimeout(r, 50));
});
