/**
 * WCAG 2.x contrast for the mobile palette. Pure (no react-native import), same formula as
 * packages/design-tokens/contrast.mjs. Accepts #RRGGBB and rgba(); a translucent colour must be
 * composited over an opaque one with `over()` before a ratio is taken.
 */

export const AA_TEXT = 4.5; // WCAG 1.4.3, normal-size text
export const AA_NON_TEXT = 3; // WCAG 1.4.11, UI parts and graphical objects

type RGBA = { r: number; g: number; b: number; a: number };

export function parseColor(input: string): RGBA {
  const hex = /^#([0-9a-f]{6})$/i.exec(input.trim());
  if (hex) {
    const h = hex[1];
    return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16), a: 1 };
  }
  const rgba = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i.exec(input.trim());
  if (rgba) {
    return { r: +rgba[1], g: +rgba[2], b: +rgba[3], a: rgba[4] === undefined ? 1 : +rgba[4] };
  }
  throw new Error(`contrast: unsupported colour ${input}`);
}

const toHex = ({ r, g, b }: RGBA) =>
  `#${[r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase()}`;

/** Composite a (possibly translucent) colour over an opaque background; returns #RRGGBB. */
export function over(fg: string, bg: string): string {
  const f = parseColor(fg);
  const b = parseColor(bg);
  if (b.a !== 1) throw new Error(`contrast: background must be opaque, got ${bg}`);
  const mix = (x: number, y: number) => x * f.a + y * (1 - f.a);
  return toHex({ r: mix(f.r, b.r), g: mix(f.g, b.g), b: mix(f.b, b.b), a: 1 });
}

export function luminance(color: string): number {
  const c = parseColor(color);
  if (c.a !== 1) throw new Error(`contrast: composite ${color} with over() first`);
  const [r, g, b] = [c.r, c.g, c.b].map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Contrast ratio between two opaque colours, 1 to 21. */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
