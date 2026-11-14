// Reusable extractor: captures every custom property declared in the top-level
// `:root` and `[data-theme="light"]` blocks of a CSS file.
// Usage: git show HEAD:apps/web/app/globals.css | node extract-baseline.mjs > out.json
//        node extract-baseline.mjs path/to/globals.css > out.json
// Prints a JSON fixture to stdout; a selector report (every selector that
// declares custom properties) goes to stderr.
import { readFileSync } from "node:fs";

export function extractVars(cssText) {
  const css = cssText.replace(/\/\*[\s\S]*?\*\//g, "");
  const result = { root: {}, light: {} };
  const declaring = new Map(); // selector -> count of custom props
  let i = 0;
  const walk = (depth, selector) => {
    // Parses a block body; returns nothing, advances i past closing brace.
    let buf = "";
    while (i < css.length) {
      const ch = css[i];
      if (ch === "{") {
        const sel = buf.trim().replace(/\s+/g, " ");
        buf = "";
        i++;
        walk(depth + 1, sel);
      } else if (ch === "}") {
        i++;
        return;
      } else if (ch === ";") {
        record(buf, depth, selector);
        buf = "";
        i++;
      } else if (ch === "(" ) {
        // copy balanced parens verbatim (url(data:...;...) etc.)
        let d = 0;
        while (i < css.length) {
          buf += css[i];
          if (css[i] === "(") d++;
          if (css[i] === ")" && --d === 0) { i++; break; }
          i++;
        }
      } else if (ch === '"' || ch === "'") {
        const q = ch;
        buf += ch; i++;
        while (i < css.length && css[i] !== q) { buf += css[i++]; }
        buf += css[i++] ?? "";
      } else {
        buf += ch;
        i++;
      }
    }
  };
  const record = (decl, depth, selector) => {
    const m = decl.trim().match(/^(--[A-Za-z0-9_-]+)\s*:\s*([\s\S]+)$/);
    if (!m) return;
    const value = m[2].trim().replace(/\s+/g, " ");
    declaring.set(selector, (declaring.get(selector) ?? 0) + 1);
    if (depth !== 1) return;
    if (selector === ":root") result.root[m[1]] = value;
    else if (selector === '[data-theme="light"]') result.light[m[1]] = value;
  };
  walk(0, "");
  return { result, declaring };
}

if (import.meta.main) {
  const src = readFileSync(process.argv[2] ?? 0, "utf8");
  const { result, declaring } = extractVars(src);
  for (const [sel, n] of declaring) console.error(`${n}\t${sel}`);
  process.stdout.write(JSON.stringify(result, null, 2) + "\n");
}
