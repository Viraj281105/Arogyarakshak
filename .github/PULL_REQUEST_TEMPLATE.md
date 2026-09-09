## Description
<!-- Provide a brief, meaningful summary of the changes made and the problem being resolved. -->

## Related Issue / Backlog Item
<!-- Link the related issue or backlog task, e.g., Closes #12 or Ref Phase 2 Backlog -->
Closes: 

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature that alters existing API contracts or DB schemas)
- [ ] Architecture / Refactoring (structural change without behavioral regression)
- [ ] Documentation update

## Affected Modules
- [ ] `packages/kadi` (Shared Context & Intelligence)
- [ ] `packages/billnyay` (Hospital Bill Audit)
- [ ] `packages/daavisetu` (Claim Form Automation)
- [ ] `packages/bimanyay` (Denial Appeal & Grievance Tracking)
- [ ] `packages/schemesetu` (Scheme Eligibility)
- [ ] `packages/dawacheck` (Medicine Pricing)
- [ ] `apps/api` (FastAPI Gateway)
- [ ] `apps/web` (Next.js Frontend)
- [ ] `apps/mobile` (Mobile App)
- [ ] Infrastructure / CI / Docker

## Architectural & Privacy Verification
- [ ] **BYOD Compliance**: Confirmed that uploaded patient documents are NEVER persistently stored beyond the active case session.
- [ ] **Model Grounding**: Does NOT invoke deprecated Groq models (`llama3-70b` or `llama-3.3-70b-versatile`). Uses `GROQ_MODEL` env var (default: `openai/gpt-oss-120b`).
- [ ] **Naming Conventions**: Pure lowercase module names, `kadi_`, `billnyay_`, `daavisetu_`, `bimanyay_`, `schemesetu_`, `dawacheck_` DB prefixes, and `/api/<module>/...` routes.
- [ ] **Shared Layer**: Cross-module entity extraction and resolution are routed through `packages/kadi`, not duplicated inside modules.

## Testing & Validation Performed
- [ ] Backend tests run and passing (`python -m pytest apps/api packages/`)
- [ ] Frontend linting clean (`npm run lint` inside `apps/web`)
- [ ] Manual endpoint or browser verification executed (e.g. `curl http://localhost:8000/health`)
- [ ] Documentation updated to reflect changes

## Screenshots / CLI Output (if applicable)
<!-- Attach screenshots or terminal command outputs demonstrating verification -->
