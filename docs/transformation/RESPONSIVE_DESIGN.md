# ArogyaRakshak — Responsive & Multi-Device Design Plan

**Core Mandate:** *Mobile is intentionally crafted for a stressed patient or family member standing at a hospital billing desk — never a squished desktop dashboard.*  
**Mobile Stitch Reference:** `ca7216e9a65844c99dd896046ba4cd2f` (*Mobile Case Desk & Quick Intake*)

---

## 1. Breakpoint & Device Matrix

| Tier | Width Range | Typical Devices | Grid | Primary Navigation | Layout Strategy |
|---|---|---|---|---|---|
| **Mobile Compact** | `320px – 599px` | Budget Android phones (dominant in India), iPhone SE/15 | 4 cols, `16px` margin | Public: Compact top bar + `<dialog>` drawer. Workspace: Bottom 5-tab bar (`Home`, `Scan`, `Cases`, `Tools`, `Settings`) | Single-column flow, thumb-zone primary CTAs, card-list tables, bottom sheets for drawers |
| **Mobile Large** | `600px – 767px` | Large phones, landscape phones | 4 cols, `20px` margin | Same as Mobile Compact | 2-col compact module tiles, stacked workspace panels |
| **Tablet** | `768px – 1023px` | iPad Portrait, Android tablets | 8 cols, `24px` margin | Top bar + `<dialog>` drawer; horizontal scrollable module rail | 2-column card grids, split Queue \| Detail on `/review` |
| **Laptop** | `1024px – 1279px` | 13" laptops, iPad Landscape | 12 cols, `32px` margin | Public nav stays in `<dialog>` drawer (prevents header crowding, verified in Wave 3 M4); collapsible workspace sidebar (`64px` icon rail / `248px` expanded) | 2-column workspace + slide-over inspector drawers |
| **Desktop** | `1280px – 1439px` | Standard monitors | 12 cols, `1240px` max | Full inline 5-item header nav + persistent `248px` workspace sidebar | Rich multi-panel workspaces (Case Desk + Activity Rail, Evidence Graph + Inspector) |
| **Desktop Wide** | `>= 1440px` | Wide displays | 12 cols, `1360px` max | Full inline header + persistent sidebar | Full 3-column BimaNyay Adjudication Studio, expanded Evidence Explorer |

---

## 2. Adaptive Patterns by Surface

### Adaptive Navigation
- **Zero Horizontal Overflow Gate:** Every route must maintain `0px` page-level horizontal overflow at `360px`, `390px`, `768px`, `1024px`, `1280px`, and `1440px` (enforced via `overflow-wrap: anywhere` on statutory clauses/SHA-256 digests and scrollable inner wrappers for wide data tables).
- **Safe Area Insets:** `viewportFit: "cover"` with `env(safe-area-inset-bottom)` padding on the mobile bottom tab bar and sticky action bars.

### Adaptive Data Visualisations
| Visualisation | Desktop (`>= 1024px`) | Tablet (`768–1023px`) | Mobile (`< 768px`) |
|---|---|---|---|
| **Evidence Explorer Graph** | Full interactive radial SVG canvas + right-hand `360px` Inspector Drawer | SVG canvas + slide-over Inspector Drawer | **Intentional Mobile Mode:** Tabbed switch between *Guided Provenance List* (default on mobile for effortless reading) and *Interactive Zoomable Graph* + bottom-sheet Inspector |
| **BillNyay Audit Table** | Full sortable `DataTable` + inline expandable `ExplainTrail` | Scrollable `DataTable` with sticky first column | **Card-per-Line Stack:** Line name + status pill on top, Billed vs CGHS side-by-side in monospace, tap to expand `ExplainTrail` |
| **BimaNyay 3-Column Studio** | Dossier \| Clause Audit \| Appeal Studio side-by-side | 2-col (Dossier+Audit \| Appeal) | Pinned compact SLA pill + 3 segmented tabs (*Dossier*, *Clause Audit*, *Appeals*) |
| **Charts (`ui/Charts.tsx`)** | Full SVG width with inline labels | Responsive `viewBox` scaling | Horizontal bars / compact stacked bars with zero truncated labels + one-tap `"View data table"` |

### Touch, Camera & Low-Bandwidth Ergonomics
- **Touch Targets:** Minimum `44×44px` everywhere (`48×48px` preferred for primary mobile buttons, bottom tabs, and consent checkboxes).
- **Camera-First Mobile Intake:** On mobile web (`DocumentUploader.tsx`), surface a prominent **"Scan with Camera"** button (`<input type="file" accept="image/*" capture="environment">`) alongside file browse; on `apps/mobile` (Expo), invoke `CameraScanScreen` directly from the center **Scan** tab.
- **Illustration Scaling:** Scientific ambient backgrounds (`MolecularNetworkBg`, `DnaHelixAccent`) automatically simplify or hide dense background layers below `640px` so foreground text remains razor-sharp and mobile GPU usage stays minimal.
- **Print Stylesheet (`@media print`):** Appeal letters (BillNyay, BimaNyay), Pre-Auth summaries (DaaviSetu), and Evidence tables print cleanly on A4 paper in high-contrast black ink on white, hiding navigation chrome.
