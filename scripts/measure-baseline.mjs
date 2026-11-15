#!/usr/bin/env node
// Dependency-free performance baseline helper (Node 20+ ESM).
// Usage: node scripts/measure-baseline.mjs <path-to-.next>
// Prints JSON: { "<route>": <gzip KB of initial JS>, ... }
import { readFileSync, existsSync } from "node:fs";
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
 * Gzip KB (2 decimals) of the initial JS each App Router route loads:
 * polyfills + root main files (framework/runtime) + the route's entry chunks
 * (layout, error/not-found boundaries and page) from its client reference manifest.
 * This matches the <script src> set in the prerendered HTML.
 */
export function measureWebRouteSizes(nextDir) {
  const dir = resolve(nextDir);
  const build = readJson(join(dir, "build-manifest.json"));
  const routes = readJson(join(dir, "app-path-routes-manifest.json"));
  const shared = [...(build.polyfillFiles ?? []), ...(build.rootMainFiles ?? [])];
  const out = {};
  for (const [key, route] of Object.entries(routes)) {
    const manifestFile = join(dir, "server", "app", `${key}_client-reference-manifest.js`);
    const files = new Set(shared);
    if (existsSync(manifestFile)) {
      const entry = loadClientManifest(manifestFile).entryJSFiles ?? {};
      for (const list of Object.values(entry)) list.forEach((f) => files.add(f));
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
  console.log(JSON.stringify(measureWebRouteSizes(nextDir), null, 2));
}
