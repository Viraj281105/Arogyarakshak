# Wave 2 handoff: stream A (Devanagari OCR enablement)

Branch `wave2/a-ocr`. Evidence and numbers: `docs/evaluation/devanagari-ocr.md`.

## What shipped
* `packages/kadi/kadi/pdf_text_quality.py`: `assess_text_layer(text) -> TextLayerAssessment`
  (`verdict` in `clean|corrupted|not_devanagari`, `devanagari_ratio`, `known_word_ratio`,
  `legacy_font_signature`, plus `malformed_token_ratio`, `mixed_token_ratio`, `devanagari_tokens`).
  Holds no document text.
* `kadi.ocr.ocr_parser`: `OCR_LANGUAGES` (env, default `en`), `get_ocr_languages()`,
  `UnsupportedOCRLanguageError`, readers cached per language tuple (`_easyocr_readers`), per-page PDF
  route (corrupted -> rasterised in memory -> OCR), `MAX_OCR_PAGES_PER_DOCUMENT = 10`, `PDF_OCR_DPI = 200`.
* `parse_document` result gains `warnings: list[str]` (counts only) on every path; `ocr_segments` is now
  also filled for OCR'd PDF pages.
* `scripts/devanagari_ocr_baseline.py` (output refused inside the repo; no WER/CER).
* Docs: `docs/evaluation/devanagari-ocr.md`, `OCR_LANGUAGES` row in `docs/configuration/environment-variables.md`
  and `.env.example`.

## Decisions
* Env var is read inside the Kadi package (not via the API `Settings`), so `packages/kadi` keeps no
  dependency on `apps/api`. The readers cache moved from one singleton to a dict; the existing test
  fixture in `kadi/ocr/tests/test_ocr_security.py` now clears the dict.
* Corrupted page + default `en`: still OCR'd (never trusted), with a warning to set `hi,mr,en`.
* Pages over the cap are skipped, not read from the corrupted layer.
* `not_devanagari` covers English, blank and image-only pages: they keep the existing text path (a
  scan page with an empty layer still ends in the old "may be a scan" error; unchanged).
* Thresholds were tuned on the six real PDFs and are constants in the module.

## Env vars
`OCR_LANGUAGES` (default `en`; `en|hi|mr`, comma separated).

## Integrator wiring (nothing was edited outside stream-A files)
1. `apps/api/app/services/case_ingestion.py` (line ~194): `parsed["warnings"]` is available after
   `parse_document`; append it to the extraction warnings recorded for the case so the "OCR used on N
   pages" and "OCR languages exclude Devanagari" notes reach the UI. Not done here (outside ownership).
2. To turn Devanagari on in a deployment set `OCR_LANGUAGES=hi,mr,en` and make sure the weights are in
   the image or mounted volume (`EASYOCR_MODULE_PATH`); the readers never download (the baseline
   script builds them with `download_enabled=False`; the parser uses EasyOCR defaults, i.e. it
   *would* download if weights are missing: bake the weights in before enabling).
3. Optional: a non-gating `workflow_dispatch` job for the baseline script (plan workstream G).
4. The `.env.example` and env-doc rows were inserted next to `OCR_LOW_CONFIDENCE_THRESHOLD` (not at the
   end of the file/table): expect a trivial textual merge if another stream edits the same lines.

## Not verified / open
* No reference transcription: **no WER/CER or accuracy** exists. Confidence numbers are engine scores.
* Gate precision on real pages rests on the corpus README's manual assessment; no real *clean*
  Devanagari PDF was available, so false positives on real clean text are untested.
* Peak memory (4297 MB) is a process high-water mark across both configurations; per-configuration
  memory is not isolated.
* Latency ~25 s/page for `hi,mr,en` on CPU (6 pages measured, one per document); no latency
  optimisation was attempted.
* `OCR_LANGUAGES=hi,mr,en` on images was not benchmarked beyond the rasterised PDF pages.
* Hindi/Marathi strings in tests and the word list are unreviewed: NEEDS NATIVE-SPEAKER QA.
