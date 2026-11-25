// Every English UI string that needs a Hindi and a Marathi translation (docs/localization.md):
// the first argument of tr(...) and msg(...), <T k="..."/>, and all public-site copy text.
//
//   npx tsx scripts/i18n-keys.ts            # print missing keys as JSON, exit 1 when any
//   npx tsx scripts/i18n-keys.ts --all      # print every key as JSON
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";
import { PUBLIC_EN } from "../app/components/public/copy/en";
import { isIdentifier } from "../app/components/public/publicCopy";
import hi from "../app/i18n/locales/hi";
import mr from "../app/i18n/locales/mr";

const APP = join(__dirname, "..", "app");
const SKIP_DIRS = new Set(["node_modules", "(dev)", "generated", "shared", "locales"]);
const CALLS = new Set(["tr", "msg"]);

export interface CodeKeys {
  keys: Set<string>;
  /** `file:line` of calls whose key is not a literal (the translation must be marked with msg). */
  dynamic: string[];
}

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return SKIP_DIRS.has(entry.name) ? [] : sourceFiles(path);
    return /\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

export function codeKeys(): CodeKeys {
  const keys = new Set<string>();
  const dynamic: string[] = [];
  const literals = (node: ts.Expression): string[] | null => {
    if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return [node.text];
    if (ts.isParenthesizedExpression(node)) return literals(node.expression);
    if (ts.isConditionalExpression(node)) {
      const a = literals(node.whenTrue);
      const b = literals(node.whenFalse);
      return a && b ? [...a, ...b] : null;
    }
    // tr(msg("a")) is collected at the inner call.
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === "msg") return [];
    return null;
  };
  for (const file of sourceFiles(APP)) {
    const source = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true, file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
    (function visit(node: ts.Node) {
      if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && CALLS.has(node.expression.text) && node.arguments.length > 0) {
        const found = literals(node.arguments[0]);
        if (found) found.forEach((k) => k && keys.add(k));
        else if (node.expression.text === "msg") dynamic.push(`${file}:${source.getLineAndCharacterOfPosition(node.getStart()).line + 1}`);
      }
      if (ts.isJsxAttribute(node) && node.name.getText() === "k" && node.parent.parent && (node.parent.parent as ts.JsxSelfClosingElement).tagName?.getText() === "T" && node.initializer) {
        if (ts.isStringLiteral(node.initializer)) keys.add(node.initializer.text);
        else if (ts.isJsxExpression(node.initializer) && node.initializer.expression) literals(node.initializer.expression)?.forEach((k) => keys.add(k));
      }
      ts.forEachChild(node, visit);
    })(source);
  }
  return { keys, dynamic };
}

export function publicKeys(value: unknown = PUBLIC_EN, key = "", out = new Set<string>()): Set<string> {
  if (isIdentifier(key, value)) return out;
  if (typeof value === "string") {
    if (value) out.add(value);
  } else if (Array.isArray(value)) value.forEach((item) => publicKeys(item, key, out));
  else if (value && typeof value === "object") for (const [k, v] of Object.entries(value)) publicKeys(v, k, out);
  return out;
}

export function allKeys(): string[] {
  return [...new Set([...codeKeys().keys, ...publicKeys()])];
}

if (process.argv[1]?.endsWith("i18n-keys.ts")) {
  const keys = allKeys();
  const wanted = process.argv.includes("--all") ? keys : keys.filter((k) => !(k in hi) || !(k in mr));
  console.log(JSON.stringify(wanted, null, 0).replace(/","/g, '",\n"'));
  if (!process.argv.includes("--all") && wanted.length > 0) process.exitCode = 1;
}
