# Multilingual QA — #94, #96, #35, #37 (Phase 4, Hindi and Marathi)

> **Read this first.** Everything here was written and checked by engineers and tools, **not by a
> native Hindi or Marathi speaker**. The phrase lists, the glossary and the OCR reference lines are
> unreviewed. Nothing below is a language-quality claim. Two of the four issues could only be
> partly done, and one could not be done as written; each section says exactly what is and is not
> in place. Measured on 2026-11-21 on the `wave1/integration` code plus this change.

| Issue | Outcome |
|---|---|
| **#94** Devanagari prompt-injection sanitisation | **Built and tested** (heuristic, see limits) |
| **#37** Terminology QA, Hindi + Marathi | **Mechanical audit built; the QA itself still needs a native-speaker reviewer** |
| **#35** Devanagari OCR test set | **Ground-truth corpus only; no images, no OCR run.** Kadi's image OCR is English-only today |
| **#96** Devanagari-grounded RAG retrieval verification | **Not built: there is nothing to verify** |

## #94 — Hindi / Marathi prompt-injection hygiene
`packages/kadi/kadi/injection.py` (shared, because Kadi owns document text), used by
`kadi.extraction` and by BillNyay's `wrap_untrusted`:

- **`sanitise_for_prompt`** removes invisible and reordering characters before text reaches a model:
  zero-width space, BOM, soft hyphen, word joiner, bidi controls, Unicode "tag" characters and C0
  controls. ZWJ/ZWNJ are kept **only between two Devanagari characters**, where they change how a
  conjunct renders (`क्‍ष`); everywhere else they are a hiding trick and are dropped. Ordinary text,
  matras and Devanagari digits come back unchanged (tested, idempotent).
- **`detect_injection_markers`** scans a normalised view (NFKC, hidden characters removed, nukta and
  chandrabindu folded, Devanagari digits folded) with the existing English patterns **plus** Hindi,
  Marathi and romanised-Hindi phrases (ignore previous instructions, new instructions, system prompt,
  act-as, do-not-follow, "instead output the following"). The normalised view also closes a gap in the
  *existing English* detector: `ig\u200bnore previous instructions` with a zero-width space, full-width
  Latin, and bidi-control splitting were previously invisible to it.
- **Behaviour:** a hit is disclosed (`extraction_warnings`, or a log line carrying a count and never the
  text) and never silently changes extraction. Document text sent to the model is sanitised; if
  characters were removed, only the count is logged.
- **Tests:** 46 new (`kadi/tests/test_injection_multilingual.py`, `billnyay/tests/test_prompt_safety_multilingual.py`):
  15 Hindi/Marathi/romanised attacks, 5 evasions, 12 benign look-alikes that must not flag (e.g.
  "पिछले निर्देशों के अनुसार दवा लें", "तुम्ही शिक्षक म्हणून काम करता"). Eight deliberate breaks of the code
  were each caught.
- **Limits, stated plainly:** this is pattern matching, not a guarantee. A reworded or translated attack
  will not match; **homoglyph substitution (a Cyrillic `о` for a Latin `o`) is not folded**; the phrase
  lists are engineering-written and unreviewed. The real protection stays architectural (schema-constrained
  output, a "this is data" boundary, deterministic cross-checks). The issue's "local LLM translation"
  does not exist in this app (translation is not an LLM step), so what was protected is the prompts that
  carry document text.

## #37 — Terminology audit (the mechanical half of a QA pass)
`apps/api/app/evaluation/terminology.py`, CLI `scripts/terminology_audit.py`, glossary
`data/terminology/glossary.json` (marked UNREVIEWED). It reads 485 strings in each of English, Hindi and
Marathi (web, mobile and shared i18n copy, through `scripts/terminology/dump_ts_copy.mjs`) plus 4 generated
letter documents per language (the three BimaNyay drafts and BillNyay's offline fallback letter) and reports candidates for a
reviewer. **The full worksheet, with a blank "Reviewer decision" column, is
[`terminology-audit.md`](terminology-audit.md).** It never decides a term is wrong.

What it found:
- **18 concepts are rendered with more than one term inside one language.** The larger ones: Hindi
  *rejection* अस्वीकृति (22) / अस्वीकार / इनकार / निरस्त; Hindi *statutory/legal* कानूनी / विधिक / वैधानिक;
  Marathi *government* शासकीय (11) / सरकारी (6); Marathi *document* दस्तऐवज (20) / कागदपत्र (11); Hindi
  *price* दर / कीमत / मूल्य. Some are legitimate register differences; a reviewer must say which.
- **3 spelling-variant pairs in Hindi:** जाँच (17) vs जांच (17), जांचें vs जाँचें, मरीज़ vs मरीज.
- **No Hindi words in Marathi text or the reverse, no untranslated (identical-to-English) strings and no
  placeholder mismatches** across the copy dictionaries. (These are the checks a machine can do well.)
- **The generated Hindi and Marathi appeal letters are not fully Hindi/Marathi.** 53 of the 58 Latin-script
  words found sit in the letters: the audit's "grounds" paragraph, the statute names and the clause text come
  from the English-only rule engine and are pasted into the localised letter ("Policy has been continuously
  active for … Under the IRDAI Master Circular …"). Only 5 come from UI copy (`Tab`, `days`, `ii`, and the
  drug examples Paracetamol and Meropenem). Fixing this means translating the audit's grounds text, which
  needs a translator, not code.

**What is not done:** nobody has judged whether any Hindi or Marathi string is *correct*, natural or legally
appropriate; the glossary and the leakage lists are the engineering team's. The reviewer should (1) fill the
"Reviewer decision" column, (2) correct `glossary.json` (add, strike, mark preferred), (3) re-run the script.

## #35 — Devanagari OCR test set
- **Shipped:** `data/evaluation/devanagari_ocr_corpus.jsonl`: 24 invented reference lines (12 Hindi, 12 Marathi)
  across 8 categories (header, bill line, medicine line, letter line, name, Devanagari-digit dates,
  conjunct-heavy words, mixed Devanagari/Latin clinical values). It loads through the same loader as the other
  datasets and scores through `evaluate_ocr(rows, hypotheses={id: ocr_text})`, per category. **Text only:
  no images, no OCR output exist for it.**
- **Finding: Kadi's image OCR cannot read Devanagari today.** `packages/kadi/kadi/ocr/ocr_parser.py` builds
  `easyocr.Reader(["en"])`. Digital PDFs with a text layer (PyMuPDF) are unaffected; photographed or scanned
  Devanagari documents would come back as Latin noise. Any Devanagari OCR benchmark therefore starts from a
  baseline of "unsupported", and supporting Hindi/Marathi means changing the reader languages and
  **downloading EasyOCR model weights from the network**, which needs explicit approval (AGENTS.md network
  rule). No model weights are cached on this machine.
- **Why there are no images:** rendering Devanagari needs a text-shaping engine. Pillow here has no Raqm or
  HarfBuzz, so conjuncts and matras would be drawn wrongly, and an image with wrong text is invalid ground
  truth. A renderer was deliberately not shipped because it could not be verified. Options: render through a
  browser or print-to-image path, or use real documents.
- **Not possible for an engineer: the "real, self-donated documents" half.** That needs donors, written
  consent and a retention decision (the app's zero-retention rule applies to patient uploads; a donated test
  set is a different data-handling question the team must decide).
- **Unmeasured:** no WER/CER exists for any Devanagari OCR. The existing `ocr_wer_synthetic.jsonl` figures are
  simulated errors, not engine output (see `phase4-harnesses.md` section 5).

## #96 — Devanagari-grounded RAG retrieval verification agent: not built
The issue asks for an agent that validates *translated Marathi/Hindi citations map to the original English
scheme parameters* in a RAG pipeline. That pipeline does not exist: SchemeSetu is rule-based (no retrieval, no
embeddings, no FAISS/pgvector, see `PROJECT_CONTEXT.md`), and it produces **no Hindi or Marathi text and no
citations of its own** (the scheme names, thresholds and reasoning trace are English; the Hindi/Marathi strings
are static UI copy). There is no translated citation to verify against an English source. The nearest useful
checks were folded into #37: the audit verifies that every `{placeholder}` and `%s` slot in every Hindi/Marathi
string matches the English source (zero mismatches), and it lists the scheme terminology for review.
If SchemeSetu ever gains retrieval or machine-translated explanations, this issue becomes buildable; until then
it should be closed or re-scoped, which is a decision for the project owner (no comment has been posted on the
issue).

## Reproduce
```bash
python -m pytest packages/kadi/tests/test_injection_multilingual.py packages/billnyay/tests/test_prompt_safety_multilingual.py
PYTHONPATH=apps/api python -m pytest apps/api/tests/test_evaluation_terminology.py
python scripts/terminology_audit.py --markdown docs/evaluation/terminology-audit.md   # needs Node + `npm install` at the repo root
```
