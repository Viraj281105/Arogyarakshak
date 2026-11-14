import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, mkdtempSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
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
  const dir = mkdtempSync(join(tmpdir(), "tokens-ts-"));
  const file = join(dir, "tokens.ts");
  writeFileSync(file, buildTs(t));
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    // module is already evaluated; safe to remove
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
