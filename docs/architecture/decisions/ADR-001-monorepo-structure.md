# ADR-001: Adoption of Monorepo Architecture

## Status
Accepted

## Context
ArogyaRakshak consists of multiple interconnected domain modules (`billnyay`, `daavisetu`, `bimanyay`, `schemesetu`, `dawacheck`), shared core intelligence infrastructure (`kadi`), a FastAPI backend (`apps/api`), and Next.js/mobile clients. We needed to choose between a multi-repository approach (separate repo per module) vs. a unified monorepo.

## Problem
In a multi-repository model, managing cross-package dependencies between Kadi and the domain modules requires constant package publishing, version pinning, and synchronization across 7+ repositories. For an engineering team of five on an SPPU project timeline, multi-repo overhead would cause severe integration friction.

## Decision
We adopted a **modular monorepo structure**:
- `apps/`: Application frontends and API gateways.
- `packages/`: Python domain libraries registered locally as editable packages (`pip install -e`).
- `docker-compose.yml`: Central container orchestration wiring Postgres, backend, and web clients.

## Consequences
### Positive
- Single source of truth for all schemas, tests, and configurations.
- Atomic cross-module PRs and continuous integration (`ci.yml`).
- Zero package publishing friction: changes in `packages/kadi` are immediately available in `apps/api` without rebuilding or reinstalling wheels.
### Negative
- Monorepo tooling and Docker build contexts must be managed carefully so containers only copy necessary dependencies.
