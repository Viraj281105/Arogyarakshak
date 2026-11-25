/**
 * Finds the mobile app's user-facing English: the keys passed to `tr()` / `msg()`, and literals
 * that would reach the screen without passing through them (docs/localization.md).
 */
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import ts from 'typescript';

const ROOT = process.cwd();
// components/ui/tones.ts names colour pairs for the contrast tests; none of it is rendered.
const SKIP_DIRS = ['src/dev', 'src/generated', 'src/shared', 'src/translations', 'src/theme', 'src/api/types', 'src/components/ui/tones.ts'];

/** JSX attributes and object properties whose value is shown or read aloud. */
const TEXT_ATTRS = new Set([
  'title', 'label', 'placeholder', 'accessibilityLabel', 'accessibilityHint', 'actionLabel', 'subtitle',
  'description', 'message', 'heading', 'caption', 'hint', 'body', 'confirmLabel', 'cancelLabel', 'retryLabel',
  'emptyText', 'text', 'detail', 'word', 'badge', 'billed', 'ceiling', 'reason', 'error', 'summary', 'consequence',
]);

/** Shown as written in every language: names, identifiers and units. */
const NOT_TRANSLATED = new Set([
  'ArogyaRakshak', '| आरोग्यरक्षक', 'BYOD', 'BillNyay', 'DaaviSetu', 'BimaNyay', 'SchemeSetu', 'DawaCheck', 'Kadi',
  'CGHS 2024', 'IRDAI 2024', 'PMJAY / MJPJAY', 'EN', 'MJPJAY', 'PM-JAY', 'Rule v', '· Rule v', 'ID', 'OCR',
  // Programmer errors and the development-only gallery menu.
  'useToast must be used inside <ToastProvider>', 'Primitives gallery',
  // HTTP details, not prose.
  'HTTP {…}', 'Bearer {…}', 'Content-Type',
]);

/** Constants whose string values are display text, whatever their keys are called. */
const TEXT_TABLE = /label|word|copy|text|title|message|hint|note|caption/i;

export interface Finding {
  file: string;
  line: number;
  kind: 'text' | 'attribute' | 'expression' | 'property' | 'sentence';
  value: string;
}

export function sourceFiles(dir = join(ROOT, 'src')): string[] {
  const found = readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    const rel = relative(ROOT, path).split(sep).join('/');
    if (SKIP_DIRS.includes(rel)) return [];
    if (statSync(path).isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(name) && !name.endsWith('.d.ts') ? [path] : [];
  });
  return dir === join(ROOT, 'src') ? [...found, join(ROOT, 'App.tsx')] : found;
}

const parse = (file: string) =>
  ts.createSourceFile(file, readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true, file.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);

const calleeName = (node: ts.Node): string => (ts.isCallExpression(node) ? node.expression.getText() : '');
const isMarker = (node: ts.Node) => ['tr', 'msg'].includes(calleeName(node));

/** The text of a literal, with each template substitution shown as {…}. */
function literalText(node: ts.Node): string | null {
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isTemplateExpression(node)) return node.head.text + node.templateSpans.map((s) => `{…}${s.literal.text}`).join('');
  return null;
}

/** Literals that can become the value of an expression (through ?:, ||, &&, ?? and +). */
function valueLiterals(node: ts.Expression): ts.Node[] {
  if (ts.isParenthesizedExpression(node)) return valueLiterals(node.expression);
  if (ts.isConditionalExpression(node)) return [...valueLiterals(node.whenTrue), ...valueLiterals(node.whenFalse)];
  if (ts.isBinaryExpression(node)) {
    const op = node.operatorToken.kind;
    if (op === ts.SyntaxKind.AmpersandAmpersandToken) return valueLiterals(node.right);
    if ([ts.SyntaxKind.BarBarToken, ts.SyntaxKind.QuestionQuestionToken, ts.SyntaxKind.PlusToken].includes(op))
      return [...valueLiterals(node.left), ...valueLiterals(node.right)];
    return [];
  }
  return literalText(node) === null ? [] : [node];
}

const hasWords = (s: string) => /[A-Za-z]{2,}/.test(s.replace(/\{…\}/g, ' '));
/** Reads as an English phrase: a capitalised word followed by another word. */
const isSentence = (s: string) => /(^|[\s“"(])[A-Z][a-z'’]+[,:]? [a-z]/.test(s) || /[a-z]{3,} [a-z]{2,} [a-z]{3,}/.test(s);
/** A value shown on screen: starts like a word, or is several words. */
const looksShown = (s: string) => /^[A-Z][a-z]/.test(s) || /[a-z]{2,} [a-z]{2,}/.test(s);

function ignored(node: ts.Node): boolean {
  for (let n: ts.Node | undefined = node.parent; n; n = n.parent) {
    if (ts.isImportDeclaration(n) || ts.isExportDeclaration(n) || ts.isTypeNode(n)) return true;
    if (isMarker(n)) return true;
    const call = calleeName(n);
    if (/^(console|logger|log)\.|^(require|describe|it)$/.test(call)) return true;
  }
  return false;
}

export function untranslated(): Finding[] {
  const findings = new Map<string, Finding>();
  for (const file of sourceFiles()) {
    const source = parse(file);
    const rel = relative(ROOT, file).split(sep).join('/');
    const add = (node: ts.Node, kind: Finding['kind'], raw: string) => {
      const value = raw.replace(/\s+/g, ' ').trim();
      // A leading [tag] marks a developer log line.
      if (!hasWords(value) || NOT_TRANSLATED.has(value) || value.startsWith('[')) return;
      const start = node.getStart(source);
      const key = `${rel}:${start}`;
      if (!findings.has(key)) findings.set(key, { file: rel, line: source.getLineAndCharacterOfPosition(start).line + 1, kind, value });
    };
    (function visit(node: ts.Node) {
      if (ts.isJsxText(node)) add(node, 'text', node.text);
      if (ts.isJsxAttribute(node) && node.initializer && TEXT_ATTRS.has(node.name.getText(source))) {
        if (ts.isStringLiteral(node.initializer)) add(node.initializer, 'attribute', node.initializer.text);
        else if (ts.isJsxExpression(node.initializer) && node.initializer.expression)
          valueLiterals(node.initializer.expression).forEach((l) => add(l, 'attribute', literalText(l)!));
      }
      if (ts.isJsxExpression(node) && node.expression && (ts.isJsxElement(node.parent) || ts.isJsxFragment(node.parent)))
        valueLiterals(node.expression).forEach((l) => add(l, 'expression', literalText(l)!));
      if (ts.isPropertyAssignment(node) && TEXT_ATTRS.has(node.name.getText(source)))
        valueLiterals(node.initializer).forEach((l) => {
          const text = literalText(l)!;
          // Single lower-case words in these properties are codes ("none", "pack"), not text.
          if (/[A-Z]|\s/.test(text)) add(l, 'property', text);
        });
      if (ts.isVariableDeclaration(node) && node.initializer && ts.isObjectLiteralExpression(node.initializer) && TEXT_TABLE.test(node.name.getText(source)))
        node.initializer.properties.forEach((p) => {
          if (ts.isPropertyAssignment(p))
            valueLiterals(p.initializer).forEach((l) => {
              const shown = literalText(l)!;
              // Identifiers (camelCase, snake_case, kebab-case, token names) are not text.
              if (/[a-z]{2,}/.test(shown) && !/^[a-z]+[A-Z]\w*$|^[\w-]*[_-][\w-]*$/.test(shown)) add(l, 'property', shown);
            });
        });
      // Enum-to-label tables, default values of text props, and messages put into state.
      const shownLiterals: ts.Node[] = [];
      if (ts.isPropertyAssignment(node) && /^[A-Z][A-Z0-9_]+$/.test(node.name.getText(source))) shownLiterals.push(...valueLiterals(node.initializer));
      if ((ts.isBindingElement(node) || ts.isParameter(node)) && node.initializer && TEXT_ATTRS.has(node.name.getText(source)))
        shownLiterals.push(...valueLiterals(node.initializer));
      if (ts.isCallExpression(node) && /^set[A-Z]/.test(node.expression.getText(source)))
        node.arguments.forEach((a) => shownLiterals.push(...valueLiterals(a)));
      shownLiterals.forEach((l) => {
        const shown = literalText(l)!;
        if (looksShown(shown) && !ignored(l)) add(l, 'property', shown);
      });
      if (ts.isTemplateExpression(node) && !ignored(node)) {
        // A short phrase built around values ("Step {…} of {…}") is text too. Paths, ids and
        // style values have no free-standing word.
        const shown = literalText(node)!;
        const parts = [node.head.text, ...node.templateSpans.map((x) => x.literal.text)];
        const phrase = parts.some((x) => /(^|[\s(“])[A-Za-z]{2,}([\s:,.”)]|$)/.test(x) && /\s/.test(x));
        if (phrase && !parts.some((x) => /\/|=|;|<|\{|solid|deg/.test(x))) add(node, 'sentence', shown);
      }
      const text = literalText(node);
      if (text !== null && isSentence(text) && !ignored(node)) add(node, 'sentence', text);
      ts.forEachChild(node, visit);
    })(source);
  }
  return [...findings.values()];
}

/** Every key the code marks for translation. */
export function codeKeys(): { keys: string[]; dynamicMsg: string[] } {
  const keys = new Set<string>();
  const dynamicMsg: string[] = [];
  for (const file of sourceFiles()) {
    const source = parse(file);
    (function visit(node: ts.Node) {
      if (ts.isCallExpression(node) && isMarker(node) && node.arguments.length > 0) {
        const literals = valueLiterals(node.arguments[0]).filter((l) => !ts.isTemplateExpression(l));
        literals.forEach((l) => keys.add(literalText(l)!));
        if (literals.length === 0 && calleeName(node) === 'msg') dynamicMsg.push(`${relative(ROOT, file)}: ${node.getText(source)}`);
      }
      ts.forEachChild(node, visit);
    })(source);
  }
  keys.delete('');
  return { keys: [...keys], dynamicMsg };
}

/** Components that call tr() but never subscribe to the language, so would keep old text. */
export function unsubscribedComponents(): string[] {
  const missing: string[] = [];
  for (const file of sourceFiles().filter((f) => f.endsWith('.tsx'))) {
    const source = parse(file);
    const calls = (node: ts.Node, names: string[]): boolean =>
      (ts.isCallExpression(node) && names.includes(node.expression.getText(source))) ||
      Boolean(ts.forEachChild(node, (child) => calls(child, names) || undefined));
    (function visit(node: ts.Node, insideComponent: boolean) {
      let name = '';
      if (ts.isFunctionDeclaration(node) && node.name) name = node.name.text;
      else if (ts.isVariableDeclaration(node) && node.initializer && (ts.isArrowFunction(node.initializer) || ts.isCallExpression(node.initializer)))
        name = node.name.getText(source);
      const component = !insideComponent && /^[A-Z][a-z]/.test(name);
      if (component && calls(node, ['tr']) && !calls(node, ['useTranslation', 'useLanguage']))
        missing.push(`${relative(ROOT, file).split(sep).join('/')}: ${name}`);
      ts.forEachChild(node, (child) => visit(child, insideComponent || component));
    })(source, false);
  }
  return missing;
}
