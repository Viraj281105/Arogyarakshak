import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  AA_TEXT,
  EVIDENCE_STATES,
  checkContrast,
  contrastPairs,
  contrastRatio,
  themeColors,
} from "../contrast.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const tokens = JSON.parse(readFileSync(join(here, "..", "tokens.json"), "utf8"));
const fmt = (r) => `${r.theme}: ${r.fg} (${r.fgValue}) on ${r.bg} (${r.bgValue}) = ${r.ratio.toFixed(2)} < ${r.min} [${r.why}]`;

test("contrastRatio matches known WCAG values", () => {
  assert.equal(contrastRatio("#000000", "#FFFFFF").toFixed(2), "21.00");
  assert.equal(contrastRatio("#FFFFFF", "#FFFFFF").toFixed(2), "1.00");
  // The brief's Needs-attention amber fails as text on white (the reason badges use an ink-grade shade).
  assert.ok(contrastRatio("#C28A35", "#FFFFFF") < AA_TEXT);
  assert.throws(() => contrastRatio("rgba(0,0,0,1)", "#FFFFFF"), /opaque/);
});

for (const theme of ["light", "dark"]) {
  test(`every text/background, evidence, action, chart and paper pair meets WCAG AA in ${theme}`, () => {
    const results = checkContrast(tokens, theme);
    const missing = results.filter((r) => r.error).map((r) => `${theme}: ${r.error}`);
    assert.deepEqual(missing, []);
    assert.deepEqual(results.filter((r) => !r.ok).map(fmt), []);
    assert.ok(results.length > 100, `expected the full pair list, got ${results.length}`);
  });
}

test("the check fails when a token drops under AA (guards against a vacuous pass)", () => {
  const broken = structuredClone(tokens);
  broken.color.light["text-secondary"] = "#9AA6B4";
  const failures = checkContrast(broken, "light").filter((r) => !r.ok);
  assert.ok(failures.some((r) => r.fg === "text-secondary"));
});

test("exactly nine evidence states, each with fg/bg/border in both themes", () => {
  assert.deepEqual(EVIDENCE_STATES, [
    "verified", "provisional", "unevaluated", "insufficient-evidence",
    "ai-generated", "human-reviewed", "rule-engine", "user-provided", "external",
  ]);
  for (const theme of ["light", "dark"]) {
    const c = themeColors(tokens, theme);
    for (const s of EVIDENCE_STATES) {
      for (const part of ["fg", "bg", "border"]) {
        assert.match(c[`evidence-${s}-${part}`] ?? "", /^#[0-9A-F]{6}$/i, `${theme} evidence-${s}-${part}`);
      }
    }
    const fgs = EVIDENCE_STATES.map((s) => c[`evidence-${s}-fg`].toUpperCase());
    assert.equal(new Set(fgs).size, 9, `${theme}: evidence foregrounds must be distinct`);
  }
});

test("dark theme is designed, not a copy of light: core surfaces and actions differ", () => {
  const d = themeColors(tokens, "dark");
  const l = themeColors(tokens, "light");
  for (const k of ["bg-base", "bg-surface", "text-primary", "action-primary", "text-on-action", "border-focus"]) {
    assert.notEqual(d[k], l[k], k);
  }
});

test("the official Deep Forest / Warm Ivory palette is present verbatim", () => {
  const d = tokens.color.dark;
  assert.deepEqual(
    [d["palette-deep-forest"], d["palette-secondary-forest"], d["palette-muted-sage"], d["palette-pale-sage"],
      d["palette-warm-ivory"], d["palette-white"], d["palette-ink"], d["palette-ink-secondary"], d["palette-hairline"]],
    ["#142F2B", "#244C42", "#91B49C", "#D5E7D9", "#F4F1E8", "#FFFFFF", "#1D2925", "#64766C", "#E2E2D8"],
  );
  assert.deepEqual(
    [d["semantic-verified"], d["semantic-ai"], d["semantic-human"], d["semantic-attention"], d["semantic-critical"],
      d["semantic-not-assessed"]],
    ["#397A58", "#52769B", "#8066A5", "#C28A35", "#C4544F", "#89918C"],
  );
  const l = tokens.color.light;
  assert.deepEqual(
    [l["bg-base"], l["bg-surface"], l["border-subtle"], l["text-primary"], l["action-primary"]],
    ["#F4F1E8", "#FFFFFF", "#E2E2D8", "#1D2925", "#142F2B"],
  );
});

test("pair list covers every evidence state and every page background", () => {
  const pairs = contrastPairs();
  for (const s of EVIDENCE_STATES) assert.ok(pairs.some((p) => p.fg === `evidence-${s}-fg`), s);
  for (const bg of ["bg-base", "bg-surface", "bg-surface-elevated", "bg-surface-secondary"]) {
    assert.ok(pairs.some((p) => p.fg === "text-muted" && p.bg === bg), bg);
  }
});
