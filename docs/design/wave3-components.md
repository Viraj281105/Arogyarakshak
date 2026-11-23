# Wave 3 web foundation: tokens, evidence vocabulary, icons, primitives, routes

**Milestone:** M2 (web foundation), 2026-11-23. **Code:** `packages/design-tokens/`, `apps/web/app/components/ui/`,
`apps/web/app/shell/icons/`, `apps/web/app/shell/commands.ts`. **Gallery:** `/primitives` under `next dev` only
(`app/(dev)/primitives/page.dev.tsx`; not in production builds). Read with `wave3-ux-architecture.md` section 5.

## 1. Tokens (navy / teal rebrand)

`packages/design-tokens/tokens.json` is still the only source; `npm run generate` writes
`apps/web/app/generated/tokens.css` and `apps/mobile/src/generated/tokens.ts`. **Every pre-Wave-3 token name is kept**
(web and mobile consumers are unchanged); values changed.

| Role | Dark theme | Light theme | Note |
|---|---|---|---|
| Page / surface / elevated / secondary | `#101B2A` / `#15263A` / `#1C3048` / `#203650` | `#F5F7FA` / `#FFFFFF` / `#EBF0F5` / `#EEF2F6` | Dark is built on Midnight and Deep Navy, not an inversion of light |
| Border subtle / medium | `#263C52` (Slate Blue) / `#33506B` | `#E0E6ED` / `#CBD5E0` | |
| Text primary / secondary / muted | `#EEF2F6` / `#B4C2D1` / `#8FA1B5` | `#172433` / `#596879` / `#5E6D80` | The brief's `#657487` is 4.45:1 on `#F5F7FA`, so secondary text is darkened |
| Primary action fill / label | `#2BC0B4` / `#101B2A` | `#0B6B64` / `#FFFFFF` | `action-primary`, `text-on-action`; `.btn-primary` uses them |
| Focus ring, links | `#43C6D5` (Electric Cyan) | `#0B6B64` | Cyan is used only on dark surfaces |
| Clinical Teal `#13A89E` | fills, gradients, `brand-teal` | not used for text | 2.95:1 on white: fails AA for text and buttons |

New token names: `palette-*` (the brief's six colours verbatim, for reference), `action-primary(-hover)`,
`text-on-action`, `text-link`, `overlay-scrim`, `status-insufficient`, `chart-grid`, `chart-series-1..6`, and
`evidence-<state>-fg|bg|border` for the eight evidence states. Legacy names now map to the new palette, for example
`brand-forest` / `brand-emerald` → teal, `accent-gold` → cyan (dark) / `#1D6A85` (light), `brand-brass` → Soft Mint.

### Contrast (WCAG 2.x AA), checked in CI

`packages/design-tokens/contrast.mjs` lists every pair the UI draws; `tests/contrast.test.mjs` fails if any pair is
under 4.5:1 (text) or 3:1 (UI parts, chart marks) in either theme, or if a token is missing. 113 pairs per theme,
**0 failures** (2026-11-23). Lowest ratio per group:

| Group | Light | Dark |
|---|---|---|
| Text on page backgrounds (11 text tokens × 5 backgrounds) | 4.61 (`text-muted` on elevated) | 4.65 (`text-muted` on secondary) |
| Evidence label on its badge background | 5.04 (verified) | 6.08 (user-provided) |
| Evidence label on page | 5.35 | 6.98 |
| Primary button label (normal / hover) | 6.36 / 8.07 | 7.67 / 9.31 |
| Focus ring on page (3:1 needed) | 5.93 | 7.50 |
| Chart marks on surfaces (3:1 needed) | 3.59 (`chart-unmatched`) | 4.63 (`chart-unmatched`) |
| Text on the paper surface | 5.46 | 5.08 |

The test caught one failure while the palette was designed (light `chart-unmatched` `#8A97A8`, 2.77:1); it is now
`#74839A`. Not covered: translucent tokens (`bg-surface-glass`, tints, `accent-gold-soft`), which depend on what is
underneath, and the hand-written colours left in `globals.css` (section 6).

## 2. Evidence vocabulary

One badge, eight states, always with a text label and a distinct icon (`EVIDENCE_ICONS`), never colour alone.
Source: `apps/web/app/components/ui/evidence.ts`.

| State | Label | Meaning |
|---|---|---|
| `verified` | Verified | Checked against the cited source: every figure appears in it |
| `provisional` | Provisional | Source attributed, not every figure confirmed |
| `unevaluated` | Not evaluated | Not checked yet, or cannot be checked automatically |
| `insufficient-evidence` | Insufficient evidence | The source does not support the statement; no conclusion drawn |
| `ai-generated` | AI-generated | Written by a language model; a draft, not a finding |
| `rule-engine` | Rule engine | Computed by a deterministic rule from published reference data |
| `user-provided` | You provided | Entered or confirmed by the user; not independently checked |
| `external` | External source | Quoted from a public reference (CGHS, NPPA, IRDAI) |

**Wave 2 citation statuses** (`schemesetu.citations.verify_citation`) map through `evidenceFromCitation()`:

| Citation status | Evidence state | Why |
|---|---|---|
| `supported` | `verified` | Every figure was found in the cited span |
| `scheme_only` | `provisional` | The scheme is attributed but no figure was verified |
| `unsupported` | `insufficient-evidence` | The span does not support the sentence (the backend drops these) |
| `uncheckable` | `unevaluated` | The figure cannot be checked (words, unknown unit); never shown as verified |
| anything else | `unevaluated` | Unknown values are never promoted to verified |

Labels are English; Hindi and Marathi labels are not written yet (they need native-speaker review). Components take
a `label` override.

## 3. Icons (decision D3)

`lucide-react` 1.71.0 (pinned; published 2026-11-10). Each icon is imported from `lucide-react/icons/<name>`
(a test fails on a value import from the package barrel). Maps: `shell/icons/moduleIcons.ts` (Kadi documents,
BillNyay, DaaviSetu, BimaNyay, SchemeSetu, DawaCheck), `actionIcons.ts` (upload, add, delete, download, next,
search, close, command, home, workspace, reviewer, info, warning, error, success), `evidenceIcons.ts`. They are
separate files because one combined map put all 29 icons into the shell chunk (+3.9 KB instead of +1.86 KB).
`shell/nav.ts` no longer hand-codes SVG paths; the module tabs, the drawer and the landing module cards use
`MODULE_ICONS`. Other hand-drawn icons in landing and module components were left for their page milestones.

## 4. Primitives (`apps/web/app/components/ui`)

| Component | File | Server-safe | Notes |
|---|---|---|---|
| `EvidenceBadge`, `StatusBadge`, `ConfidenceIndicator`, `MetricCard` | `Badges.tsx` | yes | `MetricCard.basis` is required: "estimate" or "verified", shown in words; `source` required. Confidence needs `source` and shows %, a word and a `<meter>` |
| `PageHeader`, `Breadcrumbs` | `PageHeader.tsx` | yes | One `<h1>`; breadcrumb `aria-current="page"` |
| `LoadingState`, `EmptyState`, `ErrorState`, `PartialResultState`, `InsufficientEvidenceState` | `States.tsx` | yes | Partial requires `missing[]`; insufficient-evidence requires `reason` and says nothing is guessed |
| `BarChart`, `StackedBarChart`, `DonutChart`, `WaterfallChart`, `TimelineChart` | `Charts.tsx` | yes | `source`, `units`, `period` required and printed; optional `basis`; each renders a data table in a disclosure and a `role="img"` summary; labels are HTML so they stay readable at 360 px; the waterfall scrolls inside its card |
| `DataTable` | `DataTable.tsx` | client | Real `<table>` with caption; sortable headers are buttons with `aria-sort`; stable sort, nulls last; focusable scroll region |
| `Dialog`, `ConfirmationDialog`, `Drawer` | `Overlays.tsx` | client | Native `<dialog>` + `showModal()`: focus trap, Escape, focus return (checked in the browser). Confirmation states the consequence, names the action, focuses Cancel |
| `ToastProvider` / `useToast` | `Toast.tsx` | client | Polite and assertive live regions; pauses on hover/focus; errors stay until dismissed |
| `Tooltip`, `Tabs` | `Disclosure.tsx` | client | Tooltip opens on hover and focus, Escape closes; tabs use roving tabindex |
| `StepWizard`, `Checklist` | `Steps.tsx` | yes | Each step/item states its status in words |
| `CommandPalette` | `CommandPalette.tsx` + `shell/commands.ts` + `shell/CommandPaletteLauncher.tsx` | client | Ctrl/Cmd+K; combobox + listbox; lists **only existing routes** (`/`, `/app`, `/app#intake-dropzone`, `/app#module-workspace`, five `/app#module-<id>`, `/review`) in the UI language; no data search. Loaded on first use |

Styles: `components/ui/ui.css` (tokens only). Motion is CSS on the motion tokens and only inside
`@media (prefers-reduced-motion: no-preference)` (a test enforces this). No new library besides `lucide-react`.
Palette chrome strings ("Go to a page…") are English only for now.

## 5. Routes

| Route | What | Change |
|---|---|---|
| `/` | Landing (server-rendered sections + client `LandingPage`) | Workspace removed; module cards link to `/app#module-<id>`, hero CTA to `/app#intake-dropzone` |
| `/app` | Case workspace (`HomeWorkspace`: upload, case desk, module tabs) | New path, same behaviour; static page header |
| `/review` | Clinical reviewer workspace | Moved from `/clinical-review`; `next.config.ts` redirects `/clinical-review` and `/clinical-review/*` with 308, query kept |
| `/primitives`, `/motion-lab` | Dev galleries | `next dev` only |

No placeholder routes were added for pages the plan has not built.

## 6. Known gaps

- `globals.css` still has about 90 hand-written colour literals. The forest/brass/sage ones were mapped to the new
  palette mechanically; their contrast is not in the token test. Page milestones (M3 to M5) should replace them
  with tokens.
- Mobile `Button` draws white text on `brandCyan`; in the dark theme that is about 2:1 (it was about 3:1 before).
  No single colour can be both AA text on navy and an AA fill under white text; the mobile stream should use
  `actionPrimary` / `textOnAction` for filled buttons.
- Evidence and palette labels need Hindi and Marathi versions (native-speaker review).
