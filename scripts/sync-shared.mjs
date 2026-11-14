import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync, existsSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir).sort()) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...walk(full));
    else out.push(full);
  }
  return out;
}

function render(source, ext, banner) {
  if (ext === ".ts" || ext === ".tsx") return `${banner}\n/* eslint-disable */\n${source}`;
  if (ext === ".css") return `${banner}\n${source}`;
  return source;
}

/**
 * Vendor every file under `from` into each directory in `to`.
 * `.ts`/`.tsx` get `banner` plus an eslint-disable line, `.css` gets `banner`
 * (the caller supplies a comment valid for the language). In `check` mode
 * nothing is written; stale or missing targets are reported.
 */
export function syncShared({ from, to, banner, check }) {
  const changed = [];
  const files = walk(from);
  for (const dest of to) {
    for (const file of files) {
      const rel = relative(from, file);
      const target = join(dest, rel);
      const expected = render(readFileSync(file, "utf8"), extname(file), banner);
      const current = existsSync(target) ? readFileSync(target, "utf8") : null;
      if (current === expected) continue;
      changed.push(target);
      if (!check) {
        mkdirSync(dirname(target), { recursive: true });
        writeFileSync(target, expected);
      }
    }
  }
  return { changed };
}
