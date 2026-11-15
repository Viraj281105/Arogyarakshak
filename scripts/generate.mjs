import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { discover } from "./discover.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const generators = await discover(join(here, "generators"));
if (generators.length === 0) console.log("No generators registered.");
for (const { name, fn } of generators) {
  await fn();
  console.log(`generated ${name}`);
}
