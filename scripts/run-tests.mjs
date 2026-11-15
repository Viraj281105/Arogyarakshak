import { readdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const isTest = (n) => /\.test\.[cm]?[jt]sx?$/.test(n);

function list(dir) {
  return existsSync(dir) ? readdirSync(dir).filter(isTest).map((n) => join(dir, n)) : [];
}

const files = list(join(root, "scripts", "tests"));
const pkgs = join(root, "packages");
if (existsSync(pkgs)) {
  for (const p of readdirSync(pkgs).sort()) files.push(...list(join(pkgs, p, "tests")));
}
if (files.length === 0) {
  console.log("No Node tests found.");
  process.exit(0);
}
const r = spawnSync(process.execPath, ["--import", "tsx", "--test", ...files], {
  stdio: "inherit",
  cwd: root,
});
process.exit(r.status ?? 1);
