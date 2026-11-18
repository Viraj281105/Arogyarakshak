import localFont from "next/font/local";

// CLS fix (WS4). The three families that set the hero text load through next/font/local,
// straight from the woff2 files already installed by @fontsource-variable (no network at build or
// run time). Each family is ONE CSS family with two faces, like Fontsource's own CSS:
//
//   - latin: preloaded; next/font also emits "<family> Fallback", a local Times New Roman / Arial
//     face with size-adjust and ascent/descent overrides, so the fallback-to-web-font swap does
//     not reflow the hero (lhci CLS 0.0964 -> 0).
//   - latin-ext: same family name, loaded only when a glyph needs it (no preload, no fallback).
//
// The latin-ext face matters because the generated "Fallback" face has no unicode-range: if ₹, ā
// or š lived only in a family listed AFTER it, the size-adjusted local fallback would draw them
// (measured in the WS4 review: it did). With latin-ext in the same family, the first family in
// the stack covers them. The families sit first in the token font stacks
// (packages/design-tokens/tokens.json) through var(--font-face-*); the @fontsource-variable
// imports in globals.css remain for the other subsets and JetBrains Mono, and the Devanagari
// fallbacks after them are unchanged.
//
// Paths are relative to this file; the Docker build context is apps/web, which installs them.
// next/font requires every option to be a written literal, so the Fontsource unicode-ranges are
// repeated verbatim in each call (tests/fonts.test.ts keeps them exact). The ext calls declare a
// variable only so their class (and with it their @font-face) is applied on <html>.

const arogyaFraunces = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/fraunces/files/fraunces-latin-opsz-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-display",
  display: "swap",
  preload: true,
  adjustFontFallback: "Times New Roman",
  declarations: [
    { prop: "font-family", value: "arogyaFraunces" },
    { prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" },
  ],
});

const arogyaFrauncesExt = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/fraunces/files/fraunces-latin-ext-opsz-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-display-ext",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "arogyaFraunces" },
    { prop: "unicode-range", value: "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF" },
  ],
});

const arogyaJakarta = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/plus-jakarta-sans/files/plus-jakarta-sans-latin-wght-normal.woff2", weight: "200 800", style: "normal" }],
  variable: "--font-face-headline",
  display: "swap",
  preload: true,
  adjustFontFallback: "Arial",
  declarations: [
    { prop: "font-family", value: "arogyaJakarta" },
    { prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" },
  ],
});

const arogyaJakartaExt = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/plus-jakarta-sans/files/plus-jakarta-sans-latin-ext-wght-normal.woff2", weight: "200 800", style: "normal" }],
  variable: "--font-face-headline-ext",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "arogyaJakarta" },
    { prop: "unicode-range", value: "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF" },
  ],
});

const arogyaInter = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-sans",
  display: "swap",
  preload: true,
  adjustFontFallback: "Arial",
  declarations: [
    { prop: "font-family", value: "arogyaInter" },
    { prop: "unicode-range", value: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD" },
  ],
});

const arogyaInterExt = localFont({
  src: [{ path: "../node_modules/@fontsource-variable/inter/files/inter-latin-ext-wght-normal.woff2", weight: "100 900", style: "normal" }],
  variable: "--font-face-sans-ext",
  display: "swap",
  preload: false,
  adjustFontFallback: false,
  declarations: [
    { prop: "font-family", value: "arogyaInter" },
    { prop: "unicode-range", value: "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF" },
  ],
});

/** Classes that define --font-face-display/-headline/-sans (and apply the ext faces); on <html>. */
export const fontVariables = [
  arogyaFraunces.variable,
  arogyaFrauncesExt.variable,
  arogyaJakarta.variable,
  arogyaJakartaExt.variable,
  arogyaInter.variable,
  arogyaInterExt.variable,
].join(" ");
