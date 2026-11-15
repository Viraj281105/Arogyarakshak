import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import { measureWebRouteSizes } from "../measure-baseline.mjs";

function fixture() {
  const dir = mkdtempSync(join(tmpdir(), "next-fixture-"));
  mkdirSync(join(dir, "static", "chunks"), { recursive: true });
  mkdirSync(join(dir, "server", "app", "a"), { recursive: true });
  const chunk = (name, size) => {
    const body = Buffer.from(Array.from({ length: size }, (_, i) => (i * 7919) % 251));
    writeFileSync(join(dir, "static", "chunks", name), body);
    return gzipSync(body).length / 1024;
  };
  const poly = chunk("poly.js", 3000);
  const root = chunk("root.js", 5000);
  const home = chunk("home.js", 2000);
  const a = chunk("a.js", 4000);
  chunk("unused.js", 9000);
  writeFileSync(join(dir, "build-manifest.json"), JSON.stringify({
    polyfillFiles: ["static/chunks/poly.js"], rootMainFiles: ["static/chunks/root.js"],
  }));
  writeFileSync(join(dir, "app-path-routes-manifest.json"), JSON.stringify({ "/page": "/", "/a/page": "/a" }));
  const man = (key, files) => `globalThis.__RSC_MANIFEST = globalThis.__RSC_MANIFEST || {};
globalThis.__RSC_MANIFEST["${key}"] = ${JSON.stringify({ entryJSFiles: { "[project]/app/page": files } })};`;
  writeFileSync(join(dir, "server", "app", "page_client-reference-manifest.js"), man("/page", ["static/chunks/home.js"]));
  writeFileSync(join(dir, "server", "app", "a", "page_client-reference-manifest.js"), man("/a/page", ["static/chunks/a.js", "static/chunks/home.js"]));
  return { dir, expected: { "/": poly + root + home, "/a": poly + root + a + home } };
}

test("measureWebRouteSizes sums gzip KB of shared + route entry chunks", () => {
  const { dir, expected } = fixture();
  const got = measureWebRouteSizes(dir);
  assert.deepEqual(Object.keys(got).sort(), ["/", "/a"]);
  for (const r of Object.keys(expected)) {
    assert.ok(Math.abs(got[r] - expected[r]) < 0.01, `${r}: ${got[r]} vs ${expected[r]}`);
  }
});

test("measureWebRouteSizes throws naming the route and manifest path when a manifest is missing", () => {
  const { dir } = fixture();
  rmSync(join(dir, "server", "app", "a", "page_client-reference-manifest.js"));
  assert.throws(
    () => measureWebRouteSizes(dir),
    (err) => /\/a/.test(err.message) && /a[\\/]page_client-reference-manifest\.js/.test(err.message),
  );
});
