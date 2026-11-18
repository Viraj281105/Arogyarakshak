"""Shadow runs (WS2, ADR-024): off by default, bounded, numbers only, never on inputs with
identifiers, never touching production results."""

import random

import pytest

from kadi.llm import LlmConfig, LlmRequest, LlmRuntime, PromptVersion, ResilientLlmClient
from kadi.llm import clear_llm_observers, register_llm_observer
from kadi.llm.errors import LlmServerError
from kadi.llm.shadow import agreement


class Transport:
    def __init__(self, by_model):
        self.by_model = by_model
        self.calls = []

    def __call__(self, payload, api_key, timeout_s):
        self.calls.append(payload)
        result = self.by_model[payload["model"]]
        if isinstance(result, BaseException):
            raise result
        return {"choices": [{"message": {"content": result}}]}


def runtime(transport, **cfg):
    config = LlmConfig(**{"shadow_enabled": True, "shadow_model": "cand/model", "shadow_sample_rate": 1.0,
                          "shadow_max_runs": 10, **cfg})
    return LlmRuntime(config=config, transport=transport, sleep=lambda s: None, rng=random.Random(3),
                      shadow_executor=lambda job: job())


def req(prompt='Consultation: 500', kind="test.kind", json_mode=True):
    return LlmRequest(system="sys", prompt=prompt, kind=kind, json_mode=json_mode,
                      prompt_version=PromptVersion("test.kind", "1"))


@pytest.fixture(autouse=True)
def _observers():
    clear_llm_observers()
    yield
    clear_llm_observers()


def test_shadow_is_off_by_default():
    rt = LlmRuntime(config=LlmConfig(), transport=Transport({"prod/model": "{}"}))
    assert rt.shadow is None
    assert LlmRuntime(config=LlmConfig(shadow_enabled=True)).shadow is None  # no candidate model


def test_shadow_runs_candidate_and_records_only_numbers():
    t = Transport({"prod/model": '{"a": 1, "b": 2}', "cand/model": '{"a": 1, "b": 3}'})
    rt = runtime(t)
    resp = ResilientLlmClient("k", "prod/model", runtime=rt).complete(req())
    assert resp.text == '{"a": 1, "b": 2}'  # production result untouched
    assert [c["model"] for c in t.calls] == ["prod/model", "cand/model"]
    snap = rt.shadow.snapshot()
    assert list(snap) == ["test.kind|cand/model|same-prompt"]
    s = snap["test.kind|cand/model|same-prompt"]
    assert s["runs"] == 1 and s["exact_matches"] == 0 and s["mean_agreement"] == pytest.approx(0.5)
    for value in s.values():
        assert value is None or isinstance(value, (int, float))


def test_shadow_skips_inputs_with_identifiers():
    t = Transport({"prod/model": "{}", "cand/model": "{}"})
    rt = runtime(t)
    ResilientLlmClient("k", "prod/model", runtime=rt).complete(req(prompt="Patient Name: Asha\nTotal: 5"))
    assert [c["model"] for c in t.calls] == ["prod/model"]
    assert rt.shadow.snapshot()["test.kind|cand/model|same-prompt"]["skipped_pii"] == 1


def test_shadow_cost_is_capped_and_sampling_applies():
    t = Transport({"prod/model": "{}", "cand/model": "{}"})
    rt = runtime(t, shadow_max_runs=2)
    client = ResilientLlmClient("k", "prod/model", runtime=rt)
    for _ in range(5):
        client.complete(req())
    s = rt.shadow.snapshot()["test.kind|cand/model|same-prompt"]
    assert s["runs"] == 2 and s["skipped_cap"] == 3

    t2 = Transport({"prod/model": "{}", "cand/model": "{}"})
    rt2 = runtime(t2, shadow_sample_rate=0.0)
    ResilientLlmClient("k", "prod/model", runtime=rt2).complete(req())
    assert rt2.shadow.snapshot()["test.kind|cand/model|same-prompt"]["skipped_sampled"] == 1


def test_shadow_failure_never_affects_production_and_is_counted():
    t = Transport({"prod/model": "{}", "cand/model": LlmServerError("HTTP 500", status=500)})
    rt = runtime(t, max_attempts=1)
    assert ResilientLlmClient("k", "prod/model", runtime=rt).complete(req()).text == "{}"
    s = rt.shadow.snapshot()["test.kind|cand/model|same-prompt"]
    assert s["errors"] == 1 and s["mean_agreement"] is None


def test_shadow_uses_a_registered_candidate_prompt_and_emits_a_shadow_kind_event():
    t = Transport({"prod/model": "same words here", "cand/model": "same words here"})
    rt = runtime(t)
    rt.shadow.set_candidate_prompt("test.kind", PromptVersion("test.kind", "2"), "CANDIDATE SYSTEM")
    events = []
    register_llm_observer(events.append)
    ResilientLlmClient("k", "prod/model", runtime=rt).complete(req(json_mode=False))
    assert t.calls[1]["messages"][0]["content"] == "CANDIDATE SYSTEM"
    assert [e.kind for e in events] == ["test.kind", "test.kind.shadow"]
    s = rt.shadow.snapshot()["test.kind|cand/model|test.kind@2"]
    assert s["exact_matches"] == 1 and s["mean_agreement"] == 1.0


def test_shadow_calls_do_not_charge_the_production_budget_or_use_the_cache():
    from kadi.llm import TokenBudget

    t = Transport({"prod/model": "{}", "cand/model": "{}"})
    rt = runtime(t, cache_enabled=True)
    budget = TokenBudget(limit=10_000)
    r = req()
    r.budget = budget
    ResilientLlmClient("k", "prod/model", runtime=rt).complete(r)
    assert len(rt.cache) == 1  # only the production response
    assert budget.used > 0
    used_after_first = budget.used
    ResilientLlmClient("k", "prod/model", runtime=rt).complete(r)  # cache hit -> no shadow, no charge
    assert budget.used == used_after_first
    assert [c["model"] for c in t.calls] == ["prod/model", "cand/model"]


def test_agreement_scores():
    assert agreement('{"a":1}', '{"a":1}', True) == (True, 1.0, True)
    assert agreement('{"a":1,"b":2}', '{"a":1}', True) == (False, 0.5, True)
    assert agreement('{"a":1}', "not json", True) == (False, 0.0, False)
    exact, score, valid = agreement("the cat sat", "the cat ran", False)
    assert exact is False and score == pytest.approx(2 / 4) and valid is None
