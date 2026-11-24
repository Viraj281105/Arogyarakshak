# ArogyaRakshak — Complete Animation Inventory

**Technology Constraint:** Pure CSS (`motion.css`) + `motion` (`14.14.0`, confined to `apps/web/app/motion/**`) + Native `ViewTransition` API. Zero GSAP/Lottie/Rive bloat.

---

## 1. Scientific Background Animations (9 Animations)

| ID | Name | Surface | Tech | Duration / Easing | Trigger | Reduced-Motion Fallback |
|---|---|---|---|---|---|---|
| `MOT-BG-01` | **Molecular Network Drift** | Landing Hero, `/login` left panel | CSS `@keyframes` on SVG `<g>` | `12s` infinite alternate / `--ease-organic` | Viewport visible | Static composed lattice |
| `MOT-BG-02` | **Floating Micro-Particles** | Landing Hero ambient layer (`<= 12` dots) | CSS `translateY` + `opacity` | `9s–14s` staggered / `--ease-organic` | Viewport visible | Hidden or static at `0.3` opacity |
| `MOT-BG-03` | **Scientific Grid Pulse** | Evidence Explorer canvas | CSS radial opacity mask | `8s` subtle / `ease-in-out` | Mount (paused offscreen) | Static 1px Warm Ivory grid |
| `MOT-BG-04` | **Botanical Leaf Sway** | `/about`, `/platform` dividers | CSS `rotate(-1.5deg → 1.5deg)` | `10s` infinite / `--ease-organic` | Viewport visible | Static `0deg` |
| `MOT-BG-05` | **Medical ECG Waveform** | BillNyay / Clinical Review header | SVG `stroke-dashoffset` | `1.4s` once / `--ease-emphasized` | On mount / section enter | Full static waveform |
| `MOT-BG-06` | **DNA Helix Drift** | `/platform/kadi`, `/evidence-methodology` | CSS `translateY` loop | `14s` linear | Viewport visible | Static helix |
| `MOT-BG-07` | **Cellular Breathing** | SchemeSetu & `/about` wash | CSS `scale(1 → 1.035)` | `7s` alternate / `--ease-organic` | Viewport visible | Static `scale(1)` |
| `MOT-BG-08` | **Connected Node Signal** | Landing Workflow & Kadi diagram | SVG `stroke-dashoffset` pulse | `2.4s` loop / `linear` | Active section | Static dashed connector |
| `MOT-BG-09` | **Document Intelligence Grid** | Kadi Dropzone backdrop | CSS opacity shift | `4s` subtle / `ease-in-out` | Drag-over or processing | Static border highlight |

---

## 2. Brand Animations (6 Animations)

| ID | Name | Surface | Tech | Duration / Easing | Trigger | Reduced-Motion Fallback |
|---|---|---|---|---|---|---|
| `MOT-BR-01` | **Logo Path Drawing** | Landing Hero initial load | SVG `stroke-dashoffset` (`pathLength=100`) | `680ms` total / `--ease-emphasized` | First paint (once) | Instant complete emblem |
| `MOT-BR-02` | **Shield Reveal** | Auth split panel, Splash | `motion` (`opacity` + `scale 0.96→1`) | `360ms` / `--ease-emphasized` | Mount | Instant visible |
| `MOT-BR-03` | **Medical Cross Reveal** | Coupled to `MOT-BR-01` | SVG `stroke-dashoffset` | `260ms` (delay `420ms`) | After shield draw | Instant visible |
| `MOT-BR-04` | **Wordmark Appearance** | Coupled to `MOT-BR-01` | CSS `opacity` + `translateX(-6px→0)` | `280ms` (delay `500ms`) | After cross | Instant visible |
| `MOT-BR-05` | **Branded Shield Loader** | Async route/case hydration | CSS SVG opacity cycle on leaf veins | `1.8s` infinite / `ease-in-out` | `loading === true` | Static shield + `"Loading..."` |
| `MOT-BR-06` | **Page View Transition** | Route navigation (`TransitionLink`) | `document.startViewTransition` | `220ms` / `--ease-standard` | Internal link click | Instant navigation |

---

## 3. Interface Micro-Animations (10 Animations)

| ID | Name | Component | Tech | Duration / Easing | Trigger | Reduced-Motion Fallback |
|---|---|---|---|---|---|---|
| `MOT-UI-01` | **Header Elevation & Auto-Hide** | `SiteHeader.tsx` | CSS `transform` + `box-shadow` via DOM `data-*` | `200ms` / `--ease-standard` | Scroll threshold | Instant state swap |
| `MOT-UI-02` | **Button Tactile Press** | `.btn-*` | CSS `transform: scale(0.985)` + bg | `100ms` / `--ease-standard` | `:active` / `:hover` | Colour change only |
| `MOT-UI-03` | **Interactive Card Lift** | Clickable module/case cards | CSS `translateY(-2px)` + `--shadow-md` | `200ms` / `--ease-standard` | `:hover` / `:focus-visible` | Border highlight only |
| `MOT-UI-04` | **Modal & Drawer Entrance** | `ui/Overlays.tsx` (`<dialog>`) | CSS `@starting-style` / `motion` | `240ms` / `--ease-emphasized` | `showModal()` | Instant open |
| `MOT-UI-05` | **Tab Active Indicator** | `ui/Disclosure.tsx`, Case Nav | `motion` `layoutId` or CSS transition | `200ms` / `--ease-standard` | Tab select | Instant active border |
| `MOT-UI-06` | **Progress Bar & Ring Fill** | DaaviSetu Ring, SLA Timeline | SVG `stroke-dashoffset` / CSS `scaleX` | `420ms` / `--ease-emphasized` | Data load/update | Instant final fill |
| `MOT-UI-07` | **Reference Stat Settle** | Public `ReferenceCoverage` only | `CountUp.tsx` (SSR renders final value) | `600ms` / `--ease-emphasized` | Viewport enter | Static final number (clinical findings NEVER animate from 0) |
| `MOT-UI-08` | **Chart Series Entrance** | `ui/Charts.tsx` | CSS `scaleY` / `scaleX` (`transform-origin`) | `380ms` (`40ms` stagger) | Mount / data change | Instant final bars |
| `MOT-UI-09` | **Form Validation Feedback** | Auth & Module Forms | CSS `opacity` + `translateY(-4px→0)` | `180ms` / `--ease-standard` | Field error state | Instant inline error |
| `MOT-UI-10` | **Warm Ivory Skeleton Shimmer** | `ui/States.tsx` (`LoadingState`) | CSS `background-position` | `1.6s` infinite / `linear` | Loading state | Static `#EDEAE0` block |

---

## 4. Functional Workflow Animations (8 Animations — SSE & API Driven)

| ID | Stage | Surface | Tech | Duration / Easing | Real Backend Trigger | Reduced-Motion Fallback |
|---|---|---|---|---|---|---|
| `MOT-WF-01` | **Document Upload Drop** | `DocumentUploader.tsx` | CSS scale + border shift | `180ms` / `--ease-standard` | `dragover` / file drop | Border colour change |
| `MOT-WF-02` | **OCR Scan Beam** | `AgentStreamVisualizer.tsx` / Kadi | CSS `translateY` sweep | `1.8s` loop / `ease-in-out` | SSE `stage: ocr` | Static `"Scanning document..."` badge |
| `MOT-WF-03` | **Text Extraction Stream** | Kadi Pipeline Panel | CSS staggered line highlight | `240ms` stagger | SSE `stage: extraction` | Instant text block |
| `MOT-WF-04` | **Entity Recognition Chips** | Kadi & Case Overview | `motion` staggered chip entrance | `200ms` (`40ms` stagger) | SSE `stage: resolution` | Instant chip list |
| `MOT-WF-05` | **Validation & Trust Gate** | DawaCheck / BillNyay | CSS badge pop (`scale 0.94→1`) | `220ms` / `--ease-emphasized` | `decide_medicine_trust` / audit response | Instant status badge |
| `MOT-WF-06` | **Evidence Graph Edge Draw** | `EvidenceGraph.tsx` | SVG `stroke-dashoffset` | `360ms` / `--ease-emphasized` | Graph load / node click | Instant edges + highlight |
| `MOT-WF-07` | **Human Review Seal** | `/review` & Reports Centre | SVG ring draw (`#8066A5`) | `450ms` / `--ease-emphasized` | `POST /finalize` or HMAC verify 200 | Static seal icon |
| `MOT-WF-08` | **Final Analysis Reveal** | Module Results Panels | CSS `Reveal` (`opacity` + `6px` lift) | `280ms` / `--ease-standard` | API 200 results ready | Instant results render |
