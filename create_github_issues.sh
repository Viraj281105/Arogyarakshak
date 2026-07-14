#!/usr/bin/env bash
# ArogyaRakshak — bulk GitHub issue creator
# Usage: ./create_github_issues.sh <owner>/<repo>
# Requires: gh CLI installed + authenticated (gh auth login)
set -euo pipefail

REPO="${1:-}"
if [ -z "$REPO" ]; then
  echo "Usage: ./create_github_issues.sh <owner>/<repo>"
  exit 1
fi

echo "==> Creating labels on $REPO"

create_label () { gh label create "$1" --color "$2" --repo "$REPO" --force >/dev/null 2>&1 || true; }

create_label "module:kadi"        "0E8A16"
create_label "module:billnyay"    "1D76DB"
create_label "module:schemesetu"  "5319E7"
create_label "module:dawacheck"   "B60205"
create_label "module:infra"       "FBCA04"
create_label "module:frontend"    "C5DEF5"
create_label "module:data-qa"     "D93F0B"
create_label "role:orchestration" "0052CC"
create_label "role:ocr-data"      "006B75"
create_label "role:frontend"      "BFD4F2"
create_label "role:infra"         "F9D0C4"
create_label "role:data-qa"       "E99695"
create_label "phase:0"            "000000"
create_label "phase:1"            "3B3B3B"
create_label "phase:2"            "5C5C5C"
create_label "phase:3"            "7D7D7D"
create_label "phase:4"            "9E9E9E"
create_label "phase:5"            "BFBFBF"

echo "==> Creating issues on $REPO"

create_issue () {
  local title="$1" body="$2" labels="$3"
  gh issue create --repo "$REPO" --title "$title" --body "$body" --label "$labels"
}

# ---------------- Phase 0 — Blockers ----------------
create_issue "Scaffold monorepo per Tech Doc §9" "apps/, packages/, data/, docs/, docker-compose.yml" "module:infra,role:infra,phase:0"
create_issue "Push docs into docs/" "Technical Documentation + Task Backlog into docs/" "module:infra,role:infra,phase:0"
create_issue "Re-point Groq model to openai/gpt-oss-120b" "llama3-70b deprecated 17 June 2026. Blocks every LLM-calling module." "module:billnyay,role:orchestration,phase:0"
create_issue "Confirm hackathon BillNyay code carryover with guide" "Can existing hackathon code carry into FYP directly, or must be framed as new work?" "module:data-qa,role:data-qa,phase:0"
create_issue "Confirm SPPU Phase-I review date" "Determine 'done' definition for Phase-I vs final submission." "module:data-qa,role:data-qa,phase:0"
create_issue "Check native-language availability of PMJAY/MJPJAY/CGHS/NPPA docs" "Determines source-vs-generation scope per Tech Doc §5." "module:data-qa,role:data-qa,phase:0"

# ---------------- Phase 1 — Foundations ----------------
create_issue "Design & migrate cases/entities/case_entities schema" "Postgres schema per Tech Doc §4.1." "module:kadi,role:orchestration,phase:1"
create_issue "Build shared extraction agent" "Normalizes any document into common entity schema (Tech Doc §4.2)." "module:kadi,role:orchestration,phase:1"
create_issue "Set up FAISS + pgvector indexes for Kadi entity store" "" "module:kadi,role:infra,phase:1"
create_issue "Docker Compose: Postgres+pgvector, FastAPI, Next.js wiring" "Full service wiring beyond Phase 0 scaffold." "module:infra,role:infra,phase:1"
create_issue "SSE streaming endpoint scaffold" "" "module:infra,role:infra,phase:1"
create_issue "Basic CI: lint + test on PR (GitHub Actions)" "" "module:infra,role:infra,phase:1"
create_issue "CGHS rate schedule scraping/parsing" "Structured format ingestion." "module:billnyay,role:data-qa,phase:1"
create_issue "PMJAY eligibility rules + empanelled hospital list ingestion" "" "module:schemesetu,role:data-qa,phase:1"
create_issue "MJPJAY (Maharashtra) eligibility rules ingestion" "" "module:schemesetu,role:data-qa,phase:1"
create_issue "NPPA Schedule-I ceiling price list ingestion" "~800-900 price-controlled drugs." "module:dawacheck,role:data-qa,phase:1"

# ---------------- Phase 2 — Module builds ----------------
create_issue "Port hackathon OCR pipeline into packages/billnyay" "" "module:billnyay,role:ocr-data,phase:2"
create_issue "Re-verify 5-agent pipeline against new stack" "Auditor -> Reviewer -> Advisor -> Drafter -> QA Judge." "module:billnyay,role:orchestration,phase:2"
create_issue "Integrate BillNyay with Kadi" "Write extracted entities, read shared context." "module:billnyay,role:orchestration,phase:2"
create_issue "Appeal PDF generation + download flow" "" "module:billnyay,role:frontend,phase:2"
create_issue "Build eligibility reasoning agent over PMJAY/MJPJAY RAG index" "" "module:schemesetu,role:orchestration,phase:2"
create_issue "Intake form UI (income, location, category, medical need)" "" "module:schemesetu,role:frontend,phase:2"
create_issue "SchemeSetu: integrate with Kadi" "Read context from BillNyay/DawaCheck uploads." "module:schemesetu,role:orchestration,phase:2"
create_issue "Medicine strip / prescription photo OCR" "" "module:dawacheck,role:ocr-data,phase:2"
create_issue "MRP vs NPPA ceiling price benchmarking logic" "" "module:dawacheck,role:orchestration,phase:2"
create_issue "Brand <-> generic active-ingredient mapping" "Shared dependency with Kadi entity resolution — build once." "module:dawacheck,role:orchestration,phase:2"
create_issue "DawaCheck: integrate with Kadi" "" "module:dawacheck,role:orchestration,phase:2"

# ---------------- Phase 3 — Entity resolution & integration ----------------
create_issue "String similarity scoring" "Edit distance / token overlap." "module:kadi,role:orchestration,phase:3"
create_issue "Integrate IndicXlit for transliteration matching" "pip install ai4bharat-transliteration" "module:kadi,role:orchestration,phase:3"
create_issue "Integrate IndicSBERT for cross-lingual semantic matching" "l3cube-pune/indic-sentence-similarity-sbert via sentence-transformers" "module:kadi,role:orchestration,phase:3"
create_issue "Combine signals into confidence score + merge/ask/new-entity branching" "" "module:kadi,role:orchestration,phase:3"
create_issue "Auto-triggering: fire module checks when Kadi has enough context" "" "module:kadi,role:orchestration,phase:3"
create_issue "Consent UI — per-case opt-in for cross-module data sharing" "" "module:kadi,role:frontend,phase:3"
create_issue "Cross-module insight display" "e.g. 'you may also be eligible under SchemeSetu' surfaced from a BillNyay upload." "module:frontend,role:frontend,phase:3"

# ---------------- Phase 4 — Multilingual & QA ----------------
create_issue "Build Devanagari OCR test set" "Real + synthetic self-donated documents." "module:data-qa,role:data-qa,phase:4"
create_issue "Build labeled entity-pair dataset" "For tuning entity-resolution confidence thresholds." "module:data-qa,role:data-qa,phase:4"
create_issue "Terminology QA pass on appeal letters & scheme explanations" "Hindi + Marathi." "module:data-qa,role:data-qa,phase:4"
create_issue "Trilingual UI pass across all screens" "English/Hindi/Marathi." "module:frontend,role:frontend,phase:4"
create_issue "LLM output generation in Hindi/Marathi per module" "Where source data is English-only, per Phase 0 finding." "module:billnyay,module:schemesetu,module:dawacheck,role:orchestration,phase:4"

# ---------------- Phase 5 — Polish & submission ----------------
create_issue "Decide & set up deployment target" "College server / cloud free-tier / local demo." "module:infra,role:infra,phase:5"
create_issue "End-to-end demo flow polish" "One bill upload -> three module insights, for the live demo." "module:frontend,role:frontend,phase:5"
create_issue "Blackbook / final report drafting" "Once guide sign-off on final scope confirmed." "module:data-qa,role:data-qa,phase:5"
create_issue "Ask guide if anything additional is expected" "Once core build is stable ahead of schedule." "phase:5"

echo "==> Done. $(gh issue list --repo "$REPO" --limit 100 | wc -l) issues now open on $REPO"
