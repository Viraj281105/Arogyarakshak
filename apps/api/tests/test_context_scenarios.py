"""#112: the committed context-reuse dataset equals a fresh instrumented run of scenarios A-E.

Comparison only. Regenerate the dataset after an intended change with
``python scripts/generate_context_reuse_dataset.py``.
"""

import pytest

from app.config import settings
from app.evaluation.context_reuse import evaluate_context_reuse
from app.evaluation.datasets import DATA_DIR, load_dataset
from app.telemetry import context_metrics as cm
from tests.clinical_helpers import K, client
from tests.context_flows import FLOWS, Collector, run_scenario

DATASET = DATA_DIR / "context_reuse_synthetic.jsonl"


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(settings, "clinical_demo_mode", True)  # scenario C replays its recorded OCR
    monkeypatch.setattr(settings, "groq_api_key", "")  # deterministic heuristic extraction, no network


def test_dataset_matches_the_instrumented_run(demo, monkeypatch):
    meta, rows = load_dataset(DATASET)
    assert meta["synthetic"] is True
    committed = {r["id"]: r for r in rows}
    assert set(committed) == set(FLOWS)
    for sid in FLOWS:
        assert run_scenario(sid, client, monkeypatch.setattr) == committed[sid], sid


def test_committed_dataset_scores():
    _, rows = load_dataset(DATASET)
    result = evaluate_context_reuse(rows)
    assert result["n_scenarios"] == 5 and result["n_requests"] > 0
    assert 0.0 <= result["hit_rate"] <= 1.0 and 0.0 < result["dpr"] < 1.0


def test_a_read_of_context_the_case_does_not_hold_is_empty(demo, monkeypatch):
    collector = Collector()
    monkeypatch.setattr(cm, "record_context_request", collector.request)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.post(f"/api/v1/billnyay/cases/{case_id}/audit").status_code == 200  # no billing lines yet
    assert [(e.module, e.context, e.outcome, e.items) for e in collector.events] == [
        ("billnyay", "line_items", "empty", 0)
    ]
