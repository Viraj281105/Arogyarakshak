# ArogyaRakshak — Advanced Data Visualisation & Evidence Explorer Specification

**Core Principle:** *Every chart represents verified backend data, carries explicit units, source, and provenance (`Estimate` vs `Verified`), and ships with an accessible HTML `<table>` equivalent.*  
**Technical Foundation:** Zero heavy charting libraries (`recharts`/`chart.js`/`d3` omitted to protect the 170 KB gzip budget). Promote and extend the existing server-safe SVG primitives in `apps/web/app/components/ui/Charts.tsx` + `apps/web/app/components/workspace/EvidenceGraph.tsx`.

---

## 1. Reusable Visualisation Library (10 Core Visualisations)

| # | Visualisation | Component | Real Backend Data Source | Used In | Honesty & A11y Contract |
|---|---|---|---|---|---|
| 01 | **Evidence Relationship Graph** | `EvidenceGraph.tsx` (Enhanced) | `GET /api/v1/kadi/cases/{id}/graph` + `/insights` + `/clinical-reviews` | `/app/case/evidence`, `/app/case` | Interactive radial/layered SVG graph with keyboard-focusable `<g role="button">` nodes, provenance colour-coding, filter chips, right-hand inspector drawer, and collapsible `<table>` |
| 02 | **Bill Composition & Discrepancy Waterfall** | `StackedBarChart` + `WaterfallChart` (`ui/Charts.tsx`) | `POST /api/v1/billnyay/cases/{id}/audit` | BillNyay (`/app/case/billnyay`) | Segments: Within CGHS (`#397A58`), Above CGHS (`#C4544F`), Bundled/Duplicate (`#C28A35`), Not Assessed (`#89918C`). Explicitly states *"CGHS-2024-REVISED subset (27 rows)"* |
| 03 | **Per-Unit Medicine Price Scale Bar** | `PriceBar.tsx` (Enhanced) | `GET /dawacheck/cases/{id}/benchmark`, `POST /dawacheck/benchmark` | DawaCheck (`/app/case/dawacheck`) | Compares **per-unit** billed ₹ vs NPPA ceiling ₹ on one shared linear axis. Refuses rendering when `price_basis` is unconvertible (`CANNOT_COMPARE_RELIABLY`) |
| 04 | **Document Completeness Progress Ring** | `DonutChart` (`ui/Charts.tsx`) | `POST /api/v1/daavisetu/cases/{id}/readiness` | DaaviSetu (`/app/case/daavisetu`) | 3-segment ring: `Present` (`#397A58`), `Needs Doctor Confirmation` (`#8066A5`), `Missing` (`#C28A35`). Center displays `X / Y items` — never "approval %" |
| 05 | **3-Tier Statutory SLA Progression Timeline** | `TimelineChart` (`ui/Charts.tsx`) | `POST /api/v1/bimanyay/timeline` | BimaNyay (`/app/case/bimanyay`) | Horizontal/vertical 3-tier milestone track: GRO (15d) → Bima Bharosa (15d) → Ombudsman (365d), disclosing *"Counted from today / filing date"* |
| 06 | **Denied-Amount Share Bar** | `StackedBarChart` (`ui/Charts.tsx`) | `POST /api/v1/bimanyay/analyze` | BimaNyay (`/app/case/bimanyay`) | Visualizes Claimed vs Approved vs Disputed/Denied ₹ in Indian numbering (`en-IN`) |
| 07 | **Scheme Eligibility Reasoning Flow** | `ReasoningFlowChart.tsx` (New SVG) | `POST /api/v1/schemesetu/eligibility/reasoning` + `/eligibility` | SchemeSetu (`/app/case/schemesetu`) | Interactive Sankey-style / node-flow diagram: Residence Input → Dialect Normalizer → Official Rule Check → Citation Verification Status (`Supported`, `Scheme Only`, `Uncheckable`) |
| 08 | **Income Trend Projection Chart** | `TrendLineChart.tsx` (New light SVG) | `POST /api/v1/schemesetu/eligibility/trend` | SchemeSetu (`/app/case/schemesetu`) | Clean time-series line chart over user-supplied trend inputs; explicitly labelled *"User-provided projection — income is non-determinative for PM-JAY/MJPJAY"* |
| 09 | **Document Extraction Confidence Overlay** | `ExtractionOverlayCard.tsx` (New) | `GET /api/v1/kadi/cases/{id}` (redacted excerpt + entity spans + `min_ocr_confidence`) | Kadi (`/app/case/kadi`) | Highlights extracted entity spans inside the **redacted 1,000-char excerpt** (never raw original file, honouring ADR-003) with `<meter>` confidence indicators or `"Not recorded"` |
| 10 | **Case Append-Only Audit Timeline** | `TimelineExplorer.tsx` + `TimelineChart` | `GET /api/v1/kadi/cases/{id}/timeline` | `/app/case/history`, `/app/case` | Chronological multi-source timeline unifying Kadi uploads, auto-triggers, OCR consensus, clinical statements, and downloads |

---

## 2. Signature Experience: The Evidence Explorer (`/app/case/evidence`)

**Stitch Reference:** `ee1967ba9bee4c6993547d3a84536a3f` (*Evidence Explorer & Kadi Document Intelligence Workspace*)

The Evidence Explorer is ArogyaRakshak's defining visual innovation. It transforms opaque AI outputs into an auditable, interactive **Provenance Knowledge Graph**:

### Node Taxonomy & Visual Encoding
| Node Layer | Shape / Border | Semantic Colour | Information Shown on Node |
|---|---|---|---|
| **1. Source Document** | Rounded Document Rectangle (`1px #142F2B`) | Deep Forest (`#142F2B`) | Filename, Doc Type, Short SHA-256 Digest (`e.g. a9f3…`), `"Original discarded"` tag |
| **2. Extracted Entity** | Pill Node (`1.5px`) | AI-Derived (`#52769B`) or Human-Reviewed (`#8066A5`) | Entity label (e.g., `Augmentin 625`), Confidence (`0.94` or `Settled by 2 readers`) |
| **3. Reference Rule / Source** | Chamfered Hexagon / Book Badge | Secondary Forest (`#244C42`) | Exact citation (e.g., `CGHS-2024-REVISED`, `NPPA Schedule-I`, `IRDAI 29 May 2024`) |
| **4. Computed Finding** | Elevated Status Card Node | Verified (`#397A58`), Needs Attention (`#C28A35`), Critical (`#C4544F`), or Not Assessed (`#89918C`) | Plain-language finding (e.g., `+24.4% above NPPA cap`, `Held back by Trust Gate`) |
| **5. Human Clinical Review** | Double-Ring Seal Node | Human-Reviewed (`#8066A5`) | Reviewer display name, verification tier (`Self-declared` / `Demo only`), immutable statement version |

### Interaction Model
- **Hover / Focus:** Highlights the full upstream & downstream provenance chain (all connected edges turn `#142F2B` `2px`; unrelated nodes dim to `0.35` opacity).
- **Click / Enter:** Opens the **Provenance Inspector Drawer** (right panel on desktop, bottom sheet on mobile) rendering the full **ADR-017 Explanation Trail**:
  1. **Origin:** Document digest + page/line reference.
  2. **Rule Applied:** Exact statutory clause, CGHS row, or NPPA ceiling.
  3. **Provenance Status:** Explicit `EvidenceBadge` (`AI-Derived`, `Human-Reviewed`, `Verified`, etc.).
  4. **What Could Not Be Determined:** Explicit honesty block (never hidden).
  5. **Direct Action:** Jump straight to the owning module or request a Human Review / Transcription.
- **Filter Bar:** Filter graph by provenance tier (`All`, `Critical`, `Needs Attention`, `Human-Reviewed`, `AI-Derived`, `Verified`, `Not Assessed`) or by module.
- **Zero-Fabrication Rule:** Never draw edges that are not returned by `GET /api/v1/kadi/cases/{id}/graph` or linked insights.
