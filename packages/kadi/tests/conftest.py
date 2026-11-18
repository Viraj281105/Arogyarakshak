import pytest

from kadi.llm import reset_default_runtime


@pytest.fixture(autouse=True)
def _fresh_llm_runtime():
    """The resilient LLM client's breakers/cache live in a process-wide runtime (ADR-024).
    Rebuild it for every test so one test's failures cannot open a breaker for the next."""
    reset_default_runtime()
    yield
    reset_default_runtime()
