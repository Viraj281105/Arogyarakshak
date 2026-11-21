"""Per-page verdicts over the real public Devanagari PDFs (docs/evaluation/devanagari-ocr.md).

Skipped when the git-ignored corpus is absent. Set AROGYA_DEVANAGARI_DOCS to point at it.
X = corrupted, . = not_devanagari, C = clean. These strings are the table in the evaluation doc;
if the gate changes, re-run this test and update both together. There is no per-page human label:
the expectation is the corpus README's manual assessment (every Devanagari page of these files has an
unusable text layer), so this guards regressions of the gate on these files, not its accuracy.
"""

import importlib.util
import os
from pathlib import Path

import pytest

fitz = pytest.importorskip("fitz")

from kadi.pdf_text_quality import assess_text_layer  # noqa: E402

EXPECTED = {
    "irdai_complaint_registration_form": "XX..",
    "mahabocw_gr_2017-06": "XXX",
    "mh_gr_2025-09": "XXXX",
    "mh_gr_2026-01": "XXXXXXXX",
    "ombudsman_rules_2017_gazette": "XXXXXXX......",
    "pib_pmjay_2025-11": "XXX.XXXXXX.",
}
_SYMBOL = {"clean": "C", "corrupted": "X", "not_devanagari": "."}


def _docs_dir() -> Path | None:
    env = os.environ.get("AROGYA_DEVANAGARI_DOCS")
    if env:
        return Path(env)
    script = Path(__file__).resolve().parents[3] / "scripts" / "devanagari_ocr_baseline.py"
    spec = importlib.util.spec_from_file_location("devanagari_ocr_baseline", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.default_docs_dir()


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_real_pdf_page_verdicts_match_the_documented_table(name):
    docs = _docs_dir()
    pdfs = list(docs.rglob(f"{name}.pdf")) if docs and docs.is_dir() else []
    if not pdfs:
        pytest.skip("real Devanagari corpus not available")
    with fitz.open(pdfs[0]) as doc:
        verdicts = "".join(_SYMBOL[assess_text_layer(p.get_text()).verdict] for p in doc)
    assert verdicts == EXPECTED[name]
