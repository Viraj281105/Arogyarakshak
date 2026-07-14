# Agent Configuration — ArogyaRakshak

project_name: "ArogyaRakshak"
stack: "FastAPI + Next.js 15 + PostgreSQL/pgvector + FAISS + Groq"

## Ground rules (apply to every agent, every task)

- Read `docs/ArogyaRakshak_Technical_Documentation.md` and `docs/ArogyaRakshak_Task_Backlog.md` before starting any task. These are the source of truth for architecture, naming, and scope — do not deviate from them without flagging it back to me first.
- Never call the Groq model `llama3-70b` or `llama-3.3-70b-versatile` — both are deprecated. Always read the model name from the `GROQ_MODEL` env var, default `openai/gpt-oss-120b`.
- Naming conventions are fixed: modules are `billnyay`, `schemesetu`, `dawacheck`, `kadi` (lowercase). DB tables prefix with `kadi_`, `billnyay_`, `schemesetu_`, `dawacheck_`. API routes are `/api/<module>/...`.
- Kadi (`packages/kadi`) is shared infrastructure, not a fourth module. Any feature that touches entity extraction, entity resolution, or cross-module context belongs there, not duplicated inside a module package.
- This is a bring-your-own-document app — no persistent storage of uploaded patient documents beyond the active case session unless I explicitly say otherwise. Don't add file retention "for convenience."
- After any backend change, verify with `curl localhost:8000/health` (or the relevant endpoint) before declaring the task done. After any frontend change, launch the dev server and check the affected page in the browser — don't just report that the code compiles.
- If a task is ambiguous or you have to guess at scope, stop and ask rather than guessing silently. Write the question into your final report instead of picking an interpretation and running with it.
- Do not install or invoke any package that talks to a network endpoint outside Groq, the Postgres container, and the package registries (pypi/npm) without flagging it first.

## Agent roles (mirrors Technical Documentation §10)

- name: "orchestration-agent"
  role: "Multi-agent pipeline design across BillNyay/SchemeSetu/DawaCheck, and Kadi's entity resolution pipeline"
  instructions: |
    - Own everything under packages/kadi, and the agent-pipeline logic (not the OCR/ingestion) inside each module package.
    - When building multi-agent chains (e.g. BillNyay's 5-agent pipeline), keep each agent's prompt and responsibility in a separate function/file — don't collapse them into one mega-prompt.
    - Prefer structured JSON outputs between agent stages over free text, so downstream agents parse reliably.

- name: "ocr-data-agent"
  role: "Document ingestion, OCR (incl. Devanagari), RAG ingestion for CGHS/PMJAY/MJPJAY/NPPA"
  instructions: |
    - Own everything under data/ and the ocr.py / ingestion files inside each module package.
    - Flag any source document that isn't in the format the docs assume (e.g. if a PDF is scanned images with no text layer, that changes the OCR approach — don't silently work around it).

- name: "frontend-agent"
  role: "Next.js interface, trilingual UI"
  instructions: |
    - Own apps/web.
    - Default to English-first UI with i18n scaffolding in place from the start (don't bolt on Hindi/Marathi later) — but don't write actual Hindi/Marathi copy yourself; stub it and flag for human review (see Technical Documentation §5, terminology QA).

- name: "infra-agent"
  role: "Docker, database, SSE streaming, hosting"
  instructions: |
    - Own docker-compose.yml, apps/api's app-level wiring (not business logic), and CI config.
    - Any schema migration must be a versioned migration file, never a manual ALTER TABLE run ad hoc.

- name: "data-qa-agent"
  role: "Government data structuring, IRDAI/scheme rule accuracy, entity-pair labeling, multilingual QA"
  instructions: |
    - Own data-quality scripts and the labeled entity-pair dataset.
    - When structuring government source data (CGHS/PMJAY/MJPJAY/NPPA), cite the source document/URL for every record — no rows without provenance.
