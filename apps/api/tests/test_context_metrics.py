"""#112: context-request counters - closed labels, no PHI, survive a registry rebuild."""

import random
import re
import string

import pytest

from app.telemetry import context_metrics as cm
from app.telemetry import metrics as m
from tests.test_telemetry_metrics import PHI_SAMPLES, label_values


@pytest.fixture(autouse=True)
def fresh():
    m.reset_for_tests()
    yield
    m.reset_for_tests()


def test_event_is_counted_by_module_and_outcome():
    cm.record_context_request(cm.ContextRequestEvent("billnyay", "line_items", "reused", 3))
    cm.record_context_request(cm.ContextRequestEvent("billnyay", "line_items", "reused", 1))
    cm.record_context_request(cm.ContextRequestEvent("dawacheck", "entities", "fresh", 0))
    text = m.render().decode()
    assert 'arogya_context_requests_total{module="billnyay",outcome="reused"} 2.0' in text
    assert 'arogya_context_requests_total{module="dawacheck",outcome="fresh"} 1.0' in text


def test_work_counter_and_totals():
    cm.record_context_work("ocr", "ingest", 2)
    cm.record_context_work("extraction", "repeat")
    cm.record_context_request(cm.ContextRequestEvent("kadi", "timeline", "reused", 5))
    assert cm.totals() == {"work/ingest/ocr": 2.0, "work/repeat/extraction": 1.0, "requests/kadi/reused": 1.0}


def test_bad_work_units_are_ignored():
    for bad in (0, -3, True, 1.5, None):
        cm.record_context_work("ocr", "ingest", bad)
    assert cm.totals() == {}


def test_registry_rebuild_rebinds_the_counters():
    cm.record_context_request(cm.ContextRequestEvent("kadi", "entities", "reused", 1))
    m.reset_for_tests()
    assert cm.totals() == {}
    cm.record_context_request(cm.ContextRequestEvent("kadi", "entities", "reused", 1))
    assert cm.totals() == {"requests/kadi/reused": 1.0}


def test_phi_and_random_strings_never_become_labels():
    rng = random.Random(112)
    junk = ["".join(rng.choice(string.printable) for _ in range(rng.randint(1, 40))) for _ in range(200)]
    for sample in PHI_SAMPLES + junk:
        cm.record_context_request(cm.ContextRequestEvent(sample, "entities", sample, 1))
        cm.record_context_work(sample, sample)
    allowed = cm.MODULES | cm.OUTCOMES | cm.WORK_KINDS | cm.WORK_PHASES | {m.OTHER}
    text = m.render().decode()
    seen = {v for line in text.splitlines() if line.startswith("arogya_context") for v in label_values(line)}
    assert seen and seen <= allowed, seen - allowed
    for sample in PHI_SAMPLES:
        assert sample not in text


def test_a_failing_event_never_raises():
    cm.record_context_request(object())  # no attributes at all
    cm.record_context_request(None)
    assert re.search(r'outcome="other"', m.render().decode())
