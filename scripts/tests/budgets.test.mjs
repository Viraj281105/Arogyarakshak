import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  WEB_INITIAL_JS_KB,
  evaluateWebBudget,
  checkWebBundleBudget,
} from "../build-checks/web-bundle-budget.mjs";
import {
  MOBILE_BUNDLE_BUDGET_BYTES,
  evaluateMobileBudget,
  findHermesBundle,
} from "../build-checks/mobile-bundle-budget.mjs";

test("web budget constant is the 170 KB spec value", () => {
  assert.equal(WEB_INITIAL_JS_KB, 170);
});

test("a route at 171 KB fails the web budget", () => {
  const errors = evaluateWebBudget({ "/x": 171 }, {});
  assert.equal(errors.length, 1);
  assert.match(errors[0], /\/x/);
  assert.match(errors[0], /171/);
});

test("a route at 170 KB passes the web budget", () => {
  assert.deepEqual(evaluateWebBudget({ "/x": 170 }, {}), []);
});

test("a known-violation route passes at or below its ceiling and fails above it", () => {
  assert.deepEqual(evaluateWebBudget({ "/big": 255 }, { "/big": 255 }), []);
  const errors = evaluateWebBudget({ "/big": 255.5 }, { "/big": 255 });
  assert.equal(errors.length, 1);
  assert.match(errors[0], /ceiling/);
});

test("a known-violation entry whose route is now within budget fails (ratchet)", () => {
  const errors = evaluateWebBudget({ "/fixed": 170 }, { "/fixed": 200 });
  assert.equal(errors.length, 1);
  assert.match(errors[0], /remove it from KNOWN_VIOLATIONS/);
});

test("a known-violation entry for a route that no longer exists fails", () => {
  const errors = evaluateWebBudget({ "/a": 100 }, { "/gone": 200 });
  assert.equal(errors.length, 1);
  assert.match(errors[0], /\/gone/);
  assert.match(errors[0], /no longer exists/);
});

test("an empty measurement fails even with an empty KNOWN_VIOLATIONS map", () => {
  const errors = evaluateWebBudget({}, {});
  assert.equal(errors.length, 1);
  assert.match(errors[0], /No routes were measured/);
});

test("web check throws (does not pass silently) when .next is missing", () => {
  const empty = mkdtempSync(join(tmpdir(), "no-next-"));
  assert.throws(() => checkWebBundleBudget(join(empty, ".next")), /npm run build/);
});

test("mobile bundle over budget fails with the size delta in the message", () => {
  const msg = evaluateMobileBudget(MOBILE_BUNDLE_BUDGET_BYTES + 1234);
  assert.ok(msg);
  assert.match(msg, /1,234/);
});

test("mobile bundle at or under budget passes", () => {
  assert.equal(evaluateMobileBudget(MOBILE_BUNDLE_BUDGET_BYTES), null);
  assert.equal(evaluateMobileBudget(2_361_153), null);
  assert.equal(MOBILE_BUNDLE_BUDGET_BYTES, 2_900_000);
});

test("findHermesBundle returns the single .hbc and throws on none or many", () => {
  const out = mkdtempSync(join(tmpdir(), "export-"));
  const js = join(out, "_expo", "static", "js", "android");
  mkdirSync(js, { recursive: true });
  assert.throws(() => findHermesBundle(out), /no \.hbc/i);
  writeFileSync(join(js, "AppEntry-a.hbc"), "x");
  assert.equal(findHermesBundle(out), join(js, "AppEntry-a.hbc"));
  writeFileSync(join(js, "AppEntry-b.hbc"), "y");
  assert.throws(() => findHermesBundle(out), /expected exactly one/i);
});
