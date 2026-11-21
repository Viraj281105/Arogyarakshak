# Wave 2 handoff: stream A (Devanagari OCR enablement)

Branch `wave2/a-ocr`. Evidence and numbers: `docs/evaluation/devanagari-ocr.md`.

> Every confidence number in this work is the OCR engine's own score, **not accuracy**. No reference
> transcription exists: there is no WER/CER and no correctness claim. Timings come from 6 pages; larger
> figures are extrapolations.

## What shipped
* `packages/kadi/kadi/pdf_text_quality.py`: `assess_text_layer(text)` (clean / corrupted / not_devanagari). English,
  other Indic scripts, accents, ligatures and `μg` are not condemned (tested); short or table-like Devanagari pages are
  never condemned by the known-word ratio alone.
* `kadi.ocr.ocr_parser`:
  * `OCR_LANGUAGES` (default `en`), readers cached per language set, built with `download_enabled=False` and
    `model_storage_directory=$EASYOCR_MODULE_PATH/model`; `OCRModelsUnavailableError` when weights are missing.
  * Corrupted PDF pages: OCR'd only when `hi`/`mr` is configured; with the default `en` they are **skipped and reported**
    (never read with the English model, never used as extracted).
  * Bounds: one OCR job per process (bounded queue wait), `OCR_MAX_PAGES` (default 3, ceiling 10), per-document
    wall-clock budget (120 s), pixel budget 10 MP / 8000 px per side, embedded-image bomb guard, zero-area pages,
    300-page gate limit.
  * Result keys added: `warnings`, `pages_total`, `pages_read`, `pages_skipped`, `skipped_reasons`, `partial`,
    `partial_reason`; PDF `ocr_segments` have a 1-based `page`.
* `scripts/devanagari_ocr_baseline.py`, `scripts/fetch_ocr_models.py` (operator-run, needs `--download`; **not run**).
* Env vars (docs + `.env.example`): `OCR_LANGUAGES`, `OCR_MAX_PAGES`, `OCR_DOCUMENT_BUDGET_SECONDS`,
  `OCR_QUEUE_TIMEOUT_SECONDS`, `OCR_PDF_MAX_PIXELS`; `EASYOCR_MODULE_PATH` (model root) is now meaningful for the app.

## Integrator wiring (exact)
1. `apps/api/app/services/case_ingestion.py` (around the `parse_document` call, ~line 194). After parsing:
   * append every string in `parsed["warnings"]` to the case's extraction warnings;
   * if `parsed["partial"]` is true, surface `parsed["partial_reason"]` to the user (and consider holding the case for
     review instead of treating the document as complete); counts are in `pages_total/pages_read/pages_skipped` and
     `skipped_reasons`;
   * `extraction_ok=False` messages are already user-presentable (including "OCR models not installed" and
     "OCR is busy ... try again shortly", which is retryable).
2. `apps/api/Dockerfile`: the runtime stage never downloads weights now, so OCR of Devanagari needs them in the image.
   In the build stage after `pip install`, run
   `python scripts/fetch_ocr_models.py --download --languages en,hi,mr --dest /opt/easyocr/model` (needs network at build
   time only; copy `scripts/fetch_ocr_models.py` in), `COPY --from=build /opt/easyocr /opt/easyocr` in the runtime stage and
   set `ENV EASYOCR_MODULE_PATH=/opt/easyocr`. Without this, English images fail with "OCR models not installed" too.
   Add `OCR_LANGUAGES=hi,mr,en` only once the weights are baked in.
3. `infrastructure/kubernetes/base/api.yaml`: the root filesystem is read-only; EasyOCR also needs a writable
   `$HOME/.EasyOCR`-style user directory only when it creates directories: with `model_storage_directory` pointing into the
   image path the readers do `mkdir(exist_ok)` on an existing directory (fine). Set `EASYOCR_MODULE_PATH` in the env and
   keep memory limits above the measured ~4.3 GB process high-water mark for `hi,mr,en` (not isolated per configuration; verify
   in your environment). Optionally add the new `OCR_*` bounds to the ConfigMap.
4. CI (workstream G, optional): cache the weights directory; a `workflow_dispatch` job for the baseline script.
5. `.env.example` / env-doc rows sit next to `OCR_LOW_CONFIDENCE_THRESHOLD`: expect a trivial textual merge if another
   stream edits the same lines.

## Decisions
* Env vars are read inside Kadi (not via API `Settings`) so `packages/kadi` keeps no dependency on `apps/api`.
* `fitz.open` is now used as a context manager and documents need `page_count` and indexing; the mock documents in
  `kadi/ocr/tests/test_ocr.py` were extended accordingly (a shared `_MockDocBase`).
* A page with no text layer that embeds an image is reported as skipped (`no_text_layer`); a truly blank page counts as read.
* Gate thresholds are constants in the module and were tuned on the six real PDFs plus unit cases.

## Not verified / open
* Gate precision on real pages rests on the corpus README's manual assessment; no real **clean** Devanagari PDF was
  available (false positives on real clean Devanagari are unmeasured). Not caught: short corrupted pages, mixed
  clean/corrupted regions, valid-looking corruption, code-heavy English-looking Latin legacy pages.
* Peak memory (4297 MB) is a process high-water mark across both configurations; not isolated.
* Latency (~25 s/page, `hi,mr,en`, CPU) comes from 6 pages; nothing was optimised.
* Concurrency was tested with fakes only (one OCR slot, bounded wait); not load-tested.
* `scripts/fetch_ocr_models.py` was not run (it downloads); only its guard and call shape are tested with fakes.
* Hindi/Marathi strings in tests and the word list are unreviewed: NEEDS NATIVE-SPEAKER QA.
