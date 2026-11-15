import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { common } from "../src/common";
import {
  findMissingKeys,
  findUnreviewedStubs,
  findUnusedKeys,
  UNREVIEWED_STUB_ALLOWLIST,
} from "../tools/parity";

test("common has en, hi and mr", () => {
  assert.deepEqual(Object.keys(common).sort(), ["en", "hi", "mr"]);
});

test("findMissingKeys flags a key present in en and absent in mr", () => {
  const catalogue = {
    en: { a: "A", nested: { b: "B", c: "C" } },
    hi: { a: "ए", nested: { b: "बी", c: "सी" } },
    mr: { a: "ए", nested: { b: "बी" } },
  };
  assert.deepEqual(findMissingKeys(catalogue), ["mr: nested.c"]);
});

test("findMissingKeys flags keys missing from en relative to another language, and empty values", () => {
  const catalogue = {
    en: { a: "A" },
    hi: { a: "ए", extra: "अतिरिक्त" },
    mr: { a: "  " },
  };
  assert.deepEqual(findMissingKeys(catalogue), ["en: extra", "mr: a (empty)", "mr: extra"]);
});

test("findMissingKeys returns [] for common", () => {
  assert.deepEqual(findMissingKeys(common), []);
});

test("findUnreviewedStubs lists hi/mr values identical to en, excluding the allow-list", () => {
  const catalogue = {
    en: { brand: "ArogyaRakshak", greeting: "Hello", nested: { label: "Policy No." }, empty: "" },
    hi: { brand: "ArogyaRakshak", greeting: "Hello", nested: { label: "पॉलिसी क्र." }, empty: "" },
    mr: { brand: "ArogyaRakshak", greeting: "नमस्कार", nested: { label: "Policy No." }, empty: "" },
  };
  const allow = new Set(["ArogyaRakshak"]);
  assert.deepEqual(findUnreviewedStubs(catalogue, allow), ["hi: greeting", "mr: nested.label"]);
});

test("findUnreviewedStubs uses the exported allow-list by default", () => {
  assert.ok(UNREVIEWED_STUB_ALLOWLIST instanceof Set);
  const catalogue = {
    en: { x: "Same" },
    hi: { x: "Same" },
    mr: { x: "Same" },
  };
  assert.deepEqual(findUnreviewedStubs(catalogue), ["hi: x", "mr: x"]);
});

test("findUnusedKeys returns dotted paths whose leaf is never referenced in the source files", () => {
  const dir = mkdtempSync(join(tmpdir(), "i18n-unused-"));
  const a = join(dir, "a.tsx");
  const b = join(dir, "b.ts");
  writeFileSync(a, "const x = t.title; const y = t.nested.label;");
  writeFileSync(b, 'const z = t["greeting"];');
  const catalogue = {
    en: { title: "T", greeting: "G", nested: { label: "L", orphan: "O" }, lonely: "N" },
    hi: {},
    mr: {},
  };
  assert.deepEqual(findUnusedKeys(catalogue, [a, b]), ["lonely", "nested.orphan"]);
});
