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
  // The brief's Clinical Teal fails as text on white (the reason the palette darkens it).
  assert.ok(contrastRatio("#13A89E", "#FFFFFF") < AA_TEXT);
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

test("exactly eight evidence states, each with fg/bg/border in both themes", () => {
  assert.deepEqual(EVIDENCE_STATES, [
    "verified", "provisional", "unevaluated", "insufficient-evidence",
    "ai-generated", "rule-engine", "user-provided", "external",
  ]);
  for (const theme of ["light", "dark"]) {
    const c = themeColors(tokens, theme);
    for (const s of EVIDENCE_STATES) {
      for (const part of ["fg", "bg", "border"]) {
        assert.match(c[`evidence-${s}-${part}`] ?? "", /^#[0-9A-F]{6}$/i, `${theme} evidence-${s}-${part}`);
      }
    }
    const fgs = EVIDENCE_STATES.map((s) => c[`evidence-${s}-fg`].toUpperCase());
    assert.equal(new Set(fgs).size, 8, `${theme}: evidence foregrounds must be distinct`);
  }
});

test("dark theme is designed, not a copy of light: core surfaces and actions differ", () => {
  const d = themeColors(tokens, "dark");
  const l = themeColors(tokens, "light");
  for (const k of ["bg-base", "bg-surface", "text-primary", "action-primary", "text-on-action", "border-focus"]) {
    assert.notEqual(d[k], l[k], k);
  }
});

test("the brief's palette is present verbatim as reference tokens", () => {
  const d = tokens.color.dark;
  assert.deepEqual(
    [d["palette-midnight-navy"], d["palette-deep-navy"], d["palette-slate-blue"], d["palette-clinical-teal"],
      d["palette-electric-cyan"], d["palette-soft-mint"]],
    ["#101B2A", "#15263A", "#263C52", "#13A89E", "#43C6D5", "#B6E7D8"],
  );
  const l = tokens.color.light;
  assert.deepEqual(
    [l["bg-base"], l["bg-surface"], l["bg-surface-secondary"], l["border-subtle"], l["text-primary"]],
    ["#F5F7FA", "#FFFFFF", "#EEF2F6", "#E0E6ED", "#172433"],
  );
});

test("pair list covers every evidence state and every page background", () => {
  const pairs = contrastPairs();
  for (const s of EVIDENCE_STATES) assert.ok(pairs.some((p) => p.fg === `evidence-${s}-fg`), s);
  for (const bg of ["bg-base", "bg-surface", "bg-surface-elevated", "bg-surface-secondary"]) {
    assert.ok(pairs.some((p) => p.fg === "text-muted" && p.bg === bg), bg);
  }
});
