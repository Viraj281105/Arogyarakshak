import localFont from "next/font/local";

// CLS fix (WS4). The three families that set the hero text load their LATIN subset through
// next/font/local, straight from the woff2 files already installed by @fontsource-variable
// (no network at build or run time). next/font preloads them and generates a metric-matched
// local fallback face (size-adjust / ascent / descent overrides via adjustFontFallback), so the
// swap from fallback to web font no longer reflows the hero. The resulting families sit first in
// the token font stacks (packages/design-tokens/tokens.json) through var(--font-face-*); the
// @fontsource-variable imports in globals.css still serve the other subsets (latin-ext carries
// the ₹ sign) and the Devanagari fallbacks after them are unchanged.
//
// Paths are relative to this file; the Docker build context is apps/web, which installs them.
// The unicode-range is Fontsource's latin range, copied verbatim. next/font requires every option
// to be a written literal, so it is repeated in each call (tests/fonts.test.ts keeps them equal).

const arogyaFraunces = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/fraunces/files/fraunces-latin-opsz-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-display",
  display: "swap",
  preload: true,
  adjustFontFallback: "Times New Roman",
  declarations: [{ prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" }],
});

const arogyaJakarta = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/plus-jakarta-sans/files/plus-jakarta-sans-latin-wght-normal.woff2", weight: "200 800", style: "normal" }],
  variable: "--font-face-headline",
  display: "swap",
  preload: true,
  adjustFontFallback: "Arial",
  declarations: [{ prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" }],
});

const arogyaInter = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-sans",
  display: "swap",
  preload: true,
  adjustFontFallback: "Arial",
  declarations: [{ prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" }],
});

/** Class names that define --font-face-display/-headline/-sans; applied on <html>. */
export const fontVariables = `${arogyaFraunces.variable} ${arogyaJakarta.variable} ${arogyaInter.variable}`;
