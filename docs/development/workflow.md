# Developer Workflow & Git Standards

This document establishes the collaboration guidelines, Git branching strategy, commit conventions, and review requirements for **ArogyaRakshak**.

---

## 1. Branch Strategy

We follow a feature-branch workflow rooted on `main`:

| Branch Prefix | Purpose | Example |
|---|---|---|
| `feature/` | New features or agent capabilities | `feature/bimanyay-appeal-drafter` |
| `fix/` | Bug fixes and data corrections | `fix/nppa-ceiling-price-rounding` |
| `docs/` | Documentation, specs, and ADR updates | `docs/update-architecture-overview` |
| `refactor/` | Code structure improvements without behavior change | `refactor/kadi-vector-store` |
| `test/` | Adding test suites or evaluation benchmarks | `test/add-cghs-procedure-eval` |

---

## 2. Commit Message Standards

Commits must follow the **Conventional Commits** specification:

```text
<type>(<scope>): <short summary>

[optional detailed body explaining WHY, not just WHAT]

[optional issue reference: Closes #123]
```

### Allowed Types
- `feat`: New feature or user capability.
- `fix`: Bug fix.
- `docs`: Documentation changes only.
- `refactor`: Code refactoring without behavioral impact.
- `test`: Adding or modifying tests.
- `chore`: Build tooling, dependency bumps, CI changes.

### Examples
- `feat(bimanyay): implement 5-year moratorium rule validation`
- `fix(billnyay): correct tier-2 city rate coefficient in CGHS benchmark`
- `docs(api): document SSE streaming reconnection protocol`

---

## 3. Contributor Lifecycle (Step-by-Step)

```text
1. Pick Issue from Task Backlog (docs/ArogyaRakshak_Task_Backlog.md)
   ↓
2. Create Branch: git checkout -b feature/<module>-<name>
   ↓
3. Implement Changes adhering to architectural boundaries
   ↓
4. Run Validation:
   - python -m pytest apps/api/
   - python -m pytest packages/
   - cd apps/web && npm run lint
   ↓
5. Commit with Conventional Commit message
   ↓
6. Push Branch & Open PR using .github/PULL_REQUEST_TEMPLATE.md
   ↓
7. Pass CI Checks (ci.yml) & Code Review
   ↓
8. Squash and Merge into main
```

---

## 4. Code Review Checklist

Reviewers verify every PR against these criteria:
- **BYOD Compliance**: Does this change introduce persistent file storage of patient documents? (Must be strictly NO).
- **Model Grounding**: Does this change call deprecated Groq models? (Must be strictly NO; reads from `GROQ_MODEL`).
- **Module Independence**: Are domain rules kept inside their respective packages rather than duplicated inside Kadi or API routes?
- **Public Provenance**: If government data was modified, is the authentic public source document cited?
- **Test Coverage**: Are new functions accompanied by unit tests in `packages/<module>/tests/`?
