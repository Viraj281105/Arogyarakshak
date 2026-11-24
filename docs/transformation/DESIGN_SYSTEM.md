# ArogyaRakshak — Design System Specification

**Identity Name:** AROGYARAKSHAK — DEEP FOREST / WARM IVORY  
**Primary Theme:** LIGHT (Default, Sovereign Editorial) · Optional Dark Mode Secondary  
**Stitch Design System Asset:** `assets/8789632704855580659` (Project `projects/847521722700511340`)  
**Source of Truth in Repo:** `packages/design-tokens/tokens.json` → compiled to `apps/web/app/generated/tokens.css` & `apps/mobile/src/generated/tokens.ts`

---

## 1. Design Philosophy

ArogyaRakshak's design system embodies **Editorial Botanical Clarity**:
- **Calm under stress:** Warm Ivory (`#F4F1E8`) eliminates the clinical glare of pure `#FFFFFF` backgrounds while keeping Pure White (`#FFFFFF`) cards crisp and scannable.
- **Sovereign authority without intimidation:** Deep Forest (`#142F2B`) and Secondary Forest (`#244C42`) convey institutional reliability, groundedness, and care — replacing cold navy/cyan tech-startup clichés.
- **Provenance as first-class UI:** Every piece of data carries a distinct, accessible semantic colour + icon + text label so users never confuse an AI extraction with a verified rule or a doctor's verbatim statement.
- **Zero decorative noise:** No neon halos, no glassmorphism over busy backgrounds, no animated counters that fabricate precision.

---

## 2. Spacing System (4px Base Grid)

All layout rhythm, padding, and gaps derive from a strict 4px spatial scale:

| Token | Value | Usage |
|---|---|---|
| `--space-2xs` | `2px` | Hairline badge icon offsets, inline borders |
| `--space-xs` | `4px` | Tight label-to-value gaps, pill internal gaps |
| `--space-sm` | `8px` | Compact control gaps, icon-to-text spacing |
| `--space-md` | `16px` | Default component padding, form field spacing, mobile gutters |
| `--space-lg` | `24px` | Card padding (desktop), section sub-group spacing |
| `--space-xl` | `32px` | Major grid gutters, card-to-card vertical rhythm |
| `--space-2xl` | `48px` | Page section padding (mobile/tablet), workspace header separation |
| `--space-3xl` | `64px` | Public editorial section spacing (desktop) |
| `--space-4xl` | `96px` | Hero vertical breathing room (desktop) |
| `--min-touch-target` | `44px` | Mandatory minimum interactive hit area (WCAG 2.1 AA / mobile ergonomic floor) |

---

## 3. Grid System & Responsive Breakpoints

| Breakpoint Name | Viewport Width | Columns | Container Max-Width | Outer Margin | Gutter | Navigation Pattern |
|---|---|---|---|---|---|---|
| **Mobile Compact** | `320px – 599px` | 4 cols | `100%` | `16px` | `12px` | Compact top bar + `<dialog>` drawer (public) / Bottom 5-tab bar (workspace) |
| **Mobile Large / Phablet** | `600px – 767px` | 4 cols | `100%` | `20px` | `16px` | Compact top bar + Bottom 5-tab bar (workspace) |
| **Tablet Portrait** | `768px – 1023px` | 8 cols | `100%` | `24px` | `20px` | Top bar + `<dialog>` drawer; 2-col module cards |
| **Laptop / Tablet Landscape** | `1024px – 1279px` | 12 cols | `100%` | `32px` | `24px` | Collapsible workspace sidebar; public nav stays in `<dialog>` drawer to prevent crowding |
| **Desktop Standard** | `1280px – 1439px` | 12 cols | `1240px` | `32px` | `24px` | Full inline 5-item header nav + persistent workspace sidebar (`248px`) |
| **Desktop Wide** | `>= 1440px` | 12 cols | `1360px` | `40px` | `28px` | Full 3-column adjudication layouts (e.g., BimaNyay Studio, Evidence Explorer + Inspector) |

---

## 4. Border & Radius Conventions

| Token | Value | Application |
|---|---|---|
| `--radius-xs` | `4px` | Monospace code chips, inline highlight spans |
| `--radius-sm` | `6px` | Badges, provenance pills (rectangular editorial), compact inputs |
| `--radius-md` | `10px` | Primary/secondary buttons, text inputs, selects, alert banners |
| `--radius-lg` | `14px` | Standard content cards, workspace panels, table containers |
| `--radius-xl` | `20px` | Hero showcase containers, `<dialog>` modals, upload dropzones |
| `--radius-full` | `9999px` | Status dots, filter pills, avatars, progress bars |

**Border Rules:**
- Default card & input border: `1px solid var(--border-subtle)` (`#E2E2D8`).
- Elevated/hover interactive border: `1px solid var(--border-medium)` (`#C8CFC6`).
- Focus ring (keyboard `:focus-visible`): `2px solid #142F2B` with `2px` offset (`box-shadow: 0 0 0 4px rgba(20, 47, 43, 0.14)`). Never suppressed.

---

## 5. Elevation & Shadow System

Shadows are warm, forest-tinted, and restrained — never heavy grey drop shadows or neon glows.

| Level | Token | Value (Light Mode) | Usage |
|---|---|---|---|
| **Level 0 (Flat)** | `--shadow-none` | `none` | Embedded nested boxes, Warm Ivory canvas sections |
| **Level 1 (Card)** | `--shadow-sm` | `0 1px 2px rgba(20, 47, 43, 0.04), 0 2px 8px rgba(20, 47, 43, 0.03)` | Standard White cards on Warm Ivory canvas |
| **Level 2 (Interactive / Sticky)** | `--shadow-md` | `0 4px 16px rgba(20, 47, 43, 0.06), 0 1px 3px rgba(20, 47, 43, 0.04)` | Sticky header when scrolled, hovered cards, dropdown menus |
| **Level 3 (Overlay / Modal)** | `--shadow-lg` | `0 16px 40px rgba(20, 47, 43, 0.12), 0 4px 12px rgba(20, 47, 43, 0.06)` | `<dialog>` modals, Command Palette (`Ctrl+K`), slide-over drawers, toasts |

---

## 6. Component Conventions

### Button Hierarchy
1. **Primary (`btn-primary`):** Background `#142F2B`, text `#FFFFFF`, hover `#244C42`, active `#0E221F`. One primary CTA per focal region.
2. **Secondary (`btn-secondary`):** Background `#FFFFFF`, border `1.5px solid #142F2B`, text `#142F2B`, hover `#D5E7D9` tint.
3. **Tertiary / Soft (`btn-soft`):** Background `#D5E7D9`, text `#142F2B`, hover `#C2DEC8`. Used for helpful non-destructive tools (e.g., Read Aloud, Explain Trail).
4. **Ghost (`btn-ghost`):** Transparent background, text `#244C42`, hover `rgba(20, 47, 43, 0.06)`. Used in toolbars and icon actions.
5. **Destructive (`btn-danger`):** Background `#C4544F` (or `#FFFFFF` with `#C4544F` border for secondary danger), text `#FFFFFF` (passes AA large/bold; darkened `#A63D38` for normal-weight text on white). Always gated by `ConfirmationDialog`.

### Form Conventions
- Every input has a visible persistent `<label>` (never placeholder-only).
- Minimum height `44px`, padding `10px 14px`, `#FFFFFF` background, `1px solid #E2E2D8` border, `10px` radius.
- Validation errors render inline below the field with a `#C4544F` Critical icon + `aria-describedby` linkage.
- Sensitive auth forms (`/login`, `/register`, `/reset-password`) include explicit show/hide password toggle (`aria-pressed`) and never echo submitted secrets.

### Card Conventions
- **Standard Working Card:** `#FFFFFF` surface on `#F4F1E8` canvas, `1px solid #E2E2D8`, `14px` radius, `20px–24px` padding.
- **Tinted Callout Card:** Pale Sage (`#D5E7D9` at 45% or `#EDF5EF`) for helpful context; Semantic Tint for provenance/warnings.
- **Paper Document Card:** Crisp `#FFFFFF` with subtle archival rule lines (`#E2E2D8`), monospace metadata header, and HMAC signature footer — used for BillNyay Appeal Letters, BimaNyay 3-Tier Drafts, and DaaviSetu Annexure-B previews.

### Iconography Standards
- **UI Icons:** `lucide-react` (`1.71.0`), `1.75px` stroke weight, rounded caps/joins, imported strictly via deep paths (`lucide-react/icons/<name>`) on client routes and static SVG geometry (`publicIcons.ts`) on Server Components to protect the 170 KB bundle budget.
- **Brand & Module Icons:** Custom geometric SVGs (see `LOGO_SPECIFICATION.md` and `SVG_ASSET_INVENTORY.md`) replacing all remaining emoji icons in navigation/tabs.
- **Rule:** Icons **never** communicate status alone — always paired with visible text or `aria-label`.

---

## 7. Semantic Status & Provenance System

Every finding, metric, entity, and citation uses one unified `EvidenceBadge` vocabulary anchored to the 6 official semantic colours:

| Visual Tier | Official Hex | Accessible Text Hex (on Light Tint) | Tint Background | Border | Mapped Backend Provenance / States | Icon |
|---|---|---|---|---|---|---|
| **Verified** | `#397A58` | `#24573D` (7.9:1 on tint) | `#EBF5EE` | `#B2D5BE` | `verified`, `supported`, `WITHIN_CAP`, `PRESENT`, HMAC valid | ShieldCheck |
| **AI-Derived** | `#52769B` | `#325170` (7.4:1 on tint) | `#EDF3F8` | `#B7CCE0` | `ai-generated`, `rule-engine`, `AI_DERIVED`, `scheme_only` | Cpu / Sparkle-Geometric |
| **Human-Reviewed** | `#8066A5` | `#58417A` (7.8:1 on tint) | `#F3EFF9` | `#CBBCE2` | `HUMAN_REVIEWED`, `HUMAN_AUTHORED`, doctor-confirmed fact | UserCheck |
| **Needs Attention** | `#C28A35` | `#7A5312` (6.5:1 on tint) | `#FBF4E6` | `#E8CE9A` | `provisional`, `ambiguous`, `HELD_BACK`, `MISSING`, `UNVERIFIED` clause | AlertTriangle |
| **Critical** | `#C4544F` | `#962F2B` (7.1:1 on tint) | `#FBEEED` | `#E8B8B5` | `OVERCHARGED`, `CONFLICT`, Safety Escalation, `unsupported` | OctagonAlert |
| **Not Assessed** | `#89918C` | `#4E5651` (7.0:1 on tint) | `#F1F3F1` | `#D1D6D3` | `unevaluated`, `insufficient-evidence`, `uncheckable`, `NOT_ASSESSED`, combo refused | MinusCircle |

> **WCAG AA Engineering Note:** Notice that raw mid-tone semantic hexes like `#C28A35` and `#89918C` are ideal for **icons, chart fills, borders, and status bars**, while **badge label text** uses the darkened ink-grade shade from the same hue family so every badge achieves `>= 6.5:1` contrast (exceeding WCAG AA `4.5:1` and approaching AAA `7:1`).
