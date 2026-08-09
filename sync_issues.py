import subprocess
import sys
import json

REPO = "Viraj281105/Arogyarakshak"

LABELS = {
    "module:kadi": "0E8A16",
    "module:billnyay": "1D76DB",
    "module:schemesetu": "5319E7",
    "module:dawacheck": "B60205",
    "module:daavisetu": "D4C5F9",
    "module:infra": "FBCA04",
    "module:frontend": "C5DEF5",
    "module:data-qa": "D93F0B",
    "role:orchestration": "0052CC",
    "role:ocr-data": "006B75",
    "role:frontend": "BFD4F2",
    "role:infra": "F9D0C4",
    "role:data-qa": "E99695",
    "phase:0": "000000",
    "phase:1": "3B3B3B",
    "phase:2": "5C5C5C",
    "phase:3": "7D7D7D",
    "phase:4": "9E9E9E",
    "phase:5": "BFBFBF",
}

ISSUES = [
    # Phase 0
    ("Scaffold monorepo per Tech Doc §9", "apps/, packages/, data/, docs/, docker-compose.yml", "module:infra,role:infra,phase:0"),
    ("Push docs into docs/", "Technical Documentation + Task Backlog into docs/", "module:infra,role:infra,phase:0"),
    ("Re-point Groq model to openai/gpt-oss-120b", "llama3-70b deprecated 17 June 2026. Blocks every LLM-calling module.", "module:billnyay,role:orchestration,phase:0"),
    ("Confirm hackathon BillNyay code carryover with guide", "Can existing hackathon code carry into FYP directly, or must be framed as new work?", "module:data-qa,role:data-qa,phase:0"),
    ("Confirm SPPU Phase-I review date", "Determine 'done' definition for Phase-I vs final submission.", "module:data-qa,role:data-qa,phase:0"),
    ("Check native-language availability of PMJAY/MJPJAY/CGHS/NPPA docs", "Determines source-vs-generation scope per Tech Doc §5.", "module:data-qa,role:data-qa,phase:0"),
    
    # Phase 1
    ("Design & migrate cases/entities/case_entities schema", "Postgres schema per Tech Doc §4.1.", "module:kadi,role:orchestration,phase:1"),
    ("Build shared extraction agent", "Normalizes any document into common entity schema (Tech Doc §4.2).", "module:kadi,role:orchestration,phase:1"),
    ("Set up FAISS + pgvector indexes for Kadi entity store", "", "module:kadi,role:infra,phase:1"),
    ("Docker Compose: Postgres+pgvector, FastAPI, Next.js wiring", "Full service wiring beyond Phase 0 scaffold.", "module:infra,role:infra,phase:1"),
    ("SSE streaming endpoint scaffold", "", "module:infra,role:infra,phase:1"),
    ("Basic CI: lint + test on PR (GitHub Actions)", "", "module:infra,role:infra,phase:1"),
    ("CGHS rate schedule scraping/parsing", "Structured format ingestion.", "module:billnyay,role:data-qa,phase:1"),
    ("PMJAY eligibility rules + empanelled hospital list ingestion", "", "module:schemesetu,role:data-qa,phase:1"),
    ("MJPJAY (Maharashtra) eligibility rules ingestion", "", "module:schemesetu,role:data-qa,phase:1"),
    ("NPPA Schedule-I ceiling price list ingestion", "~800-900 price-controlled drugs.", "module:dawacheck,role:data-qa,phase:1"),
    ("Register for ABDM Developer Sandbox & complete initial HIU flow walkthrough", "Register at sandbox.abdm.gov.in and verify access to sandbox ABHA accounts.", "module:kadi,role:data-qa,phase:1"),
    ("Configure monorepo build setup in Docker & setup local editable packages", "Define local packages in pyproject.toml files and update FastAPI Dockerfile to install them.", "module:infra,role:infra,phase:1"),

    # Phase 2
    ("Port hackathon OCR pipeline into packages/billnyay", "", "module:billnyay,role:ocr-data,phase:2"),
    ("Re-verify 5-agent pipeline against new stack", "Auditor -> Reviewer -> Advisor -> Drafter -> QA Judge.", "module:billnyay,role:orchestration,phase:2"),
    ("Integrate BillNyay with Kadi", "Write extracted entities, read shared context.", "module:billnyay,role:orchestration,phase:2"),
    ("Appeal PDF generation + download flow", "", "module:billnyay,role:frontend,phase:2"),
    ("Build eligibility reasoning agent over PMJAY/MJPJAY RAG index", "", "module:schemesetu,role:orchestration,phase:2"),
    ("Intake form UI (income, location, category, medical need)", "", "module:schemesetu,role:frontend,phase:2"),
    ("SchemeSetu: integrate with Kadi", "Read context from BillNyay/DawaCheck uploads.", "module:schemesetu,role:orchestration,phase:2"),
    ("Medicine strip / prescription photo OCR", "", "module:dawacheck,role:ocr-data,phase:2"),
    ("MRP vs NPPA ceiling price benchmarking logic", "", "module:dawacheck,role:orchestration,phase:2"),
    ("Brand <-> generic active-ingredient mapping", "Shared dependency with Kadi entity resolution — build once.", "module:dawacheck,role:orchestration,phase:2"),
    ("DawaCheck: integrate with Kadi", "", "module:dawacheck,role:orchestration,phase:2"),
    ("DaaviSetu: Ingest blank insurance claim and pre-authorization form templates", "Sourced from public insurer websites.", "module:daavisetu,role:ocr-data,phase:2"),
    ("DaaviSetu: Map KADI patient context into cashless pre-authorization form schema", "Fills common insurer claim fields.", "module:daavisetu,role:orchestration,phase:2"),
    ("DaaviSetu: Output submission-ready package (PDF + structured summary)", "Provides download link for review and manual submission.", "module:daavisetu,role:frontend,phase:2"),
    ("BillNyay: Auto-draft IRDAI Bima Bharosa complaint packages", "Drafts compliant IRDAI grievance text in standard schema.", "module:billnyay,role:orchestration,phase:2"),
    ("BillNyay: Implement self-reported grievance tracker and portal deep-linking", "Track grievance status and deep-link directly to Bima Bharosa portal.", "module:billnyay,role:frontend,phase:2"),
    ("BillNyay: Add reminder nudges for IRDAI turnaround times", "Surfaces reminders when responses are due based on turnaround times.", "module:billnyay,role:frontend,phase:2"),

    # Phase 3
    ("String similarity scoring", "Edit distance / token overlap.", "module:kadi,role:orchestration,phase:3"),
    ("Integrate IndicXlit for transliteration matching", "pip install ai4bharat-transliteration", "module:kadi,role:orchestration,phase:3"),
    ("Integrate IndicSBERT for cross-lingual semantic matching", "l3cube-pune/indic-sentence-similarity-sbert via sentence-transformers", "module:kadi,role:orchestration,phase:3"),
    ("Combine signals into confidence score + merge/ask/new-entity branching", "", "module:kadi,role:orchestration,phase:3"),
    ("Auto-triggering: fire module checks when Kadi has enough context", "", "module:kadi,role:orchestration,phase:3"),
    ("Consent UI — per-case opt-in for cross-module data sharing", "", "module:kadi,role:frontend,phase:3"),
    ("Cross-module insight display", "e.g. 'you may also be eligible under SchemeSetu' surfaced from a BillNyay upload.", "module:frontend,role:frontend,phase:3"),
    ("ABDM: Connect pulled medical history with Kadi shared case context", "Parse ABHA sandbox-pulled clinical records into case context.", "module:kadi,role:orchestration,phase:3"),
    ("DaaviSetu: Integrate with Kadi context layer", "Read case entities to pre-fill claim forms.", "module:daavisetu,role:orchestration,phase:3"),

    # Phase 4
    ("Build Devanagari OCR test set", "Real + synthetic self-donated documents.", "module:data-qa,role:data-qa,phase:4"),
    ("Build labeled entity-pair dataset", "For tuning entity-resolution confidence thresholds.", "module:data-qa,role:data-qa,phase:4"),
    ("Terminology QA pass on appeal letters & scheme explanations", "Hindi + Marathi.", "module:data-qa,role:data-qa,phase:4"),
    ("Trilingual UI pass across all screens", "English/Hindi/Marathi.", "module:frontend,role:frontend,phase:4"),
    ("LLM output generation in Hindi/Marathi per module", "Where source data is English-only, per Phase 0 finding.", "module:billnyay,module:schemesetu,module:dawacheck,role:orchestration,phase:4"),

    # Phase 5
    ("Decide & set up deployment target", "College server / cloud free-tier / local demo.", "module:infra,role:infra,phase:5"),
    ("End-to-end demo flow polish", "One bill upload -> three module insights, for the live demo.", "module:frontend,role:frontend,phase:5"),
    ("Blackbook / final report drafting", "Once guide sign-off on final scope confirmed.", "module:data-qa,role:data-qa,phase:5"),
    ("Ask guide if anything additional is expected", "Once core build is stable ahead of schedule.", "phase:5"),
]

def run_command(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
    return result

def main():
    print(f"==> Creating labels on {REPO}...")
    for label, color in LABELS.items():
        cmd = f'gh label create "{label}" --color "{color}" --repo "{REPO}" --force'
        res = run_command(cmd)
        if res.returncode == 0:
            print(f"  Label '{label}' ensured.")
        else:
            print(f"  Failed label '{label}': {res.stderr.strip()}")

    print("==> Fetching existing issues...")
    res = run_command(f'gh issue list --repo "{REPO}" --state all --limit 200 --json title')
    existing_titles = set()
    if res.returncode == 0:
        try:
            data = json.loads(res.stdout)
            existing_titles = {item["title"] for item in data}
        except Exception as e:
            print(f"  Error parsing issue JSON: {e}")
    else:
        print(f"  Failed to fetch issues: {res.stderr.strip()}")

    print(f"==> Creating issues on {REPO}...")
    for title, body, labels in ISSUES:
        if title in existing_titles:
            print(f"  -> Issue '{title}' already exists, skipping.")
        else:
            print(f"  -> Creating issue: '{title}'")
            cmd = f'gh issue create --repo "{REPO}" --title "{title}" --body "{body}" --label "{labels}"'
            create_res = run_command(cmd)
            if create_res.returncode != 0:
                print(f"     Failed to create issue: {create_res.stderr.strip()}")

    print("==> Issue sync completed.")

if __name__ == "__main__":
    main()
