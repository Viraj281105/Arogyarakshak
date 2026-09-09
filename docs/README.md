# ArogyaRakshak Documentation Portal

Welcome to the official technical documentation for **ArogyaRakshak (आरोग्यरक्षक)**. This documentation provides comprehensive architectural specifications, developer manuals, operational guides, and decision records for both human contributors and AI coding agents.

---

## Documentation Navigation

```text
docs/
├── README.md                          # This documentation portal & sitemap
├── architecture/                      # System design and specifications
│   ├── overview.md                    # Platform architecture, stack & principles
│   ├── repository-structure.md        # Monorepo restructuring migration record
│   ├── components.md                  # Deep dive into each module & Kadi layer
│   ├── data-flow.md                   # End-to-end data pipelines & SSE streaming
│   └── decisions/                     # Architecture Decision Records (ADRs)
│       ├── ADR-001-monorepo-structure.md
│       ├── ADR-002-kadi-shared-intelligence-layer.md
│       ├── ADR-003-bring-your-own-document-privacy.md
│       ├── ADR-004-groq-model-selection.md
│       └── ADR-005-bimanyay-and-daavisetu-lifecycle-division.md
├── development/                       # Developer experience & operations
│   ├── setup.md                       # Local environment & dependency setup
│   ├── workflow.md                    # Git flow, conventions, and review standards
│   ├── testing.md                     # Pytest, integration, and evaluation suites
│   └── troubleshooting.md             # Common errors, diagnosis & remedies
├── configuration/                     # Environment and secrets management
│   └── environment-variables.md       # Full environment variable reference
├── api/                               # Backend REST & streaming documentation
│   └── overview.md                    # Versioned API routes & SSE protocol
├── ArogyaRakshak_Task_Backlog.md      # Phased issue backlog & progress tracking
└── BimaNyay_and_Mobile_Architecture.md# BimaNyay & mobile app technical spec
```

---

## Quick Reference Links

| Category | Primary Reference | Target Audience |
|---|---|---|
| **Architecture** | [Architecture Overview](architecture/overview.md) | All engineers & AI agents |
| **Modules & Components** | [Component Specifications](architecture/components.md) | Module developers |
| **Data Pipelines** | [Data Flow & SSE Streaming](architecture/data-flow.md) | Pipeline & frontend engineers |
| **Architectural Decisions** | [Architecture Decisions (ADRs)](architecture/decisions/ADR-001-monorepo-structure.md) | System architects & reviewers |
| **Local Setup** | [Developer Setup Guide](development/setup.md) | New contributors |
| **Testing Strategy** | [Testing Guide](development/testing.md) | QA & automation engineers |
| **Troubleshooting** | [Troubleshooting & Failure Modes](development/troubleshooting.md) | DevOps & developers |
| **Configuration** | [Environment Variables](configuration/environment-variables.md) | Deployment & infra engineers |
| **API Endpoints** | [API Gateway Reference](api/overview.md) | Frontend & mobile developers |
| **BimaNyay & Mobile** | [BimaNyay & Mobile Spec](BimaNyay_and_Mobile_Architecture.md) | Insurance & mobile engineers |
| **Project Backlog** | [Task Backlog](ArogyaRakshak_Task_Backlog.md) | Project managers & team leads |

---

## Ground Rules for AI Coding Agents

If you are an AI coding agent operating in this repository, you must read and adhere strictly to the root [AGENTS.md](../AGENTS.md).
