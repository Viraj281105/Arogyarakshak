// WCAG 2.x contrast for the design tokens (Wave 3, M2). Pure functions plus the list of
// foreground/background pairs the UI actually draws, checked in both themes by
// tests/contrast.test.mjs. Add a pair here whenever a component draws a new token on another.

/** Relative luminance of an opaque #RRGGBB colour (WCAG 2.x definition). */
export function luminance(hex) {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) throw new Error(`contrast needs an opaque #RRGGBB colour, got ${hex}`);
  const [r, g, b] = [0, 2, 4].map((i) => {
    const c = parseInt(m[1].slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Contrast ratio between two opaque colours, 1 to 21. */
export function contrastRatio(a, b) {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

/** Resolved colour map for a theme. Light = dark values overridden by light (as in tokens.css). */
export function themeColors(tokens, theme) {
  return theme === "dark" ? { ...tokens.color.dark } : { ...tokens.color.dark, ...tokens.color.light };
}

export const AA_TEXT = 4.5; // WCAG 1.4.3, normal-size text
export const AA_NON_TEXT = 3; // WCAG 1.4.11, UI parts and graphical objects

/** The eight evidence states (EvidenceBadge). Order is the display order in docs and the demo. */
export const EVIDENCE_STATES = [
  "verified",
  "provisional",
  "unevaluated",
  "insufficient-evidence",
  "ai-generated",
  "rule-engine",
  "user-provided",
  "external",
];

const PAGE_BACKGROUNDS = ["bg-base", "bg-surface", "bg-surface-elevated", "bg-surface-secondary", "bg-input"];
const TEXT_ON_PAGE = [
  "text-primary",
  "text-secondary",
  "text-muted",
  "text-link",
  "brand-emerald",
  "accent-gold",
  "status-warning",
  "status-danger",
  "status-success",
  "status-info",
  "status-insufficient",
];
const CHART_MARKS = [
  "chart-within",
  "chart-over",
  "chart-bundled",
  "chart-unmatched",
  "chart-series-1",
  "chart-series-2",
  "chart-series-3",
  "chart-series-4",
  "chart-series-5",
  "chart-series-6",
];

/**
 * Every pair the UI draws, as { fg, bg, min, why }. Themes share the list; values differ.
 * `brand-forest` is a light-theme text colour and, in both themes, the fill of the legacy
 * primary tab/button with white text. `paper-*` tokens are drawn on `surface-paper`.
 */
export function contrastPairs() {
  const pairs = [];
  for (const fg of TEXT_ON_PAGE) {
    for (const bg of PAGE_BACKGROUNDS) pairs.push({ fg, bg, min: AA_TEXT, why: "text" });
  }
  for (const s of EVIDENCE_STATES) {
    pairs.push({ fg: `evidence-${s}-fg`, bg: `evidence-${s}-bg`, min: AA_TEXT, why: "evidence badge label" });
    for (const bg of ["bg-surface", "bg-base"]) {
      pairs.push({ fg: `evidence-${s}-fg`, bg, min: AA_TEXT, why: "evidence label outside a badge" });
    }
  }
  pairs.push({ fg: "text-on-action", bg: "action-primary", min: AA_TEXT, why: "primary button label" });
  pairs.push({ fg: "text-on-action", bg: "action-primary-hover", min: AA_TEXT, why: "primary button label (hover)" });
  pairs.push({ fg: "#FFFFFF", bg: "brand-forest", min: AA_TEXT, why: "legacy filled tab / button label" });
  for (const bg of ["bg-base", "bg-surface"]) {
    pairs.push({ fg: "action-primary", bg, min: AA_NON_TEXT, why: "primary button against the page" });
    pairs.push({ fg: "border-focus", bg, min: AA_NON_TEXT, why: "focus ring" });
  }
  for (const fg of CHART_MARKS) {
    for (const bg of ["bg-surface", "bg-base"]) pairs.push({ fg, bg, min: AA_NON_TEXT, why: "chart mark" });
  }
  for (const fg of ["surface-paper-ink", "paper-muted", "paper-within", "paper-over", "paper-bundled"]) {
    pairs.push({ fg, bg: "surface-paper", min: AA_TEXT, why: "text on the paper (document) surface" });
  }
  return pairs;
}

/** Evaluate every pair in one theme. A pair side starting with "#" is a literal colour. */
export function checkContrast(tokens, theme, pairs = contrastPairs()) {
  const colors = themeColors(tokens, theme);
  const value = (name) => (name.startsWith("#") ? name : colors[name]);
  return pairs.map((p) => {
    const fg = value(p.fg);
    const bg = value(p.bg);
    if (fg === undefined || bg === undefined) {
      return { ...p, theme, ratio: 0, ok: false, error: `missing token ${fg === undefined ? p.fg : p.bg}` };
    }
    const ratio = contrastRatio(fg, bg);
    return { ...p, theme, fgValue: fg, bgValue: bg, ratio, ok: ratio >= p.min };
  });
}
