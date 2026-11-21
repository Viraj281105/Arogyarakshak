"""The scenario A-E flows behind the context-reuse dataset (#112), shared by the comparison test
and ``scripts/generate_context_reuse_dataset.py``.

Each flow uploads the scenario's committed synthetic documents through the real pipeline
(heuristic extraction, no LLM; scenario C replays its recorded OCR in demo mode) and then makes
the listed module calls. Context reads and ingestion work are collected from the in-process
recording functions (explicit events, not by reading the Prometheus registry back).

Calls the scenario scripts make through routes that read context outside the instrumented
readers are not listed; see docs/evaluation/context-reuse.md.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from app.telemetry import context_metrics as cm

DOCS = Path(__file__).resolve().parents[3] / "demo" / "documents"
K = "/api/v1/kadi"

FLOWS: Dict[str, Tuple[str, List[str], List[Tuple[str, str]]]] = {
    "A": ("Hospital bill + discharge summary, then audit, ICD audit and appeal",
          ["A_hospital_bill.txt", "A_discharge_summary.txt"],
          [("POST", "/billnyay/cases/{c}/audit"), ("GET", "/billnyay/cases/{c}/icd-audit"), ("POST", "/billnyay/cases/{c}/appeal")]),
    "B": ("Pre-authorisation request (upload-time module checks only)", ["B_preauth_request.txt"], []),
    "C": ("Uncertain prescription image, then DawaCheck case benchmark",
          ["C_prescription_uncertain.png"], [("GET", "/dawacheck/cases/{c}/benchmark")]),
    "D": ("Insurance denial letter, then appeal draft", ["D_insurance_denial_letter.txt"], [("POST", "/billnyay/cases/{c}/appeal")]),
    "E": ("Diabetes admission note (upload-time module checks only)", ["E_diabetes_admission_note.txt"], []),
}


class Collector:
    """Records the events the production code emits, in place of the Prometheus counters."""

    def __init__(self) -> None:
        self.events: List[Any] = []
        self.work: Dict[str, int] = defaultdict(int)

    def request(self, event: Any) -> None:
        self.events.append(event)

    def ingest(self, kind: str, units: int = 1) -> None:
        self.work[kind] += units


def run_scenario(sid: str, client: Any, patch) -> Dict[str, Any]:
    """Runs one flow on ``client`` and returns the dataset row. ``patch(obj, name, value)``
    installs a replacement (``monkeypatch.setattr`` in tests)."""
    title, docs, calls = FLOWS[sid]
    collector = Collector()
    patch(cm, "record_context_request", collector.request)
    patch(cm, "record_context_work", collector.ingest)
    case_id = client.post(f"{K}/cases", json={"consent_opt_in": True}).json()["id"]
    for name in docs:
        res = client.post(f"{K}/cases/{case_id}/upload", files={"file": (name, (DOCS / name).read_bytes())})
        assert res.status_code == 202, res.text
    for verb, path in calls:
        res = client.request(verb, f"/api/v1{path.format(c=case_id)}")
        assert res.status_code == 200, (path, res.text)
    requests: Dict[str, Dict[str, int]] = {}
    for event in collector.events:
        bucket = requests.setdefault(event.module, {"served": 0, "empty": 0})
        bucket[event.outcome] += 1
    return {
        "id": sid, "scenario": title, "documents": len(docs),
        "module_calls": [f"{v} {p}" for v, p in calls],
        "ingest": dict(sorted(collector.work.items())),
        "requests": dict(sorted(requests.items())),
    }
