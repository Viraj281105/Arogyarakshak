import pytest

from kadi.llm import reset_default_runtime


@pytest.fixture(autouse=True)
def _fresh_llm_runtime():
    """The resilient LLM client's breakers/cache live in a process-wide runtime (ADR-024).
    Rebuild it for every test so one test's failures cannot open a breaker for the next."""
    reset_default_runtime()
    yield
    reset_default_runtime()


@pytest.fixture(autouse=True)
def _no_live_network(monkeypatch):
    """Tests never reach Groq (AGENTS.md network rule): no key from the environment, and
    ``urllib.request.urlopen`` raises unless a test patches it itself."""
    import urllib.request

    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    def guarded_urlopen(req, *args, **kwargs):
        raise RuntimeError("live network calls are forbidden in tests")

    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)
