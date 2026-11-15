import { readdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

/** Import the default export of every `*.mjs` in `dir`, sorted by name. */
export async function discover(dir) {
  if (!existsSync(dir)) return [];
  const names = readdirSync(dir).filter((n) => n.endsWith(".mjs")).sort();
  const out = [];
  for (const name of names) {
    const mod = await import(pathToFileURL(join(dir, name)).href);
    out.push({ name, fn: mod.default });
  }
  return out;
}
