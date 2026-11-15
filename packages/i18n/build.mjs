// i18n vendoring: packages/i18n/src (shared types + `common` namespace) is copied into both apps.
// Usage: node packages/i18n/build.mjs [--check]
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { syncShared } from "../../scripts/sync-shared.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");
const BANNER = "// GENERATED - do not edit; source: packages/i18n/src";

export const defaultPaths = {
  srcDir: join(here, "src"),
  targets: [
    join(repoRoot, "apps", "web", "app", "shared", "i18n"),
    join(repoRoot, "apps", "mobile", "src", "shared", "i18n"),
  ],
};

/** Vendor src/ into both apps. In check mode nothing is written; throws listing stale, missing or orphaned files. */
export function runBuild({ check = false, paths = defaultPaths } = {}) {
  const { changed } = syncShared({ from: paths.srcDir, to: paths.targets, banner: BANNER, check });
  if (check && changed.length > 0) {
    throw new Error(`i18n vendored copies are stale; run \`npm run generate\`:\n${changed.map((f) => `  ${f}`).join("\n")}`);
  }
  return { changed };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  runBuild({ check: process.argv.includes("--check") });
}
