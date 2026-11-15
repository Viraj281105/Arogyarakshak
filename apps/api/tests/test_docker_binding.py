"""SEC-13 regression: the api (and postgres) host port mappings in docker-compose.yml
must never bind to every interface. Direct 0.0.0.0 exposure of the API puts it on the
network with no reverse proxy in front of it, which breaks the trusted-proxy assumption
behind app/rate_limit.py::resolve_client_ip (X-Forwarded-For must only be trusted from a
deliberately configured proxy topology).

Loaded by path since scripts/ is not on pythonpath — same script CI invokes directly.
"""

import importlib.util
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location("ci_guardrails", ROOT_DIR / "scripts" / "ci_guardrails.py")
ci_guardrails = importlib.util.module_from_spec(_SPEC)
sys.modules["ci_guardrails"] = ci_guardrails
_SPEC.loader.exec_module(ci_guardrails)


def test_api_port_is_not_bound_to_all_interfaces():
    assert ci_guardrails.check_docker_api_binding() == []


def test_postgres_port_is_not_bound_to_all_interfaces():
    assert ci_guardrails.check_docker_postgres_binding() == []


def test_guardrail_catches_an_unbound_api_port(tmp_path, monkeypatch):
    """Adversarial: a regression back to '\"8000:8000\"' must be caught, proving the
    check actually inspects content rather than always passing."""
    fake_compose = tmp_path / "docker-compose.yml"
    fake_compose.write_text('services:\n  api:\n    ports:\n      - "8000:8000"\n', encoding="utf-8")
    monkeypatch.setattr(ci_guardrails, "ROOT_DIR", tmp_path)
    errors = ci_guardrails.check_docker_api_binding()
    assert errors, "an all-interfaces '8000:8000' binding must be flagged"
    assert "8000:8000" in errors[0]


# --- package hygiene: TypeScript source packages (ADR-022) -------------------


def test_real_repo_passes_package_hygiene():
    assert ci_guardrails.check_package_hygiene() == []


def _fake_packages(tmp_path, names):
    for name in names:
        (tmp_path / "packages" / name).mkdir(parents=True)
    for req in ci_guardrails.REQUIRED_PACKAGES:
        (tmp_path / "packages" / req).mkdir(parents=True, exist_ok=True)
        (tmp_path / "packages" / req / "pyproject.toml").write_text("", encoding="utf-8")


def test_python_package_without_config_still_fails(tmp_path, monkeypatch):
    _fake_packages(tmp_path, ["rogue"])
    monkeypatch.setattr(ci_guardrails, "ROOT_DIR", tmp_path)
    errors = ci_guardrails.check_package_hygiene()
    assert any("'rogue'" in e and "pyproject.toml" in e for e in errors)


def test_ts_source_packages_are_exempt_only_from_python_config(tmp_path, monkeypatch):
    _fake_packages(tmp_path, ["design-tokens", "api-client", "i18n"])
    monkeypatch.setattr(ci_guardrails, "ROOT_DIR", tmp_path)
    assert ci_guardrails.check_package_hygiene() == []
    (tmp_path / "packages" / "Upper-Ts").mkdir()
    monkeypatch.setattr(ci_guardrails, "TS_SOURCE_PACKAGES", {"design-tokens", "api-client", "i18n", "Upper-Ts"})
    assert any("lowercase" in e for e in ci_guardrails.check_package_hygiene())
