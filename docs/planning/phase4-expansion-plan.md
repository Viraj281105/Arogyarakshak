# Phase 4 expansion plan — multilingual QA, Devanagari OCR, retrieval

**Written 2026-11-21.** Planning only: no feature code accompanies this document. Decisions below were taken
autonomously under the maintainer's instruction to decide what suits the project and to **expand rather than
scope down**. Figures marked *proposed* are targets to be revised after the first real baseline; nothing here
is a measured result unless it says so.

## 1. Where we stand (facts, 2026-11-21)

| Area | State |
|---|---|
| Devanagari OCR | `ocr_parser.py` builds `easyocr.Reader(["en"])`: **no Hindi/Marathi recognition in Kadi today**. The Devanagari model (`devanagari.pth`, 215 MB, shared by Hindi and Marathi) is now downloaded locally. |
| First OCR probe | One real Marathi GR page, 200 dpi, `["hi","mr","en"]`, CPU: 86 segments, **32 s**, mean confidence 0.65, 26 of 86 below the 0.5 review threshold; headings read correctly. A probe, not a benchmark (no reference transcription). |
| Real documents | 6 official public PDFs downloaded (`data/raw/devanagari_public_docs/README.md`). Their **text layers are corrupted** (wrong glyph maps, legacy font encodings), so they give no automatic ground truth and a text-layer-first PDF path would feed garbage to extraction. |
| Hindi/Marathi copy | 485 strings per language audited mechanically (`docs/evaluation/terminology-audit.md`): 18 concepts with more than one term, 3 spelling variants. No native-speaker review has happened. The generated hi/mr appeal letters embed English grounds/statute text. |
| Injection hygiene | Devanagari-aware layer exists (`kadi/injection.py`), heuristic, phrase lists unreviewed; homoglyphs and translated attacks not covered. |
| SchemeSetu | Rule-based; **no retrieval, no ranking, no Hindi/Marathi output, no citations**. This is why #96, #105, #110, #111 could not be built as written. |
| Evaluation | 8 offline harnesses on synthetic data behind a CI regression gate. No live-LLM figure exists anywhere. |
| CI | PR #162 green after fixing a gitleaks false positive and a CI-only `conftest` collision. |

## 2. Decisions

| # | Decision | Why |
|---|---|---|
| D1 | **Keep #96, #105, #110, #111 open and expand** (build the missing capability, then evaluate it) rather than close or shrink them. | The user's direction, and the capabilities are genuinely useful: cited, multilingual scheme/policy explanations. Eligibility stays **deterministic and rule-based**; retrieval only supplies grounded citations and explanations. |
| D2 | Enable Hindi/Marathi image OCR in Kadi (`["hi","mr","en"]`), behind a setting, after the baseline exists. | Evidence the model reads real documents; without it Devanagari scans are unsupported. |
| D3 | Add a **PDF text-layer quality gate**: detect corrupted Devanagari text layers and route those pages to OCR. | The real documents show this is the normal case for Indian government PDFs, not an edge case. |
| D4 | Ground truth = **human transcription** of stratified lines from the real documents, double-annotated; plus **browser-rendered synthetic images** for scale. | No usable text layers; Pillow here cannot shape Devanagari. |
| D5 | Real patient-style documents come only through a **consent-based donor protocol** (team and family first), never scraped. | Privacy and zero-retention norms; a person must decide retention. |
| D6 | Build a **reviewed Hindi/Marathi message catalogue** for BimaNyay (denial grounds, statute names) and govern terminology with a versioned glossary. | The letters are not fully localised today; this needs a translator, not code. |
| D7 | Retrieval is **BM25-first** (deterministic, offline, explainable, no new dependency), IndicSBERT dense as an optional second stage that may only re-rank. | Matches the project's rule-based, no-fabrication principles and the Kadi design (dense may never decide). |
| D8 | Define a **"context request"** for #112 as a module's call for case context through Kadi, and instrument it with the WS1 metrics. | Makes CRR and DPR measurable without a new subsystem. |
| D9 | Do **not** disable TLS verification for any download, ever. | A blocked action this session; also correct practice. |

## 3. Workstreams

### A. Devanagari OCR enablement and benchmark (P0, critical path)
1. **Baseline first (no behaviour change):** rasterise the 6 documents, run `["hi","mr","en"]` and the current `["en"]`, record segments, confidence histogram, latency per page, memory. Write the reference transcriptions (workstream B) and compute **WER/CER per category** with the existing `evaluate_ocr`.
2. **Enable in Kadi:** reader languages from a setting (`OCR_LANGUAGES`, default keeps `en` until the benchmark passes); lazy single load already exists; confirm memory with three languages loaded.
3. **Latency and cost:** 32 s/page on CPU is too slow for the demo path. Options, in order: lower dpi where legible, crop to text regions, page cap per case, run per page in the existing async document job, optional GPU. Decide from measurements, not guesses.
4. **Preprocessing experiments** (each judged by CER on the held-out set): deskew, binarise, upscale small text, line segmentation.
5. **Low-confidence routing (ADR-011):** measure *recall of errors among segments below the threshold*; the point is that wrong text is sent to a human, not that every line is right.
6. **Packaging:** models are fetched from the network on first use. Production must bake them into the image or mount a volume (zero document egress, no runtime download); CI caches them.
*Proposed targets:* CER ≤ 0.15 on clean printed Marathi/Hindi lines, ≤ 0.30 on photographed documents, ≥ 90 % of erroneous segments below the review threshold.

### B. QA corpus and ground truth
- **Real public documents** (done, 6): see the manifest. Gaps: bilingual IRDAI Protection of Policyholders' Interests Regulations (host certificate expired / path 404); NHA *Adhikar Patra*; Maharashtra GR set on a host that refuses connections here. A person can fetch these from a browser and drop them in.
- **Transcription:** 150 lines stratified over headers, tables, amounts with Devanagari digits, stamps, forms, low-quality pages; two native annotators per language; report inter-annotator CER; store text, document hash, page, bounding box. **No page images in git.**
- **Synthetic at scale:** render HTML with open-licence Devanagari fonts through a headless browser (correct shaping), then degrade (skew, blur, noise, JPEG) to produce ~500 images with exact ground truth, in the categories already in `devanagari_ocr_corpus.jsonl`.
- **Donor protocol (needs the project guide's approval):** written consent, what is collected, redaction before storage, encrypted storage off-repo, deletion on request, a named retention decision. Target ≈ 40 documents (bills, prescriptions, denial letters; half Hindi, half Marathi). Ask the guide (backlog item #43) whether institutional review applies.
- **Public datasets to evaluate** (licence check before any download): printed and handwritten Devanagari OCR corpora from Indian research groups.

### C. Multilingual explanation and terminology
1. **Native-speaker review programme:** one Hindi and one Marathi reviewer, each given the worksheet (`terminology-audit.md`) and a rubric (correct, natural, register, legal appropriateness); outcome recorded in `glossary.json` (`preferred`, `status: REVIEWED`, reviewer, date).
2. **Message catalogue for BimaNyay:** denial grounds, violation summaries, statute names (official Hindi from gazette text once obtained) for the 5 denial categories in en/hi/mr (~150 strings), keyed so the letter stays fully localised and the grounding harness (#115) can verify it.
3. **SchemeSetu multilingual explanations:** templated, reviewed hi/mr explanations of the deterministic reasoning trace; **no machine translation in the decision path**.
4. **CI:** a terminology job (needs Node) so a new term or leakage shows up in review; reviewer sign-off required to change `status`.

### D. Retrieval layer (turns #96, #105, #110, #111 into real work)
- **Corpus:** public scheme and regulation documents (the GRs above, PM-JAY guidelines, IRDAI regulations); for DaaviSetu the user's **own uploaded policy**, indexed transiently in memory per case and expunged with the case (BYOD).
- **Design:** clause-level chunking, BM25 index, each result carries `(document, page, quote, score)`; optional IndicSBERT re-rank; every explanation sentence carries citation keys.
- **Evaluation, per issue:** #105 PCRA and Recall@k on ~60 hand-labelled queries; #110 MRR over ranked schemes for ~40 case profiles (eligibility status first, relevance second, always labelled provisional); #111 precision/recall of retrieved clauses; #96 a **citation verifier**: figures, scheme names and thresholds in each hi/mr sentence must match the cited source span (reuses the grounding harness).
- **Guardrails:** retrieval never decides eligibility; a failed lookup says "not found", never invents a citation.

### E. #112 CRR / DPR
Define *context request* = a module asking Kadi for case context (entities, line items, timeline). **CRR** = requests served from existing case context ÷ all requests. **DPR** = redundant extraction/OCR/LLM calls avoided vs a baseline where each module re-extracts. Instrument with the WS1 counters; compute on the demo scenarios A-E with the baseline measured by a flag that disables reuse. Needs no new subsystem.

### F. Injection hardening v2
Homoglyph/confusables folding in the matching view; a red-team corpus of ~100 hi/mr/Hinglish and translated attacks (kept separate from benign text to measure false positives); schema-constrained-output tests; a controlled **live-model** red-team run once a Groq key is available (no number is claimed before then).

### G. Engineering hygiene
Cache EasyOCR models in CI; a manual (`workflow_dispatch`) Devanagari benchmark job that is non-gating; run the real mobile scanner on a device; keep the single combined `pytest` invocation (the `conftest` collision is fixed and guarded by CI).

## 4. Sequence

| Step | Work | Depends on |
|---|---|---|
| 1 | A1 baseline + B transcription (start annotator recruitment now) | downloaded corpus (done) |
| 2 | A2-A5 OCR enablement, preprocessing, routing metric | step 1 numbers |
| 3 | C1-C2 reviewer programme and BimaNyay catalogue | reviewers |
| 4 | D retrieval + #105/#110/#111/#96 harnesses | public corpus, labelled queries |
| 5 | E (#112) and F injection v2 | WS1 counters; Groq key for the live part |
| 6 | Wave 2 (WS3 platform, WS6 anomaly detection) and Wave 3 page loops | PR #162 merged |

Critical path: transcription and reviewers (people), not code. Start them first.

## 5. What needs a human
- Two native reviewers (Hindi, Marathi) and ~2 annotators; the guide's view on donor documents.
- A browser download of the three documents that could not be fetched here.
- A Groq key for live runs; an Android device or emulator; a decision on CPU versus GPU hosting.

## 6. Risks
| Risk | Mitigation |
|---|---|
| CPU OCR too slow for the demo | measure first; page caps, cropping, async jobs, optional GPU |
| Reviewer availability | recruit now; keep the worksheet small and ordered by impact |
| Redistributing government page images | keep images out of git; store hashes and transcriptions only |
| Retrieval presented as advice | provisional labels, deterministic eligibility, "not found" over invention |
| Over-claiming from small sets | every report states synthetic/real, n, and that it is not real-world accuracy |
