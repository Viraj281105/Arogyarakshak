// ArogyaRakshak emblem geometry: the single source for every logo variant, the React components
// and the static files in public/ (scripts/brand-assets.ts writes those). Pure data, no JSX.
//
// Concept (docs/transformation/LOGO_SPECIFICATION.md, refined): a protective shield (Rakshak); two
// leaves rising from its base (Arogya, botanical geometry) that cradle a human figure (the patient at
// the centre); a medical cross on the figure's chest. At 32 px and below the figure is dropped and the
// cross is enlarged, so nothing turns to mush at favicon size.
//
// Master grid: viewBox 0 0 64 64, ~4 px optical padding. Every stroke path that animates carries
// pathLength="100" (set by the components) so the draw animation is deterministic.

export const BRAND_COLORS = {
  deepForest: "#142F2B",
  secondaryForest: "#244C42",
  mutedSage: "#91B49C",
  paleSage: "#D5E7D9",
  warmIvory: "#F4F1E8",
  white: "#FFFFFF",
  ink: "#1D2925",
} as const;

/** Shield contour with gently chamfered shoulders. */
export const SHIELD =
  "M32 4.5 C38.6 7.6 45.4 9.6 52.5 10.6 C53.2 11.2 53.5 12 53.5 12.9 V29.5 C53.5 43.6 44.6 53.6 32 59.5 C19.4 53.6 10.5 43.6 10.5 29.5 V12.9 C10.5 12 10.8 11.2 11.5 10.6 C18.6 9.6 25.4 7.6 32 4.5 Z";

/** Inner hairline that echoes the contour (primary emblem only, >= 48 px). */
export const SHIELD_INNER =
  "M32 8.6 C37.9 11.2 43.9 13 50 14 V29.5 C50 41.4 42.8 50 32 55.5 C21.2 50 14 41.4 14 29.5 V14 C20.1 13 26.1 11.2 32 8.6 Z";

/** Leaves rising from the base and opening outward (filled). */
export const LEAF_LEFT = "M32 52.4 C21.6 50.6 14 42.4 13.2 27.6 C22.8 29.6 29.4 38 32 52.4 Z";
export const LEAF_RIGHT = "M32 52.4 C42.4 50.6 50 42.4 50.8 27.6 C41.2 29.6 34.6 38 32 52.4 Z";

/** Leaf midribs (venation), drawn in the shield colour over the leaves. */
export const VEIN_LEFT = "M31.2 50.2 C25.2 46 19.6 39.4 15.6 30.6";
export const VEIN_RIGHT = "M32.8 50.2 C38.8 46 44.4 39.4 48.4 30.6";

/** The figure: head and a broad head-and-shoulders bust (a narrow arch read as a gravestone). */
export const HEAD = { cx: 32, cy: 19.2, r: 4.7 } as const;
export const TORSO =
  "M22.2 40 C22.2 32.4 26.6 27.8 32 27.8 C37.4 27.8 41.8 32.4 41.8 40 C41.8 40.9 41.1 41.6 40.2 41.6 H23.8 C22.9 41.6 22.2 40.9 22.2 40 Z";

/** Medical cross on the figure's chest (stroked, round caps). */
export const CROSS_V = "M32 31.6 V38.4";
export const CROSS_H = "M28.6 35 H35.4";

/** Compact symbol (viewBox 0 0 32 32): shield, two leaves, bold cross. No figure. */
export const COMPACT = {
  shield:
    "M16 2 C19.4 3.6 22.8 4.6 26.4 5.1 C26.8 5.4 27 5.8 27 6.3 V14.6 C27 21.7 22.5 26.8 16 30 C9.5 26.8 5 21.7 5 14.6 V6.3 C5 5.8 5.2 5.4 5.6 5.1 C9.2 4.6 12.6 3.6 16 2 Z",
  leafLeft: "M16 26 C11.2 24.6 8 20.6 7.8 14.8 C12.2 15.6 15 19.2 16 26 Z",
  leafRight: "M16 26 C20.8 24.6 24 20.6 24.2 14.8 C19.8 15.6 17 19.2 16 26 Z",
  crossV: "M16 7.6 V17.6",
  crossH: "M11 12.6 H21",
} as const;

export type EmblemTone = "light" | "dark" | "mono-dark" | "mono-light";

/** Paint for each tone. "light" = on ivory/white; "dark" = on Deep Forest panels or dark mode. */
export function emblemPaint(tone: EmblemTone) {
  const c = BRAND_COLORS;
  switch (tone) {
    case "dark":
      return { shield: c.secondaryForest, shieldStroke: c.mutedSage, inner: c.mutedSage, leaf: c.mutedSage, vein: c.secondaryForest, figure: c.warmIvory, cross: c.secondaryForest };
    case "mono-dark":
      return { shield: c.ink, shieldStroke: c.ink, inner: c.white, leaf: c.white, vein: c.ink, figure: c.white, cross: c.ink };
    case "mono-light":
      return { shield: "none", shieldStroke: c.warmIvory, inner: c.warmIvory, leaf: c.warmIvory, vein: "none", figure: c.warmIvory, cross: c.deepForest };
    case "light":
    default:
      return { shield: c.deepForest, shieldStroke: c.deepForest, inner: c.mutedSage, leaf: c.mutedSage, vein: c.deepForest, figure: c.warmIvory, cross: c.deepForest };
  }
}

/** Static SVG markup of the primary emblem (used by the asset script; the React component mirrors it). */
export function emblemSvg(tone: EmblemTone = "light", { title = "ArogyaRakshak", inner = true } = {}): string {
  const p = emblemPaint(tone);
  const mono = tone === "mono-light";
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="${title}">`,
    `<title>${title}</title>`,
    `<path d="${SHIELD}" fill="${p.shield}" stroke="${p.shieldStroke}" stroke-width="${mono ? 2.5 : 1.5}" stroke-linejoin="round"/>`,
    inner && !mono ? `<path d="${SHIELD_INNER}" fill="none" stroke="${p.inner}" stroke-width="0.8" stroke-opacity="0.35"/>` : "",
    `<path d="${LEAF_LEFT}" fill="${p.leaf}"/>`,
    `<path d="${LEAF_RIGHT}" fill="${p.leaf}"/>`,
    p.vein !== "none" ? `<path d="${VEIN_LEFT} ${VEIN_RIGHT}" fill="none" stroke="${p.vein}" stroke-width="0.9" stroke-linecap="round" stroke-opacity="0.55"/>` : "",
    `<circle cx="${HEAD.cx}" cy="${HEAD.cy}" r="${HEAD.r}" fill="${p.figure}"/>`,
    `<path d="${TORSO}" fill="${p.figure}" stroke="${mono ? "none" : p.shield}" stroke-width="1.4" paint-order="stroke"/>`,
    `<path d="${CROSS_V} ${CROSS_H}" fill="none" stroke="${mono ? BRAND_COLORS.deepForest : p.cross}" stroke-width="2" stroke-linecap="round"/>`,
    `</svg>`,
  ].join("");
}

/** Static SVG markup of the compact symbol (32 px grid). */
export function compactSvg(tone: EmblemTone = "light", title = "ArogyaRakshak"): string {
  const p = emblemPaint(tone);
  const mono = tone === "mono-light";
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" role="img" aria-label="${title}">`,
    `<title>${title}</title>`,
    `<path d="${COMPACT.shield}" fill="${p.shield}" stroke="${p.shieldStroke}" stroke-width="${mono ? 2 : 1}" stroke-linejoin="round"/>`,
    `<path d="${COMPACT.leafLeft}" fill="${p.leaf}"/>`,
    `<path d="${COMPACT.leafRight}" fill="${p.leaf}"/>`,
    `<path d="${COMPACT.crossV} ${COMPACT.crossH}" fill="none" stroke="${p.figure}" stroke-width="3" stroke-linecap="round"/>`,
    `</svg>`,
  ].join("");
}
