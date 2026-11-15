import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { runBuild } from "../../packages/i18n/build.mjs";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

/** Fails when a vendored i18n copy is stale/orphaned, or `common` is missing a key/value in any language. */
export default async function check() {
  runBuild({ check: true });
  // findMissingKeys is TypeScript; run it under tsx (the same loader the test runner uses).
  const result = spawnSync(
    process.execPath,
    ["--import", "tsx", join(repoRoot, "packages", "i18n", "tools", "check-parity.ts")],
    { cwd: repoRoot, encoding: "utf8" },
  );
  if (result.status !== 0) {
    throw new Error(`i18n common namespace is missing keys:\n${result.stderr || result.stdout}`);
  }
}
