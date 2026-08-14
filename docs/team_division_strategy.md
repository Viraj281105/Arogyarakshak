# ArogyaRakshak — Team Task Division Strategy (4-5 Member Allocations)

This document provides a structured framework for dividing the 103 synchronized GitHub issues among a team consisting of **1 Strong Programmer (You)** and **3 to 4 Vibe Coders**.

---

## 1. The Core Basis of Division

To prevent project bottlenecks, issues should **not** be divided randomly or by module (e.g., one person doing all of BillNyay). Instead, the division must be based on **Technical Roles (GitHub `role` labels)**. 

By grouping tasks by technical roles, the strong coder retains control over the core platform stability, while vibe coders focus on isolated areas where visual builders, AI prompt tools, or document preparation can be leveraged.

### Role Mappings:
1. **`role:orchestration` + `role:infra`**: Requires deep understanding of async Python, databases, and multi-agent loops. (Assigned to the **Strong Coder**).
2. **`role:frontend`**: Involves React, Next.js 15, HTML/CSS, and visualization. (Perfect for UI-oriented vibe coders).
3. **`role:ocr-data` + `role:data-qa`**: Involves prompt engineering, OCR testing, and data entry. (Low coding barrier; excellent for vibe coders).

---

## 2. Division Blueprint (5-Member Team)
*If your team has 5 members (You + 4 Vibe Coders):*

### Person 1: The System Architect (YOU — Strong Coder)
* **Labels**: `role:orchestration`, `role:infra`
* **Task Count**: ~30 issues
* **Responsibilities**:
  - FastAPI server setups, SQLAlchemy database models, and migration.
  - Multi-agent LLM consensus logic (Auditor, Barrister, Judge).
  - KADI shared context layer integration.
  - Docker Compose configurations and CI/CD pipelines.

### Person 2: The UI/UX Developer (Vibe Coder A)
* **Labels**: `role:frontend`
* **Task Count**: ~20 issues
* **Responsibilities**:
  - Building Next.js 15 page layouts and responsive components.
  - Designing visual billing anomaly dashboards (using HSL charts).
  - Hooking frontend forms (pre-auth claim forms, intake eligibility) to Person 1's API endpoints.

### Person 3: The Data Curator & Prompt Engineer (Vibe Coder B)
* **Labels**: `role:data-qa` (focused on Ingestion & Prompts)
* **Task Count**: ~18 issues
* **Responsibilities**:
  - Gathering and cleaning reference schedules (CGHS rates, NPPA drug lists, PMJAY rules).
  - Prompt engineering (writing and refining LLM prompts for the legal/clinical agents).
  - Translating default system instructions into Hindi and Marathi.

### Person 4: The Quality Assurance Analyst (Vibe Coder C)
* **Labels**: `role:ocr-data` / `role:data-qa` (focused on Verification)
* **Task Count**: ~18 issues
* **Responsibilities**:
  - Creating mock test-bills and prescriptions to feed into the OCR parser.
  - Validating OCR accuracy (WER/CER) and reporting extraction failures.
  - Calculating system evaluation metrics (BMA, PEA, PCRA) using the test suite.

### Person 5: The Compliance & Documentation Lead (Vibe Coder D)
* **Labels**: `role:data-qa` (focused on Documentation)
* **Task Count**: ~17 issues
* **Responsibilities**:
  - Writing SPPU university reports (Phase-1 report, final Blackbook thesis).
  - Designing presentation slide decks.
  - Mapping regulatory rules (IRDAI compliance details, ABDM sandbox setup).

---

## 3. Division Blueprint (4-Member Team)
*If your team has 4 members total (You + 3 Vibe Coders), collapse the roles as follows:*

### Person 1: System Architect & QA Lead (YOU — Strong Coder)
* **Labels**: `role:orchestration`, `role:infra`, `role:data-qa` (Testing)
* **Task Count**: ~40 issues
* **Responsibilities**: Core backend, pipelines, database integration, running `pytest`, and generating latency metrics.

### Person 2: UI/UX & Interaction Developer (Vibe Coder A)
* **Labels**: `role:frontend`
* **Task Count**: ~22 issues
* **Responsibilities**: All Next.js frontend pages, dashboard charts, multi-step intake forms, and Web Crypto client-side encryption.

### Person 3: Ingestion & Prompt Engineer (Vibe Coder B)
* **Labels**: `role:data-qa` (Ingestion), `role:ocr-data` (OCR validation)
* **Task Count**: ~21 issues
* **Responsibilities**: Scraping rate cards, prompt tuning, OCR test-set collection, and translation variables.

### Person 4: Compliance & Report Writer (Vibe Coder C)
* **Labels**: `role:data-qa` (Documentation/Reports)
* **Task Count**: ~20 issues
* **Responsibilities**: College thesis reports, slide deck preparations, manual verification, and IRDAI/ABDM regulation tracking.

---

## 4. How to track this on the Project Board

1. **Group by Milestone**: Set up your board columns or filters based on the GitHub Milestones (`Phase 0` through `Phase 5`).
2. **Filter by Role**: Assign team members to their corresponding role label. 
3. **Weekly Handshakes**: 
   - Vibe coders can build UI mockups or write CSV data files concurrently.
   - You wire their work into the backend routing and agent loops.
   - Once wired, vibe coders can verify the functionality using the Next.js visual interface.
