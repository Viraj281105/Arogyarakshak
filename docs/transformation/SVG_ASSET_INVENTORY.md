# ArogyaRakshak — SVG Asset Inventory & Engineering Specification

**Location Convention:**
- Static public & favicon assets: `apps/web/public/icons/` and `apps/web/public/brand/`
- Server-safe inline React SVG components: `apps/web/app/components/brand/` and `apps/web/app/components/illustrations/`
- Static server-safe UI icon paths: `apps/web/app/components/public/publicIcons.ts`
- Client UI icons: `lucide-react/icons/<name>` (per-icon deep imports enforced by `apps/web/tests/icons.test.ts`)

---

## 1. Naming & Technical Conventions

- **File Naming:** `ar-<category>-<name>.svg` (kebab-case) for static assets; `Ar<Name>Illustration.tsx` (PascalCase) for tokenized React Server Components.
- **Optimization Gate:** Every SVG MUST pass SVGO (`multipass: true`, preserve `viewBox`, preserve semantic `#id` hooks required for CSS/Motion animations, strip editor metadata).
- **Size Budgets:**
  - Brand emblems & icons: `<= 2 KB` uncompressed.
  - Spot illustrations (empty states, module headers): `<= 6 KB` uncompressed.
  - Hero & complex scientific backdrops: `<= 14 KB` uncompressed.

---

## 2. Complete SVG Asset Inventory

### A. Brand Identity Assets (8 Assets)
| Asset ID | Target Path | ViewBox | Stroke / Fill | Responsive / Animation Notes |
|---|---|---|---|---|
| `BRD-01` | `app/components/brand/ArogyaEmblem.tsx` | `0 0 64 64` | `#142F2B` fill, `#91B49C` veins, `#F4F1E8` cross | Supports `variant="primary"\|"mono-dark"\|"mono-light"` |
| `BRD-02` | `app/components/brand/ArogyaWordmark.tsx` | `0 0 240 48` | Emblem + Manrope text | Collapses subtitle `<640px` |
| `BRD-03` | `app/components/brand/ArogyaLogoAnimated.tsx` | `0 0 64 64` | `pathLength="100"` groups | One-shot draw-in on hero/auth; static on reduced motion |
| `BRD-04` | `app/components/brand/ArogyaLoader.tsx` | `0 0 48 48` | `#142F2B` / `#91B49C` | Breathing shield-leaf loader (`role="status"`) |
| `BRD-05` | `public/icons/favicon.svg` | `0 0 32 32` | Simplified 3-path shield | Crisp at `16×16px` |
| `BRD-06` | `public/icons/icon.svg` | `0 0 512 512` | Warm Ivory badge + Deep Forest shield | Replaces legacy navy icon |
| `BRD-07` | `public/icons/icon-maskable.svg` | `0 0 512 512` | Safe-zone 80% centered shield on `#142F2B` | Android adaptive icon safe zone |
| `BRD-08` | `public/icons/icon-192.png`, `icon-512.png`, `apple-touch-icon.png` | `192/512/180` | Rasterized from `BRD-06` | Fixes current missing PNG PWA icons |

### B. Scientific Backgrounds & Ambient Patterns (5 Assets)
| Asset ID | Target Path | ViewBox | Surface | Animation Hook |
|---|---|---|---|---|
| `BG-01` | `app/components/illustrations/MolecularNetworkBg.tsx` | `0 0 960 640` | Landing hero & `/login` left panel | `#mol-nodes` subtle opacity stagger |
| `BG-02` | `app/components/illustrations/BotanicalGridBg.tsx` | `0 0 800 600` | Evidence Explorer canvas & `/platform` | `#grid-hairs` static CSS pattern |
| `BG-03` | `app/components/illustrations/DnaHelixAccent.tsx` | `0 0 180 480` | `/platform/kadi` & `/evidence-methodology` | `#helix-strand-a/b` gentle drift |
| `BG-04` | `app/components/illustrations/HeartbeatWaveBg.tsx` | `0 0 600 120` | BillNyay & Clinical Review header accent | `#ecg-line` single-pass trace |
| `BG-05` | `app/components/illustrations/CellularDriftBg.tsx` | `0 0 480 320` | SchemeSetu & `/about` subtle section wash | `#cell-rings` gentle scale breath |

### C. Custom Domain & Workflow Illustrations (12 Assets)
| Asset ID | Target Path | ViewBox | Used On | Replaces / New |
|---|---|---|---|---|
| `ILL-01` | `app/components/landing/HeroIllustration.tsx` | `0 0 480 540` | `/` Landing Hero (Scanning document + molecular network + provenance tags) | **Refactors** existing `HeroIllustration.tsx` to Deep Forest / Warm Ivory |
| `ILL-02` | `app/components/illustrations/DocumentScanIll.tsx` | `0 0 240 180` | Kadi Dropzone & `/platform/kadi` | New |
| `ILL-03` | `app/components/illustrations/DataExtractionIll.tsx` | `0 0 320 200` | `/how-it-works` & Kadi Processing | New |
| `ILL-04` | `app/components/illustrations/EvidenceVerifyIll.tsx` | `0 0 280 200` | Evidence Explorer empty state & `/evidence-methodology` | New |
| `ILL-05` | `app/components/illustrations/HospitalBillIll.tsx` | `0 0 240 180` | BillNyay empty state & `/platform/billnyay` | New |
| `ILL-06` | `app/components/illustrations/HumanAnatomyIll.tsx` | `0 0 200 220` | BillNyay Clinical Plausibility & ICD panel | New |
| `ILL-07` | `app/components/illustrations/MedicineStripIll.tsx` | `0 0 260 180` | DawaCheck Price Basis (ADR-012) & `/platform/dawacheck` | New |
| `ILL-08` | `app/components/illustrations/MedicineCapsulesIll.tsx` | `0 0 220 160` | DawaCheck empty state & Jan Aushadhi card | New |
| `ILL-09` | `app/components/illustrations/InsurancePolicyIll.tsx` | `0 0 240 180` | BimaNyay empty state & `/platform/bimanyay` | New |
| `ILL-10` | `app/components/illustrations/PreAuthDossierIll.tsx` | `0 0 240 180` | DaaviSetu empty state & `/platform/daavisetu` | New |
| `ILL-11` | `app/components/illustrations/DoctorPatientIll.tsx` | `0 0 260 180` | `/review` Sign-in & `/trust` | New |
| `ILL-12` | `app/components/illustrations/ByodShieldIll.tsx` | `0 0 240 180` | `/security` & Privacy Settings card | New |

### D. Custom Module Emblem Icons (6 Assets — Replacing Legacy Emojis)
| Asset ID | Module | ViewBox | Visual Metaphor |
|---|---|---|---|
| `MOD-01` | **Kadi** | `0 0 24 24` | Interlocking document-link prism |
| `MOD-02` | **BillNyay** | `0 0 24 24` | Receipt ledger with balanced scale bar |
| `MOD-03` | **DawaCheck** | `0 0 24 24` | Precision capsule with rupee-ceiling line |
| `MOD-04` | **DaaviSetu** | `0 0 24 24` | Bridge arch + verified checklist shield |
| `MOD-05` | **BimaNyay** | `0 0 24 24` | Policy umbrella/shield + statutory gavel bar |
| `MOD-06` | **SchemeSetu** | `0 0 24 24` | Civic pillars + family care arch |
