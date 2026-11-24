import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { gzipSync } from "node:zlib";
import { measureWebRouteSizes, noModuleFiles } from "../measure-baseline.mjs";

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
  mkdirSync(join(dir, "server", "app", "nested"), { recursive: true });
  writeFileSync(join(dir, "server", "app", "index.html"),
    '<script src="/_next/static/chunks/poly.js" noModule=""></script><script src="/_next/static/chunks/root.js" async=""></script>');
  writeFileSync(join(dir, "server", "app", "nested", "deep.html"), '<script src="/_next/static/chunks/root.js"></script>');
  return {
    dir,
    expected: { "/": root + home, "/a": root + a + home },
    withNoModule: { "/": poly + root + home, "/a": poly + root + a + home },
  };
}

const near = (got, expected) => {
  assert.deepEqual(Object.keys(got).sort(), Object.keys(expected).sort());
  for (const r of Object.keys(expected)) {
    assert.ok(Math.abs(got[r] - expected[r]) < 0.01, `${r}: ${got[r]} vs ${expected[r]}`);
  }
};

test("measureWebRouteSizes sums gzip KB of root + route entry chunks, excluding the noModule polyfills", () => {
  const { dir, expected } = fixture();
  near(measureWebRouteSizes(dir), expected);
});

test("includeNoModule restores the pre-Wave-3 measure (polyfills counted)", () => {
  const { dir, withNoModule } = fixture();
  near(measureWebRouteSizes(dir, { includeNoModule: true }), withNoModule);
});

test("a polyfill file loaded WITHOUT noModule in any prerendered page (nested too) makes the measure throw", () => {
  const { dir } = fixture();
  writeFileSync(join(dir, "server", "app", "nested", "deep.html"), '<script src="/_next/static/chunks/poly.js"></script>');
  assert.throws(() => measureWebRouteSizes(dir), /poly\.js is loaded without noModule in nested[\\/]deep\.html/);
  assert.doesNotThrow(() => measureWebRouteSizes(dir, { includeNoModule: true }));
});

test("noModuleFiles returns the build manifest's polyfill files", () => {
  const { dir } = fixture();
  const build = JSON.parse(readFileSync(join(dir, "build-manifest.json"), "utf8"));
  assert.deepEqual([...noModuleFiles(dir, build)], ["static/chunks/poly.js"]);
});

test("measureWebRouteSizes throws naming the route and manifest path when a manifest is missing", () => {
  const { dir } = fixture();
  rmSync(join(dir, "server", "app", "a", "page_client-reference-manifest.js"));
  assert.throws(
    () => measureWebRouteSizes(dir),
    (err) => /\/a/.test(err.message) && /a[\\/]page_client-reference-manifest\.js/.test(err.message),
  );
});
