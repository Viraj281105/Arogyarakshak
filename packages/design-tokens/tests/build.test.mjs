import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { existsSync, copyFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { buildCss, buildTs, runBuild } from "../build.mjs";
import { extractVars } from "../scripts/extract-baseline.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const tokensPath = join(here, "..", "tokens.json");
const tokens = JSON.parse(readFileSync(tokensPath, "utf8"));
const baseline = JSON.parse(readFileSync(join(here, "fixtures", "globals-vars.baseline.json"), "utf8"));

// Generated variables not in the baseline are only allowed with these prefixes.
const ALLOWED_EXTRA = ["--space-", "--radius-", "--motion-", "--z-"];

/** Compare a baseline block against a generated block; returns a list of problems. */
function diffVars(expected, actual) {
  const problems = [];
  for (const [k, v] of Object.entries(expected)) {
    if (!(k in actual)) problems.push(`missing ${k}`);
    else if (actual[k] !== v) problems.push(`value ${k}: expected ${v} got ${actual[k]}`);
  }
  for (const k of Object.keys(actual)) {
    if (!(k in expected) && !ALLOWED_EXTRA.some((p) => k.startsWith(p))) problems.push(`unexplained extra ${k}`);
  }
  return problems;
}

test("parity: generated :root vars match baseline.root (no missing, no unexplained extras)", () => {
  const { result } = extractVars(buildCss(tokens));
  assert.deepEqual(diffVars(baseline.root, result.root), []);
});

test("parity: generated light vars match baseline.light (no missing, no unexplained extras)", () => {
  const { result } = extractVars(buildCss(tokens));
  assert.deepEqual(diffVars(baseline.light, result.light), []);
});

test("parity check fails when a light override is dropped", () => {
  const broken = structuredClone(tokens);
  delete broken.color.light["bg-base"];
  const { result } = extractVars(buildCss(broken));
  assert.ok(diffVars(baseline.light, result.light).includes("missing --bg-base"));
});

test("generated CSS uses LF and carries the generated banner", () => {
  const css = buildCss(tokens);
  assert.ok(!css.includes("\r"));
  assert.match(css, /GENERATED — do not edit; source: packages\/design-tokens\/tokens\.json/);
});

test("buildTs output camelCases keys (bg-base -> bgBase)", () => {
  const ts = buildTs(tokens);
  assert.match(ts, /bgBase:/);
  assert.doesNotMatch(ts, /bg-base/);
  assert.ok(!ts.includes("\r"));
  assert.match(ts, /GENERATED — do not edit; source: packages\/design-tokens\/tokens\.json/);
});

async function loadGenerated(t) {
  // Node-version independent: strip the TS-only syntax and load the result as plain ESM.
  const js = buildTs(t)
    .replace(/ as const;/g, ";")
    .replace(/^export type .*$/gm, "");
  const dir = mkdtempSync(join(tmpdir(), "tokens-ts-"));
  const file = join(dir, "tokens.mjs");
  writeFileSync(file, js);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

const MOBILE_KEYS = [
  "bgBase", "bgSurface", "bgSurfaceElevated", "borderSubtle", "borderMedium", "borderFocus",
  "textPrimary", "textSecondary", "textMuted", "brandForest", "brandBrass", "brandSage",
  "brandCyan", "brandTeal", "brandEmerald", "statusWarning", "statusDanger", "statusSuccess", "statusInfo",
];

test("buildTs exposes every key the mobile ColorPalette needs, in dark and light", async () => {
  const mod = await loadGenerated(tokens);
  for (const theme of ["dark", "light"]) {
    for (const k of MOBILE_KEYS) assert.equal(typeof mod.colors[theme][k], "string", `${theme}.${k}`);
  }
  assert.equal(mod.colors.dark.bgBase, "#151B18");
  assert.equal(mod.colors.light.bgBase, "#F7F6F2");
});

test("buildTs light palette falls back to dark values for non-overridden keys", async () => {
  const t = structuredClone(tokens);
  t.color.dark["only-dark"] = "#123456";
  const mod = await loadGenerated(t);
  assert.equal(mod.colors.light.onlyDark, "#123456");
  assert.deepEqual(Object.keys(mod.colors.light).sort(), Object.keys(mod.colors.dark).sort());
});

test("buildTs exports spacing, radii, motion and fonts from tokens", async () => {
  const mod = await loadGenerated(tokens);
  assert.deepEqual(
    [mod.spacing.xs, mod.spacing.sm, mod.spacing.md, mod.spacing.lg, mod.spacing.xl, mod.spacing.xxl],
    [4, 8, 16, 24, 32, 48],
  );
  assert.equal(mod.spacing.minTouchTarget, 44);
  assert.deepEqual([mod.radii.sm, mod.radii.md, mod.radii.lg, mod.radii.full], [6, 10, 16, 9999]);
  assert.equal(mod.motion.duration.base, 250);
  assert.equal(mod.motion.easing.standard, "cubic-bezier(0.2,0,0,1)");
  assert.equal(typeof mod.fonts.display, "string");
});

test("--check passes when outputs are current and fails after editing a generated file", () => {
  const dir = mkdtempSync(join(tmpdir(), "tokens-check-"));
  try {
    const cssPath = join(dir, "web", "tokens.css");
    const tsPath = join(dir, "mobile", "tokens.ts");
    mkdirSync(dirname(cssPath), { recursive: true });
    mkdirSync(dirname(tsPath), { recursive: true });
    const opts = { tokensPath, cssPath, tsPath };
    runBuild(opts);
    assert.doesNotThrow(() => runBuild({ ...opts, check: true }));
    writeFileSync(cssPath, readFileSync(cssPath, "utf8") + "\n/* hand edit */\n");
    assert.throws(() => runBuild({ ...opts, check: true }), /out of date/);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("parity check fails when a value is altered", () => {
  const altered = structuredClone(tokens);
  altered.color.dark["bg-base"] = "#000000";
  altered.color.light["bg-surface"] = "#010101";
  const { result } = extractVars(buildCss(altered));
  assert.ok(diffVars(baseline.root, result.root).some((p) => p.startsWith("value --bg-base")));
  assert.ok(diffVars(baseline.light, result.light).some((p) => p.startsWith("value --bg-surface")));
});

test("--check reports a missing output file and creates nothing", () => {
  const dir = mkdtempSync(join(tmpdir(), "tokens-missing-"));
  try {
    const cssPath = join(dir, "web", "tokens.css");
    const tsPath = join(dir, "mobile", "tokens.ts");
    assert.throws(() => runBuild({ tokensPath, cssPath, tsPath, check: true }), /out of date/);
    assert.ok(!existsSync(join(dir, "web")) && !existsSync(join(dir, "mobile")));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("CLI `node build.mjs --check` exits non-zero on stale or missing output, zero when current", () => {
  // Mirror the package layout in a temp repo so the CLI's default paths resolve inside it.
  const root = mkdtempSync(join(tmpdir(), "tokens-cli-"));
  try {
    const pkg = join(root, "packages", "design-tokens");
    mkdirSync(pkg, { recursive: true });
    copyFileSync(join(here, "..", "build.mjs"), join(pkg, "build.mjs"));
    copyFileSync(tokensPath, join(pkg, "tokens.json"));
    const run = (...args) => spawnSync(process.execPath, [join(pkg, "build.mjs"), ...args], { encoding: "utf8" });

    assert.notEqual(run("--check").status, 0, "missing outputs must fail");
    assert.equal(run().status, 0, "build writes outputs");
    assert.equal(run("--check").status, 0, "current outputs pass");
    const css = join(root, "apps", "web", "app", "generated", "tokens.css");
    writeFileSync(css, readFileSync(css, "utf8") + "/* stale */\n");
    const r = run("--check");
    assert.notEqual(r.status, 0, "stale output must fail");
    assert.match(r.stderr, /out of date/);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("extractVars keeps a final custom property that has no trailing semicolon", () => {
  const css = [":root {", "  --a: 1px;", "  --b: #fff", "}", '[data-theme="light"] { --a: 2px; --c: red }', ""].join("\n");
  const { result } = extractVars(css);
  assert.deepEqual(result.root, { "--a": "1px", "--b": "#fff" });
  assert.deepEqual(result.light, { "--a": "2px", "--c": "red" });
});
