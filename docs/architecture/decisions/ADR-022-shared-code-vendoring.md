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

## Scope and rulings made while implementing WS0
- **Vendored, not installed.** The spec called the shared pieces "packages" installed as dependencies; the decision above replaces that. `packages/design-tokens`, `packages/api-client` and `packages/i18n` are source packages that are copied into `apps/web/app/{generated,shared}` and `apps/mobile/src/{generated,shared}`.
- **Governance guardrail.** `scripts/ci_guardrails.py` (`check_package_hygiene`) requires `pyproject.toml` or `setup.py` in every `packages/*` directory except the explicit `TS_SOURCE_PACKAGES` set (`design-tokens`, `api-client`, `i18n`), which are vendored TypeScript sources with no Python packaging; lowercase naming and the required domain packages are still checked for them. Covered by tests in `apps/api/tests/test_docker_binding.py`.
- **This is the only ADR WS0 adds.** The spec also named ADRs for self-hosted telemetry and for a job queue that supersedes ADR-019; they are written in WS1 and WS3 when those decisions are implemented.
- **Adoption of the shared API client is partial.** It is the transport of the mobile client (`apps/mobile/src/api/client.ts`) and of the web `fetchDemoStatus`. Other web endpoints migrate page by page in WS4 and mobile screens in WS5.
- **Types come from the existing contract.** The client's `schema.d.ts` is generated with `openapi-typescript` from the committed `docs/api/openapi.json` (kept current by `scripts/export_openapi.py` and `apps/api/tests/test_openapi_contract.py`); no second OpenAPI export was added.
- **Fonts were not dropped.** All four families (Fraunces, Plus Jakarta Sans, Inter, JetBrains Mono) are used today, so the spec's "drop unused fonts" waits for the page redesigns. They are now self-hosted.
- **Budgets.** The web 170 KB initial-JS budget is enforced as a ratchet because every route was already over it (see `docs/development/performance-budgets.md`). The Lighthouse step lives in `web-ci` and runs on Node 22 (its own `setup-node` step) because `@lhci/cli` needs Node 22.19 or newer; `foundation-checks` (tooling tests and the freshness check) stays on Node 20 on purpose, as that is what proves the repo scripts are Node 20 compatible. The mobile bundle budget is in `mobile-ci`.
