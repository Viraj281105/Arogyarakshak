# ADR-022: Shared TypeScript code is vendored, not published or workspace-linked

## Status
Accepted (2026-11-06). Part of WS0 Foundation (`docs/superpowers/specs/2026-11-06-foundation-design.md`).

## Context
`apps/web` (Next.js) and `apps/mobile` (Expo) need the same design tokens, API client and
i18n catalogues. Constraints found in the repository:

- **Separate npm roots.** Each app has its own `package.json` and lockfile; there is no
  root workspace, and introducing one would change dependency hoisting for both apps.
- **Web Docker build context** is `apps/web` only, so anything outside that directory
  (for example a sibling `packages/*` TypeScript package) is invisible to the image build.
- **React version split.** Web and mobile pin different React versions; a linked package
  that declares React as a dependency would resolve a second copy and break hooks.

## Decision
1. Shared TypeScript source lives under `packages/<name>/src` and is **vendored**
   (copied) into each consuming app by `scripts/sync-shared.mjs` (`syncShared`).
2. Vendored `.ts` files carry a generated banner plus `/* eslint-disable */`; `.css` files
   carry a CSS comment banner. Vendored directories are committed so Docker builds and
   app-local tooling work unchanged.
3. A **staleness check** (`npm run check:generated`, which runs every `scripts/checks/*.mjs`)
   re-runs the sync in `check` mode and fails CI when a vendored copy differs from source.
   `npm run generate` runs every `scripts/generators/*.mjs`.
4. The root `package.json` holds scripts and dev tooling only: no `workspaces`.

## Consequences
- Generated directories are **never edited by hand**; change `packages/<name>/src`, run
  `npm run generate`, commit both.
- Drift is caught mechanically in CI rather than by convention.
- Cost: duplicated files in the repository and a small diff noise on every shared change.
- A future move to a real workspace or a published package remains possible; consumers
  import from one local path, so only the vendoring step would change.
