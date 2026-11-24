# ArogyaRakshak — Colour System & Design Tokens Specification

**Theme Name:** AROGYARAKSHAK — DEEP FOREST / WARM IVORY  
**Default Mode:** LIGHT (`[data-theme="light"]` / `:root`)  
**Secondary Mode:** Optional Dark Mode (`[data-theme="dark"]`, never default)  
**Token Pipeline:** `packages/design-tokens/tokens.json` → `packages/design-tokens/build.mjs` → `apps/web/app/generated/tokens.css` & `apps/mobile/src/generated/tokens.ts`

---

## 1. Official Brand Seed Tokens (Exact Values)

| Role | Token Name | Hex | RGB | Purpose |
|---|---|---|---|---|
| **Deep Forest** | `--color-deep-forest` | `#142F2B` | `20, 47, 43` | Primary brand authority, primary CTA fill, active nav, emblem core |
| **Secondary Forest** | `--color-secondary-forest` | `#244C42` | `36, 76, 66` | Primary CTA hover, secondary headers, dark editorial accents |
| **Muted Sage** | `--color-muted-sage` | `#91B49C` | `145, 180, 156` | Botanical illustrations, graph edges, subtle accents, progress tracks |
| **Pale Sage** | `--color-pale-sage` | `#D5E7D9` | `213, 231, 217` | Soft highlight surfaces, active pills, tertiary button fill, callout tints |
| **Warm Ivory** | `--color-warm-ivory` | `#F4F1E8` | `244, 241, 232` | Primary page canvas (light mode default) |
| **White** | `--color-white` | `#FFFFFF` | `255, 255, 255` | Elevated cards, inputs, modals, paper appeal surfaces |
| **Primary Text** | `--color-text-primary` | `#1D2925` | `29, 41, 37` | Headings, primary body copy, tabular numbers |
| **Secondary Text** | `--color-text-secondary` | `#64766C` | `100, 118, 108` | Supporting labels, metadata, timestamps (verified >= 4.5:1 on `#FFFFFF`) |
| **Borders** | `--color-border` | `#E2E2D8` | `226, 226, 216` | 1px hairline card/table/input borders |

---

## 2. Semantic & Provenance Palette

| Semantic Role | Seed Hex | Ink-Grade Text Token (AA/AAA) | Soft Tint Surface | Border Token |
|---|---|---|---|---|
| **Verified** | `#397A58` | `#24573D` | `#EBF5EE` | `#B2D5BE` |
| **AI-Derived** | `#52769B` | `#325170` | `#EDF3F8` | `#B7CCE0` |
| **Human-Reviewed** | `#8066A5` | `#58417A` | `#F3EFF9` | `#CBBCE2` |
| **Needs Attention** | `#C28A35` | `#7A5312` | `#FBF4E6` | `#E8CE9A` |
| **Critical** | `#C4544F` | `#962F2B` | `#FBEEED` | `#E8B8B5` |
| **Not Assessed** | `#89918C` | `#4E5651` | `#F1F3F1` | `#D1D6D3` |

---

## 3. WCAG 2.1 AA Contrast Verification Matrix (Light Mode)

*Note: `packages/design-tokens/contrast.mjs` enforces `>= 4.5:1` for normal text and `>= 3.0:1` for large text/UI components on every build.*

| Foreground | Background | Approximate Ratio | Verdict | Usage Constraint |
|---|---|---|---|---|
| `#1D2925` (Primary Text) | `#F4F1E8` (Warm Ivory) | **13.5 : 1** | AAA Pass | All headings & body text on canvas |
| `#1D2925` (Primary Text) | `#FFFFFF` (White) | **15.1 : 1** | AAA Pass | All card headings & body text |
| `#64766C` (Secondary Text) | `#FFFFFF` (White) | **4.8 : 1** | AA Pass | Card subtitles, metadata, form helper text |
| `#56675E` (Secondary Ink on Ivory) | `#F4F1E8` (Warm Ivory) | **5.2 : 1** | AA Pass | Use darkened `#56675E` (vs `#64766C` ~4.3:1 on Ivory) for small body text directly on `#F4F1E8` |
| `#FFFFFF` (White) | `#142F2B` (Deep Forest) | **14.3 : 1** | AAA Pass | Primary buttons, dark trust panels |
| `#FFFFFF` (White) | `#244C42` (Secondary Forest) | **9.6 : 1** | AAA Pass | Button hover states, section banners |
| `#142F2B` (Deep Forest) | `#D5E7D9` (Pale Sage) | **11.1 : 1** | AAA Pass | Active pills, soft buttons, highlight tags |
| `#397A58` (Verified) | `#FFFFFF` (White) | **5.1 : 1** | AA Pass | Verified icons, links, bold status text |
| `#52769B` (AI-Derived) | `#FFFFFF` (White) | **4.7 : 1** | AA Pass | AI-derived icons, graph nodes, labels |
| `#8066A5` (Human-Reviewed) | `#FFFFFF` (White) | **4.8 : 1** | AA Pass | Human-reviewed icons, doctor badges |
| `#C28A35` (Needs Attention) | `#FFFFFF` (White) | **3.0 : 1** | UI/Large Only | Use `#C28A35` for icons/bars/borders; use `#7A5312` (**6.5:1**) for text |
| `#C4544F` (Critical) | `#FFFFFF` (White) | **4.1 : 1** | UI/Large Only | Use `#C4544F` for icons/bars/fills; use `#962F2B` (**7.1:1**) for normal text |
| `#89918C` (Not Assessed) | `#FFFFFF` (White) | **3.2 : 1** | UI/Large Only | Use `#89918C` for icons/bars/borders; use `#4E5651` (**7.0:1**) for text |

---

## 4. Data Visualisation Palette (Colorblind-Conscious)

| Series Token | Light Mode Hex | Dark Mode Hex | Meaning / Module Accent |
|---|---|---|---|
| `--chart-within` | `#397A58` | `#5CC08C` | Within benchmark / Compliant / Present |
| `--chart-over` | `#C4544F` | `#E87A75` | Above ceiling / Overcharged / Critical |
| `--chart-bundled` | `#C28A35` | `#E3AE57` | Bundled / Duplicate / Needs Attention |
| `--chart-unmatched` | `#89918C` | `#9FA8A3` | Not assessed / Unmatched / Refused |
| `--chart-ai` | `#52769B` | `#7DA4CC` | AI-Derived / Kadi Extraction |
| `--chart-human` | `#8066A5` | `#A98FD1` | Human-Reviewed / Clinical Statement |
| `--chart-track` | `#E9E6DC` | `#23332E` | Empty progress/comparison bar track |
| `--chart-grid` | `#E2E2D8` | `#2B3D37` | Chart axis & subtle grid lines |

**Module Signature Accents** (used strictly for module icon badges, 2px top rules, and subtle tinted fills — never replacing Deep Forest primary actions):
- **Kadi:** `#244C42` (Secondary Forest) + `#91B49C` (Muted Sage)
- **BillNyay:** `#142F2B` (Deep Forest) + `#397A58` (Verified Green)
- **DawaCheck:** `#52769B` (AI/Analytical Slate Blue) + `#397A58` (Within Cap)
- **DaaviSetu:** `#244C42` (Secondary Forest) + `#8066A5` (Doctor Confirmation)
- **BimaNyay:** `#8066A5` (Adjudication Plum) + `#C28A35` (SLA Amber)
- **SchemeSetu:** `#397A58` (Civic Forest Green) + `#C28A35` (Verification Amber)

---

## 5. Optional Secondary Dark Mode Token Map

Dark mode is **strictly opt-in** (never the initial default; `<html data-theme="light">` is default unless the user explicitly toggles Dark in header/settings).

| Token | Light Mode (Default) | Dark Mode (Optional) |
|---|---|---|
| `--bg-base` | `#F4F1E8` | `#0F1A17` |
| `--bg-surface` | `#FFFFFF` | `#162521` |
| `--bg-surface-elevated` | `#FAF8F3` | `#1E322C` |
| `--bg-surface-secondary` | `#EDEAE0` | `#243B34` |
| `--border-subtle` | `#E2E2D8` | `#2A4039` |
| `--border-medium` | `#C8CFC6` | `#3A544C` |
| `--text-primary` | `#1D2925` | `#EEF2EE` |
| `--text-secondary` | `#64766C` | `#A7B8AE` |
| `--action-primary` | `#142F2B` | `#91B49C` |
| `--action-primary-hover` | `#244C42` | `#A9C9B3` |
| `--text-on-action` | `#FFFFFF` | `#0F1A17` |
| `--border-focus` | `#142F2B` | `#91B49C` |

---

## 6. Migration Note from Current `packages/design-tokens/tokens.json`

Currently `tokens.json` defaults `:root` to Dark Navy (`#101B2A`) and Light to Cool Slate (`#F5F7FA`). During implementation:
1. Flip `:root` default to **Light Deep Forest / Warm Ivory** (`#F4F1E8` / `#142F2B`) and move Dark to `[data-theme="dark"]`.
2. Update `apps/web/app/layout.tsx` pre-paint `<script>` so first-time visitors without a stored preference always receive `light` (ignoring OS dark preference on first load, per *"Dark mode may be designed as an optional secondary theme. It must never be the default"*).
3. Re-run `npm run generate` and `packages/design-tokens/contrast.mjs` to lock all 113+ contrast pairs in CI.
