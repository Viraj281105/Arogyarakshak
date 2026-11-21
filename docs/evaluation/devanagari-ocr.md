# Devanagari OCR enablement (Wave 2, stream A)

Status: **implemented, default behaviour unchanged** (`OCR_LANGUAGES=en`). No accuracy claim is made:
there is no reference transcription yet, so WER/CER cannot be computed. Everything below is a count,
a latency or the engine's own confidence score, and says so.

## What changed
| Piece | Where | Behaviour |
|---|---|---|
| Text-layer gate | `packages/kadi/kadi/pdf_text_quality.py` | `assess_text_layer(text)` returns `clean`, `corrupted` or `not_devanagari` plus ratios (no document text). |
| Language setting | `OCR_LANGUAGES` (env), `kadi.ocr.ocr_parser.get_ocr_languages` | Default `en`. `hi,mr,en` enables Devanagari. Unknown codes raise `UnsupportedOCRLanguageError`; the parser turns that into `extraction_ok=False` with an error that names `OCR_LANGUAGES`. |
| Reader cache | `_easyocr_readers` keyed by the language tuple | One reader per tuple per process; double-checked lock as before. |
| PDF route | `ocr_parser._parse_pdf` | Per page: `corrupted` -> rasterised in memory (200 dpi, scaled down to the 40 MP budget) and OCR'd; `clean`/`not_devanagari` keep the text path. Result gains `warnings` (counts only) and `ocr_segments` for OCR'd pages. |
| Page cap | `MAX_OCR_PAGES_PER_DOCUMENT = 10` | Corrupted pages beyond the cap are skipped and reported; the corrupted text is never substituted. |
| Baseline script | `scripts/devanagari_ocr_baseline.py` | `["en"]` vs `["hi","mr","en"]`, JSON report outside git. |

Zero retention: pages are rendered to numpy arrays in memory; nothing is written to disk by the
parser. The baseline script writes only counts/scores (text only with `--include-text`) and refuses an
output path inside the repository.

## The text-layer gate
Signals (all thresholds are constants in the module, chosen against the six real PDFs and the
README's qualitative notes, so they are **tuned on the corpus they are reported on**):

* **Legacy-font signature**: Latin tokens that are glyph codes (`jftLVªh`, `vlk/kj.k`: internal
  capitals, Latin-1 glyphs or `/ ] [ \` ;` between letters, >= 3 and >= 5 % of Latin tokens), or letters
  from unrelated scripts (Sundanese, Ol Chiki, Vedic extensions: >= 2 % of letters).
* **Malformed Devanagari**: tokens starting with a vowel sign, two vowel signs in a row, virama plus
  vowel sign, or U+0904 (ऄ). >= 2 tokens and >= 3 % of Devanagari tokens.
* **Glyph substitution**: Latin letters or odd punctuation/digits inside a Devanagari word
  (`साव$भौ'मक`, `आरो4य`). >= 2 tokens and >= 5 %.
* **Known-word ratio**: share of Devanagari tokens in a small curated Hindi/Marathi function-word
  list (UNREVIEWED, NEEDS NATIVE-SPEAKER QA); below 0.12 on >= 40 tokens is corrupted.
* Fewer than 5 Devanagari tokens or < 5 % Devanagari letters: `not_devanagari` (English and blank
  pages stay on the text path).

### Result on the six real public PDFs (43 pages, per-page verdict)
`X` corrupted, `.` not_devanagari, `C` clean.

| Document | Pages | Verdicts |
|---|---|---|
| `irdai_complaint_registration_form` | 4 | `XX..` (pages 3-4 have no text layer) |
| `mahabocw_gr_2017-06` | 3 | `XXX` |
| `mh_gr_2025-09` | 4 | `XXXX` |
| `mh_gr_2026-01` | 8 | `XXXXXXXX` |
| `ombudsman_rules_2017_gazette` | 13 | `XXXXXXX......` (pages 8-13 are English) |
| `pib_pmjay_2025-11` | 11 | `XXX.XXXXXX.` |

Every Devanagari page of these documents is judged corrupted, which agrees with the README's manual
assessment of each file. **Not verified:** there is no per-page human label of "corrupted", so
precision on real pages is the README's judgement, not a measurement; and **no real clean
Devanagari PDF is in the corpus**, so the false-positive rate on real clean text is untested (only
hand-written clean Hindi/Marathi strings in the unit tests, which are unreviewed). Expect misses where
corruption yields valid-looking words, and expect possible false positives on clean text that is rich
in rare vocabulary.

## Baseline run (one page per document, 200 dpi, CPU)
Run 2026-11-21 with `python scripts/devanagari_ocr_baseline.py --out <outside git> --max-pages 1`.
Page 1 of each of the six PDFs; EasyOCR weights from the local cache (no download).

| Languages | Pages | Total OCR time | Mean time per page | Mean confidence range | Segments below 0.5 |
|---|---|---|---|---|---|
| `["en"]` | 6 | 86.4 s | 14.4 s | 0.17-0.28 | 341 of 395 |
| `["hi","mr","en"]` | 6 | 148.3 s | 24.7 s | 0.58-0.65 | 138 of 395 |

* Model load: 4.7 s (`en`), 2.2 s (`hi,mr,en`, with the file cache warm).
* Peak process working set after both runs: **4297 MB**. It is a monotone high-water mark and was
  identical after each configuration, so it cannot be attributed to the three-language reader; it
  includes torch, the rasterised pages and both readers. Treat it as an upper bound for a process
  that has loaded both; a separate per-configuration process run is needed to isolate it.
* The probe in the corpus README (page 1 of `mh_gr_2026-01`, 86 segments, 26 below 0.5, mean 0.65)
  is reproduced here (86 segments, 26 below 0.5, mean 0.6546).
* **Meaning:** the English-only model reads Devanagari as low-confidence noise (mean about 0.2), the
  three-language model scores about three times higher. Confidence is the engine's own score, **not
  correctness**; no statement about accuracy follows from it.
* End-to-end check through `parse_document` on the real IRDAI form with `OCR_LANGUAGES=hi,mr,en`:
  2 of 4 pages routed to OCR, 75 segments, 32.4 s, one count-only warning.
* **Latency is the open problem** (about 25 s per page on this CPU). At 10 OCR pages the cap alone
  bounds one document at roughly 4 minutes; the plan's options (lower dpi, cropping, async document
  job, GPU) are not yet tried.

## Behaviour notes
* With the default `OCR_LANGUAGES=en`, a corrupted Devanagari PDF page is still not trusted: it is
  OCR'd with the English reader and a warning says the reading is unreliable (`Set OCR_LANGUAGES=hi,mr,en`).
* Clean English PDFs never load a reader (verified by test), and with the setting on their text and
  line items are identical (tested).
* A per-page OCR crash drops that page, records a count, and never falls back to the corrupted text.
* Logs and warnings contain page counts only (tested for the absence of document text and filename).

## Not done (next steps)
1. Reference transcriptions (workstream B) and WER/CER per category with the existing
   `evaluate_ocr`; the proposed targets in the expansion plan remain targets.
2. Latency options and preprocessing experiments, judged by CER once references exist.
3. Low-confidence routing recall (ADR-011).
4. Model packaging in the image / CI cache; wiring `result["warnings"]` into the case's extraction
   warnings (see the stream handoff).
