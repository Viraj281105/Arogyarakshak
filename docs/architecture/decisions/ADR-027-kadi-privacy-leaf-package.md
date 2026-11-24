# ADR-027: Direct-identifier redaction lives in a dependency-free `kadi.privacy` package

## Status
Accepted (2026-11-24). Number 026 is reserved by the Wave 3 plan for the accounts decision
(`docs/superpowers/plans/2026-11-23-wave3.md`).

## Context
An Archify Code Analysis of `packages/kadi`
([report](../code-analysis/kadi/README.md)) reported an error-level package cycle:
`kadi` → `kadi/llm` → `kadi`. The edge back to the root was `kadi/llm/cache.py` importing
`kadi.redaction`, because the response cache and the shadow runner must apply the same
direct-identifier rule as the rest of Kadi (ADR-003, ADR-024: only requests that
`redact_pii` leaves unchanged are cached or shadowed). Root modules such as `kadi.extraction`
import `kadi.llm`, which closed the loop. `redaction.py` imports only the standard library, so
no file cycle existed, but the layering was inverted: a low-level client depended on the
package's top level.

## Decision
1. `redact_pii`, `contains_direct_identifier` and `REDACTION_MARK` live in
   `kadi/privacy/redaction.py`. `kadi/privacy` is a leaf: it imports nothing else from `kadi`.
2. `kadi/redaction.py` remains as a re-export alias. The public import path used by
   `apps/api`, `kadi.clinical_review`, the tests and ADR-003/ADR-024 is unchanged.
3. Code that sits below the root modules (`kadi.llm`, `kadi.privacy`) imports redaction from
   `kadi.privacy`. The rule is enforced two ways: the `kadi-llm-and-privacy-below-root` contract
   in `.importlinter` (CI) and `packages/kadi/tests/test_package_layering.py`.

4. **Second cycle, `kadi` ↔ `kadi/ocr` (added the same day).** `kadi/__init__.py` re-exports
   `parse_document` lazily (PEP 562 `__getattr__`) instead of importing
   `kadi/ocr/ocr_parser.py` at the top, because that module imports root modules
   (`kadi.line_items`, `kadi.pdf_text_quality`). Public behaviour is unchanged; only the load time
   moves, so `import kadi` no longer loads the OCR module. `packages/kadi/tests/test_package_layering.py`
   pins this, because `lint-imports` cannot forbid a top-level import while allowing a deferred one.

## Alternatives rejected
- **Inject the redactor into `kadi.llm`** (a callable passed by the caller): removes the import
  but makes the privacy rule optional at every construction site. For a rule whose failure mode
  is caching one patient's data for another, it must not be possible to forget it.
- **Delete the alias and rewrite every caller**: churn across `apps/api` and several ADRs for no
  behavioural gain.
- **For `kadi` ↔ `kadi/ocr`, move `line_items` and `pdf_text_quality` into a leaf package**:
  correct but a larger move (the extraction fallback and the OCR gate both use them) for a
  problem the lazy export already removes at import time. Still available if the static report's
  remaining warning needs to go away entirely.

## Consequences
- No functional behaviour change: the redaction module is moved, not edited, and
  `parse_document` is still exported from the package root (only when it loads changes).
- New privacy primitives that other Kadi subpackages need belong in `kadi/privacy`, which must
  stay free of imports from the rest of `kadi`.
- The static report still lists `kadi` ↔ `kadi/ocr` as a **warning** ("deferred, conditional, or
  type-only edges"): the lazy import is still an import. It cannot occur at import time, and
  would return as an error if the import moved back to the top of `kadi/__init__.py`.
- `kadi.ocr` is no longer a side effect of `import kadi`; code that needs it imports
  `kadi.ocr.ocr_parser` (as every caller in the repository already does) or uses
  `kadi.parse_document`.
