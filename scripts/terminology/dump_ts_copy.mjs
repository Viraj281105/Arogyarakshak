// Dumps every hi/mr (and en) string in the app's TypeScript copy dictionaries as JSON:
//   { "<source>": { "en|hi|mr": { "<dotted.path>": "<string>" } } }
// Used by scripts/terminology_audit.py. Read-only; imports the real dictionaries so nothing is re-parsed.
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1")), "..", "..");
const SOURCES = [
  ["web/translations", "apps/web/app/translations.ts", "translations"],
  ["web/shellCopy", "apps/web/app/shell/shellCopy.ts", "shellCopy"],
  ["web/listenCopy", "apps/web/app/lib/listenCopy.ts", "listenCopy"],
  ["web/explainStrings", "apps/web/app/lib/explainStrings.ts", "EXPLAIN_STRINGS"],
  ["mobile/strings", "apps/mobile/src/translations/strings.ts", "translations"],
  ["shared/common", "packages/i18n/src/common.ts", "common"],
];

function flatten(value, prefix, out) {
  if (typeof value === "string") out[prefix] = value;
  else if (Array.isArray(value)) value.forEach((v, i) => flatten(v, `${prefix}[${i}]`, out));
  else if (value && typeof value === "object") for (const [k, v] of Object.entries(value)) flatten(v, prefix ? `${prefix}.${k}` : k, out);
  // functions and other values carry no copy
}

const result = {};
for (const [name, file, exportName] of SOURCES) {
  const mod = await import(pathToFileURL(path.join(root, file)).href);
  const dict = mod[exportName];
  result[name] = {};
  for (const lang of ["en", "hi", "mr"]) {
    const flat = {};
    if (dict && dict[lang]) flatten(dict[lang], "", flat);
    result[name][lang] = flat;
  }
}
process.stdout.write(JSON.stringify(result));
