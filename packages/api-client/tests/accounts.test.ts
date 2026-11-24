import test from "node:test";
import assert from "node:assert/strict";
import { accountPaths, createClient, isAuthPath, passwordProblem } from "../src/index";

test("password policy mirrors the API: 12..128 code points after NFKC", () => {
  assert.equal(passwordProblem("short"), "too_short");
  assert.equal(passwordProblem("a".repeat(11)), "too_short");
  assert.equal(passwordProblem("a".repeat(12)), null);
  assert.equal(passwordProblem("a".repeat(128)), null);
  assert.equal(passwordProblem("a".repeat(129)), "too_long");
  // Devanagari and emoji are counted per code point, as Python len() does.
  assert.equal(passwordProblem("😀".repeat(12)), null);
  // NFKC: the ligature "ﬁ" becomes two letters.
  assert.equal(passwordProblem("ﬁ".repeat(6)), null);
});

test("only whitespace and the email address are refused", () => {
  assert.equal(passwordProblem(" ".repeat(14)), "only_spaces");
  assert.equal(passwordProblem("Person@Example.com", " person@example.com "), "same_as_email");
  assert.equal(passwordProblem("person@example.com1", "person@example.com"), null);
});

test("auth paths are recognised; case paths are not", () => {
  assert.ok(isAuthPath(accountPaths.login));
  assert.ok(isAuthPath(accountPaths.me));
  assert.ok(!isAuthPath(accountPaths.cases));
  assert.equal(accountPaths.claim("a/b"), "/api/v1/kadi/cases/a%2Fb/claim");
});

test("credentials option is sent, read per request, and a per-request value wins", async () => {
  const seen: (RequestCredentials | undefined)[] = [];
  const fetchImpl = (async (_url: string, init: RequestInit) => {
    seen.push(init.credentials);
    return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
  }) as unknown as typeof fetch;
  let mode: RequestCredentials = "include";
  const client = createClient({ baseUrl: "http://api", fetchImpl, credentials: () => mode });
  await client.request("/a");
  mode = "same-origin";
  await client.request("/b");
  await client.request("/c", { credentials: "omit" });
  await createClient({ baseUrl: "http://api", fetchImpl }).request("/d");
  assert.deepEqual(seen, ["include", "same-origin", "omit", undefined]);
});
