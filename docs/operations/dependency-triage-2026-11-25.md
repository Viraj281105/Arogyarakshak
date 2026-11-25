# Dependency alert triage, 2026-11-25

Branch `security/dependency-triage`, from `main` at `d67883f`.

## Starting point

68 open Dependabot alerts (2 critical, 39 high, 21 moderate, 6 low): 66 in
`apps/mobile/package-lock.json`, 1 in `apps/web`, 1 in the root tooling. None for Python.
`npm audit` also reported findings Dependabot had not listed (`zod` in web, more `basic-ftp`
advisories in the root).

## Does any of it ship to users?

For the mobile app, **none of the flagged packages is in the app**. The source maps of the exported
Android and web bundles were checked for all eleven (`tar`, `shell-quote`, `node-forge`,
`@xmldom/xmldom`, `brace-expansion`, `undici`, `image-size`, `compression`, `minimatch`, `glob`,
`uuid`): no match. They belong to the Expo and React Native build tooling, so the exposure is to a
developer machine or CI runner, including the development server, which listens on the local
network. The exported Android bundle file name (a content hash) was the same before and after the
upgrades.

The root and web findings are in development tools (`@lhci/cli`, ESLint).

## Fixed

| Package | From → to | Where |
|---|---|---|
| `shell-quote` (critical) | 1.10.0 → 1.12.0 | mobile |
| `node-forge` | 1.4.0 → 1.4.4 | mobile |
| `@xmldom/xmldom` | 0.7.13 → 0.8.15, by an override for `@expo/plist` | mobile |
| `brace-expansion` | 1.1.18 → 1.1.22, 2.1.4 → 2.1.8 | mobile |
| `undici` | 6.28.1 → 6.29.1 | mobile |
| `compression` | 1.8.1 → 1.8.2 | mobile |
| `basic-ftp` and its proxy chain | 5.3.1 → 6.2.6 | root |
| `typescript-eslint` family (brings `minimatch` 11) | 8.70.0 → 8.74.0 | web |
| `zod` | 4.6.2 → 4.6.7 | web |

`npm audit` afterwards: root 0, web 0, mobile 17 advisories. Expected Dependabot result once this is
on `main`: 51 alerts close and 17 remain (not yet observed).

Notes: `node-forge` 1.4.4 was two days old when adopted. `minimatch` 11 adds one new package,
`@isaacs/nonrecursive-glob-match`, from the same maintainer, with no install script. `quickjs-wasi`
moved a major version inside the root proxy chain.

## Still open (17, all mobile build tooling)

| Package | Advisories | Why it is not fixed | Exposure |
|---|---|---|---|
| `tar` 6.2.1 | 12, including 1 critical | Fixed only in 7.x. `@expo/cli` 0.22 calls `require('tar').default.extract`; 7.x has no default export (checked with 7.5.23), so forcing it breaks template extraction | Unpacking an untrusted archive during development |
| `image-size` 1.2.1 | 2 high | Fixed only in 2.x; Metro requires `^1` and the interface changed | A malicious image among project assets can hang the bundler |
| `glob`, `minimatch`, `uuid` | 1 each, moderate | Fixes need new major versions inside Expo's tree | Build-time denial of service; `uuid` needs a caller-supplied buffer |

The only upgrade `npm audit` offers for these is **Expo SDK 52 → 58**, a major migration that needs
its own plan and a device test. Until then: do not unpack or bundle files from untrusted sources,
and run `expo start` only on a trusted network.

## Open pull requests (reviewed 2026-11-25)

| PR | What | Recommendation |
|---|---|---|
| 177 | Dependabot npm group | **Do not merge.** Moves `react-native` 0.76.7 → 0.88.1, outside Expo SDK 52 (mobile CI fails on it; see PROJECT_CONTEXT, known issue 3). Its safe updates are here. Close |
| 171 | `undici` 6.29.1 | Included here. Close |
| 175, 166 | `setup-node` 4 → 7, `setup-python` 5 → 7 | Keep; checks passed. Merge one at a time |
| 174, 172 | `gitleaks-action` 2 → 3, `trivy-action` pin | Keep; checks passed |
| 173 | `docker/login-action` 3 → 4 | Keep, but its workflow runs only on release tags, so passing checks did not exercise it |
| 150 | NPPA 2025 data (contributor) | Maintainer and author decide. 226 commits behind, conflicts, failing backend tests. The data is useful; it needs reapplying on current `reference_data.py`, whose entries now carry a unit form |
| 145 | Prescription OCR (contributor) | Maintainer and author decide. 226 commits behind, conflicts, failing tests, and it adds scratch files and a zip. Recommend closing and reopening as a clean change |

## Checks after the upgrades

Clean `npm ci` in all three places, then: mobile type-check, tests 226/226, Android export within
budget, `expo config --type introspect`, a development-server bundle request, and a script that
exercised plist parsing, code signing, certificate generation, `shell-quote`, brace globs and
compression with `undici`; web lint, type-check, tests 343/343, build and bundle budget; root tests
79/79, generated-file check, `lhci --version` and a load of its proxy chain; infrastructure policy
tests 236/236.

Not checked: `expo prebuild`, a device or emulator run, a Lighthouse CI run, GitHub CI.
