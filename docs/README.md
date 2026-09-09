# ArogyaRakshak Documentation Portal

Welcome to the official technical documentation for **ArogyaRakshak (आरोग्यरक्षक)**. This documentation provides comprehensive architectural specifications, developer manuals, operational guides, and decision records for both human contributors and AI coding agents.

---

## Documentation Navigation

```text
docs/
├── README.md                          # This documentation portal & sitemap
├── ArogyaRakshak_Task_Backlog.md      # Phased engineering issue backlog & tracking
│
├── architecture/                      # System design and specifications
│   ├── overview.md                    # Platform architecture, stack & principles
│   ├── components.md                  # Deep dive into all 5 modules & Kadi layer
│   ├── data-flow.md                   # End-to-end data pipelines & SSE streaming
│   ├── bimanyay-and-mobile.md         # BimaNyay post-denial & mobile app blueprint
│   ├── repository-structure.md        # Monorepo restructuring migration record
│   ├── diagrams/                      # System architecture & data flow diagrams
│   │   ├── Application Services Diagram.jpeg
│   │   ├── Architecture Diagram.jpeg
│   │   └── Kadi-Shared AI Intelligence layer Diagram.jpeg
│   └── decisions/                     # Architecture Decision Records (ADRs)
│       ├── ADR-001-monorepo-structure.md
│       ├── ADR-002-kadi-shared-intelligence-layer.md
│       ├── ADR-003-bring-your-own-document-privacy.md
│       ├── ADR-004-groq-model-selection.md
│       └── ADR-005-bimanyay-and-daavisetu-lifecycle-division.md
│
├── api/                               # Backend REST & streaming documentation
│   └── overview.md                    # Versioned API routes & SSE protocol
│
├── configuration/                     # Environment and secrets management
│   └── environment-variables.md       # Full environment variable reference
│
├── development/                       # Developer experience & operations
│   ├── setup.md                       # Local environment & multi-client setup
│   ├── workflow.md                    # Git flow, conventions, and review standards
│   ├── testing.md                     # Pytest, mobile tests, and evaluation suites
│   └── troubleshooting.md             # Common errors, diagnosis & remedies
│
├── planning/                          # Project management & team strategy
│   ├── team-division-strategy.md      # 5-member role allocation framework
│   ├── weekly-sprint-playbook.md      # Weekend-by-weekend agile delivery plan
│   └── futuristic-scope.md            # Mark-85 high-concept R&D roadmap
│
└── academic/                          # SPPU Final Year Project & research collateral
    ├── README.md                      # Academic portfolio index & rubric mapping
    ├── presentations/                 # Seminar, progress & defense slides
    ├── viva-and-defense/              # Oral viva Q&A, challenges & metrics
    ├── research-and-literature/       # Literature review, datasets, contribution notes & papers
    └── reports/                       # Formal technical documentation & report PDFs
```

---

## Quick Reference Links

| Category | Primary Reference | Target Audience |
|---|---|---|
| **Architecture** | [Architecture Overview](architecture/overview.md) | All engineers & AI agents |
| **Modules & Components** | [Component Specifications](architecture/components.md) | Module developers |
| **Data Pipelines** | [Data Flow & SSE Streaming](architecture/data-flow.md) | Pipeline & frontend engineers |
| **BimaNyay & Mobile** | [BimaNyay & Mobile Blueprint](architecture/bimanyay-and-mobile.md) | Insurance & mobile engineers |
| **Architecture Diagrams** | [System Diagrams](architecture/diagrams/) | Architects & reviewers |
| **Architectural Decisions** | [Architecture Decisions (ADRs)](architecture/decisions/ADR-001-monorepo-structure.md) | System architects & reviewers |
| **Local Setup** | [Developer Setup Guide](development/setup.md) | New contributors |
| **Testing Strategy** | [Testing Guide](development/testing.md) | QA & automation engineers |
| **Troubleshooting** | [Troubleshooting & Failure Modes](development/troubleshooting.md) | DevOps & developers |
| **Configuration** | [Environment Variables](configuration/environment-variables.md) | Deployment & infra engineers |
| **API Endpoints** | [API Gateway Reference](api/overview.md) | Frontend & mobile developers |
| **Team Strategy** | [Team Division Strategy](planning/team-division-strategy.md) | Team leads & contributors |
| **Sprint Playbook** | [Weekly Sprint Playbook](planning/weekly-sprint-playbook.md) | Scrum masters & contributors |
| **Academic Portfolio** | [Academic & Research Index](academic/README.md) | Project guides, evaluators & viva candidates |
| **Project Backlog** | [Task Backlog](ArogyaRakshak_Task_Backlog.md) | Project managers & team leads |

---

## Ground Rules for AI Coding Agents

If you are an AI coding agent operating in this repository, you must read and adhere strictly to the root [AGENTS.md](../AGENTS.md).
