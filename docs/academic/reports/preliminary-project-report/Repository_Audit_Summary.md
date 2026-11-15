# Preliminary Project Report — Repository Audit Summary

Prepared 4 November 2026 alongside `ArogyaRakshak_Preliminary_Project_Report.docx` / `.pdf`
(67 pages including front matter; limit 75). Branch audited: `arch/engineering-foundation` at `b2ba9a3`, clean working tree.

## 1. Sources inspected

| Source | What was read |
|---|---|
| Reference reports | The three PPRs attached as local PDFs (`PPR_Group_id_B_13`, `A_17`, `B_05`; 44, 42 and 54 pages). Fonts, outline, cover, certificate, chapter-opener, header/footer, table and appendix conventions extracted programmatically and visually. **The Google Drive links in the brief were not fetched**; the local copies were assumed to be the same three files. |
| Living docs | `AGENTS.md`, `PROJECT_CONTEXT.md` (all 854 lines), `README.md`, `CHANGELOG.md` headings, `docs/ArogyaRakshak_Task_Backlog.md`, `docs/planning/futuristic-scope.md`, `team-division-strategy.md` |
| Specs | `docs/academic/reports/ArogyaRakshak_Technical_Documentation.md`; text of the Project Synopsis and Project Abstract `.docx` files |
| ADRs | ADR-001…021 (001–013 read in detail; 014–021 via summaries in PROJECT_CONTEXT and the code) |
| Evaluation | `docs/evaluation/phase4-harnesses.md`, `entity-resolution.md`, `latency.md` |
| Audits | Headings and key findings of `ArogyaRakshak_Current_State_Audit.md`; `Healthathon2026_Deck_Audit_and_Claims.md` claims ledger |
| Code | Module docstrings and public functions of every file in `packages/*` and `apps/api/app/*`; `cghs_rates.json`, `law_library.json`, DawaCheck reference table, ICD table, tracker SLA table, OCR reader config, config defaults, Dockerfiles, `requirements.txt`, `package.json` files, CI workflow and guardrail script, OpenAPI snapshot (route counts), ORM `__tablename__`s |
| GitHub | All 128 issues (state + title) and PR counts via `gh` |
| Literature | First pages / DOIs of the 13 PDFs in `docs/academic/research-and-literature/papers/` |

## 2. Verification performed (not copied from docs)

| Check | Result |
|---|---|
| `pytest` (packages + API, project `.venv`) | 1,119 passed, 7 skipped |
| `lint-imports` | 5 contracts kept, 0 broken |
| `scripts/ci_guardrails.py` | 8/8 passed |
| Web `npm test` / `eslint` | 153/153 passed / 0 problems |
| Mobile `npm test` | 126/126 passed |
| Running stack | API in demo mode on SQLite + `next dev`; Scenario A loaded through the real pipeline; BillNyay audit and DawaCheck check run in the browser; 4 screenshots captured for Chapter 8 |
| Web searches | NHA 2022–23 OOPE (43.4%), IRDAI Master Circular reference number, IndicSBERT and Aksharantar citations |

Note: the global Python 3.11 on this machine has stale packages (Starlette lacks `HTTP_422_UNPROCESSABLE_CONTENT`), so tests must be run with `.venv`.

## 3. How claims were classified

Every capability in the report was placed in one of four classes, stated next to it in the text and consolidated in Table 5.1:

- **Implemented and tested** — code exists and automated tests cover it.
- **Verified in a running system** — additionally exercised in a running stack/browser (by this audit or recorded in PROJECT_CONTEXT with evidence).
- **Partial / planned** — open issue, scaffold, design-only ADR, or documented as not done.
- **Synthetic-only measurement** — every evaluation number is labelled as a development-set figure on team-written data.

## 4. Discrepancies found between documents and code

| Document claim | What the code / repo shows | How the report handles it |
|---|---|---|
| Project Abstract `.docx`: FAISS-backed vector store; Devanagari OCR | No FAISS code (scaffold deleted Oct 2026); EasyOCR configured `["en"]` only | Report states both as not implemented / planned |
| Synopsis & tech spec: IndicXlit for transliteration | Blocked (#29); rule-based romaniser + Indic phonetic key used | Stated explicitly, never called IndicXlit |
| Tech spec: SchemeSetu RAG | Deterministic rule engine, no embeddings | Described as rule engine; change explained |
| ADR-010: "no automatic time-based purge" | `case_retention.py` enforces a 90-day TTL sweep (SEC-03); API logs it at start-up | Report describes the TTL; **ADR-010 text is stale and should be amended** |
| Issues #9 (FAISS), #21 (RAG), #58 (ONNX fallback), #86 (GraphDB) closed | Closed as design-changed / not built | Report does not treat closure as implementation |
| `futuristic-scope.md` ("Mark-85") items | None implemented | Presented as long-term research directions with feasibility notes; smart-contract payouts called out as out of scope for advocacy |
| Synopsis: guide name "Deipali" vs "Deepali" | Both spellings in team documents | Report uses **"Deipali V. Gore"** (cover of synopsis and abstract) — please confirm |

## 5. Placeholders and items the team must supply

- Roll numbers for **Sanjali Paygude** and **Raj Janvekar** (blank lines on the cover).
- **Name of the Head of Department** on the certificate (`[Name of HoD]`).
- College **logo** on cover/certificate (the reference reports carry it; it is not in the repo).
- **Plagiarism report** (the reference reports include one as Appendix C). Not fabricated; attach the institutional check result. No similarity or AI-detection score is claimed anywhere.
- Signatures and dates.

## 6. References — verification status

- Checked by search or against PDFs in the repo: [1], [3], [24]–[30], [38], [39].
- Standard, widely cited works cited from established bibliographic knowledge: [2], [16]–[23], [32]–[37], [40]–[44], [46].
- Government/portal references are cited at the level of detail the project itself uses ([4]–[14], [47]–[50]); [5] and [11] reproduce the project's own citations, whose full text could not be retrieved.
- **[15] (base paper, ETCC 2025, DOI 10.1109/ETCC65847.2025.11108371)** came from the team's synopsis and **could not be found by web search**. Confirm it on IEEE Xplore before submission.
- Literature-bank entries without authors (MDPI 2026 citation-enforced prompting, HalluGraph, "Dialogue to Detection", CBR-RAG, reasoning-focused legal retrieval benchmark) were **left out** because they could not be cited completely.

## 7. Reproducing the build

Report sources (chapter markup, SVG figure scripts, screenshots, DOCX builder, Word export script) are in `source/` — see `source/README.md`. The DOCX here has its Contents, List of Figures and List of Tables fields already updated by Word; if you edit headings, right-click a list → *Update Field* → *Update entire table*.
