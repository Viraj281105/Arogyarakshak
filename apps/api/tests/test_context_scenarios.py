"""#112: instrumented context requests over the synthetic demo scenarios A-E.

Each scenario's documents go through the real upload pipeline (heuristic extraction, no
LLM, scenario C replays its recorded OCR as in demo mode), then the module calls listed in
FLOWS are made. The counters are read twice, once with reuse on (default) and once with
``CONTEXT_REUSE_ENABLED=false`` (the baseline), and compared with the committed dataset
``data/evaluation/context_reuse_synthetic.jsonl``, so the dataset cannot drift from the code.

Regenerate the dataset after an intended change with ``CONTEXT_REUSE_REGEN=1``.
"""

import json
import os
from pathlib import Path

import pytest

from app.config import settings
from app.evaluation.context_reuse import evaluate_context_reuse
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.telemetry import context_metrics as cm
from app.telemetry import metrics as m
from tests.clinical_helpers import K, client

DOCS = Path(__file__).resolve().parents[3] / "demo" / "documents"
B = "/api/v1/billnyay"
DATASET = DATA_DIR / "context_reuse_synthetic.jsonl"

# scenario -> (title, documents, module calls made after upload). Calls the scenario script
# makes through routes that are not instrumented yet (DaaviSetu readiness, clinical
# plausibility) are not listed; see docs/evaluation/context-reuse.md.
FLOWS = {
    "A": ("Hospital bill + discharge summary, then audit, ICD audit and appeal",
          ["A_hospital_bill.txt", "A_discharge_summary.txt"],
          [("POST", "/billnyay/cases/{c}/audit"), ("GET", "/billnyay/cases/{c}/icd-audit"), ("POST", "/billnyay/cases/{c}/appeal")]),
    "B": ("Pre-authorisation request (upload-time module checks only)", ["B_preauth_request.txt"], []),
    "C": ("Uncertain prescription image, then DawaCheck case benchmark",
          ["C_prescription_uncertain.png"], [("GET", "/dawacheck/cases/{c}/benchmark")]),
    "D": ("Insurance denial letter, then appeal draft", ["D_insurance_denial_letter.txt"], [("POST", "/billnyay/cases/{c}/appeal")]),
    "E": ("Diabetes admission note (upload-time module checks only)", ["E_diabetes_admission_note.txt"], []),
}


# Row order of an unordered entity query, and ids/timestamps/hashes minted per case or per
# call, legitimately differ between two runs; everything else must be identical.
VOLATILE = {"entity_id", "document_sha256", "evaluated_at", "transcription_task_id", "task_id"}


def _canonical(value):
    if isinstance(value, dict):
        return {k: _canonical(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return sorted((_canonical(v) for v in value), key=lambda v: json.dumps(v, sort_keys=True, default=str))
    return value


def _run(sid: str, reuse: bool, monkeypatch):
    title, docs, calls = FLOWS[sid]
    monkeypatch.setenv("CONTEXT_REUSE_ENABLED", "true" if reuse else "false")
    m.reset_for_tests()
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    for name in docs:
        res = client.post(f"{K}/cases/{case_id}/upload", files={"file": (name, (DOCS / name).read_bytes())})
        assert res.status_code == 202, res.text
    bodies = []
    for verb, path in calls:
        res = client.request(verb, f"/api/v1{path.format(c=case_id)}")
        assert res.status_code == 200, (path, res.text)
        bodies.append(_canonical(json.loads(res.text.replace(case_id, "CASE"))))
    row = {"requests": {}, "work": {}}
    for key, value in cm.totals().items():
        kind, a, b = key.split("/")
        if kind == "requests":
            row["requests"].setdefault(a, {})[b] = int(value)
        else:
            row["work"].setdefault(a, {})[b] = int(value)
    return row, bodies


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", True)  # scenario C replays its recorded OCR
    monkeypatch.setattr(settings, "groq_api_key", "")  # deterministic heuristic extraction, no network
    yield
    m.reset_for_tests()


def _observe_all(monkeypatch):
    rows = []
    for sid, (title, docs, calls) in FLOWS.items():
        on, bodies_on = _run(sid, True, monkeypatch)
        off, bodies_off = _run(sid, False, monkeypatch)
        rows.append({"id": sid, "scenario": title, "documents": len(docs),
                     "module_calls": [f"{v} {p}" for v, p in calls], "reuse_on": on, "reuse_off": off,
                     "_bodies": (bodies_on, bodies_off)})
    return rows


def test_dataset_matches_the_instrumented_run(demo, monkeypatch):
    observed = _observe_all(monkeypatch)
    clean = [{k: v for k, v in r.items() if k != "_bodies"} for r in observed]
    if os.environ.get("CONTEXT_REUSE_REGEN") == "1":
        meta = {
            "name": "context_reuse_synthetic_v1", "synthetic": True,
            "provenance": ("Instrumented counts from running the committed synthetic demo documents (scenarios A-E) "
                           "through the upload pipeline and the listed module calls, once with reuse on and once with "
                           "CONTEXT_REUSE_ENABLED=false. Not production traffic. Regenerate with CONTEXT_REUSE_REGEN=1 "
                           "pytest apps/api/tests/test_context_scenarios.py."),
            "description": "Per-scenario context-request outcomes and OCR/extraction work units, reuse on versus off.",
        }
        lines = [json.dumps({"_meta": meta})] + [json.dumps(r, sort_keys=True) for r in clean]
        DATASET.write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta, rows = load_dataset(DATASET)
    assert meta["synthetic"] is True
    assert {r["id"]: r for r in rows} == {r["id"]: r for r in json.loads(json.dumps(clean))}


def test_turning_reuse_off_never_changes_module_results(demo, monkeypatch):
    for r in _observe_all(monkeypatch):
        on, off = r["_bodies"]
        assert on == off, r["id"]


def test_baseline_invariants_on_the_observed_counts(demo, monkeypatch):
    for r in _observe_all(monkeypatch):
        on, off = r["reuse_on"], r["reuse_off"]
        assert "repeat" not in on["work"], "reuse on never repeats extraction"
        assert on["work"]["ingest"] == off["work"]["ingest"], "ingestion work is the same in both modes"
        assert all(set(v) == {"fresh"} for v in off["requests"].values()), "baseline: every request is fresh"
        n_on = sum(sum(v.values()) for v in on["requests"].values())
        n_off = sum(sum(v.values()) for v in off["requests"].values())
        assert n_on == n_off, "the same requests are made in both modes"
        # Documents are taken in one at a time, so a request during the first upload of a
        # two-document case repeats one document's work, not two.
        assert 0 < off["work"]["repeat"]["ocr"] <= r["documents"] * n_off
        assert off["work"]["repeat"]["ocr"] == off["work"]["repeat"]["extraction"]


def test_committed_dataset_scores():
    _, rows = load_dataset(DATASET)
    result = evaluate_context_reuse(rows)
    assert result["n_scenarios"] == 5
    assert result["n_requests"] > 0
    assert 0.0 <= result["crr"] <= 1.0 and 0.0 <= result["dpr"] < 1.0


def test_a_request_for_context_the_case_does_not_hold_is_fresh(demo, monkeypatch):
    monkeypatch.setenv("CONTEXT_REUSE_ENABLED", "true")
    m.reset_for_tests()
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(f"{B}/cases/{case_id}/audit").status_code == 200  # no billing lines stored yet
    assert cm.totals() == {"requests/billnyay/fresh": 1.0}  # nothing to reuse, and no repeat work counted


@pytest.mark.parametrize("value, expected", [("false", False), ("0", False), ("OFF", False), ("true", True), ("", True)])
def test_reuse_switch_parsing(monkeypatch, value, expected):
    from app.services.context_requests import reuse_enabled

    monkeypatch.setenv("CONTEXT_REUSE_ENABLED", value)
    assert reuse_enabled() is expected
