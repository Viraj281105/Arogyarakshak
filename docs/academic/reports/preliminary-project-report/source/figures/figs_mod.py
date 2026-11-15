from svglib import *
import sys
OUT = sys.argv[1] if len(sys.argv) > 1 else "."


def fig_problem():
    f = Fig(1200, 330)
    steps = [("Admission", "treatment begins", None), ("Cashless pre-auth", "form + documents", "DaaviSetu"),
             ("Itemised bill", "lines vs fair rates?", "BillNyay"), ("Claim denied", "clause + deadline?", "BimaNyay"),
             ("Discharge medicines", "MRP vs ceiling?", "DawaCheck")]
    x = 20
    for i, (t, s, m) in enumerate(steps):
        f.box(x, 40, 205, 76, t, [s], fill=WHITE if m is None else SAGE)
        if m:
            f.pill(x + 102 - len(m) * 3.6 - 10, 132, m)
        if i < 4:
            f.line(x + 205, 78, x + 243, 78)
        x += 243
    f.rect(20, 190, 1160, 62, BRASSL, BRASS, 8)
    f.text(600, 216, "Across the whole journey: is the family covered by PM-JAY or MJPJAY at all?", 14.5, color=GRAPH, weight="600")
    f.text(600, 238, "SchemeSetu", 13, color=BRASS, weight="700")
    f.text(600, 290, "Every step produces a document the patient must read, check against a public rule, and act on — usually in English,", 13, color=GREY, italic=True)
    f.text(600, 310, "under time pressure, with no single place that connects them. Kadi is that connecting layer.", 13, color=GREY, italic=True)
    f.text(20, 24, "PATIENT'S ADMINISTRATIVE JOURNEY", 12.5, "start", FOREST, "700")
    return f.save("fig_problem", OUT)


def ell(f, cx, cy, s, rx=150, ry=22, fill=WHITE):
    f.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{FOREST}" stroke-width="1.3"/>')
    f.text(cx, cy + 5, s, 12.5)


def actor(f, x, y, name):
    f.add(f'<circle cx="{x}" cy="{y}" r="11" fill="none" stroke="{GRAPH}" stroke-width="1.6"/>')
    f.add(f'<path d="M{x} {y+11} L{x} {y+42} M{x-18} {y+22} L{x+18} {y+22} M{x} {y+42} L{x-14} {y+64} M{x} {y+42} L{x+14} {y+64}" '
          f'stroke="{GRAPH}" stroke-width="1.6" fill="none"/>')
    for i, part in enumerate(name.split("\n")):
        f.text(x, y + 84 + i * 16, part, 12.5, weight="600")


def fig_usecase():
    f = Fig(1200, 640)
    f.rect(190, 15, 820, 610, MUTED, BORDER, 12)
    f.text(600, 40, "ArogyaRakshak", 15, color=FOREST, weight="700")
    left = ["Create case and choose consent", "Upload bill / letter / prescription", "Follow live processing (SSE)",
            "Audit hospital bill vs CGHS", "Draft dispute or appeal letter", "Check pre-auth readiness, fill form",
            "Analyse denial, compute deadlines", "Check PM-JAY / MJPJAY eligibility", "Check medicine price vs NPPA",
            "Download Claim Pack / delete case"]
    right = ["Review delegated evidence (after COI)", "Write versioned clinical statement", "Resolve uncertain OCR reading",
             "Approve or retire safety rules", "Reset demo / load Scenario A–E"]
    for i, s in enumerate(left):
        ell(f, 420, 75 + i * 54, s, rx=190)
    for i, s in enumerate(right):
        ell(f, 820, 120 + i * 95, s, rx=170)
    actor(f, 95, 250, "Patient /\ncaregiver")
    for i in range(len(left)):
        f.line(115, 290, 230, 75 + i * 54, color=BORDER, sw=1.1, arrow=False)
    acts = [("Clinical\nreviewer", 70, (0, 1)), ("Pharmacist /\ntranscriptionist", 225, (2,)),
            ("Governance\nboard member", 380, (3,)), ("Demo\noperator", 545, (4,))]
    for name, y, idx in acts:
        actor(f, 1100, y - 40, name)
        for j in idx:
            f.line(1080, y - 10, 990, 120 + j * 95, color=BORDER, sw=1.1, arrow=False)
    f.add(f'<path d="M 610 290 C 640 250, 640 170, 650 140" stroke="{GREY}" fill="none" stroke-dasharray="5 4" stroke-width="1.2" marker-end="url(#ah)"/>')
    f.label(655, 266, "«delegates one review»", 11, GREY, "start")
    return f.save("fig_usecase", OUT)


def fig_workflow():
    f = Fig(1200, 420)
    f.box(20, 150, 150, 90, "Upload", ["photo · PDF · text", "web or mobile"], fill=WHITE)
    f.box(205, 150, 150, 90, "Consent", ["opt-in per case", "default: off"], fill=TERRAL, stroke=TERRA)
    f.box(390, 130, 200, 130, "Kadi", ["OCR · extraction", "redaction · resolution", "duplicate questions", "auto-triggered checks"], fill=SAGE)
    f.line(170, 195, 205, 195); f.line(355, 195, 390, 195)
    mods = [("BillNyay", "line audit · appeal PDF"), ("DaaviSetu", "readiness · pre-auth form"), ("BimaNyay", "violations · 3 drafts · dates"),
            ("SchemeSetu", "eligibility + trace"), ("DawaCheck", "per-unit vs ceiling")]
    for i, (n, s) in enumerate(mods):
        y = 20 + i * 78
        f.box(660, y, 230, 64, n, [s], fill=WHITE)
        f.path([(590, 195), (625, 195), (625, y + 32), (660, y + 32)])
    f.box(940, 110, 240, 170, "Patient-facing output", ["finding + explanation trail", "provenance label", "plain-language summary", "(optional read-aloud)", "Claim Pack ZIP"], fill=BRASSL, stroke=BRASS)
    for i in range(5):
        y = 20 + i * 78 + 32
        f.path([(890, y), (915, y), (915, 195), (940, 195)])
    f.text(600, 410, "Clinical facts route to a human reviewer; uncertain handwriting routes to two blind readers before any price is compared.", 12.5, color=GREY, italic=True)
    return f.save("fig_workflow", OUT)


def fig_kadi():
    f = Fig(1200, 400)
    st = [("1  Read", ["PDF: PyMuPDF text", "image: EasyOCR (en)", "segment confidences"]),
          ("2  Line items", ["shared regex parser", "summary rows dropped", "Indian digit grouping"]),
          ("3  Extract", ["Groq LLM → JSON", "or heuristic fallback", "hospital · Dx · Px · meds"]),
          ("4  Ground & redact", ["medicine ↔ source line", "price facts kept", "PII removed from excerpt"]),
          ("5  Resolve", ["block by case + type", "merge / ask / new", "SHA-256 duplicate check"]),
          ("6  Persist & trigger", ["entities + decisions", "consent-gated checks", "timeline events"])]
    for i, (t, ls) in enumerate(st):
        x = 20 + i * 196
        f.box(x, 40, 176, 120, t, ls, fill=SAGE if i % 2 == 0 else WHITE, lfs=12)
        if i < 5:
            f.line(x + 176, 100, x + 196, 100)
    f.text(20, 26, "IN MEMORY ONLY — THE FILE NEVER TOUCHES DISK", 12, "start", TERRA, "700")
    f.rect(20, 180, 560, 92, TERRAL, TERRA, 8)
    f.text(300, 205, "Low-confidence OCR segment linked to exactly one medicine", 13, weight="600")
    f.text(300, 228, "→ transcription task (redacted text + bounding box, no image)", 12.5, color=GREY)
    f.text(300, 250, "→ medicine held back from DawaCheck until two blind readings agree", 12.5, color=GREY)
    f.line(108, 160, 108, 180)
    f.rect(620, 180, 560, 92, SLATEL, SLATE, 8)
    f.text(900, 205, "Upload-time safety scan over the full text (active rules)", 13, weight="600")
    f.text(900, 228, "stores rule id / version / matched terms only", 12.5, color=GREY)
    f.text(900, 250, "→ escalation card for red-flag terms (decision-support floor)", 12.5, color=GREY)
    f.line(700, 160, 700, 180)
    f.rect(20, 292, 1160, 92, MUTED, BORDER, 8)
    f.text(600, 318, "Also in Kadi: FHIR R4 bundle import (client-supplied ABDM-style records) · case graph projection (no graph DB) ·", 12.5, color=GRAPH)
    f.text(600, 340, "explanation-trail type shared by all modules · case timeline from persisted records · clinical-review lifecycle", 12.5, color=GRAPH)
    f.text(600, 364, "Degraded mode is explicit: without GROQ_API_KEY, extraction is heuristic and the API logs that it is running degraded.", 12, color=GREY, italic=True)
    return f.save("fig_kadi", OUT)


def fig_resolution():
    f = Fig(1200, 430)
    f.box(20, 160, 150, 70, "New mention", ["e.g. क्रोसिन 500"], fill=WHITE)
    f.box(200, 160, 160, 70, "Blocking", ["same case,", "same entity type"], fill=WHITE)
    f.line(170, 195, 200, 195)
    sig = [("Lexical  w=0.9", "Levenshtein · core-token Jaccard"), ("Phonetic  w=0.7", "Devanagari romanisation + Indic key"),
           ("Semantic  w=0.5", "IndicSBERT · optional, off by default")]
    for i, (t, s) in enumerate(sig):
        y = 70 + i * 90
        f.box(400, y, 260, 70, t, [s], fill=SAGE if i < 2 else BRASSL, stroke=FOREST if i < 2 else BRASS, dash=(i == 2))
        f.path([(360, 195), (380, 195), (380, y + 35), (400, y + 35)])
        f.path([(660, y + 35), (685, y + 35), (685, 195), (700, 195)])
    f.box(700, 150, 190, 90, "Noisy-OR", ["c = 1 − Π(1 − wᵢ·sᵢ)"], fill=WHITE, fs=15)
    f.box(700, 20, 190, 100, "Hard guards", ["strength · form · side", "variant letter", "hyper-/hypo-"], fill=TERRAL, stroke=TERRA)
    f.line(795, 120, 795, 150)
    outs = [("MERGE", "c ≥ 0.90 on lexical+phonetic alone", FOREST), ("ASK USER", "c ≥ 0.70, or semantic lift, or 2+ candidates", BRASS),
            ("NEW ENTITY", "otherwise, or any guard conflict", GREY)]
    for i, (t, s, col) in enumerate(outs):
        y = 70 + i * 90
        f.box(930, y, 250, 70, t, [s], fill=WHITE, stroke=col, tc=col, lfs=11.5)
        f.path([(890, 195), (910, 195), (910, y + 35), (930, y + 35)])
    f.path([(1055, 350), (1055, 395), (295, 395), (295, 230)], dash=True)
    f.label(675, 390, "user confirms / rejects → labels → bounded recalibration (≥30 labels, ±0.05 per step) — not RLHF", 12, GRAPH)
    return f.save("fig_resolution", OUT)


def fig_billnyay():
    f = Fig(1200, 470)
    f.text(20, 24, "DETERMINISTIC AUDIT (ALWAYS ON)", 12, "start", FOREST, "700")
    f.box(20, 40, 200, 80, "Case line items", ["from Kadi"], fill=WHITE)
    f.box(250, 40, 240, 80, "CGHS key match", ["27-entry reference table", "bundled-item rules"], fill=SAGE)
    f.box(520, 40, 240, 80, "Rate basis", ["per day / visit / session", "needs a stated count"], fill=SAGE)
    f.box(790, 40, 180, 80, "Line verdict", ["within · above ·", "not benchmarked"], fill=WHITE)
    f.box(1000, 40, 180, 80, "ICD-10 ↔ procedure", ["plausibility (curated)", "never 'necessity'"], fill=SLATEL, stroke=SLATE)
    for a, b in ((220, 250), (490, 520), (760, 790)):
        f.line(a, 80, b, 80)
    f.text(20, 162, "APPEAL DRAFTING CHAIN (GROQ WHEN CONFIGURED; OFFLINE TEMPLATE OTHERWISE)", 12, "start", FOREST, "700")
    ag = [("Auditor", "structured denial"), ("Clinician", "rationale, unverifiable\ncitations stripped"), ("Regulatory", "law library entries\nwith provenance")]
    for i, (t, s) in enumerate(ag):
        x = 20 + i * 210
        f.box(x, 180, 185, 86, t, s.split("\n"), fill=WHITE)
        if i < 2:
            f.line(x + 185, 223, x + 210, 223)
    f.box(660, 180, 160, 86, "Consensus", ["weighted votes", "(triage only)"], fill=BRASSL, stroke=BRASS)
    f.line(605, 223, 660, 223)
    f.box(850, 180, 150, 86, "Barrister", ["letter (en/hi/mr)"], fill=SAGE)
    f.line(820, 223, 850, 223)
    f.box(1030, 180, 150, 86, "Judge", ["deterministic", "scorecard"], fill=SAGE)
    f.line(1000, 223, 1030, 223)
    f.path([(1105, 266), (1105, 300), (925, 300), (925, 266)], dash=True)
    f.label(1015, 316, "needs_revision → critique → redraft (bounded)", 11.5, GRAPH)
    f.box(850, 350, 330, 90, "Appeal PDF", ["ReportLab · SHA-256 + HMAC integrity", "provenance footer · clinician annex verbatim"], fill=BRASSL, stroke=BRASS)
    f.line(1105, 300, 1105, 350)
    f.rect(20, 300, 790, 140, MUTED, BORDER, 8)
    f.text(40, 326, "Safeguards built into the chain", 13.5, "start", FOREST, "700")
    for i, s in enumerate(["• Every document-derived string is wrapped in a random, per-call fence (prompt-injection defence).",
                           "• The Judge checks the letter against the case's own facts; it no longer returns fixed scores.",
                           "• No clinician's opinion may be implied; human statements enter only verbatim, through the annex.",
                           "• A probability of success is refused unless a cited, non-synthetic dispute dataset exists (#90)."]):
        f.text(40, 352 + i * 22, s, 12.5, "start")
    return f.save("fig_billnyay", OUT)


def fig_pricebasis():
    f = Fig(1200, 330)
    f.box(20, 120, 170, 80, "Medicine entry", ["case line or", "manual form"], fill=WHITE)
    f.box(220, 120, 170, 80, "Trust gate", ["settled reading?", "(ADR-011)"], fill=TERRAL, stroke=TERRA)
    f.box(420, 120, 200, 80, "Find the basis", ["declaration · line text", "· document heading"], fill=SAGE)
    f.box(650, 40, 220, 80, "Convert to per-unit", ["only with a stated,", "whole unit count"], fill=SAGE)
    f.box(900, 40, 280, 80, "Compare with ceiling", ["within / above + deviation %", "explanation names the row"], fill=WHITE)
    f.box(650, 200, 530, 80, "CANNOT_COMPARE", ["unknown basis · pack size missing · contradictory counts · different dosage form", "→ no percentage, no verdict, a plain reason instead"], fill=BRASSL, stroke=BRASS)
    f.line(190, 160, 220, 160); f.line(390, 160, 420, 160)
    f.path([(620, 160), (635, 160), (635, 80), (650, 80)]); f.path([(620, 160), (635, 160), (635, 240), (650, 240)])
    f.line(870, 80, 900, 80)
    f.label(305, 236, "held back → human reading", 11.5, TERRA)
    f.text(600, 318, "Example that motivated the rule: “Dolo 650: ₹33” was once reported as +1,335% against the ₹2.30 per-tablet ceiling — it was a strip of 15 (₹2.20 per tablet).",
           12, color=GREY, italic=True)
    return f.save("fig_pricebasis", OUT)


def fig_bimanyay():
    f = Fig(1200, 330)
    f.line(60, 150, 1150, 150, color=FOREST, sw=3, arrow=True)
    pts = [(150, "Day 0", "Denial / representation", "entered by the patient"), (420, "Day 15", "Tier 1 — Insurer GRO", "response window"),
           (690, "Day 30", "Tier 2 — Bima Bharosa", "IRDAI portal review window"), (1000, "≤ 1 year", "Tier 3 — Insurance Ombudsman", "complaint limitation")]
    for x, d, t, s in pts:
        f.add(f'<circle cx="{x}" cy="150" r="9" fill="{WHITE}" stroke="{FOREST}" stroke-width="3"/>')
        f.text(x, 128, d, 14, color=FOREST, weight="700")
        f.box(x - 115, 175, 230, 64, t, [s], fill=SAGE if x > 150 else WHITE, fs=13.5, lfs=12)
    f.rect(20, 20, 1160, 70, MUTED, BORDER, 8)
    f.text(600, 46, "Clause auditor (category + policy age): PED / moratorium · investigation-only · room-rent · delayed intimation · general exclusion", 13, weight="600")
    f.text(600, 70, "Drafter: GRO letter · Bima Bharosa narrative (≤ 2,000 characters) · Ombudsman statement of facts — English, Hindi, Marathi", 12.5, color=GREY)
    f.text(600, 280, "Deadlines are counted in calendar days from the date the user enters and every milestone cites its source;", 12.5, color=GREY, italic=True)
    f.text(600, 300, "the explanation trail says so. Labels are the team's reading of the regulations, not legal advice.", 12.5, color=GREY, italic=True)
    return f.save("fig_bimanyay", OUT)


def fig_scheme_ready():
    f = Fig(1200, 380)
    f.group(20, 15, 560, 350, "SchemeSetu — rule engine with a reasoning trace")
    f.box(40, 55, 230, 70, "Inputs", ["state of residence", "(income recorded, not used)"], fill=WHITE)
    f.box(310, 55, 250, 70, "Dialect normaliser", ["महाराष्ट्र · Maharastra · Pune", "→ maharashtra"], fill=SAGE)
    f.line(270, 90, 310, 90)
    f.box(40, 165, 250, 95, "PM-JAY", ["always: verification needed", "SECC-2011 · ASHA/AWW/AWH", "family · age 70+"], fill=BRASSL, stroke=BRASS)
    f.box(310, 165, 250, 95, "MJPJAY", ["Maharashtra → provisionally", "eligible; else not applicable", "(GR 28 Jul 2023)"], fill=SAGE)
    f.path([(435, 125), (435, 145), (165, 145), (165, 165)]); f.line(435, 125, 435, 165)
    f.box(40, 285, 520, 60, "Output: verdict + step-by-step trace + criteria provenance + sources", [], fill=WHITE, fs=13)
    f.group(620, 15, 560, 350, "DaaviSetu — readiness, not approval")
    f.box(640, 55, 250, 70, "Case evidence", ["Kadi entities + excerpt"], fill=WHITE)
    f.box(910, 55, 250, 70, "Playbook", ["institution-private list", "(never shared across)"], fill=WHITE)
    f.box(640, 160, 520, 60, "Checklist item status", ["PRESENT  ·  MISSING  ·  NEEDS_CLINICAL_CONFIRMATION"], fill=SAGE)
    f.line(765, 125, 765, 160); f.line(1035, 125, 1035, 160)
    f.box(640, 250, 250, 95, "Doctor confirmation", ["fact confirmed by a", "named reviewer only"], fill=SLATEL, stroke=SLATE)
    f.box(910, 250, 250, 95, "Package", ["Annexure-B-style PDF", "ZIP + manifest · opt-in", "browser-side encryption"], fill=BRASSL, stroke=BRASS)
    f.line(765, 220, 765, 250); f.line(1035, 220, 1035, 250)
    return f.save("fig_scheme_ready", OUT)


def fig_method():
    f = Fig(1200, 300)
    st = [("Plan", "GitHub issue · labels", "phase milestone"), ("Build", "smallest change", "in the owning package"),
          ("Test", "pytest · tsx · tsc", "lint · contracts"), ("Verify", "running stack, browser", "demo smoke 58 checks"),
          ("Audit", "adversarial review", "honesty sweep"), ("Record", "PROJECT_CONTEXT · ADR", "CHANGELOG · docs")]
    cx, cy, R = 600, 150, 0
    for i, (t, a, b) in enumerate(st):
        x = 20 + i * 196
        f.box(x, 70, 170, 90, t, [a, b], fill=SAGE if i % 2 == 0 else WHITE, lfs=12)
        if i < 5:
            f.line(x + 170, 115, x + 196, 115)
    f.path([(1105, 160), (1105, 215), (105, 215), (105, 160)], dash=True)
    f.label(600, 220, "next issue — findings from audits re-enter the backlog as defects, never silently", 12.5, GRAPH)
    f.text(600, 40, "Iterative, issue-driven cycle used across Phases 1–4 (each pass closes only with tests and documentation updated)", 13.5, color=FOREST, weight="600")
    f.text(600, 270, "CI gates on every PR: guardrails 8 · Ruff · import-linter 5 · Alembic on PostgreSQL · pytest · web lint/test/build · mobile tsc/test · security workflow", 12, color=GREY, italic=True)
    return f.save("fig_method", OUT)


def hbar_chart(name, title, rows, w=1200, note=None):
    h = 70 + 44 * len(rows) + (40 if note else 10)
    f = Fig(w, h)
    f.text(20, 30, title, 14, "start", FOREST, "700")
    x0, x1 = 420, w - 90
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        x = x0 + (x1 - x0) * t
        f.line(x, 50, x, 55 + 44 * len(rows), color="#E3E7E1", sw=1, arrow=False)
        f.text(x, 66 + 44 * len(rows), f"{t:.2f}", 11.5, color=GREY)
    for i, (lab, sub, v) in enumerate(rows):
        y = 58 + i * 44
        f.text(x0 - 14, y + 14, lab, 13, "end", GRAPH, "600")
        f.text(x0 - 14, y + 30, sub, 11, "end", GREY)
        col = FOREST if v >= 0.8 else (BRASS if v >= 0.65 else TERRA)
        f.rect(x0, y + 4, (x1 - x0) * v, 26, col, col, 3)
        f.text(x0 + (x1 - x0) * v + 8, y + 22, f"{v:.3f}", 12.5, "start", GRAPH, "600")
    if note:
        f.text(20, h - 12, note, 11.5, "start", GREY, italic=True)
    return f.save(name, OUT)


def fig_eval():
    rows = [("PEA — procedure F1", "28 mock bills, heuristic extractor", 0.942),
            ("DawaCheck mapping accuracy", "52 queries vs 7-drug table", 0.865),
            ("Entity resolution — merge F1", "100 pairs, lexical + phonetic", 0.843),
            ("Billing anomaly — line F1", "39 bills / 70 lines", 0.810),
            ("BMA — mapping accuracy", "78 bill lines vs 27 CGHS keys", 0.705),
            ("CRMA — fully-correct share", "25 denial scenarios", 0.560)]
    return hbar_chart("fig_eval", "Measured on synthetic, team-written development sets (2026-09-13 / 2026-10-19)", rows,
                      note="Not real-world accuracy and not a held-out test. Colour bands: ≥ 0.80, 0.65–0.80, < 0.65.")


def fig_tests():
    f = Fig(1200, 380)
    ms = [("Phase-1 close", "early Sep", 139, 25, 27), ("ADR-011", "23 Sep", 835, 74, 87), ("Demo hardening", "27 Sep", 922, 88, 109),
          ("Release cand.", "27 Sep", 1011, 93, 115), ("Foundation", "19 Oct", 1119, 133, 126), ("This report", "4 Nov", 1119, 153, 126)]
    f.text(20, 28, "Automated tests passing at each milestone (backend pytest | web | mobile)", 14, "start", FOREST, "700")
    base, top = 320, 60
    sc = (base - top) / 1200
    for i, (n, d, b, w, m) in enumerate(ms):
        x = 70 + i * 185
        for j, (v, col) in enumerate(((b, FOREST), (w, BRASS), (m, SLATE))):
            hh = v * sc
            f.rect(x + j * 44, base - hh, 38, hh, col, col, 2)
            f.text(x + j * 44 + 19, base - hh - 6, str(v), 11.5, color=GRAPH, weight="600")
        f.text(x + 63, base + 22, n, 12.5, weight="600")
        f.text(x + 63, base + 40, d, 11.5, color=GREY)
    f.line(50, base, 1170, base, color=BORDER, arrow=False)
    for k, (lab, col) in enumerate((("backend (pytest)", FOREST), ("web (tsx --test)", BRASS), ("mobile (tsx --test)", SLATE))):
        f.rect(760 + k * 140, 12, 12, 12, col, col, 2)
        f.text(778 + k * 140, 23, lab, 11.5, "start", GREY)
    return f.save("fig_tests", OUT)


def fig_gantt():
    f = Fig(1200, 460)
    months = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]
    x0, x1 = 330, 1180
    mw = (x1 - x0) / len(months)
    f.text(20, 28, "Project timeline, July 2026 – April 2027 (completed bars from commit history; dashed = planned / indicative)", 13.5, "start", FOREST, "700")
    for i, m in enumerate(months):
        f.rect(x0 + i * mw, 45, mw, 24, SAGE if i % 2 == 0 else WHITE, BORDER, 0, 0.8)
        f.text(x0 + i * mw + mw / 2, 62, m + (" '26" if i == 0 else (" '27" if m == "Jan" else "")), 12, weight="600")

    def pos(mo, day):
        return x0 + (mo + (day - 1) / 31) * mw
    rows = [("Phase 0 — scoping, monorepo, model swap", (0, 14), (1, 9), "done"),
            ("Phase 1 — Kadi, four modules, CI", (0, 24), (1, 18), "done"),
            ("Phase 2 — BimaNyay, mobile, wiring", (1, 18), (2, 13), "done"),
            ("Phase 3 — entity resolution, triggers", (1, 25), (2, 13), "done"),
            ("Clinical review & safety (ADR-011)", (2, 16), (2, 27), "done"),
            ("Phase 4 — multilingual, eval, hardening", (2, 15), (4, 30), "active"),
            ("Engineering foundation + UI pass", (3, 15), (3, 21), "done"),
            ("Preliminary project report", (4, 1), (4, 15), "active"),
            ("Phase 4 remainder (real-data validation)", (4, 15), (6, 31), "plan"),
            ("Phase 5 — deployment decision, final demo", (7, 1), (8, 31), "plan"),
            ("Final report (blackbook) & submission", (8, 15), (9, 30), "plan")]
    for i, (n, a, b, s) in enumerate(rows):
        y = 85 + i * 33
        f.text(x0 - 12, y + 16, n, 12.5, "end", GRAPH)
        col = {"done": FOREST, "active": BRASS, "plan": WHITE}[s]
        f.rect(pos(*a), y + 3, max(6, pos(*b) - pos(*a)), 19, col, FOREST if s != "active" else BRASS, 4, 1.2, dash=(s == "plan"))
    tx = pos(4, 4)
    f.line(tx, 45, tx, 450, color=TERRA, sw=1.6, dash=True, arrow=False)
    f.label(tx, 452 - 4, "4 Nov 2026", 11.5, TERRA)
    return f.save("fig_gantt", OUT)


def fig_roadmap():
    f = Fig(1200, 560)
    cols = [("Near term — next semester", FOREST, SAGE, [
        "Devanagari OCR + real-scan WER/CER (#35, #114)", "Full CGHS schedule + synonym mapping (#13)",
        "BimaNyay reads the insurer's reason text", "Android device run + SLA push alerts",
        "Native-speaker Hindi/Marathi QA (#37)", "Wire BillNyay appeal/grievance UI (#20)",
        "One real Groq end-to-end run", "◆ Tamper-evident audit log export for users"]),
        ("Medium term — after submission", BRASS, BRASSL, [
            "Real authentication (supersede ADR-008)", "ABDM sandbox / HIU integration (#46, #56)",
            "Insurer templates + CFMA metric (#48, #78)", "IndicXlit once fairseq unblocks (#29)",
            "Clinical NER, vision extraction (#85, #63)", "NFI guideline checks (#69)",
            "Outcome base rates from real disputes (#90)", "◆ More state scheme rule packs"]),
        ("Long-term research horizon", SLATE, SLATEL, [
            "Federated consent verification (ADR-007)", "Voice intake in regional dialects",
            "Camera overlay on bills (AR)", "Strip / pill authenticity models (#75, #77)",
            "Layout-aware form re-mapping", "Differential-privacy statistics (#93)",
            "◆ Consented public bill-rate observatory", "◆ Legal-aid / NGO partner workspace"])]
    for i, (t, col, fill, items) in enumerate(cols):
        x = 20 + i * 392
        f.rect(x, 20, 372, 500, fill, col, 10, 1.4)
        f.add(f'<rect x="{x}" y="20" width="372" height="44" rx="10" fill="{col}"/>')
        f.text(x + 186, 48, t, 14.5, color=WHITE, weight="700")
        for j, it in enumerate(items):
            y = 84 + j * 54
            f.rect(x + 14, y, 344, 42, WHITE, BORDER, 6, 1)
            f.text(x + 186, y + 26, it, 12.2, color=GRAPH if not it.startswith("◆") else TERRA)
    f.text(600, 545, "Items come from the repository's backlog, ADRs and futuristic-scope document; ◆ marks ideas newly suggested in this report.", 12, color=GREY, italic=True)
    return f.save("fig_roadmap", OUT)


if __name__ == "__main__":
    for fn in [fig_problem, fig_usecase, fig_workflow, fig_kadi, fig_resolution, fig_billnyay, fig_pricebasis,
               fig_bimanyay, fig_scheme_ready, fig_method, fig_eval, fig_tests, fig_gantt, fig_roadmap]:
        print(fn())
