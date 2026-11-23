#!/usr/bin/env node
// Dependency-free performance baseline helper (Node 20+ ESM).
// Usage: node scripts/measure-baseline.mjs <path-to-.next> [--include-nomodule]
// Prints JSON: { "<route>": <gzip KB of initial JS>, ... }. By default the noModule polyfill
// chunk is excluded (what module browsers download); --include-nomodule gives the old measure.
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { gzipSync } from "node:zlib";
import { pathToFileURL } from "node:url";
import vm from "node:vm";

// Routes (by public path) that legitimately have no client reference manifest.
// Empty on purpose: in the Next.js 16.4.2 production build every app route
// (/, /clinical-review, /motion-lab, /_not-found, /_global-error) emits one, so a
// missing manifest means a broken/partial build. Silently counting only the shared
// chunks would let a budget check pass wrongly. Add a route here only after
// confirming in a real build that it has none, and say why in a comment.
const ROUTES_WITHOUT_CLIENT_MANIFEST = new Set();

function readJson(file) {
  return JSON.parse(readFileSync(file, "utf8"));
}

function gzipKb(file) {
  return gzipSync(readFileSync(file)).length / 1024;
}

// page_client-reference-manifest.js assigns into globalThis.__RSC_MANIFEST.
function loadClientManifest(file) {
  const sandbox = { globalThis: {} };
  sandbox.globalThis.__RSC_MANIFEST = {};
  vm.runInNewContext(readFileSync(file, "utf8"), sandbox);
  const all = sandbox.globalThis.__RSC_MANIFEST;
  return Object.values(all)[0] ?? {};
}

/**
 * The polyfill files Next.js renders as `<script noModule>`. Module-capable browsers (every
 * browser Next 16 supports) never download them. Throws if any prerendered page references one
 * of them WITHOUT `noModule`, so excluding them can never hide JS that is really downloaded.
 */
export function noModuleFiles(dir, build) {
  const files = build.polyfillFiles ?? [];
  const appDir = join(dir, "server", "app");
  const pages = existsSync(appDir)
    ? readdirSync(appDir, { recursive: true }).map(String).filter((f) => f.endsWith(".html"))
    : [];
  for (const page of pages) {
    const tags = readFileSync(join(appDir, page), "utf8").match(/<script[\s>][^>]*>?/gi) ?? [];
    for (const f of files) {
      const name = f.slice(f.lastIndexOf("/") + 1);
      const loaded = tags.filter((tag) => tag.includes(name));
      if (loaded.some((tag) => !/nomodule/i.test(tag))) {
        throw new Error(`${f} is loaded without noModule in ${page}; it cannot be excluded from the measure.`);
      }
    }
  }
  return new Set(files);
}

/**
 * Gzip KB (2 decimals) of the initial JS a module-capable browser downloads for each App Router
 * route: root main files (framework/runtime) + the route's entry chunks (layout, error/not-found
 * boundaries and page) from its client reference manifest. That is the <script src> set in the
 * prerendered HTML minus the `noModule` polyfill chunk (Wave 3 decision B1, 2026-11-23).
 * `{ includeNoModule: true }` gives the pre-Wave-3 measure (polyfills counted) for comparison.
 */
export function measureWebRouteSizes(nextDir, { includeNoModule = false } = {}) {
  const dir = resolve(nextDir);
  const build = readJson(join(dir, "build-manifest.json"));
  const routes = readJson(join(dir, "app-path-routes-manifest.json"));
  const excluded = includeNoModule ? new Set() : noModuleFiles(dir, build);
  const shared = [...(build.polyfillFiles ?? []), ...(build.rootMainFiles ?? [])].filter((f) => !excluded.has(f));
  const out = {};
  for (const [key, route] of Object.entries(routes)) {
    const manifestFile = join(dir, "server", "app", `${key}_client-reference-manifest.js`);
    const files = new Set(shared);
    if (existsSync(manifestFile)) {
      const entry = loadClientManifest(manifestFile).entryJSFiles ?? {};
      for (const list of Object.values(entry)) list.forEach((f) => excluded.has(f) || files.add(f));
    } else if (!ROUTES_WITHOUT_CLIENT_MANIFEST.has(route)) {
      throw new Error(
        `Route ${route} has no client reference manifest at ${manifestFile}; ` +
          "refusing to report a size that omits its entry chunks (incomplete build?).",
      );
    }
    let total = 0;
    for (const f of files) {
      if (f.endsWith(".js")) total += gzipKb(join(dir, f));
    }
    out[route] = Math.round(total * 100) / 100;
  }
  return out;
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? "").href) {
  const nextDir = process.argv[2];
  if (!nextDir) {
    console.error("usage: node scripts/measure-baseline.mjs <path-to-.next>");
    process.exit(2);
  }
  const includeNoModule = process.argv.includes("--include-nomodule");
  console.log(JSON.stringify(measureWebRouteSizes(nextDir, { includeNoModule }), null, 2));
}
