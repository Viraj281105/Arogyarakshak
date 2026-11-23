#!/usr/bin/env node
// Web initial-JS budget (gzip KB per route) with a ratchet for known violations.
// Needs a built apps/web/.next, so it lives in scripts/build-checks/ (NOT scripts/checks/,
// which the generic runner executes without a build). Run it with:
//   npm run check:web-budget   (or: node scripts/build-checks/web-bundle-budget.mjs --require-build)
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { measureWebRouteSizes } from "../measure-baseline.mjs";

export const WEB_INITIAL_JS_KB = 170;

/**
 * Routes already over WEB_INITIAL_JS_KB when the budget was introduced (Task 1 baseline:
 * every route was over). Value = ceiling in whole gzip KB (measured size rounded up), so
 * they cannot grow. Fix a route, then DELETE its entry: the check fails on entries that
 * are no longer needed.
 * WS4 ratchet (2026-11-18, fresh build): / 254.24 -> 222.26, /clinical-review 201.87 -> 190.32,
 * /_not-found 182.79 -> 179.84, /_global-error 174.57 -> 171.94; /motion-lab is no longer built
 * for production. About 167 KB of every route was framework (polyfills + React/Next runtime).
 * Wave 3 B1 (2026-11-23): the measure now excludes the `noModule` polyfill chunk (38.70 KB gzip),
 * which module-capable browsers never download (scripts/measure-baseline.mjs `noModuleFiles`).
 * Same WS4 build re-measured: / 222.26 -> 183.56, /clinical-review 190.32 -> 151.62, /_not-found
 * 179.84 -> 141.14, /_global-error 171.94 -> 133.24, so only / stays a known violation.
 * The framework floor is now about 128 KB (React/Next runtime only).
 */
export const KNOWN_VIOLATIONS = {
  "/": 184,
};

/** Pure: returns a list of failure messages (empty = pass). */
export function evaluateWebBudget(sizes, known = KNOWN_VIOLATIONS, limit = WEB_INITIAL_JS_KB) {
  const errors = [];
  if (Object.keys(sizes).length === 0) {
    return ["No routes were measured; refusing to pass an empty measurement (broken build?)."];
  }
  for (const [route, kb] of Object.entries(sizes)) {
    if (Object.hasOwn(known, route)) {
      const ceiling = known[route];
      if (kb <= limit) {
        errors.push(
          `${route} is now ${kb} KB (<= ${limit} KB budget): remove it from KNOWN_VIOLATIONS.`,
        );
      } else if (kb > ceiling) {
        errors.push(
          `${route} is ${kb} KB, above its known-violation ceiling of ${ceiling} KB (budget ${limit} KB).`,
        );
      }
    } else if (kb > limit) {
      errors.push(`${route} is ${kb} KB, above the ${limit} KB initial-JS budget (gzip).`);
    }
  }
  for (const route of Object.keys(known)) {
    if (!Object.hasOwn(sizes, route)) {
      errors.push(
        `KNOWN_VIOLATIONS lists ${route} but it no longer exists in the build: remove it.`,
      );
    }
  }
  return errors;
}

/** Throws when .next is missing or any budget rule fails; returns the sizes otherwise. */
export function checkWebBundleBudget(nextDir) {
  const dir = resolve(nextDir);
  if (!existsSync(join(dir, "build-manifest.json"))) {
    throw new Error(
      `No production build found at ${dir}. Run "npm run build" in apps/web first ` +
        "(the web bundle budget cannot be checked without it).",
    );
  }
  const sizes = measureWebRouteSizes(dir);
  const errors = evaluateWebBudget(sizes);
  if (errors.length > 0) throw new Error(errors.join("\n"));
  return sizes;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
  const nextDir = process.argv.find((a, i) => i >= 2 && !a.startsWith("--")) ?? join(root, "apps", "web", ".next");
  try {
    const sizes = checkWebBundleBudget(nextDir);
    for (const [r, kb] of Object.entries(sizes)) console.log(`${r}: ${kb} KB gzip`);
    console.log(`PASS web bundle budget (${WEB_INITIAL_JS_KB} KB + known-violation ceilings)`);
  } catch (err) {
    console.error(`FAIL web bundle budget:\n${err instanceof Error ? err.message : err}`);
    process.exit(1);
  }
}
