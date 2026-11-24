// Writes every static brand file from app/components/brand/geometry.ts:
//   public/brand/*.svg   emblem (light, dark, mono-dark, mono-light), compact, wordmarks
//   public/icons/*.svg   favicon, app icon, maskable icon
//   public/icons/*.png   192, 512, maskable 512, apple-touch-icon 180, favicon 32 (rendered with sharp)
// Run from apps/web:  npx tsx scripts/brand-assets.ts
// sharp is not a declared dependency: it is the image library Next.js already installs. The PNGs are
// committed, so this script only runs when the emblem changes. tests/brand.test.ts checks the files.
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { BRAND_COLORS as C, COMPACT, compactSvg, emblemSvg } from "../app/components/brand/geometry";

const web = join(__dirname, "..");
const brandDir = join(web, "public", "brand");
const iconDir = join(web, "public", "icons");
mkdirSync(brandDir, { recursive: true });
mkdirSync(iconDir, { recursive: true });

const inner = (svg: string) => svg.replace(/^<svg[^>]*>/, "").replace(/<title>[^<]*<\/title>/, "").replace(/<\/svg>$/, "");

function wordmark(tone: "light" | "dark"): string {
  const ink = tone === "light" ? C.deepForest : C.warmIvory;
  const sub = tone === "light" ? "#56675E" : C.mutedSage;
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 248 56" role="img" aria-label="ArogyaRakshak">`,
    `<title>ArogyaRakshak</title>`,
    `<g transform="translate(0 0) scale(0.875)">${inner(emblemSvg(tone === "light" ? "light" : "dark", { inner: false }))}</g>`,
    `<text x="64" y="30" font-family="Manrope, 'Manrope Variable', Inter, 'Segoe UI', Arial, sans-serif" font-size="22" font-weight="700" letter-spacing="-0.44" fill="${ink}">Arogya<tspan font-weight="600">Rakshak</tspan></text>`,
    `<text x="64.5" y="47" font-family="'Noto Sans Devanagari', 'Nirmala UI', Mangal, sans-serif" font-size="12" fill="${sub}">आरोग्यरक्षक</text>`,
    `</svg>`,
  ].join("");
}

/** App icon: full-bleed forest square; emblem in ivory/sage centred inside the 80% maskable safe zone. */
function appIcon({ maskable }: { maskable: boolean }): string {
  const scale = maskable ? 4.6 : 6.4; // 64 * 4.6 = 294 (inside the 410 px safe circle); 64 * 6.4 = 410
  const offset = (512 - 64 * scale) / 2;
  const bg = maskable
    ? `<rect width="512" height="512" fill="${C.deepForest}"/>`
    : `<rect width="512" height="512" rx="116" fill="${C.deepForest}"/>`;
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">`,
    bg,
    `<g transform="translate(${offset} ${offset}) scale(${scale})">${inner(emblemSvg("dark", { inner: true }))}</g>`,
    `</svg>`,
  ].join("");
}

/** Favicon: compact geometry on a rounded forest tile so it reads on light and dark browser chrome. */
function favicon(): string {
  return [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">`,
    `<rect width="32" height="32" rx="7" fill="${C.deepForest}"/>`,
    `<g transform="translate(2.2 2.2) scale(0.8625)">`,
    `<path d="${COMPACT.shield}" fill="${C.secondaryForest}" stroke="${C.mutedSage}" stroke-width="1.4" stroke-linejoin="round"/>`,
    `<path d="${COMPACT.leafLeft}" fill="${C.mutedSage}"/><path d="${COMPACT.leafRight}" fill="${C.mutedSage}"/>`,
    `<path d="${COMPACT.crossV} ${COMPACT.crossH}" fill="none" stroke="${C.warmIvory}" stroke-width="3.2" stroke-linecap="round"/>`,
    `</g></svg>`,
  ].join("");
}

const files: Record<string, string> = {
  [join(brandDir, "ar-emblem-primary.svg")]: emblemSvg("light"),
  [join(brandDir, "ar-emblem-dark.svg")]: emblemSvg("dark"),
  [join(brandDir, "ar-emblem-mono-dark.svg")]: emblemSvg("mono-dark"),
  [join(brandDir, "ar-emblem-mono-light.svg")]: emblemSvg("mono-light"),
  [join(brandDir, "ar-emblem-compact.svg")]: compactSvg("light"),
  [join(brandDir, "ar-emblem-compact-dark.svg")]: compactSvg("dark"),
  [join(brandDir, "ar-wordmark-horizontal.svg")]: wordmark("light"),
  [join(brandDir, "ar-wordmark-horizontal-dark.svg")]: wordmark("dark"),
  [join(iconDir, "favicon.svg")]: favicon(),
  [join(iconDir, "icon.svg")]: appIcon({ maskable: false }),
  [join(iconDir, "icon-maskable.svg")]: appIcon({ maskable: true }),
};
for (const [path, svg] of Object.entries(files)) writeFileSync(path, svg + "\n", "utf8");

async function pngs() {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const sharp = require("sharp") as typeof import("sharp").default;
  const render = (svg: string, size: number, out: string) =>
    sharp(Buffer.from(svg), { density: 384 }).resize(size, size).png({ compressionLevel: 9 }).toFile(join(iconDir, out));
  await Promise.all([
    render(appIcon({ maskable: false }), 192, "icon-192.png"),
    render(appIcon({ maskable: false }), 512, "icon-512.png"),
    render(appIcon({ maskable: true }), 512, "icon-maskable-512.png"),
    render(appIcon({ maskable: true }), 180, "apple-touch-icon.png"),
    render(favicon(), 32, "favicon-32.png"),
  ]);
}

pngs().then(
  () => console.log(`wrote ${Object.keys(files).length} SVG files and 5 PNG icons`),
  (e) => {
    console.error(e);
    process.exit(1);
  },
);
