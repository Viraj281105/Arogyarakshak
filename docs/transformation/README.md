# ArogyaRakshak — Complete Product Transformation Blueprint

**Visual Identity:** AROGYARAKSHAK — DEEP FOREST / WARM IVORY (Light-First Sovereign Editorial)  
**Verified Baseline Branch:** `wave3/m3m4-integration`  
**Google Stitch Project:** `projects/847521722700511340` (*ArogyaRakshak — Deep Forest / Warm Ivory Transformation*)  
**Open the UI mockups:** <https://stitch.google.com/projects/847521722700511340> (needs a Google account with access to the project; ask the maintainer for access)  
**Google Stitch Design System:** `assets/8789632704855580659` (*ArogyaRakshak — Deep Forest / Warm Ivory*)

**Implementation status (2026-11-24):** the foundation is built on branch `wave3/transformation` (tokens, fonts,
brand set, 15 illustrations, 5 backgrounds; ADR-028). Page work is handed to Antigravity:
read **[ANTIGRAVITY_HANDOFF.md](./ANTIGRAVITY_HANDOFF.md)** first.

---

## 1. Transformation Documentation Package (All 21 Deliverables)

| # | Deliverable | Focus Area |
|---|---|---|
| 01 | [PRODUCT_VISION.md](./PRODUCT_VISION.md) | Executive vision, verified repo audit, non-negotiable pillars, personas |
| 02 | [PRODUCT_ARCHITECTURE.md](./PRODUCT_ARCHITECTURE.md) | Dual-zone experience architecture, 6-module relationships, hard privacy boundaries |
| 03 | [PAGE_INVENTORY.md](./PAGE_INVENTORY.md) | Complete 31-surface inventory (15 public/auth + 16 workspace/clinical) & navigation map |
| 04 | [USER_JOURNEYS.md](./USER_JOURNEYS.md) | 7 end-to-end journeys grounded in real FastAPI/Kadi flows |
| 05 | [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) | Spacing, grids, breakpoints, radii, shadows, buttons, forms, cards, icons, 6-tier semantic system |
| 06 | [COLORS_AND_TOKENS.md](./COLORS_AND_TOKENS.md) | Exact Deep Forest / Warm Ivory hex tokens, WCAG AA contrast matrix, data viz & optional Dark mode |
| 07 | [TYPOGRAPHY.md](./TYPOGRAPHY.md) | Manrope + Inter + JetBrains Mono fluid scale, `en-IN` tabular currency, Devanagari rules |
| 08 | [BRAND_IDENTITY.md](./BRAND_IDENTITY.md) | Brand personality, Stitch exploration comparison & complete 14-screen inventory |
| 09 | [LOGO_SPECIFICATION.md](./LOGO_SPECIFICATION.md) | Custom Botanical-Medical Protective Shield emblem, canonical SVG paths, variants & loader |
| 10 | [ILLUSTRATION_SYSTEM.md](./ILLUSTRATION_SYSTEM.md) | Botanical-Architectural Line & Wash style grammar across 16 custom illustration families |
| 11 | [SVG_ASSET_INVENTORY.md](./SVG_ASSET_INVENTORY.md) | 31 itemized SVG assets (brand, scientific backgrounds, domain illustrations, module icons) |
| 12 | [MOTION_DESIGN_SYSTEM.md](./MOTION_DESIGN_SYSTEM.md) | Stack-grounded `motion` + CSS architecture, timing/easing tokens, 4 motion families, reduced-motion |
| 13 | [ANIMATION_INVENTORY.md](./ANIMATION_INVENTORY.md) | 33 itemized animations across scientific, brand, interface, and SSE workflow families |
| 14 | [DATA_VISUALISATION_SPEC.md](./DATA_VISUALISATION_SPEC.md) | 10 real-data SVG visualisations & flagship Evidence Explorer knowledge graph specification |
| 15 | [MODULE_DESIGN_SPECIFICATIONS.md](./MODULE_DESIGN_SPECIFICATIONS.md) | Six distinct visual & interaction specs (Kadi, BillNyay, DawaCheck, DaaviSetu, BimaNyay, SchemeSetu) |
| 16 | [RESPONSIVE_DESIGN.md](./RESPONSIVE_DESIGN.md) | Desktop, laptop, tablet, and intentionally crafted mobile ergonomics & adaptive charts |
| 17 | [ACCESSIBILITY_PLAN.md](./ACCESSIBILITY_PLAN.md) | WCAG 2.1 AA/AAA plan, keyboard/focus architecture, screen readers, Simple Language & Read-Aloud |
| 18 | [FRONTEND_ARCHITECTURE.md](./FRONTEND_ARCHITECTURE.md) | Token pipeline, routing, component retain/enhance/refactor/replace audit, newly wired APIs, mobile |
| 19 | [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) | 7-milestone dependency map, prioritised backlog, and milestone acceptance criteria |
| 20 | [TESTING_AND_PERFORMANCE_PLAN.md](./TESTING_AND_PERFORMANCE_PLAN.md) | Automated test gates, 170 KB gzip web / 2.6 MB mobile budgets, Lighthouse & deployment rules |
| 21 | [OPEN_QUESTIONS_AND_RISKS.md](./OPEN_QUESTIONS_AND_RISKS.md) | Explicit conflict rulings, open maintainer decisions (Q1–Q6), and risk mitigations |

---

## 2. Google Stitch Visual Deliverables (`projects/847521722700511340`)

All 14 high-fidelity screens were generated in **Google Stitch** using Design System `assets/8789632704855580659` (**ArogyaRakshak — Deep Forest / Warm Ivory**, Light Mode, Manrope + Inter):

1. **Flagship Landing Page (Selected Base):** `projects/847521722700511340/screens/5fdc7a05515f47c8be06efddd2fc2eec`
2. **Landing Variant — Editorial Magazine:** `projects/847521722700511340/screens/9b26009a804f42928aaf7fa8b7a8a6a2`
3. **Landing Variant — Scientific Laboratory Clarity:** `projects/847521722700511340/screens/b7c94cf87b3b40c9906d063470c419d6`
4. **Sign In & Registration (45/55 Editorial Split):** `projects/847521722700511340/screens/2471128a54bc4eefbe4736edc08e1b34`
5. **Main Dashboard — Case Desk:** `projects/847521722700511340/screens/20aa2636b77c43cca183a603cf99d156`
6. **Evidence Explorer & Kadi Intelligence Workspace:** `projects/847521722700511340/screens/ee1967ba9bee4c6993547d3a84536a3f`
7. **BillNyay — Hospital Bill Intelligence Workspace:** `projects/847521722700511340/screens/95be66a38bab48c5ad5047b862bd2eda`
8. **BimaNyay — Claim Denial & IRDAI Appeal Studio:** `projects/847521722700511340/screens/fc0c3bba3163434d964cdcc9cadcbe30`
9. **DawaCheck — Medicine Price & Trust Gate Studio:** `projects/847521722700511340/screens/275f3364cf8942aca89b2b2b94935a59`
10. **DaaviSetu — Pre-Authorisation & Readiness Studio:** `projects/847521722700511340/screens/666810eb58214253ae9c0cdf403c47db`
11. **SchemeSetu — Government Scheme Intelligence:** `projects/847521722700511340/screens/4c9fa17dcc6c4e38ad975cb4d31cd6c5`
12. **Account Settings, Privacy & Notifications:** `projects/847521722700511340/screens/a49396f731ec42bb975a837fd747289b`
13. **Mobile Case Desk & Quick Intake (Mobile):** `projects/847521722700511340/screens/ca7216e9a65844c99dd896046ba4cd2f`
14. **Clinical Review & Human Governance (`/review`):** `projects/847521722700511340/screens/a6dc0d844dc3403ba7cc48949f2687fc`
