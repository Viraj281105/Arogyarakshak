import { readFileSync } from "node:fs";
import { LANGUAGES, type Language } from "../src/types";

type Catalogue = Record<Language, object>;

/**
 * Identical-by-design strings: whole values that legitimately read the same in English, Hindi and
 * Marathi (e.g. a brand name or an agency abbreviation kept in Latin script). Anything else that equals
 * the English text in hi/mr is reported as an unreviewed stub. Empty today: the shared `common`
 * namespace has no hi/mr value identical to its English value (the brand name is transliterated).
 * Add an entry only after a native-speaker reviewer confirms the identical text is correct.
 */
export const UNREVIEWED_STUB_ALLOWLIST: ReadonlySet<string> = new Set([]);

/** Flatten a nested string dictionary to dotted paths. Non-string leaves are ignored. */
export function flatten(dict: object, prefix = ""): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(dict)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") out[path] = value;
    else if (value && typeof value === "object") Object.assign(out, flatten(value, path));
  }
  return out;
}

function flattenAll(catalogue: Catalogue): Record<Language, Record<string, string>> {
  return Object.fromEntries(LANGUAGES.map((l) => [l, flatten(catalogue[l] ?? {})])) as Record<
    Language,
    Record<string, string>
  >;
}

/**
 * Keys present in one language but absent in another ("<lang>: <path>"), and blank values
 * ("<lang>: <path> (empty)"). The reference set is the union of keys across languages.
 */
export function findMissingKeys(catalogue: Catalogue): string[] {
  const flat = flattenAll(catalogue);
  const all = [...new Set(LANGUAGES.flatMap((l) => Object.keys(flat[l])))].sort();
  const problems: string[] = [];
  for (const lang of LANGUAGES) {
    for (const key of all) {
      if (!(key in flat[lang])) problems.push(`${lang}: ${key}`);
      else if (flat[lang][key].trim() === "") problems.push(`${lang}: ${key} (empty)`);
    }
  }
  return problems;
}

/**
 * Hindi/Marathi values that are identical to the English value (and non-empty): likely copy-pasted
 * placeholders awaiting native-speaker review. Whole-value matches in `allowlist` are skipped.
 */
export function findUnreviewedStubs(
  catalogue: Catalogue,
  allowlist: ReadonlySet<string> = UNREVIEWED_STUB_ALLOWLIST,
): string[] {
  const flat = flattenAll(catalogue);
  const stubs: string[] = [];
  for (const lang of ["hi", "mr"] as const) {
    for (const [key, value] of Object.entries(flat[lang])) {
      if (value !== "" && value === flat.en[key] && !allowlist.has(value)) stubs.push(`${lang}: ${key}`);
    }
  }
  return stubs;
}

/**
 * English keys whose leaf name is never referenced as `.leaf` or `["leaf"]` / `['leaf']` in any of the
 * given source files. Heuristic (leaf-name based, so it errs toward "used"); intended for platform-local
 * catalogues, not as proof of deadness.
 */
export function findUnusedKeys(catalogue: Catalogue, sourceFiles: string[]): string[] {
  const source = sourceFiles.map((f) => readFileSync(f, "utf8")).join("\n");
  return Object.keys(flatten(catalogue.en))
    .filter((path) => {
      const leaf = path.split(".").pop()!;
      const escaped = leaf.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      const dotted = new RegExp(String.raw`\.${escaped}(?![\w$])`);
      const quoted = new RegExp(String.raw`\[\s*["']${escaped}["']\s*\]`);
      return !dotted.test(source) && !quoted.test(source);
    })
    .sort();
}
