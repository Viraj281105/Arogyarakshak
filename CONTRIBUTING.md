# Contributing to ArogyaRakshak

Thank you for your interest in contributing to **ArogyaRakshak**.

ArogyaRakshak is a healthcare intelligence and hospital resource-management platform designed to help healthcare organizations move from **reactive crisis management to proactive preparedness**. The system combines historical healthcare data, weather conditions, festival calendars, environmental signals, and AI-powered analysis to anticipate patient surges and recommend operational actions.

The project brings together a web dashboard, predictive services, AI agents, real-time communication, healthcare resource optimization, and multilingual patient advisories.

Because this is a healthcare-focused project, contributions must prioritize **correctness, reliability, security, privacy, explainability, and responsible use of AI** over simply adding more features.

---

## Table of Contents

* [Code of Conduct](#code-of-conduct)
* [Project Philosophy](#project-philosophy)
* [Ways to Contribute](#ways-to-contribute)
* [Before You Start](#before-you-start)
* [Development Environment](#development-environment)
* [Getting the Repository](#getting-the-repository)
* [Project Architecture](#project-architecture)
* [Repository Structure](#repository-structure)
* [Setting Up the Backend](#setting-up-the-backend)
* [Setting Up the Frontend](#setting-up-the-frontend)
* [Database Development](#database-development)
* [Environment Variables](#environment-variables)
* [Working With AI Features](#working-with-ai-features)
* [Working With External APIs](#working-with-external-apis)
* [Real-Time Features](#real-time-features)
* [Branching Strategy](#branching-strategy)
* [Commit Guidelines](#commit-guidelines)
* [Coding Standards](#coding-standards)
* [Frontend Guidelines](#frontend-guidelines)
* [Backend Guidelines](#backend-guidelines)
* [Database Guidelines](#database-guidelines)
* [AI and Prediction Guidelines](#ai-and-prediction-guidelines)
* [Healthcare Data and Privacy](#healthcare-data-and-privacy)
* [Testing Requirements](#testing-requirements)
* [Documentation Guidelines](#documentation-guidelines)
* [Issue Guidelines](#issue-guidelines)
* [Pull Request Guidelines](#pull-request-guidelines)
* [Review Process](#review-process)
* [Security](#security)
* [Performance Guidelines](#performance-guidelines)
* [What Not to Commit](#what-not-to-commit)
* [Common Contribution Patterns](#common-contribution-patterns)
* [Definition of Done](#definition-of-done)
* [Getting Help](#getting-help)
* [License](#license)

---

# Code of Conduct

All contributors are expected to interact professionally and respectfully.

We welcome contributors regardless of experience level. Good-faith questions, constructive criticism, alternative technical approaches, and requests for clarification are encouraged.

Contributors should:

* Be respectful and professional.
* Assume good intent.
* Give constructive feedback.
* Focus criticism on implementations rather than individuals.
* Avoid discriminatory, abusive, or harassing behavior.
* Respect project maintainers and reviewers.
* Protect sensitive healthcare and user information.
* Clearly communicate uncertainty when working with AI or predictive systems.

Maintainers reserve the right to reject contributions that compromise the project's technical, ethical, security, or healthcare-related standards.

---

# Project Philosophy

ArogyaRakshak is not just another dashboard application.

The platform operates in a domain where incorrect information can potentially influence real-world healthcare decisions. Consequently, engineering decisions should follow these principles:

### 1. Correctness over convenience

A contribution that is slightly slower but substantially more reliable is preferable to a fast implementation that produces questionable results.

### 2. Explainability over black-box behavior

AI-generated recommendations should be understandable to the people responsible for acting on them.

### 3. Human oversight

ArogyaRakshak provides intelligence and recommendations. It should not be designed under the assumption that an AI system can independently replace qualified healthcare professionals or hospital administrators.

### 4. Privacy by design

Healthcare-related data should be treated as sensitive by default.

### 5. Fail safely

External APIs can fail. Models can fail. Networks can fail. Databases can fail.

The application should degrade gracefully rather than silently producing misleading information.

### 6. Reproducibility

Predictions, analytics, and data-processing pipelines should be reproducible whenever practical.

---

# Ways to Contribute

There are many ways to contribute beyond writing code.

## Code

You can contribute:

* Frontend features
* Backend APIs
* Database improvements
* Prediction models
* AI agents
* Resource optimization algorithms
* Real-time functionality
* Authentication and authorization
* Performance improvements
* Accessibility improvements
* Testing infrastructure
* Developer tooling

## Data

Contributions can include:

* Data preprocessing pipelines
* Dataset validation
* Data quality checks
* Feature engineering
* Historical healthcare datasets
* Weather and environmental data integrations
* Festival/event datasets
* Data normalization

Never contribute real patient-identifiable information.

## Documentation

Documentation contributions are highly valuable.

Examples:

* API documentation
* Setup guides
* Architecture documentation
* Developer guides
* Deployment documentation
* Troubleshooting guides
* AI model documentation
* Data dictionaries

## Design

You can contribute:

* Dashboard UX
* Accessibility improvements
* Information architecture
* Data visualization
* Responsive layouts
* Mobile UX
* Design-system components

## Testing

Testing contributions are especially welcome.

Examples:

* Unit tests
* Integration tests
* API tests
* End-to-end tests
* Prediction validation
* Regression tests
* Security testing
* Performance testing

## Issues and Ideas

You can also contribute by:

* Reporting bugs
* Identifying edge cases
* Suggesting improvements
* Reviewing existing issues
* Testing proposed features
* Reviewing pull requests

---

# Before You Start

Before implementing a new feature:

1. Search existing issues and pull requests.
2. Check whether the feature already exists.
3. Check whether someone is already working on it.
4. Read the relevant documentation.
5. Understand the affected architecture.
6. For major changes, open an issue or discussion before implementation.

For small bug fixes, a pull request can generally be opened directly.

For large architectural changes, discuss the approach first.

---

# Development Environment

ArogyaRakshak consists of multiple services.

At a high level, development may involve:

* **Frontend:** React + TypeScript
* **Backend:** FastAPI / Python
* **Database:** MySQL
* **Real-time communication:** Socket.IO
* **AI:** Gemini API
* **External data:** Weather and other data services
* **Containerization:** Docker

The exact versions should always be taken from the project's lockfiles, dependency manifests, Docker configuration, or CI configuration rather than assumed from this document.

Recommended development tools include:

* Git
* Node.js
* npm / compatible package manager
* Python
* pip or the project's Python dependency manager
* MySQL
* Docker
* Docker Compose
* A code editor such as VS Code

---

# Getting the Repository

Fork the repository on GitHub and clone your fork:

```bash
git clone https://github.com/<your-username>/<repository>.git
cd <repository>
```

Add the upstream repository:

```bash
git remote add upstream https://github.com/<organization>/<repository>.git
```

Verify:

```bash
git remote -v
```

You should have:

* `origin` → your fork
* `upstream` → the main project repository

---

# Keeping Your Fork Updated

Before starting new work:

```bash
git fetch upstream
git checkout main
git pull upstream main
git push origin main
```

Then create a feature branch.

Do not develop directly on `main`.

---

# Project Architecture

At a conceptual level, ArogyaRakshak can be viewed as the following pipeline:

```text
                    ┌──────────────────────┐
                    │ External Data Sources│
                    │                      │
                    │ Weather               │
                    │ Festivals             │
                    │ Historical Data       │
                    │ Environmental Data    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Data Processing Layer│
                    │                      │
                    │ Validation            │
                    │ Normalization         │
                    │ Feature Engineering   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Prediction / AI Layer │
                    │                      │
                    │ Forecasting           │
                    │ AI Agents             │
                    │ Risk Analysis         │
                    └──────────┬───────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌────────────┐ ┌──────────────┐ ┌─────────────┐
        │ Resource   │ │ Alerts &      │ │ Analytics   │
        │ Optimizer  │ │ Advisories   │ │             │
        └─────┬──────┘ └──────┬───────┘ └──────┬──────┘
              │               │                │
              └───────────────┼────────────────┘
                              ▼
                    ┌──────────────────────┐
                    │ FastAPI Backend      │
                    │ REST + Socket.IO     │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ React + TypeScript UI │
                    │ Hospital Dashboard    │
                    └──────────────────────┘
```

Contributors should understand which layer their change belongs to before implementing it.

Avoid putting business logic directly into UI components or API handlers when it belongs in a dedicated service.

---

# Repository Structure

The exact structure may evolve, but the preferred conceptual separation is:

```text
.
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   └── utils/
│   └── ...
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── agents/
│   │   ├── database/
│   │   └── utils/
│   ├── tests/
│   └── ...
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── ...
│
├── docs/
│   ├── architecture/
│   ├── api/
│   └── ...
│
├── docker/
├── scripts/
├── .github/
└── README.md
```

Do not create new top-level directories without a clear architectural reason.

---

# Setting Up the Backend

Navigate to the backend:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it.

### Windows

```bash
.venv\Scripts\activate
```

### Linux/macOS

```bash
source .venv/bin/activate
```

Install dependencies using the project's dependency manifest:

```bash
pip install -r requirements.txt
```

Start the development server using the command defined by the project.

A typical FastAPI development command is:

```bash
uvicorn app.main:app --reload
```

Do not assume this command is correct if the repository uses a different application entry point.

---

# Setting Up the Frontend

Navigate to the frontend:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

Before opening a pull request, also run the project's available:

```bash
npm run lint
npm run test
npm run build
```

Only run commands that actually exist in the project's `package.json`.

---

# Database Development

ArogyaRakshak uses MySQL for persistent application data.

Contributors modifying database behavior must consider:

* Schema compatibility
* Existing production data
* Migration safety
* Indexing
* Query performance
* Referential integrity
* Data validation
* Backward compatibility

## Database Changes

Do not manually modify the database schema and leave the change undocumented.

Schema changes should be represented through the project's migration mechanism.

A database migration should:

1. Clearly describe the change.
2. Be deterministic.
3. Be safe to apply.
4. Preserve existing data where possible.
5. Include rollback considerations.
6. Be tested against a clean database.
7. Be tested against an existing database when practical.

Avoid destructive migrations unless they are explicitly reviewed.

---

# Environment Variables

Never commit secrets to Git.

Typical environment configuration may include:

```text
DATABASE_URL
MYSQL_HOST
MYSQL_PORT
MYSQL_DATABASE
MYSQL_USER
MYSQL_PASSWORD

GEMINI_API_KEY

WEATHER_API_KEY

FRONTEND_URL
BACKEND_URL

SOCKET_IO_URL
```

The actual variables used by the repository take precedence over this example.

Create a local environment file based on the project's example environment file:

```bash
cp .env.example .env
```

On Windows, create the equivalent file manually if necessary.

### Never commit:

* API keys
* Database passwords
* JWT secrets
* Cloud credentials
* Private keys
* Production credentials
* Patient data
* Authentication tokens

If a secret is accidentally committed, removing it from the latest commit is **not sufficient**. The secret should be considered compromised and rotated immediately.

---

# Working With AI Features

ArogyaRakshak uses AI as part of its intelligence layer.

AI-related contributions require additional care.

## AI should augment decisions

AI-generated outputs should be treated as recommendations, predictions, classifications, summaries, or decision-support information.

They should not be presented as unquestionable medical truth.

Avoid UI language such as:

> "The AI has determined the correct treatment."

Prefer language such as:

> "AI-generated recommendation"

or:

> "Predicted surge risk"

or:

> "Recommended resource allocation"

---

## Prompt Changes

When modifying prompts:

* Explain why the prompt is changing.
* Test representative inputs.
* Test ambiguous inputs.
* Test missing-data scenarios.
* Check for hallucinations.
* Check for unsafe recommendations.
* Check that the output format remains stable.
* Avoid unnecessarily exposing sensitive data to the model.

Prompt changes can be functional changes and should therefore be reviewed like code.

---

## AI Output Validation

Never assume model output is valid simply because it is syntactically returned.

Validate:

* Required fields
* Data types
* Numeric ranges
* Enumerations
* Confidence values
* Missing values
* Unexpected text
* Contradictory recommendations

Where structured output is required, use a schema rather than parsing arbitrary natural language whenever possible.

---

# Prediction and Forecasting Guidelines

Prediction quality is a first-class concern.

When modifying a prediction system, document:

* Input features
* Data sources
* Prediction target
* Time horizon
* Training methodology
* Evaluation methodology
* Known limitations
* Expected error
* Confidence interpretation

Do not report model accuracy without specifying the evaluation methodology.

For example, avoid:

> "The model is 90% accurate."

Prefer:

> "The model achieved X% accuracy on the defined validation dataset using the specified evaluation methodology."

Do not tune a model against the test dataset.

---

# Working With External APIs

External services may include:

* Weather APIs
* AI APIs
* Messaging services
* Hospital data sources
* Environmental data sources

External API integrations must handle:

* Timeouts
* Rate limits
* Invalid responses
* Authentication failures
* Service outages
* Unexpected payloads
* Partial responses
* Network failures

Do not make the application crash simply because a third-party API is temporarily unavailable.

Where appropriate, implement:

```text
Request
   ↓
Timeout
   ↓
Validation
   ↓
Retry / Fallback
   ↓
Safe failure
```

Retries should be bounded.

Never implement an infinite retry loop.

---

# Real-Time Features

ArogyaRakshak may use Socket.IO for real-time communication.

Real-time events should:

* Have clear names.
* Use documented payload structures.
* Validate incoming data.
* Avoid leaking sensitive information.
* Handle disconnected clients.
* Avoid duplicate event processing.
* Be resilient to reconnects.

Document new events in the relevant API or architecture documentation.

Example:

```text
resource:update
prediction:updated
alert:created
hospital:status_changed
```

Event names should be consistent and descriptive.

---

# Branching Strategy

Use focused branches.

Recommended naming:

```text
feature/<short-description>
fix/<short-description>
refactor/<short-description>
docs/<short-description>
test/<short-description>
chore/<short-description>
security/<short-description>
```

Examples:

```text
feature/hospital-resource-dashboard
feature/pollution-risk-agent
fix/weather-api-timeout
fix/bed-allocation-calculation
refactor/ai-agent-service
docs/api-authentication
test/prediction-edge-cases
```

Keep branches focused on one logical change.

Avoid combining unrelated work.

---

# Commit Guidelines

Use clear, meaningful commit messages.

Recommended format:

```text
<type>: <short description>
```

Examples:

```text
feat: add hospital surge prediction endpoint
fix: handle weather API timeout
refactor: separate resource optimization service
docs: update local development guide
test: add prediction validation tests
chore: update backend dependencies
security: validate API authentication
```

Good commit:

```text
fix: prevent negative bed allocation values
```

Bad commit:

```text
fixed stuff
```

Very bad commit:

```text
asdfghjkl
```

Atomic commits are preferred.

A commit should ideally represent one logical change.

---

# Coding Standards

## General

Write code that is:

* Readable
* Maintainable
* Testable
* Explicit
* Consistent with existing project conventions

Avoid unnecessary abstraction.

Do not introduce a framework or dependency simply because it is interesting.

Every dependency creates:

* Maintenance cost
* Security surface
* Bundle/runtime impact
* Upgrade responsibility

---

# Frontend Guidelines

The frontend uses React and TypeScript.

## TypeScript

Prefer explicit types over `any`.

Avoid:

```typescript
const data: any = response.data;
```

Prefer:

```typescript
const data: HospitalPrediction = response.data;
```

If an API response is uncertain, validate it rather than simply casting it.

---

## React Components

Keep components focused.

Avoid extremely large components containing:

* API calls
* business logic
* data transformation
* state management
* rendering
* validation

all in the same file.

Separate reusable logic into:

* Hooks
* Services
* Utilities
* Types
* Components

---

## UI States

Every data-driven UI should consider:

1. Loading
2. Success
3. Empty
4. Error
5. Partial data

Do not design only the happy path.

For example:

```text
Loading...
     ↓
Data available → Display dashboard
     ↓
No data → Display meaningful empty state
     ↓
API failure → Display recoverable error
```

---

## Accessibility

Interactive UI should be accessible.

Consider:

* Keyboard navigation
* Semantic HTML
* Focus states
* Labels
* Color contrast
* Screen-reader compatibility
* Appropriate ARIA attributes

Do not use color as the only indicator of medical or operational risk.

For example, a "High Risk" indicator should not communicate risk solely through red color.

---

# Backend Guidelines

FastAPI endpoints should be:

* Explicit
* Validated
* Documented
* Testable
* Secure

Avoid putting complex business logic directly inside route handlers.

Prefer:

```text
Route
  ↓
Validation
  ↓
Service
  ↓
Repository / Database
  ↓
Response
```

rather than:

```text
Route
  ↓
Everything
```

---

## API Validation

Validate:

* Request body
* Query parameters
* Path parameters
* Authentication
* Authorization
* Data ranges
* Required fields

Never trust client-provided data.

---

# API Design

New APIs should have:

* Clear resource names
* Consistent HTTP methods
* Consistent status codes
* Structured error responses
* Input validation
* Documentation
* Tests

Use appropriate HTTP status codes.

Examples:

```text
200 OK
201 Created
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
409 Conflict
422 Validation Error
500 Internal Server Error
```

Do not return `200 OK` for every possible outcome.

---

# Error Handling

Errors should be useful to developers without exposing sensitive information.

Bad:

```text
Database password: ...
```

Good:

```text
Unable to retrieve hospital resource data.
```

Detailed internal errors should be logged securely.

Client-facing errors should contain only information the client needs.

---

# Logging

Logs should help diagnose failures without leaking sensitive information.

Good:

```text
Prediction service unavailable for hospital_id=<internal identifier>
```

Avoid logging:

* Passwords
* API keys
* Authentication tokens
* Personal medical information
* Full patient records
* Sensitive request payloads

Use appropriate log levels:

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

Do not use `print()` as a permanent logging strategy.

---

# Healthcare Data and Privacy

This section is particularly important.

ArogyaRakshak operates in a healthcare context.

Contributors must assume that healthcare-related information may be sensitive.

## Never commit real patient data

Do not commit:

* Patient names
* Phone numbers
* Addresses
* Medical records
* Diagnoses
* Prescription information
* Hospital identifiers tied to individuals
* Medical images
* Personal identifiers
* Authentication information

Use synthetic or anonymized datasets for development.

---

## Data Minimization

Only collect and process data required for the feature.

If a feature can work without storing a particular field, do not store it.

---

## Anonymization

When using real-world datasets for development or testing:

* Remove direct identifiers.
* Remove unnecessary quasi-identifiers.
* Follow the project's approved data-handling process.
* Verify that the resulting dataset cannot trivially identify individuals.

---

# Testing Requirements

Every meaningful code change should be tested.

Testing expectations depend on the change.

## Unit Tests

Use unit tests for:

* Utility functions
* Business logic
* Prediction transformations
* Data processing
* Validation
* Resource calculations

---

## Integration Tests

Use integration tests for:

* API + database interactions
* External service integrations
* AI service wrappers
* Authentication flows
* Real-time functionality

---

## Frontend Tests

Test:

* Component rendering
* User interactions
* Loading states
* Error states
* API failures
* Empty states
* Important business logic

---

## Prediction Tests

Prediction-related contributions should include tests for:

* Normal inputs
* Missing inputs
* Extreme values
* Invalid inputs
* Boundary conditions
* Historical edge cases

---

# Documentation Guidelines

Documentation is part of the feature.

Update documentation when changing:

* APIs
* Environment variables
* Database schema
* Deployment
* Architecture
* AI behavior
* External integrations
* User-facing workflows

Avoid documenting implementation details that are likely to become obsolete unless they are important for contributors.

---

# Issue Guidelines

Before opening an issue, search existing issues.

## Bug Reports

Include:

### Description

Clearly explain what went wrong.

### Expected Behavior

Explain what should have happened.

### Actual Behavior

Explain what actually happened.

### Steps to Reproduce

Provide the smallest reproducible sequence.

### Environment

Include relevant information such as:

* Operating system
* Browser
* Node/Python version
* Application version/commit
* Database version where relevant

### Logs

Include relevant logs.

**Remove secrets and sensitive healthcare information before posting.**

---

# Feature Requests

A good feature request should explain:

1. What problem does it solve?
2. Who benefits?
3. What behavior is expected?
4. Why is the proposed solution appropriate?
5. Are there alternatives?
6. What are the potential risks?

Avoid proposing a technology first and inventing a problem afterward.

---

# Pull Request Guidelines

Before opening a PR:

```text
[ ] Code works locally
[ ] Tests pass
[ ] Linting passes
[ ] Build passes
[ ] Documentation is updated
[ ] No secrets are committed
[ ] No sensitive healthcare data is included
[ ] Database changes are documented
[ ] API changes are documented
[ ] Error states are handled
[ ] New functionality has tests
[ ] Existing functionality has not been unnecessarily broken
```

---

# Pull Request Title

Use the same style as commit messages where practical.

Examples:

```text
feat: add pollution surge prediction
fix: handle unavailable weather service
refactor: simplify hospital resource service
docs: improve contributor setup
```

---

# Pull Request Description

A good PR should explain:

## What changed?

Describe the implementation.

## Why?

Explain the problem being solved.

## How?

Briefly describe the technical approach.

## Testing

Explain how the change was tested.

## Screenshots

For UI changes, include screenshots or recordings where useful.

## Breaking Changes

Clearly identify breaking changes.

---

# Keep Pull Requests Small

Prefer:

```text
PR #1
Add pollution data integration

PR #2
Add pollution-based prediction

PR #3
Display pollution risk in dashboard
```

over:

```text
PR #1
Rewrite the entire platform
+ new AI system
+ new dashboard
+ database migration
+ authentication
+ random refactoring
```

Smaller PRs are easier to review, test, debug, and revert.

---

# Review Process

Pull requests may be reviewed for:

* Correctness
* Architecture
* Security
* Performance
* Maintainability
* Testing
* Accessibility
* Documentation
* Data privacy
* AI safety
* Backward compatibility

A reviewer may request changes.

Do not take review comments personally.

The goal of review is to improve the codebase, not to win an argument.

When disagreeing with a review comment, explain the technical reasoning and provide evidence where possible.

---

# Security

Security vulnerabilities should **not** be reported through ordinary public issues if they could expose exploitable information.

Follow the repository's security-reporting process if one exists.

Potential security issues include:

* Authentication bypass
* Authorization bypass
* SQL injection
* XSS
* CSRF
* Secret exposure
* Insecure API endpoints
* Sensitive data leakage
* Dependency vulnerabilities
* Unsafe file handling
* Prompt injection vulnerabilities
* AI data leakage

Security fixes should be treated as high priority.

---

# AI Security

AI systems introduce additional attack surfaces.

Contributors should consider:

* Prompt injection
* Data exfiltration
* Malicious external content
* Model hallucination
* Unauthorized tool usage
* Excessive model permissions
* Sensitive data exposure
* Untrusted model output

Never allow model output to directly execute privileged operations without appropriate validation and authorization.

AI-generated SQL, shell commands, API requests, or database operations must not be trusted automatically.

---

# Performance Guidelines

Do not optimize blindly.

Measure first.

When changing performance-sensitive code, consider:

* Database indexes
* Query count
* API latency
* Network requests
* Frontend rendering
* Bundle size
* AI API latency
* External API latency
* Caching
* Memory usage

Avoid unnecessary polling when real-time events or appropriate caching can solve the problem.

Avoid repeatedly requesting expensive AI or external API operations when the result can safely be cached.

---

# What Not to Commit

Never commit:

```text
.env
.env.local
*.pem
*.key
credentials.json
API keys
Database dumps containing sensitive information
Production logs containing sensitive information
node_modules/
Python virtual environments
Build artifacts
Temporary files
IDE-specific private configuration
Real patient datasets
```

The exact ignore rules should be maintained in `.gitignore`.

---

# Common Contribution Patterns

## Adding a New API

Recommended flow:

```text
Define requirement
      ↓
Define request/response schema
      ↓
Implement service logic
      ↓
Implement API route
      ↓
Add validation
      ↓
Add tests
      ↓
Document endpoint
      ↓
Update frontend if required
```

---

## Adding a New AI Agent

Recommended flow:

```text
Define responsibility
      ↓
Define inputs
      ↓
Define outputs
      ↓
Define failure behavior
      ↓
Implement service
      ↓
Validate model output
      ↓
Add tests
      ↓
Integrate with orchestrator
      ↓
Expose through API/UI
      ↓
Document behavior and limitations
```

Every agent should have a clearly defined responsibility.

Avoid creating an agent simply because "AI agent" sounds cool.

---

## Adding a Dashboard Widget

Recommended flow:

```text
Define metric
      ↓
Identify authoritative data source
      ↓
Define API response
      ↓
Implement backend logic
      ↓
Implement frontend component
      ↓
Handle loading state
      ↓
Handle empty state
      ↓
Handle error state
      ↓
Test
      ↓
Document
```

---

# Definition of Done

A contribution is considered complete when:

* The implementation solves the intended problem.
* The code follows existing project conventions.
* Relevant tests have been added or updated.
* Existing tests pass.
* Linting passes.
* The application builds successfully.
* Errors and edge cases are handled.
* Documentation has been updated where necessary.
* No secrets have been committed.
* No real patient information has been introduced.
* Security implications have been considered.
* AI-generated behavior has been validated where applicable.
* The pull request clearly explains the change.
* Review feedback has been addressed.

"Works on my machine" is not the definition of done.

---

# Getting Help

If you are stuck:

1. Read the README.
2. Search the documentation.
3. Search existing issues.
4. Search existing pull requests.
5. Inspect similar implementations in the codebase.
6. Ask a focused question with relevant context.

When asking for help, include:

* What you are trying to achieve.
* What you expected.
* What actually happened.
* What you have already tried.
* Relevant error messages.
* Relevant code snippets.
* Your development environment.

Do not paste credentials, API keys, or sensitive healthcare information.

---

# Contribution Checklist

Before submitting your contribution:

* [ ] I have read this guide.
* [ ] I understand the part of the architecture I am modifying.
* [ ] I searched for existing issues/PRs.
* [ ] My branch is based on the latest relevant upstream code.
* [ ] My changes are focused and do not contain unrelated refactoring.
* [ ] I followed the project's coding conventions.
* [ ] I added or updated tests where appropriate.
* [ ] I tested error and edge cases.
* [ ] I updated documentation where necessary.
* [ ] I did not commit secrets.
* [ ] I did not commit real patient or personally identifiable healthcare data.
* [ ] I considered security implications.
* [ ] I considered AI safety and model failure modes where applicable.
* [ ] I verified the application builds successfully.
* [ ] I have written a clear pull request description.

---

# Final Note

ArogyaRakshak is intended to help healthcare organizations prepare **before** demand becomes a crisis.

That principle should also apply to the codebase.

Good contributors do not merely make features work. They anticipate failure, validate assumptions, protect data, document decisions, and build systems that remain dependable when conditions are anything but normal.

If you are unsure whether a contribution is ready, open a discussion early. It is much cheaper to align on architecture before writing 2,000 lines of code than to rewrite 2,000 lines afterward.

**Build responsibly. Test aggressively. Document clearly. Protect the people behind the data.**

Thank you for contributing to ArogyaRakshak.
