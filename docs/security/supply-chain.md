# Supply-chain and dependency security

Workflow: `.github/workflows/security.yml` (pull requests, pushes to `main`, weekly).

## Policy

| Check | Tool | Blocking? | Rationale |
|---|---|---|---|
| Committed secrets | gitleaks (full history) | **Yes** | A leaked key must be rotated, not merged. `scripts/ci_guardrails.py` also blocks Groq-style keys in the CI job. |
| API Python dependencies | pip-audit on `apps/api/requirements.txt` | **Yes, any known vulnerability** | Was clean after the 2026-10-19 upgrade, so a new advisory is a real change. |
| Web production dependencies | `npm audit --omit=dev --audit-level=high` | **Yes, high/critical** | Same. |
| Mobile dependencies | `npm audit --omit=dev` | Report only | 56 known advisories (2 critical) on 2026-10-19, accepted until the Expo SDK upgrade (`PROJECT_CONTEXT.md`, known risks). |
| API image | Trivy (HIGH/CRITICAL, fixed only) + CycloneDX SBOM artifact | Report only | Base-image CVEs often have no fix; review the artifact each run. |

Not yet in place: SAST (Semgrep), image signing/provenance attestations, pinning GitHub
Actions by commit SHA. Actions are pinned by major version tag today.

Network note: Trivy downloads its vulnerability database from GitHub Container Registry and
gitleaks/Trivy actions come from GitHub — outside the project's usual "Groq + Postgres +
package registries" boundary, CI-only.

## Remediation

1. A blocking finding fails the PR. Upgrade to the fixed version, run the full test suite,
   regenerate `docs/api/openapi.json` if the framework changed it, and review the diff.
2. If no fix exists or the upgrade is unsafe, record an exception in this file (advisory id,
   affected path, why it is not exploitable here or the compensating control, review date) and
   use the tool's ignore mechanism for that id only.

## History

- 2026-10-19: FastAPI 0.115.12 → 0.148.0 with Starlette 0.46.2 → 1.9.0 (pinned explicitly;
  form-parsing DoS PYSEC-2026-249 / -1941 affected the upload routes, plus Host/path URL
  reconstruction and Range-header advisories), python-multipart 0.0.12 → 0.0.32 (7 advisories).
  Next.js 16.3.4 → 16.4.2 (critical `next/og` RCE and cache-poisoning advisories) and
  transitive `sharp` / `source-map-js`. pip-audit and `npm audit --omit=dev` (web) both clean
  afterwards. Full backend suite, web lint/typecheck/tests/build re-run green.
