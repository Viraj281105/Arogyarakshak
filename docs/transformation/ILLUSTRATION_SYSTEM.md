# ArogyaRakshak — Custom Scientific & Medical Illustration System

**Style Name:** *Botanical-Architectural Line & Wash*  
**Medium:** 100% Vector SVG (Server-renderable, theme-tokenized via CSS custom properties, lightweight `< 8 KB` gzip per illustration)

---

## 1. Visual Style Grammar

Every illustration across ArogyaRakshak follows one unified artistic language so landing pages, module empty states, and scientific backgrounds feel crafted by a single studio:

1. **Line Weight Hierarchy:**
   - Primary structural contours: `1.75px` in Deep Forest (`#142F2B`) or Secondary Forest (`#244C42`).
   - Secondary internal anatomy / document lines / grid hairs: `1.1px` in Muted Sage (`#91B49C`) or `#64766C`.
   - Micro-details & coordinate ticks: `0.75px` dashed (`stroke-dasharray="2 3"`).
2. **Fill & Wash Conventions:**
   - Primary paper/object bodies: Pure White (`#FFFFFF`) or Warm Ivory (`#F4F1E8`).
   - Soft botanical/scientific washes: Pale Sage (`#D5E7D9` at `40%–70%` opacity) and Muted Sage (`#91B49C` at `15%–25%` opacity).
   - Semantic highlight accents ONLY where illustrating real product states: Verified `#397A58`, AI-Derived `#52769B`, Human-Reviewed `#8066A5`, Needs Attention `#C28A35`, Critical `#C4544F`.
3. **Geometry:** Rounded stroke caps (`stroke-linecap="round"`), rounded joins (`stroke-linejoin="round"`), subtle geometric precision (architectural blueprint meets botanical engraving). Zero gradients with neon glow, zero photorealistic stock overlays, zero cartoon clip-art.

---

## 2. Complete Illustration Library (16 Custom Families)

| # | Subject | Primary Placement | Visual Composition | Animation Opportunity |
|---|---|---|---|---|
| 01 | **Human Anatomy (Outline Silhouette)** | `/about`, BillNyay Clinical Plausibility empty state | Minimalist front-facing anatomical contour with subtle meridian nodes and Pale Sage wash | Gentle node pulse on hover/focus |
| 02 | **Heart & Heartbeat Waveform** | Landing subtle hero layer, Cardiac BillNyay scenario | Architectural botanical heart silhouette intersecting a clean ECG waveform line | Single-pass SVG `stroke-dashoffset` trace |
| 03 | **DNA Double Helix** | `/platform/kadi`, scientific hero background | Fine dual-strand geometric helix in Muted Sage `#91B49C` with nucleotide rungs | Slow subtle vertical drift (CSS transform, paused in reduced motion) |
| 04 | **Molecular Network** | Landing hero ambient backdrop, `/login` Deep Forest left panel | Connected hexagonal & circular molecular lattice with low-opacity botanical edges | Gentle ambient node breathing (`opacity` 0.35 → 0.75) |
| 05 | **Cellular Structures** | `/evidence-methodology`, SchemeSetu empty state | Concentric organic cell rings in Pale Sage & Muted Sage with nucleus focal dots | Subtle scale breathing (`1.0 → 1.03`) |
| 06 | **Medical Capsules** | DawaCheck overview & empty state | Precision-drawn two-tone capsules (White + Pale Sage / Deep Forest) with dosage measurement ticks | Subtle tilt on hover |
| 07 | **Tablets & Blister Strip** | DawaCheck Price Basis (ADR-012) explainer | 15-tablet blister strip visually segmented into `1 tablet` unit callout — directly illustrating per-unit math | Highlight single tablet unit on step focus |
| 08 | **Medicine Packaging** | `/platform/dawacheck`, Jan Aushadhi comparison | Branded box vs clean generic Jan Aushadhi strip side-by-side with equal-molecule bridge | Molecule bridge line draw |
| 09 | **Hospital Building** | `/platform/billnyay`, BillNyay empty state | Clean architectural Indian hospital facade with geometric cross pediment and subtle botanical trees | Static architectural anchor |
| 10 | **Doctors & Patients** | `/review` clinical portal, `/trust`, Human-in-the-loop explainer | Dignified abstract editorial figures (doctor with clipboard + patient family) connected by a verified shield bridge | Static / subtle fade-in |
| 11 | **Medical Documents** | Kadi upload dropzone, Case Desk empty state | Layered hospital bill, prescription, and discharge sheet with clean ruled lines & corner fold | Slight fanned-deck elevation on drag-over |
| 12 | **Insurance Policy Dossier** | `/platform/bimanyay`, BimaNyay standalone header | Bound policy booklet with magnifying glass over a highlighted statutory clause ribbon | Clause highlight sweep |
| 13 | **Healthcare Shield** | `/security`, BYOD privacy section | Layered ArogyaRakshak shield enveloping a transient RAM-wave icon with a dashed "discarded" arc | Shield contour draw + gentle fade |
| 14 | **Scanning Documents** | Landing Hero centerpiece (`HeroIllustration.tsx`), Kadi OCR processing | Translucent hospital bill over molecular grid with a crisp Muted Sage / Deep Forest scan beam revealing structured fields | Smooth vertical scan-beam sweep (`translateY`) |
| 15 | **Data Extraction** | `/how-it-works`, Kadi pipeline step 2–3 | Unstructured document lines flowing through a geometric prism into structured Entity Cards (Drug, Rate, Date) | Sequential node illumination |
| 16 | **Evidence Verification** | Evidence Explorer empty state, `/evidence-methodology` | Connected triad of Document Digest + Statutory Rule Book + Clinician Seal converging on a Verified badge | Edge draw connecting the 3 sources |

---

## 3. Theme-Tokenized SVG Authoring Rules

All SVGs MUST bind colours to CSS custom properties with Light-Mode fallbacks so they adapt cleanly to optional Dark Mode without duplicating files:

```xml
<path stroke="var(--svg-ink, #142F2B)" fill="var(--svg-wash, #D5E7D9)" />
```

- **Accessibility:** Decorative background illustrations MUST carry `aria-hidden="true"` and `focusable="false"`. Meaningful explanatory diagrams MUST carry `role="img"` + `<title>` + `aria-labelledby`.
- **Responsive Scaling:** Always specify `viewBox`, omit fixed `width`/`height` attributes (or size via CSS `aspect-ratio` + `max-width: 100%`), and simplify or hide dense background lattices below `640px` to preserve readability and battery life.
