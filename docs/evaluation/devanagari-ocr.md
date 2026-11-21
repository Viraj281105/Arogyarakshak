# Devanagari OCR enablement (Wave 2, stream A)

> **Read this first.** Every confidence figure below is the OCR engine's **own score, not accuracy**.
> There is no reference transcription, so no WER/CER and no correctness claim exists or is made.
> Timings are from one page per document (6 pages); anything extrapolated from them is marked so.

Status: **implemented**; `OCR_LANGUAGES` defaults to `en`. English PDFs and images are covered by golden
and no-reader tests (below); no claim is made beyond what those tests assert.

## What changed
| Piece | Where | Behaviour |
|---|---|---|
| Text-layer gate | `packages/kadi/kadi/pdf_text_quality.py` | `assess_text_layer(text)` returns `clean`, `corrupted` or `not_devanagari` plus ratios (no document text). |
| Language setting | `OCR_LANGUAGES` (env), `get_ocr_languages` | Default `en`; `hi,mr,en` enables Devanagari. Unknown codes raise `UnsupportedOCRLanguageError`, reported as `extraction_ok=False` naming `OCR_LANGUAGES`, even for a PDF with only clean pages. |
| Reader | `_get_easyocr_reader` | Cached per language **set** (`hi,mr,en` and `en,hi,mr` share one reader); built with `download_enabled=False` and `model_storage_directory=$EASYOCR_MODULE_PATH/model`. Missing weights raise `OCRModelsUnavailableError` ("OCR models not installed"); failures are not cached. |
| PDF route | `ocr_parser._parse_pdf` | Per page: clean / English / blank pages keep the text path; a `corrupted` page is rasterised in memory and OCR'd **only if** `OCR_LANGUAGES` contains `hi` or `mr`; otherwise it is skipped and reported. The corrupted text is never used. |
| Partial results | result keys `pages_total`, `pages_read`, `pages_skipped`, `skipped_reasons`, `partial`, `partial_reason`, `warnings` | A document with unread pages is never presented as complete (see below). `ocr_segments` of OCR'd PDF pages carry a 1-based `page`. |
| Bounds | env, see `docs/configuration/environment-variables.md` | one OCR job per process (`BoundedSemaphore(1)`, bounded queue wait, then "busy"); `OCR_MAX_PAGES` default 3 (ceiling 10); `OCR_DOCUMENT_BUDGET_SECONDS` 120 checked between pages; `OCR_PDF_MAX_PIXELS` 10 MP and 8000 px per side checked before and after rendering; pages referencing an embedded image above 40 MP are refused; zero-area pages refused; the gate examines at most 300 pages. |
| Model fetch | `scripts/fetch_ocr_models.py` | Operator-run, needs `--download`; never called by the app (not run in this work). |
| Baseline script | `scripts/devanagari_ocr_baseline.py` | `["en"]` vs `["hi","mr","en"]`, JSON outside git (symlink and `..` paths into the repo are refused). |

Zero retention: pages are rendered to numpy arrays in memory; nothing is written to disk by the parser.
Logs and warnings carry page counts and exception type names only.

### Skip reasons (`skipped_reasons` keys)
`corrupted_text_layer_needs_devanagari_ocr`, `page_cap`, `time_budget`, `ocr_busy`, `ocr_unavailable`,
`ocr_failed`, `ocr_empty`, `unsafe_page_image`, `no_text_layer` (image-only page in a text PDF),
`not_examined` (beyond the 300-page gate limit). `extraction_ok` stays True when at least one page was
read; `partial` and a user-presentable `partial_reason` are always set when anything was skipped.

## The text-layer gate
Signals (constants in the module; tuned on the six real PDFs and unit cases, so **tuned on what they are
reported on**):

* **Legacy-font signature**, any of:
  * letters from the Unicode blocks legacy-font corruption lands in (Balinese, Sundanese, Batak, Lepcha,
    Ol Chiki, Cyrillic Ext-C, Vedic Extensions, Devanagari Extended): >= 3 and >= 2 % of letters. Other
    Indic scripts (Tamil, Gujarati, Bengali, Telugu, Kannada, Malayalam, Gurmukhi) and Greek are **not**
    counted (tested);
  * Latin-1 glyphs legacy fonts use and English never does between letters (`jftLVªh`, `laö`): >= 3 and >= 5 %
    of Latin tokens;
  * token shapes (`vlk/kj.k`, a backtick or glued `]` inside a word, a vowel-less run before a capital) and
    pages where most Latin tokens are vowel-less codes (`dk;Zky;`), only on pages that are **not**
    predominantly common English words (>= 25 % of >= 8 Latin tokens). Slashes like `bed/day`, names like
    `iPhone` or `McDonald`, accents, ligatures (`ﬁ`), NFD marks and `μg` are legitimate (tested).
* **Malformed Devanagari**: token starts with a vowel sign, two vowel signs in a row, virama plus vowel
  sign, or U+0904. >= 2 tokens and >= 3 %.
* **Glyph substitution**: Latin letters or odd punctuation/digits inside a Devanagari word. >= 2 tokens, >= 5 %.
* **Known-word ratio**: only on **long prose** pages (>= 100 Devanagari tokens, most lines >= 6 tokens),
  suffix-aware matching against a small curated function-word list (UNREVIEWED, NEEDS NATIVE-SPEAKER QA);
  below 0.10 is corrupted. It is deliberately the weakest signal: short and table-like pages are never
  condemned by it alone.
* Fewer than 5 Devanagari tokens or < 5 % Devanagari letters: `not_devanagari`.

### Per-page verdicts on the six real public PDFs
Reproducible: `packages/kadi/tests/test_pdf_text_quality_corpus.py` asserts exactly this table (skipped when the
git-ignored corpus is absent; `AROGYA_DEVANAGARI_DOCS` overrides the path). Run on 2026-11-21 after the
review-round changes: 6 passed. `X` corrupted, `.` not_devanagari, `C` clean.

| Document | Pages | Verdicts |
|---|---|---|
| `irdai_complaint_registration_form` | 4 | `XX..` (pages 3-4 have no text layer) |
| `mahabocw_gr_2017-06` | 3 | `XXX` |
| `mh_gr_2025-09` | 4 | `XXXX` |
| `mh_gr_2026-01` | 8 | `XXXXXXXX` |
| `ombudsman_rules_2017_gazette` | 13 | `XXXXXXX......` (pages 8-13 are English) |
| `pib_pmjay_2025-11` | 11 | `XXX.XXXXXX.` |

These agree with the corpus README's manual assessment (no per-page human label exists).

### What is NOT measured or NOT caught
* No real **clean** Devanagari PDF is in the corpus, so the false-positive rate on real clean Devanagari is
  untested (only hand-written, unreviewed strings). English false positives were found by review and fixed;
  the English tests are synthetic, not a corpus.
* Not reliably caught: short corrupted pages (cover pages, a few lines), a page mixing clean and corrupted
  regions, corruption that yields valid-looking words, and Latin legacy encodings on pages dominated by
  English-looking codes or tables of codes.
* Thresholds were tuned on the same six PDFs they are reported on.

## Baseline run (one page per document, 200 dpi, CPU)
Run 2026-11-21 with `python scripts/devanagari_ocr_baseline.py --out <outside git> --max-pages 1`: page 1 of each
of the six PDFs; EasyOCR weights from the local cache. (Run before the review-round changes; the baseline script
itself was not changed in a way that affects these figures.)

| Languages | Pages | Total OCR time | Mean time per page | Mean confidence range (engine score) | Segments below 0.5 |
|---|---|---|---|---|---|
| `["en"]` | 6 | 86.4 s | 14.4 s | 0.17-0.28 | 341 of 395 |
| `["hi","mr","en"]` | 6 | 148.3 s | 24.7 s | 0.58-0.65 | 138 of 395 |

* Model load: 4.7 s (`en`), 2.2 s (`hi,mr,en`, file cache warm).
* Peak process working set after both runs: **4297 MB**; a monotone high-water mark, identical after each
  configuration, so it cannot be attributed to the three-language reader (it includes torch, rasterised
  pages and both readers). Per-configuration memory is not isolated.
* The README probe (page 1 of `mh_gr_2026-01`: 86 segments, 26 below 0.5, mean 0.65) is reproduced.
* **Meaning:** the English-only model reads Devanagari as low-confidence noise; the three-language model scores
  about three times higher. Engine score only: **not correctness**.
* **~25 s/page and "~4 minutes at the 10-page ceiling" are extrapolations from these 6 pages**, not measured
  documents. The default cap is now 3 pages (~75 s extrapolated) and the budget 120 s.
* End-to-end through `parse_document` (real weights, `download_enabled=False`, model directory from
  `EASYOCR_MODULE_PATH`) on the IRDAI form with `OCR_LANGUAGES=hi,mr,en`: 75 segments from the 2 corrupted pages in
  26.1 s; pages 3-4 are image-only and are reported (`partial`, reason `no_text_layer`). With the default `en`:
  `extraction_ok=False`, 2 pages skipped for the corrupted text layer and 2 for no text layer, in 0.1 s, no model
  loaded.

## Behaviour notes
* Default `en` + corrupted page: the page is **not** read with the English-only model (that would turn untrusted
  text into English-only noise reported as success). It is skipped with reason "corrupted text layer; set
  OCR_LANGUAGES=hi,mr,en"; clean pages are kept; `partial=True`.
* Clean English PDFs never load a reader (tested with realistic invoices, a prescription, slashes, names, accents,
  ligatures, `μg`); their text equals the independently written expected string (golden test); English images
  build `Reader(["en"])` exactly as before. With the Devanagari setting on, English output is identical (tested).
* A reader build failure (missing weights) never fails the whole PDF: clean pages are kept and the report says
  "OCR models not installed".
* A blank PDF still returns the exact "may be a scan" error.

## Not done (next steps)
1. Reference transcriptions (workstream B) and WER/CER per category with the existing `evaluate_ocr`.
2. Latency options and preprocessing experiments, judged by CER once references exist.
3. Low-confidence routing recall (ADR-011).
4. Image build/CI model packaging (see the handoff), wiring `partial`/`warnings` into case ingestion.
