#!/usr/bin/env node
// Android Hermes bundle size budget. Needs an `expo export --platform android` output dir,
// so it lives in scripts/build-checks/ (not run by the generic checks runner). Run:
//   cd apps/mobile && npx expo export --platform android --output-dir <dir>
//   npm run check:mobile-budget -- <dir>
import { existsSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

// WS5-shell measured 2,394,806 B; budget = that + about 8%, rounded (ruling 2026-11-18; was
// 2,900,000). Raising it needs a concrete screen, a fresh measurement and a documented ruling
// (see docs/development/performance-budgets.md, mobile section).
export const MOBILE_BUNDLE_BUDGET_BYTES = 2_600_000;

const fmt = (n) => n.toLocaleString("en-US");

/** Pure: null when within budget, otherwise a failure message including the delta. */
export function evaluateMobileBudget(bytes, budget = MOBILE_BUNDLE_BUDGET_BYTES) {
  if (bytes <= budget) return null;
  return `Android Hermes bundle is ${fmt(bytes)} B, over the ${fmt(budget)} B budget by ${fmt(bytes - budget)} B.`;
}

/** Locates the single .hbc under <exportDir>/_expo/static/js/android. */
export function findHermesBundle(exportDir) {
  const dir = join(resolve(exportDir), "_expo", "static", "js", "android");
  const found = existsSync(dir) ? readdirSync(dir).filter((n) => n.endsWith(".hbc")) : [];
  if (found.length === 0) {
    throw new Error(`No .hbc bundle found in ${dir}. Run "npx expo export --platform android --output-dir <dir>" first.`);
  }
  if (found.length > 1) {
    throw new Error(`Expected exactly one .hbc in ${dir}, found ${found.length}: ${found.join(", ")}`);
  }
  return join(dir, found[0]);
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  const exportDir = process.argv.find((a, i) => i >= 2 && !a.startsWith("--"));
  if (!exportDir) {
    console.error("usage: node scripts/build-checks/mobile-bundle-budget.mjs <expo-export-output-dir>");
    process.exit(2);
  }
  try {
    const file = findHermesBundle(exportDir);
    const bytes = statSync(file).size;
    console.log(`${file}: ${fmt(bytes)} B (budget ${fmt(MOBILE_BUNDLE_BUDGET_BYTES)} B)`);
    const msg = evaluateMobileBudget(bytes);
    if (msg) throw new Error(msg);
    console.log("PASS mobile bundle budget");
  } catch (err) {
    console.error(`FAIL mobile bundle budget: ${err instanceof Error ? err.message : err}`);
    process.exit(1);
  }
}
