"""Case erasure also empties the opt-in LLM response cache (ADR-010, ADR-024).

The cache holds no case id (keys are SHA-256 digests), so erasing any case purges the
whole in-memory cache rather than leaving output derived from that case's documents."""

from kadi.llm import LlmConfig, LlmRuntime, set_default_runtime

from app.main import app
from tests.auth_test_client import AuthAwareTestClient

client = AuthAwareTestClient(app)


def test_deleting_a_case_purges_the_llm_cache():
    rt = LlmRuntime(config=LlmConfig(cache_enabled=True))
    set_default_runtime(rt)
    rt.cache.put("a" * 64, "cached model output")
    assert len(rt.cache) == 1

    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.delete(f"/api/v1/kadi/cases/{case_id}").status_code == 204

    assert len(rt.cache) == 0


def test_case_deletion_works_with_the_cache_disabled():
    set_default_runtime(LlmRuntime(config=LlmConfig()))
    case_id = client.post("/api/v1/kadi/cases", json={"consent_opt_in": True}).json()["id"]
    assert client.delete(f"/api/v1/kadi/cases/{case_id}").status_code == 204
