import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { syncShared } from "../sync-shared.mjs";

const TS_BANNER = "// GENERATED - do not edit";
const BANNER = "/* GENERATED - do not edit */";

function fixture() {
  const root = mkdtempSync(join(tmpdir(), "sync-shared-"));
  const from = join(root, "src");
  mkdirSync(join(from, "nested"), { recursive: true });
  writeFileSync(join(from, "a.ts"), "export const a = 1;\n");
  writeFileSync(join(from, "nested", "b.css"), ":root { --x: 1; }\n");
  writeFileSync(join(from, "c.json"), "{}\n");
  return { root, from, to: [join(root, "out1"), join(root, "out2")] };
}

test("copies files into every target, prepending the banner to ts and css", () => {
  const { from, to } = fixture();
  const { changed } = syncShared({ from, to, banner: TS_BANNER, check: false });
  assert.ok(changed.length > 0);
  for (const dir of to) {
    const ts = readFileSync(join(dir, "a.ts"), "utf8");
    assert.ok(ts.startsWith(`${TS_BANNER}\n/* eslint-disable */\n`));
    assert.ok(ts.endsWith("export const a = 1;\n"));
    const css = readFileSync(join(dir, "nested", "b.css"), "utf8");
    assert.ok(!css.includes("eslint-disable"));
    assert.equal(readFileSync(join(dir, "c.json"), "utf8"), "{}\n");
  }
});

test("css banner is a plain css comment", () => {
  const { from, to } = fixture();
  syncShared({ from, to, banner: BANNER, check: false });
  const css = readFileSync(join(to[0], "nested", "b.css"), "utf8");
  assert.ok(css.startsWith(`${BANNER}\n`));
});

test("second run is idempotent", () => {
  const { from, to } = fixture();
  syncShared({ from, to, banner: TS_BANNER, check: false });
  assert.deepEqual(syncShared({ from, to, banner: TS_BANNER, check: false }).changed, []);
});

test("check mode reports an edited vendored file and writes nothing", () => {
  const { from, to } = fixture();
  syncShared({ from, to, banner: TS_BANNER, check: false });
  const target = join(to[0], "a.ts");
  writeFileSync(target, "// hand edit\n");
  const { changed } = syncShared({ from, to, banner: TS_BANNER, check: true });
  assert.deepEqual(changed, [target]);
  assert.equal(readFileSync(target, "utf8"), "// hand edit\n");
});

test("missing target dir: created in write mode, reported (not created) in check mode", () => {
  const { from, to } = fixture();
  const checked = syncShared({ from, to, banner: TS_BANNER, check: true });
  assert.equal(checked.changed.length, 6);
  assert.ok(!existsSync(to[0]));
  syncShared({ from, to, banner: TS_BANNER, check: false });
  assert.ok(existsSync(join(to[0], "a.ts")));
});
