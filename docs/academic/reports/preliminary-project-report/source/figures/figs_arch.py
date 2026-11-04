from svglib import *
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "."


def fig_arch():
    f = Fig(1200, 790)
    # clients
    f.group(20, 15, 1160, 118, "Clients (apps/web · apps/mobile)")
    f.box(50, 45, 330, 72, "Web client", ["Next.js 16.4 · React 19 · TypeScript", "EN / हिंदी / मराठी · light & dark"], fill=WHITE)
    f.box(435, 45, 330, 72, "Mobile client", ["Expo SDK 52 · React Native 0.76", "camera capture · offline action queue"], fill=WHITE)
    f.box(820, 45, 330, 72, "Reviewer workspace", ["/clinical-review (web)", "header-only bearer credentials"], fill=WHITE)
    for x in (215, 600, 985):
        f.line(x, 117, x, 160, both=True)
    f.label(600, 148, "REST/JSON  ·  Server-Sent Events  ·  X-Case-Access-Token header", 12)
    # API
    f.group(20, 162, 1160, 230, "apps/api — FastAPI modular monolith (one process, ADR-019/021)")
    f.box(45, 195, 255, 82, "Middleware", ["request id · JSON logs", "rate limit · CORS · headers"], fill=WHITE)
    f.box(315, 195, 560, 82, "Versioned route modules  /api/v1/…", ["kadi · billnyay · daavisetu · bimanyay · schemesetu · dawacheck", "99 paths / 109 operations (OpenAPI snapshot test)"], fill=WHITE)
    f.box(890, 195, 265, 82, "Access control", ["case token (SHA-256 hash, ADR-009)", "consent gate (ADR-003)"], fill=TERRAL, stroke=TERRA)
    f.box(45, 292, 560, 82, "Application services  (app/services, ADR-018)", ["case ingestion · document jobs · billnyay audit/appeal", "dawacheck benchmarks · schemesetu eligibility · case purge"], fill=SAGE2)
    f.box(620, 292, 535, 82, "Background work (in-process)", ["document job state + restart reconciliation", "auto-triggers · 90-day retention sweep · SSE status"], fill=SAGE2)
    f.line(600, 392, 600, 420)
    # packages
    f.group(20, 420, 1160, 210, "Framework-free domain packages (packages/*, pip install -e)")
    xs = [45, 268, 491, 714, 937]
    names = [("BillNyay", "bill audit · appeals"), ("DaaviSetu", "pre-auth · readiness"), ("BimaNyay", "denial audit · SLAs"),
             ("SchemeSetu", "PM-JAY / MJPJAY"), ("DawaCheck", "NPPA ceilings")]
    for x, (n, s) in zip(xs, names):
        f.box(x, 455, 210, 62, n, [s], fill=WHITE)
        f.line(x + 105, 517, x + 105, 545)
    f.box(45, 545, 1102, 70, "Kadi — shared intelligence layer", ["OCR (PyMuPDF / EasyOCR) · line items · extraction (Groq or heuristic) · PII redaction · entity resolution",
                                                                    "clinical review & safety governance · explanation trail · case timeline · FHIR R4 import · triggers"],
          fill=SAGE, lfs=12.5)
    # data & external
    f.group(20, 655, 700, 120, "State and reference data")
    f.box(40, 688, 300, 72, "PostgreSQL 16", ["27 module-prefixed tables", "Alembic migrations (ADR-020)"], fill=SLATEL, stroke=SLATE)
    f.box(355, 688, 350, 72, "Packaged reference tables", ["CGHS subset (27) · NPPA subset (7)", "scheme criteria · law library (cited)"], fill=SLATEL, stroke=SLATE)
    f.group(740, 655, 440, 120, "External (optional)", dash=True)
    f.box(760, 688, 195, 72, "Groq API", ["GROQ_MODEL", "openai/gpt-oss-120b"], fill=BRASSL, stroke=BRASS, dash=True)
    f.box(970, 688, 195, 72, "Hugging Face Hub", ["IndicSBERT weights", "off by default"], fill=BRASSL, stroke=BRASS, dash=True)
    f.line(330, 630, 330, 655)
    f.line(860, 630, 860, 655, dash=True)
    return f.save("fig_arch", OUT)


def fig_layers():
    f = Fig(1100, 470)
    f.text(550, 28, "Allowed import direction (arrows) — enforced by import-linter, 5 contracts kept", 14, color=FOREST, weight="600")
    f.box(330, 50, 440, 64, "Route modules  (app/api/v1/endpoints)", ["thin HTTP layer · never import each other"], fill=WHITE)
    f.box(330, 150, 440, 64, "Application services  (app/services)", ["use cases shared by >1 entry point"], fill=SAGE2)
    f.box(60, 150, 230, 64, "App infrastructure", ["models · database · consent · auth"], fill=SLATEL, stroke=SLATE)
    f.line(550, 114, 550, 150); f.line(400, 114, 250, 150)
    f.line(330, 182, 290, 182)
    xs = [60, 260, 460, 660, 860]
    for x, n in zip(xs, ["billnyay", "daavisetu", "bimanyay", "schemesetu", "dawacheck"]):
        f.box(x, 270, 180, 54, n, [], fill=WHITE, fs=14)
        f.line(x + 90, 324, x + 90, 372)
    f.line(550, 214, 550, 270)
    f.line(470, 214, 150, 270); f.line(630, 214, 950, 270)
    f.box(60, 372, 980, 60, "kadi  (shared layer — depends on no domain module)", [], fill=SAGE, fs=14.5)
    f.text(1050, 300, "✕", 20, color=TERRA, weight="700")
    f.label(950, 254, "domain ↔ domain imports forbidden", 11.5, TERRA)
    f.label(550, 455, "Packages import neither FastAPI nor SQLAlchemy nor app.*", 12, GREY)
    return f.save("fig_layers", OUT)


def fig_sequence():
    f = Fig(1200, 700)
    lanes = [("Patient client", 90), ("API route", 290), ("Job state", 470), ("Kadi pipeline", 650), ("Module services", 850), ("Database", 1060)]
    for n, x in lanes:
        f.box(x - 85, 15, 170, 44, n, [], fill=SAGE if n != "Database" else SLATEL, stroke=FOREST if n != "Database" else SLATE, fs=14)
        f.line(x, 59, x, 690, color=BORDER, sw=1.2, dash=True, arrow=False)
    f.rect(615, 255, 70, 100, fill=TERRAL, stroke=TERRA, r=6, dash=True)
    f.text(650, 248, "bytes in RAM", 11, color=TERRA, italic=True)
    f.text(650, 370, "raw file discarded", 11, color=TERRA, italic=True)
    steps = [
        (90, 290, 90, "POST /kadi/cases  (consent_opt_in)"),
        (290, 90, 120, "case id + access token (shown once)"),
        (90, 290, 160, "POST /cases/{id}/upload  (file in request body)"),
        (290, 470, 195, "create kadi_document_jobs row"),
        (290, 90, 230, "202 Accepted"),
        (290, 650, 270, "background task: bytes stay in RAM"),
        (650, 650, 305, "OCR → line items → extraction"),
        (650, 650, 340, "redact PII · ground medicine lines"),
        (650, 1060, 395, "resolve + persist entities"),
        (650, 850, 430, "auto-triggers (if consent)"),
        (850, 1060, 462, "store kadi_module_insights"),
        (650, 470, 495, "job → completed (or failed / interrupted)"),
        (90, 290, 530, "GET /cases/{id}/stream  (SSE)"),
        (290, 90, 565, "stage events: ocr_start … module_checks … completed"),
        (90, 290, 610, "module calls with X-Case-Access-Token"),
        (290, 90, 650, "findings + explanation trail"),
    ]
    for a, b, y, s in steps:
        if a == b:
            f.path([(a, y - 12), (a + 60, y - 12), (a + 60, y + 4), (a + 4, y + 4)])
            f.label(a + 66, y - 1, s, 12, GRAPH, "start")
        else:
            f.line(a + (6 if b > a else -6), y, b - (6 if b > a else -6), y, color=FOREST2 if b > a else GREY)
            f.label((a + b) / 2, y - 6, s, 12, GRAPH)
    return f.save("fig_sequence", OUT)


def fig_erd():
    f = Fig(1200, 640)

    def ent(x, y, name, cols, w=230, fill=WHITE, stroke=FOREST):
        h = 30 + 19 * len(cols) + 8
        f.rect(x, y, w, h, fill, stroke, 6, 1.4)
        f.add(f'<rect x="{x}" y="{y}" width="{w}" height="30" rx="6" fill="{stroke}"/>')
        f.text(x + w / 2, y + 20, name, 13.5, color=WHITE, weight="600")
        for i, c in enumerate(cols):
            f.text(x + 10, y + 48 + 19 * i, c, 12, "start", GRAPH if not c.startswith("FK") else FOREST2)
        return (x, y, w, h)

    a = ent(470, 20, "kadi_cases", ["PK id  (CASE-<64-bit hex>)", "access_token_hash (SHA-256)", "consent_opt_in", "total_charged", "expires_at  (TTL sweep)"], w=260)
    b = ent(40, 30, "kadi_entities", ["PK id", "entity_type", "name / value / meta", "meta.mentions[]"])
    c = ent(40, 230, "kadi_case_documents", ["PK id · FK case_id", "sha256 digest only", "(never the file)"])
    d = ent(40, 400, "kadi_resolution_decisions", ["PK id · FK case_id", "decision: merge / ask / new", "status: pending / confirmed"])
    e = ent(470, 230, "kadi_document_jobs", ["PK id · FK case_id", "state: queued … completed", "interrupted on restart"], w=260)
    g = ent(470, 400, "kadi_module_insights", ["PK id · FK case_id", "module · check · result", "status / error id"], w=260)
    h = ent(900, 20, "billnyay_appeals", ["PK id · FK case_id", "letter text · pdf_bytes", "integrity HMAC"], w=260, stroke=FOREST2)
    i = ent(900, 165, "daavisetu_claims", ["PK id · FK case_id", "pre-auth form data", "playbook / institution"], w=260, stroke=FOREST2)
    j = ent(900, 310, "schemesetu_case_profiles", ["PK id · FK case_id", "opt-in income profile", "state of residence"], w=260, stroke=FOREST2)
    k = ent(900, 455, "kadi_clinical_reviews", ["PK id · FK case_id", "reviewer · COI declared", "→ statements (versioned)"], w=260, stroke=SLATE)
    # relations
    f.line(470, 70, 270, 70, both=False); f.label(370, 62, "1 — N (via case link)", 11)
    f.path([(470, 120), (380, 120), (380, 270), (270, 270)]); f.label(380, 200, "1 — N", 11)
    f.path([(470, 140), (400, 140), (400, 445), (270, 445)]); f.label(400, 390, "1 — N", 11)
    f.line(600, 153, 600, 230); f.label(600, 195, "1 — N", 11)
    f.path([(730, 120), (760, 120), (760, 445), (730, 445)]); f.label(760, 380, "1 — N", 11)
    for yy in (60, 205, 350, 495):
        f.path([(730, 60), (830, 60), (830, yy), (900, yy)])
    f.label(830, 160, "1 — 0..N", 11)
    f.text(600, 600, "Separate domain: bimanyay_cases / _grievances / _timeline_events (own UUID; case-linked records purged with the case).  "
                     "27 tables in total, all module-prefixed.", 12, color=GREY, italic=True)
    return f.save("fig_erd", OUT)


def fig_security():
    f = Fig(1200, 430)
    f.box(20, 150, 150, 80, "Request", ["case id + token"], fill=WHITE)
    stages = [("Rate limit", "per-client IP, 120/min", WHITE, FOREST),
              ("Case access", "hash compare, constant time", TERRAL, TERRA),
              ("Consent gate", "cross-module reads only", TERRAL, TERRA),
              ("Route / service", "module logic", SAGE, FOREST)]
    x = 210
    for n, s, fl, st in stages:
        f.box(x, 150, 200, 80, n, [s], fill=fl, stroke=st)
        f.line(x - 40, 190, x - 2, 190)
        x += 240
    f.text(210 + 100, 260, "429 Retry-After", 12, color=TERRA)
    f.text(450 + 100, 260, "401 no token · 403 mismatch", 12, color=TERRA)
    f.text(690 + 100, 260, "403 without opt-in", 12, color=TERRA)
    f.group(20, 300, 1160, 115, "Data-minimisation controls that apply to every path")
    items = [("BYOD", "file bytes in RAM only"), ("Redaction", "names, phone, Aadhaar, PAN"), ("Digest only", "SHA-256 for duplicates"),
             ("Erasure", "DELETE case + 90-day TTL"), ("Logs", "route templates, no input"), ("Prompt safety", "random fences per call")]
    for i, (n, s) in enumerate(items):
        f.box(40 + i * 190, 335, 175, 62, n, [s], fill=WHITE, fs=13.5, lfs=11.5)
    f.group(20, 15, 1160, 115, "Accepted, disclosed risks (ADR-008/013)", fill=BRASSL, stroke=BRASS, lc=BRASS)
    f.text(40, 62, "• No user accounts: the per-case token is authorisation, not identity.", 13, "start")
    f.text(40, 86, "• Single local deployment only; public hosting needs real authentication, TLS and a data-protection review first.", 13, "start")
    f.text(40, 110, "• The token in an SSE query string (EventSource cannot set headers) is limited to the stream route.", 13, "start")
    return f.save("fig_security", OUT)


def fig_deploy():
    f = Fig(1200, 380)
    f.group(20, 15, 560, 350, "Supported today: local demo (ADR-013)")
    f.box(45, 60, 250, 70, "web container", ["Next.js production build", "127.0.0.1:3000"], fill=WHITE)
    f.box(310, 60, 250, 70, "api container", ["Uvicorn, 1 worker, non-root", "127.0.0.1:8000"], fill=WHITE)
    f.box(310, 170, 250, 70, "postgres container", ["pgvector/pgvector:pg16 image", "127.0.0.1 only"], fill=SLATEL, stroke=SLATE)
    f.box(45, 170, 250, 70, "hf_cache volume", ["IndicSBERT weights (opt.)"], fill=MUTED, stroke=BORDER, dash=True)
    f.line(295, 95, 310, 95); f.line(435, 130, 435, 170)
    f.text(300, 290, "docker-compose.yml + docker-compose.demo.yml", 12.5, color=GREY)
    f.text(300, 312, "multi-stage images · CPU-only torch pin · guardrails check bindings", 12.5, color=GREY)
    f.group(620, 15, 560, 350, "Validated, not deployed: Kubernetes path (ADR-021)", dash=True)
    f.box(645, 60, 510, 70, "kustomize base + example overlay", ["rendered and policy-tested in CI (tests/infrastructure)"], fill=WHITE, dash=True)
    f.box(645, 150, 245, 70, "api Deployment", ["replicas: 1 (no HPA/PDB)"], fill=WHITE, dash=True)
    f.box(910, 150, 245, 70, "Probes", ["/health/live · /health/ready"], fill=WHITE, dash=True)
    f.box(645, 240, 510, 70, "Migration Job", ["alembic upgrade head before rollout"], fill=WHITE, dash=True)
    f.text(900, 340, "One replica by design: document bytes cannot be queued durably (BYOD).", 12, color=TERRA, italic=True)
    return f.save("fig_deploy", OUT)


if __name__ == "__main__":
    for fn in [fig_arch, fig_layers, fig_sequence, fig_erd, fig_security, fig_deploy]:
        print(fn())
