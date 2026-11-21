"""#112: context-request counters - closed labels, no PHI, survive a registry rebuild."""

import ast
import pathlib
import random
import string

import pytest

from app.telemetry import context_metrics as cm
from app.telemetry import metrics as m
from tests.telemetry_helpers import PHI_SAMPLES, label_values

APP = pathlib.Path(__file__).resolve().parents[1] / "app"


@pytest.fixture(autouse=True)
def fresh():
    m.reset_for_tests()
    yield
    m.reset_for_tests()


def _lines(prefix):
    return [line for line in m.render().decode().splitlines() if line.startswith(prefix)]


def test_event_is_counted_by_module_context_and_outcome():
    cm.record_context_request(cm.ContextRequestEvent("billnyay", "line_items", "served", 3))
    cm.record_context_request(cm.ContextRequestEvent("billnyay", "line_items", "served", 1))
    cm.record_context_request(cm.ContextRequestEvent("dawacheck", "entities", "empty", 0))
    text = m.render().decode()
    assert 'arogya_context_requests_total{context="line_items",module="billnyay",outcome="served"} 2.0' in text
    assert 'arogya_context_requests_total{context="entities",module="dawacheck",outcome="empty"} 1.0' in text


def test_ingest_work_counter():
    cm.record_context_work("ocr", 2)
    cm.record_context_work("extraction")
    text = m.render().decode()
    assert 'arogya_context_ingest_work_total{kind="ocr"} 2.0' in text
    assert 'arogya_context_ingest_work_total{kind="extraction"} 1.0' in text


def test_bad_work_units_are_ignored():
    for bad in (0, -3, True, 1.5, None):
        cm.record_context_work("ocr", bad)
    assert not _lines("arogya_context_ingest_work_total{")


def test_registry_rebuild_rebinds_the_counters():
    cm.record_context_request(cm.ContextRequestEvent("kadi", "entities", "served", 1))
    m.reset_for_tests()
    assert not _lines("arogya_context_requests_total{")
    cm.record_context_request(cm.ContextRequestEvent("kadi", "entities", "served", 1))
    assert len(_lines("arogya_context_requests_total{")) == 1


def test_phi_and_random_strings_never_become_labels():
    rng = random.Random(112)
    junk = ["".join(rng.choice(string.printable) for _ in range(rng.randint(1, 40))) for _ in range(200)]
    for sample in PHI_SAMPLES + junk:
        cm.record_context_request(cm.ContextRequestEvent(sample, sample, sample, 1))
        cm.record_context_work(sample)
    allowed = cm.MODULES | cm.CONTEXT_KINDS | cm.OUTCOMES | cm.WORK_KINDS | {m.OTHER}
    text = m.render().decode()
    seen = {v for line in text.splitlines() if line.startswith("arogya_context") for v in label_values(line)}
    assert seen and seen <= allowed, seen - allowed
    for sample in PHI_SAMPLES:
        assert sample not in text


def test_a_failing_event_never_raises():
    cm.record_context_request(object())
    cm.record_context_request(None)
    assert 'outcome="other"' in m.render().decode()


def test_every_call_site_uses_declared_module_and_context_values():
    """A typo in ``module=``/``context=`` would otherwise be counted silently as ``other``."""
    checked = 0
    for path in APP.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == "load_case_entities":
                kwargs = {k.arg: k.value for k in node.keywords}
                for name, allowed in (("module", cm.MODULES), ("context", cm.CONTEXT_KINDS)):
                    value = kwargs.get(name)
                    assert isinstance(value, ast.Constant) and value.value in allowed, (path.name, node.lineno, name)
                checked += 1
    assert checked >= 10, "the call-site scan found too few readers; has the reader been renamed?"
