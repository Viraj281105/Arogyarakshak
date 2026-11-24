# ArogyaRakshak — Custom Logo & Emblem Specification

**Concept:** *The Botanical-Medical Protective Shield* — an original geometric emblem uniting three ideas in a single balanced form:
1. **Protective Shield (`Rakshak`):** Architectural outer shield perimeter with subtly chamfered shoulders representing patient financial and legal protection.
2. **Botanical Leaf Geometry (`Arogya`):** Bilateral inner leaf venation curves springing from the base apex, symbolizing organic healing, Indian heritage, and vitality.
3. **Medical Cross & Human Center:** A precision negative-space cross and central focal node at the heart of the shield, representing evidence-verified care and the human patient at the center.

*Never use generic stock red crosses, caduceus clip-art, or stethoscope silhouettes.*

---

## 1. Logo Variant Suite

| Variant | File Name | ViewBox | Min Render Size | Primary Use |
|---|---|---|---|---|
| **Primary Emblem** | `ar-emblem-primary.svg` | `0 0 64 64` | `32×32 px` | Hero anchor, auth split panel, PDF masthead, app splash |
| **Horizontal Wordmark** | `ar-wordmark-horizontal.svg` | `0 0 240 48` | `140×28 px` | Global desktop header, footer, official documents |
| **Compact Symbol** | `ar-emblem-compact.svg` | `0 0 32 32` | `20×20 px` | Mobile header, collapsed sidebar, compact badges |
| **Monochrome (Dark Ink)** | `ar-emblem-mono-dark.svg` | `0 0 64 64` | `24×24 px` | Printable black-and-white appeal PDFs, Annexure-B forms |
| **Monochrome (Light Ink)** | `ar-emblem-mono-light.svg` | `0 0 64 64` | `24×24 px` | Deep Forest `#142F2B` panels, optional dark mode header |
| **Favicon** | `favicon.svg` + `favicon.ico` | `0 0 32 32` | `16×16 px` | Browser tab icon (simplified 3-path geometry for crisp 16px legibility) |
| **App Icon (Standard & Maskable)** | `public/icons/icon.svg`, `icon-maskable.svg`, `icon-192.png`, `icon-512.png`, `apple-touch-icon.png` | `0 0 512 512` | `48×48 px` | Web manifest, iOS/Android home screen, Expo mobile app icon |
| **Animated SVG Logo** | `ArogyaLogoAnimated.tsx` | `0 0 64 64` | `48×48 px` | Hero reveal, initial auth transitions, branded loading state |

---

## 2. Geometry, Stroke & Path Organisation

### Canonical Construction Grid
- **Master ViewBox:** `0 0 64 64` (8×8 construction grid, safe optical padding `4px` on all sides).
- **Stroke Conventions:**
  - Outer shield contour: `stroke-width: 2.5`, `stroke-linecap: round`, `stroke-linejoin: round`.
  - Inner botanical venation & medical cross accents: `stroke-width: 1.75`, `stroke-linecap: round`.
  - Compact `32×32` & Favicon: outer stroke `2.75`, simplified inner cross + dual leaf arcs (removes fine secondary veins so nothing muddies at 16px).
- **Colour Assignments:**
  - **Light Surface (Default):** Shield fill `#142F2B` (or outline `#142F2B` with `#D5E7D9` subtle inner tint), botanical arcs `#91B49C`, central cross `#F4F1E8`.
  - **Dark Forest Surface (e.g., `/login` left panel):** Shield outline `#D5E7D9`, botanical arcs `#91B49C`, central cross `#FFFFFF`.

### Canonical SVG Path Structure (Animation-Ready)
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" fill="none" role="img" aria-label="ArogyaRakshak">
  <g id="ar-shield-outer">
    <!-- Single closed path with pathLength="100" for deterministic stroke-dashoffset drawing -->
    <path id="shield-contour" pathLength="100"
      d="M32 5 L53 13.5 V30.5 C53 44.5 43.8 54.4 32 59 C20.2 54.4 11 44.5 11 30.5 V13.5 L32 5 Z"
      fill="#142F2B" stroke="#142F2B" stroke-width="2" stroke-linejoin="round" />
  </g>
  <g id="ar-botanical-veins">
    <!-- Bilateral symmetric botanical leaf arcs -->
    <path id="leaf-left" pathLength="100"
      d="M32 50 C23 44 18.5 36.5 18.5 27 C23.5 28.5 28 32.5 32 38"
      stroke="#91B49C" stroke-width="2" stroke-linecap="round" />
    <path id="leaf-right" pathLength="100"
      d="M32 50 C41 44 45.5 36.5 45.5 27 C40.5 28.5 36 32.5 32 38"
      stroke="#91B49C" stroke-width="2" stroke-linecap="round" />
  </g>
  <g id="ar-medical-cross">
    <!-- Precision geometric medical cross with human focal core -->
    <path id="cross-vertical" pathLength="100" d="M32 16 V34" stroke="#F4F1E8" stroke-width="3.2" stroke-linecap="round" />
    <path id="cross-horizontal" pathLength="100" d="M23 25 H41" stroke="#F4F1E8" stroke-width="3.2" stroke-linecap="round" />
    <circle id="human-core" cx="32" cy="25" r="2.2" fill="#D5E7D9" />
  </g>
</svg>
```

---

## 3. Clear Space, Wordmark Lockup & Misuse Rules

- **Wordmark Typography:** `ArogyaRakshak` set in **Manrope Bold (`700`)**, tracking `-0.02em`, `#142F2B` (light) / `#F4F1E8` (dark), with `Arogya` at `700` and `Rakshak` at `600` (subtle contrast) or uniform `700`. Optional secondary lockup places `आरोग्यरक्षक` below in `11px` Inter/Devanagari `#64766C`.
- **Minimum Clear Space:** Equal to `0.5 ×` emblem height on all four sides.
- **Responsive Behaviour:**
  - `>= 640px`: Horizontal emblem + `ArogyaRakshak` wordmark.
  - `< 640px` (compact mobile workspace bar): Emblem + concise wordmark or `32×32` compact symbol when paired with a page title.
- **Loading Animation Spec:** Uses `#shield-contour` steady outline with a gentle `1.8s` breathing opacity/stroke sweep along `#leaf-left`, `#leaf-right`, and `#cross-*`. Under `prefers-reduced-motion: reduce`, renders the static completed emblem with a calm `Loading...` text label.
