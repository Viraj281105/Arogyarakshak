# Scoped Agent Instructions: GitHub Workflows & Automation (`.github/`)

This directory contains GitHub Actions workflows, issue templates, PR templates, and repository governance configurations.

## Critical Rules for AI Agents Modifying `.github/`

1. **Workflow Safety**:
   - Never add secrets or hardcoded tokens directly to any workflow file. Always use `${{ secrets.NAME }}`.
   - Do not invoke external webhooks, telemetry, or endpoints outside standard GitHub runners, Postgres service containers, and official registries (PyPI, npm).
2. **CI Pipeline Integrity (`ci.yml`)**:
   - The CI service requires `pgvector/pgvector:pg16` for native vector search testing.
   - Any new package added to `packages/` must be installed in editable mode (`pip install -e packages/<new_package>`) in `.github/workflows/ci.yml`.
   - The default model environment variable in CI is `GROQ_MODEL=openai/gpt-oss-120b`.
3. **Template Preservation**:
   - PR and Issue templates enforce Bring-Your-Own-Document (BYOD) compliance and model grounding checks. Do not remove these checkboxes.
