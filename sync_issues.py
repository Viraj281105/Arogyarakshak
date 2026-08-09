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
    # ---------------- Phase 0 — Blockers ----------------
    ("Scaffold monorepo per Tech Doc §9", "apps/, packages/, data/, docs/, docker-compose.yml", "module:infra,role:infra,phase:0"),
    ("Push docs into docs/", "Technical Documentation + Task Backlog into docs/", "module:infra,role:infra,phase:0"),
    ("Re-point Groq model to openai/gpt-oss-120b", "llama3-70b deprecated 17 June 2026. Blocks every LLM-calling module.", "module:billnyay,role:orchestration,phase:0"),
    ("Confirm hackathon BillNyay code carryover with guide", "Can existing hackathon code carry into FYP directly, or must be framed as new work?", "module:data-qa,role:data-qa,phase:0"),
    ("Confirm SPPU Phase-I review date", "Determine 'done' definition for Phase-I vs final submission.", "module:data-qa,role:data-qa,phase:0"),
    ("Check native-language availability of PMJAY/MJPJAY/CGHS/NPPA docs", "Determines source-vs-generation scope per Tech Doc §5.", "module:data-qa,role:data-qa,phase:0"),
    
    # ---------------- Phase 1 — Foundations ----------------
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
    # Futuristic Phase 1 Issues
    ("KADI: Develop ABDM M2/M3 Sandbox FHIR-compliant resource converter", "Map sandbox clinical records into HL7 FHIR JSON objects for universal case ingestion.", "module:kadi,role:data-qa,phase:1"),
    ("KADI: Develop Real-Time SSE patient document processing status stream", "Provide live processing logs and progress bars directly to Next.js UI using Server-Sent Events.", "module:infra,role:infra,phase:1"),
    ("SchemeSetu: Implement local offline fallback embedding model", "Configure ONNX runtime for SentenceTransformers to allow offline semantic matching on edge nodes.", "module:schemesetu,role:infra,phase:1"),
    ("SchemeSetu: Create automated web-scraping crawler for real-time PMJAY circular/policy changes", "Ingest new policy circulars directly into PostgreSQL using a BeautifulSoup/Playwright crawler.", "module:schemesetu,role:data-qa,phase:1"),
    ("DawaCheck: Create database tables for brand-to-generic formulation mappings", "Create `dawacheck_generic_mappings` model with indexed chemical compound columns.", "module:dawacheck,role:infra,phase:1"),
    ("DawaCheck: Design automated NPPA Schedule-I PDF ceiling price list scraper and parser", "Automated PDF ingestion from the NPPA portal to parse table columns into DB ceiling rates.", "module:dawacheck,role:data-qa,phase:1"),

    # ---------------- Phase 2 — Module builds ----------------
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
    # Futuristic Phase 2 Issues
    ("KADI: Implement Self-Healing OCR Correction Loop", "Deploy an LLM-based verification check to detect and correct spelling/syntax typos in raw OCR texts.", "module:kadi,role:ocr-data,phase:2"),
    ("KADI: Implement Multi-Modal Document Extraction using open vision models", "Parse handwritten doctors' notes, bills, and prescriptions utilizing visual-LLM (LLaVA/Qwen-VL) APIs.", "module:kadi,role:ocr-data,phase:2"),
    ("BillNyay: Develop Auto-Audit heuristic engine matching ICD-10 codes with procedures", "Automate compliance validation by flagging hospital bills with mismatched procedure-vs-diagnosis codes.", "module:billnyay,role:orchestration,phase:2"),
    ("BillNyay: Design Multi-Agent consensus voting protocol with dynamic weights", "Enable cooperative evaluation between Auditor, Clinician, and Regulatory agents for final Judge approval.", "module:billnyay,role:orchestration,phase:2"),
    ("BillNyay: Implement IRDAI appeal letter PDF digital signature verification", "Enable secure digital signing and SHA-256 integrity checks on generated legal document packages.", "module:billnyay,role:infra,phase:2"),
    ("BillNyay: Create Bima Bharosa automated form crawler", "Build an automated headless browser check to confirm mock registration status on portal endpoints.", "module:billnyay,role:infra,phase:2"),
    ("BillNyay: Design self-correcting appeal letter drafter feedback loops", "Auto-trigger draft revisions when the QA Judge agent detects inconsistencies or low confidence parameters.", "module:billnyay,role:orchestration,phase:2"),
    ("BillNyay: Implement clinical guideline checks using National Formulary of India", "Cross-reference prescription items with standard NFI formulas to flag arbitrary treatments.", "module:billnyay,role:data-qa,phase:2"),
    ("SchemeSetu: Build predictive future eligibility estimator using trend lines", "Analyze patient demographic trends over time to forecast future eligibility status for regional schemes.", "module:schemesetu,role:orchestration,phase:2"),
    ("SchemeSetu: Implement automatic Scheme-to-Scheme transition adviser", "Generate transition checklists when patients transition between PMJAY (national) and MJPJAY (state) schemes.", "module:schemesetu,role:orchestration,phase:2"),
    ("DawaCheck: Implement Fuzzy Matching Brand name to Generic Formulation", "Match brand mentions to ceiling price ingredients using Double Metaphone algorithms.", "module:dawacheck,role:orchestration,phase:2"),
    ("DawaCheck: Develop active-ingredient dosage normalization logic", "Proportionately benchmark dosage variances (e.g. Paracetamol 650mg vs 500mg) against ceiling prices.", "module:dawacheck,role:orchestration,phase:2"),
    ("DawaCheck: Integrate Jan Aushadhi Store APIs and physical store locations", "Query generic medicine store lists to suggest the three closest locations based on patient zip code.", "module:dawacheck,role:frontend,phase:2"),
    ("DawaCheck: Implement medicine strip expiration and authenticity visual classification model", "Deploy lightweight vision filters to detect generic medicine strip integrity and expiry prints.", "module:dawacheck,role:ocr-data,phase:2"),
    ("DawaCheck: Develop real-time pricing variance statistics calculator", "Generate statistical price distribution curves matching brand pricing vs generic ceiling alternatives.", "module:dawacheck,role:data-qa,phase:2"),
    ("DawaCheck: Design pill shape and color verification model using OpenCV", "Enable prescription-to-pill consistency checks by verifying pill appearance from photos.", "module:dawacheck,role:ocr-data,phase:2"),
    ("DaaviSetu: Ingest blank cashless pre-authorization form templates for 5 major insurers", "Ingest and structure form templates from ICICI Lombard, HDFC Ergo, Star Health, Care, and Niva Bupa.", "module:daavisetu,role:ocr-data,phase:2"),
    ("DaaviSetu: Design JSON Schema definitions for universal claim form data mapping", "Build standard schemas for cashless pre-auth parameters (hospital, policy details, procedure, cost).", "module:daavisetu,role:orchestration,phase:2"),
    ("DaaviSetu: Implement automated PDF form-field coordinate mapping tool", "Use PyPDF to scan form coordinates and map Kadi entities into PDF form fields dynamically.", "module:daavisetu,role:infra,phase:2"),
    ("DaaviSetu: Build claim package assembler zipping pre-auth PDF and bill copies", "Zip filled PDFs, scanned bill PDFs, and clinical notes into a secure consolidated package.", "module:daavisetu,role:infra,phase:2"),
    ("DaaviSetu: Implement OCR validation check on filled PDF fields prior to download", "Re-run a mock OCR parse on completed fields to ensure print readability before patient download.", "module:daavisetu,role:data-qa,phase:2"),
    ("DaaviSetu: Develop claim pre-population progress tracker UI", "Create a multi-step workflow in Next.js displaying real-time field filling progress.", "module:daavisetu,role:frontend,phase:2"),
    ("DaaviSetu: Implement automatic policy limit validation against estimated costs", "Flag procedures where estimated hospital costs exceed the policy holder's maximum sum insured.", "module:daavisetu,role:orchestration,phase:2"),

    # ---------------- Phase 3 — Entity resolution & integration ----------------
    ("String similarity scoring", "Edit distance / token overlap.", "module:kadi,role:orchestration,phase:3"),
    ("Integrate IndicXlit for transliteration matching", "pip install ai4bharat-transliteration" , "module:kadi,role:orchestration,phase:3"),
    ("Integrate IndicSBERT for cross-lingual semantic matching", "l3cube-pune/indic-sentence-similarity-sbert via sentence-transformers", "module:kadi,role:orchestration,phase:3"),
    ("Combine signals into confidence score + merge/ask/new-entity branching", "", "module:kadi,role:orchestration,phase:3"),
    ("Auto-triggering: fire module checks when Kadi has enough context", "", "module:kadi,role:orchestration,phase:3"),
    ("Consent UI — per-case opt-in for cross-module data sharing", "", "module:kadi,role:frontend,phase:3"),
    ("Cross-module insight display", "e.g. 'you may also be eligible under SchemeSetu' surfaced from a BillNyay upload.", "module:frontend,role:frontend,phase:3"),
    ("ABDM: Connect pulled medical history with Kadi shared case context", "Parse ABHA sandbox-pulled clinical records into case context.", "module:kadi,role:orchestration,phase:3"),
    ("DaaviSetu: Integrate with Kadi context layer", "Read case entities to pre-fill claim forms.", "module:daavisetu,role:orchestration,phase:3"),
    # Futuristic Phase 3 Issues
    ("KADI: Implement Real-Time Clinical Named Entity Recognition utilizing localized BioBERT", "Run local BioBERT models to extract detailed clinical findings and symptoms from case files.", "module:kadi,role:ocr-data,phase:3"),
    ("KADI: Develop Cross-Lingual Patient Semantic Knowledge Graph using GraphDB", "Wire Kadi entities into a graph structure linking hospital stays, procedures, and drugs.", "module:kadi,role:orchestration,phase:3"),
    ("KADI: Design Federated Privacy-Preserving Case Context Sharing via Zero-Knowledge Proofs", "Verify patient identity and consent parameters across nodes without decrypting case logs.", "module:kadi,role:infra,phase:3"),
    ("KADI: Build Self-Tuning Entity Resolution Confidence Thresholds using online RLHF", "Leverage doctor/patient feedback to fine-tune matching parameters dynamically.", "module:kadi,role:orchestration,phase:3"),
    ("KADI: Implement Cross-Script Soundex/Metaphone matching for Indian regional names", "Configure phonetic matching in IndicXlit to connect dialectic variations in Hindi/Marathi.", "module:kadi,role:orchestration,phase:3"),
    ("BillNyay: Implement predictive outcome estimation model for IRDAI appeals", "Generate probability scorecards for IRDAI complaints based on historical dispute results.", "module:billnyay,role:orchestration,phase:3"),
    ("DawaCheck: Develop generic medicines awareness delivery statistics logging", "Store anonymous patient metrics detailing MRP pricing awareness to generate impact statistics.", "module:dawacheck,role:data-qa,phase:3"),
    ("SchemeSetu: Design consent-bounded scheme recommendation triggers", "Trigger background eligibility runs whenever case income data falls below defined thresholds.", "module:schemesetu,role:orchestration,phase:3"),

    # ---------------- Phase 4 — Multilingual & QA ----------------
    ("Build Devanagari OCR test set", "Real + synthetic self-donated documents.", "module:data-qa,role:data-qa,phase:4"),
    ("Build labeled entity-pair dataset", "For tuning entity-resolution confidence thresholds.", "module:data-qa,role:data-qa,phase:4"),
    ("Terminology QA pass on appeal letters & scheme explanations", "Hindi + Marathi.", "module:data-qa,role:data-qa,phase:4"),
    ("Trilingual UI pass across all screens", "English/Hindi/Marathi.", "module:frontend,role:frontend,phase:4"),
    ("LLM output generation in Hindi/Marathi per module", "Where source data is English-only, per Phase 0 finding.", "module:billnyay,module:schemesetu,module:dawacheck,role:orchestration,phase:4"),
    # Futuristic Phase 4 Issues
    ("KADI: Design Differential Privacy noise addition for aggregate health statistics export", "Enable safe, anonymous medical statistical exports without exposing individual patient case records.", "module:kadi,role:data-qa,phase:4"),
    ("BillNyay: Develop Hindi & Marathi custom prompt injection sanitization layer for Devanagari", "Filter Devanagari text input strings to prevent prompt injections during local LLM translation.", "module:billnyay,role:data-qa,phase:4"),
    ("SchemeSetu: Design automated regional dialect normalization agent", "Map regional Marathi variations (e.g. Varhadi dialect) to standard Marathi scheme terminology.", "module:schemesetu,role:orchestration,phase:4"),
    ("SchemeSetu: Develop Devanagari-grounded RAG retrieval verification agent", "Validate that translated Marathi/Hindi citations map precisely to original English scheme parameters.", "module:schemesetu,role:data-qa,phase:4"),
    ("DawaCheck: Implement interactive prescription translator", "Parse shorthand doctor instructions (TDS, BD, QD) into local regional language prescriptions.", "module:dawacheck,role:orchestration,phase:4"),

    # ---------------- Phase 5 — Polish & submission ----------------
    ("Decide & set up deployment target", "College server / cloud free-tier / local demo.", "module:infra,role:infra,phase:5"),
    ("End-to-end demo flow polish", "One bill upload -> three module insights, for the live demo.", "module:frontend,role:frontend,phase:5"),
    ("Blackbook / final report drafting", "Once guide sign-off on final scope confirmed.", "module:data-qa,role:data-qa,phase:5"),
    ("Ask guide if anything additional is expected", "Once core build is stable ahead of schedule.", "phase:5"),
    # Futuristic Phase 5 Issues
    ("BillNyay: Develop interactive conversational audit walkthrough UI", "Enable a conversational interface in Next.js allowing patients to chat with the Judge agent.", "module:billnyay,role:frontend,phase:5"),
    ("BillNyay: Design real-time billing anomalies visualization dashboard", "Implement responsive dashboards using HSL colors mapping deviations from the CGHS benchmark.", "module:billnyay,role:frontend,phase:5"),
    ("SchemeSetu: Develop eligibility RAG citation tracing UI", "Embed dynamic source citation views in Next.js enabling inline viewing of source PDF clauses.", "module:schemesetu,role:frontend,phase:5"),
    ("DaaviSetu: Design secure client-side document package encryption using Web Crypto API", "Ensure all download packages are encrypted client-side with patient-controlled passwords.", "module:daavisetu,role:infra,phase:5"),
    # Evaluation & Testing Issues
    ("Eval: Implement automated pipeline for calculating Procedure Extraction Accuracy (PEA) on BillNyay mock bills", "PEA = (Correctly Extracted Procedures / Total Procedures) * 100. Target: > 95%", "module:billnyay,role:data-qa,phase:4"),
    ("Eval: Implement evaluation harness for Benchmark Mapping Accuracy (BMA) comparing hospital procedures to CGHS codes", "BMA = (Correctly Mapped Procedures / Total Extracted Procedures) * 100. Target: > 92%", "module:billnyay,role:data-qa,phase:4"),
    ("Eval: Measure Billing Anomaly Precision, Recall, and F1-score on synthetic overcharged bill data", "Precision = TP / (TP+FP), Recall = TP / (TP+FN). Target: > 90%", "module:billnyay,role:data-qa,phase:4"),
    ("Eval: Establish evaluation framework for DaaviSetu Policy Clause Retrieval Accuracy (PCRA) using RAG test sets", "PCRA = (Correctly Retrieved Clauses / Total Relevant Clauses) * 100. Target: > 90%", "module:daavisetu,role:data-qa,phase:4"),
    ("Eval: Implement validation suite for DaaviSetu Claim Rejection Mapping Accuracy (CRMA)", "CRMA = (Correctly Mapped Rejection Reasons / Total Rejection Reasons) * 100. Target: > 90%", "module:daavisetu,role:data-qa,phase:4"),
    ("Eval: Implement automated completeness scoring for generated IRDAI appeal drafts using a weighted checklist", "Check completeness of Appeal details: Patient Details (15%), Policy Info (20%), Clauses (30%), Justification (25%), References (10%)", "module:billnyay,role:data-qa,phase:4"),
    ("Eval: Implement testing harness for DawaCheck Medicine Recognition Accuracy comparing prescription OCR to ground truth", "Medicine Recognition Accuracy = (Correctly Recognized Medicines / Total Medicines) * 100. Target: > 95%", "module:dawacheck,role:data-qa,phase:4"),
    ("Eval: Measure DawaCheck NPPA price mapping accuracy and price deviation detection rates", "NPPA Accuracy = (Correctly Mapped Medicines / Total Medicines) * 100.", "module:dawacheck,role:data-qa,phase:4"),
    ("Eval: Implement ranking evaluation (MRR - Mean Reciprocal Rank) for SchemeSetu recommendation engine", "MRR = (1/N) * sum(1/Rank_i) to evaluate ranking quality of schemes.", "module:schemesetu,role:data-qa,phase:4"),
    ("Eval: Implement RAG precision and recall evaluation for SchemeSetu recommendations", "Recommendation Precision & Recall calculations on test database.", "module:schemesetu,role:data-qa,phase:4"),
    ("Eval: Build KADI integration metrics suite to measure Context Reuse Ratio (CRR) and Duplicate Processing Reduction (DPR)", "CRR = (Reused Context Requests / Total Context Requests) * 100. DPR = ((Baseline Processing - Current Processing) / Baseline Processing) * 100.", "module:kadi,role:data-qa,phase:4"),
    ("Eval: Implement testing harness for KADI Entity Resolution Accuracy (ERA) using fuzzy matched names", "ERA = (Correctly Merged Duplicate Entities / Total Duplicate Entities) * 100.", "module:kadi,role:data-qa,phase:4"),
    ("Eval: Implement OCR benchmark suite calculating Word Error Rate (WER) and Character Error Rate (CER)", "Evaluate OCR digitization performance using Edit Distance against ground truth.", "module:kadi,role:data-qa,phase:4"),
    ("Eval: Develop validation suite to calculate AI Hallucination Rate and Grounding Scores on generated legal letters", "Hallucination Rate < 2%, Grounding Score > 95%.", "module:billnyay,role:data-qa,phase:4"),
    ("Eval: Implement system-level latency monitoring to verify End-to-End Processing Time (< 10 seconds)", "E2E processing time dashboard and metric collection hook.", "module:infra,role:infra,phase:4"),
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
