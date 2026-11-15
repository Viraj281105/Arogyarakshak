import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { discover } from "./discover.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const checks = await discover(join(here, "checks"));
for (const { name, fn } of checks) {
  try {
    await fn();
    console.log(`PASS ${name}`);
  } catch (err) {
    console.error(`FAIL ${name}: ${err instanceof Error ? err.message : err}`);
    process.exit(1);
  }
}
console.log(`${checks.length} check(s) passed`);
