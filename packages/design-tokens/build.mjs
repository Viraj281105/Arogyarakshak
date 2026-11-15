// Design-token generator. Source of truth: packages/design-tokens/tokens.json.
// Usage: node packages/design-tokens/build.mjs [--check]
import { readFileSync, writeFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, "..", "..");
const BANNER = "GENERATED — do not edit; source: packages/design-tokens/tokens.json";

export const defaultPaths = {
  tokensPath: join(here, "tokens.json"),
  cssPath: join(repoRoot, "apps", "web", "app", "generated", "tokens.css"),
  tsPath: join(repoRoot, "apps", "mobile", "src", "generated", "tokens.ts"),
};

const camel = (k) => k.replace(/-([a-z0-9])/g, (_, c) => c.toUpperCase());
const decls = (entries, indent = "  ") =>
  entries.map(([k, v]) => `${indent}--${k}: ${v};`).join("\n");

/** CSS custom properties: `:root` (dark + non-theme vars) and `[data-theme="light"]` overrides. */
export function buildCss(t) {
  const px = (rec, prefix) => Object.entries(rec).map(([k, v]) => [`${prefix}-${k}`, `${v}px`]);
  const motion = [
    ...Object.entries(t.motion.duration).map(([k, v]) => [`motion-duration-${k}`, `${v}ms`]),
    ...Object.entries(t.motion.easing).map(([k, v]) => [`motion-easing-${k}`, v]),
  ];
  const z = Object.entries(t.z).map(([k, v]) => [`z-${k}`, String(v)]);
  const root = [
    ...Object.entries(t.color.dark),
    ...Object.entries(t.font).map(([k, v]) => [`font-${k}`, v]),
    ...px(t.space, "space"),
    ...px(t.radius, "radius"),
    ...motion,
    ...z,
    ...Object.entries(t.webOnly.root),
  ];
  const light = [...Object.entries(t.color.light), ...Object.entries(t.webOnly.light)];
  return `/* ${BANNER} */\n\n:root {\n${decls(root)}\n}\n\n[data-theme="light"] {\n${decls(light)}\n}\n`;
}

const camelObj = (rec) => Object.fromEntries(Object.entries(rec).map(([k, v]) => [camel(k), v]));
/** Serialize to a TS object literal with bare identifier keys (all keys are camelCase identifiers). */
function lit(o, indent = "") {
  const inner = indent + "  ";
  const body = Object.entries(o).map(([k, v]) =>
    typeof v === "object" ? `${inner}${k}: ${lit(v, inner)},` : `${inner}${k}: ${JSON.stringify(v)},`,
  );
  return `{\n${body.join("\n")}\n${indent}}`;
}

/** TypeScript module for the mobile app. Light palette = dark merged with light overrides. */
export function buildTs(t) {
  const dark = camelObj(t.color.dark);
  const light = { ...dark, ...camelObj(t.color.light) };
  const motion = {
    duration: camelObj(t.motion.duration),
    easing: camelObj(t.motion.easing),
  };
  return [
    `// ${BANNER}`,
    ``,
    `export const colors = ${lit({ dark, light })} as const;`,
    ``,
    `export type Palette = { [K in keyof typeof colors.dark]: string };`,
    ``,
    `export const spacing = ${lit(camelObj(t.space))} as const;`,
    ``,
    `export const radii = ${lit(camelObj(t.radius))} as const;`,
    ``,
    `export const motion = ${lit(motion)} as const;`,
    ``,
    `export const zIndex = ${lit(camelObj(t.z))} as const;`,
    ``,
    `export const fonts = ${lit(camelObj(t.font))} as const;`,
    ``,
  ].join("\n");
}

/** Write (or with `check`, verify) both generated outputs. Throws on a stale output. */
export function runBuild({ check = false, ...overrides } = {}) {
  const p = { ...defaultPaths, ...overrides };
  const tokens = JSON.parse(readFileSync(p.tokensPath, "utf8"));
  const outputs = [
    [p.cssPath, buildCss(tokens)],
    [p.tsPath, buildTs(tokens)],
  ];
  const stale = [];
  for (const [path, content] of outputs) {
    if (check) {
      if (!existsSync(path) || readFileSync(path, "utf8") !== content) stale.push(path);
    } else {
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content);
    }
  }
  if (stale.length) {
    throw new Error(
      `design tokens out of date: ${stale.join(", ")} — run \`npm run generate\` and commit the result`,
    );
  }
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  try {
    runBuild({ check: process.argv.includes("--check") });
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
}
