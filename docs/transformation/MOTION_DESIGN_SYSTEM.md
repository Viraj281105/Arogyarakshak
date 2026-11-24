# ArogyaRakshak — Motion Design System Specification

**Philosophy:** *Purposeful, Calm, Scientific Vitality.*  
ArogyaRakshak should feel alive, responsive, and quietly reassuring — never jittery, theatrical, or distracting for a stressed patient at a hospital desk.

---

## 1. Stack-Grounded Motion Architecture

Verified against `apps/web/package.json` and `apps/web/eslint.config.mjs`:
- **Installed & Approved:** `motion` (`14.14.0`, Framer Motion's modern successor), pure CSS `@keyframes` & CSS Scroll-Driven Animations (`animation-timeline: view()`), and native `document.startViewTransition` (`apps/web/app/motion/viewTransition.ts`).
- **Architectural Boundary (Enforced by ESLint):** All `motion` imports MUST remain strictly inside `apps/web/app/motion/**`. Feature components consume thin, budget-safe wrappers (`Reveal`, `MotionPresence`, `PipelineScan`, `GraphFocus`) rather than importing `motion` directly.
- **No Unnecessary Heavy Libraries:** Do **NOT** add GSAP, Lottie (`lottie-web` ~70 KB gzip), or Rive (`@rive-app/canvas` ~120 KB+ WASM) — they would immediately blow past ArogyaRakshak's strict **170 KB gzip** per-route web bundle budget and add zero capability beyond what SVG + CSS + `motion` already deliver cleanly.
- **Mobile (`apps/mobile`):** Stay on React Native's built-in `Animated` API (`src/motion/`), keeping Android export well under the 2.6 MB budget.

---

## 2. Core Timing & Easing Tokens

Aligned with `packages/design-tokens/tokens.json` and extended for scientific & workflow choreography:

| Token | Value | Use Case |
|---|---|---|
| `--motion-instant` | `100ms` | Button active press, checkbox tick, badge hover |
| `--motion-fast` | `160ms` | Tooltips, dropdowns, tab indicator slide, focus ring |
| `--motion-base` | `260ms` | Card hover lift, modal/drawer open, accordion expand, filter updates |
| `--motion-deliberate` | `420ms` | Page view transitions, chart bar/ring entrance, Evidence Explorer node focus |
| `--motion-ceremonial` | `750ms` | Hero logo stroke draw, workflow stage completion chime |
| `--motion-ambient` | `6000ms – 14000ms` | Ultra-slow molecular network drift, cellular breathing (GPU `transform`/`opacity` only) |

**Easing Curves:**
- `--ease-standard`: `cubic-bezier(0.2, 0, 0, 1)` — Default UI transitions (fast out, silky settle).
- `--ease-emphasized`: `cubic-bezier(0.22, 1, 0.36, 1)` — Modal entrances, chart reveals, brand stroke drawing.
- `--ease-exit`: `cubic-bezier(0.4, 0, 1, 1)` — Clean, crisp dismissals.
- `--ease-organic`: `cubic-bezier(0.45, 0.05, 0.55, 0.95)` — Continuous botanical/molecular ambient loops.

---

## 3. Four Motion Families

### Family 1: Scientific & Botanical Backgrounds (Ambient, Non-Distracting)
- **GPU-Only Rule:** Strictly `transform` and `opacity` (zero layout thrash, zero `filter: blur()` animations).
- **Viewport Gating:** Pause ambient animations via `IntersectionObserver` (or CSS `content-visibility`) when off-screen so CPU/battery stays idle.
- **Includes:** Molecular network node breathing, gentle floating particles (`<= 12` micro-nodes), architectural scientific grid shimmer, subtle organic leaf sway, single-pass ECG medical waveform, slow DNA helix drift, cellular ring pulse, connected node edge pulses, document intelligence scan grid.

### Family 2: Brand & Navigation Animations
- **Logo Path Drawing:** `stroke-dashoffset` from `100 → 0` sequentially: Shield contour (`0–380ms`) → Botanical veins (`240–540ms`) → Medical cross (`420–680ms`) → Wordmark fade-slide (`520–750ms`). Runs **once** on first hero load only.
- **Branded Loading State (`ArogyaLoader`):** Calm 1.8s cyclical botanical vein illumination inside the static shield.
- **Page Transitions:** Native `document.startViewTransition` cross-fade (`220ms`) with graceful instant fallback on unsupported browsers.

### Family 3: Interface Micro-Interactions
- **Buttons:** `scale(0.985)` on `:active` (`100ms`), smooth background transition to Secondary Forest `#244C42`.
- **Cards:** Subtle `translateY(-2px)` + `--shadow-md` on interactive cards only (static read-only cards do not bounce).
- **Modals & Drawers (`<dialog>`):** `opacity 0→1` + `translateY(8px→0)` (`240ms`, `--ease-emphasized`); slide-over drawers translate from right (`280ms`).
- **Tabs & Steppers:** Sliding Deep Forest underline/pill indicator (`200ms`, `--ease-standard`).
- **Loading Skeletons:** Warm Ivory shimmer (`#EDEAE0 → #F9F7F1 → #EDEAE0`, `1.6s` linear) — never cold harsh grey.
- **Honest Counters Rule:** Reference coverage stats on public pages may smoothly settle, **but** clinical/financial findings (`₹38,200`, `78 / 100`) **NEVER** count up from zero (prevents misleading intermediate numbers — preserves Wave 3 honesty invariant).

### Family 4: Functional Workflow Animations (Real Backend State-Driven)
Every workflow animation maps directly to real **Kadi SSE** (`/api/v1/kadi/cases/{id}/stream`) and API lifecycle events — never fake timers:
1. **Document Upload:** Dropzone border shifts to Deep Forest `#142F2B`, document deck fans subtly, deterministic upload progress bar fills.
2. **OCR Scanning:** Indeterminate crisp Muted Sage scan-beam sweeps across the Document Provenance Card while SSE reports `ocr_processing`.
3. **Text Extraction & Entity Recognition:** Entity chips (`Medicine`, `Procedure`, `Hospital`, `Amount`) fade in with `40ms` stagger as SSE emits extraction completion.
4. **Validation & Trust Gate:** Settled items settle with a crisp Verified (`#397A58`) micro-check; uncertain OCR medicines gently pause and pivot to an amber Trust Gate (`#C28A35`) hold card.
5. **Evidence Generation:** Curved SVG edges in the Evidence Explorer draw from Document → Entity → Rule → Finding (`stroke-dashoffset`, `350ms`).
6. **Human Review & Final Analysis:** When a finalized clinician statement attaches or an appeal PDF is HMAC-signed, a calm violet (`#8066A5`) or forest (`#397A58`) seal ring completes once.

---

## 4. Mandatory Reduced-Motion Contract

ArogyaRakshak honours **both** OS-level `@media (prefers-reduced-motion: reduce)` AND the user's in-app toggle (`<html data-motion="reduce">`, persisted in `localStorage["arogyarakshak.motion"]`):
- All ambient scientific backgrounds freeze in a composed, balanced static frame.
- All scroll-driven reveals render immediately at `opacity: 1; transform: none`.
- Workflow scan beams and loading shimmers switch to crisp static progress indicators + clear status text (`aria-live="polite"`).
- View transitions degrade to instant cut.
