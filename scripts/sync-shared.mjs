import { mkdirSync, readFileSync, readdirSync, statSync, writeFileSync, existsSync, rmSync } from "node:fs";
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
 * (the caller supplies a comment valid for the language). Files present in a
 * target but absent from `from` (orphans, e.g. a deleted source file) are
 * reported, and removed in write mode. In `check` mode nothing is written or
 * removed; stale, missing or orphaned targets are reported.
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
    if (existsSync(dest)) {
      const expectedRel = new Set(files.map((f) => relative(from, f)));
      for (const file of walk(dest)) {
        if (expectedRel.has(relative(dest, file))) continue;
        changed.push(file);
        if (!check) rmSync(file);
      }
    }
  }
  return { changed };
}
