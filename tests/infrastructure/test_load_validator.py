"""Unit tests for tests/load/validate_base_url.py (the load-test workflow's target guard)."""

import importlib.util
import pathlib
import sys

import pytest

LOAD = pathlib.Path(__file__).resolve().parents[2] / "tests" / "load"
_spec = importlib.util.spec_from_file_location("validate_base_url", LOAD / "validate_base_url.py")
v = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = v
_spec.loader.exec_module(v)

ALLOWED = ["staging.example.test", "Perf.Example.Test"]
PUBLIC = lambda host: ["93.184.216.34"]  # noqa: E731  (a global address)


def ok(url, resolver=PUBLIC):
    return v.validate(url, ALLOWED, resolver)


def test_an_allow_listed_https_origin_is_accepted_and_normalised():
    assert ok("https://staging.example.test") == "https://staging.example.test"
    assert ok("https://staging.example.test/") == "https://staging.example.test"
    assert ok("https://STAGING.example.test:443") == "https://staging.example.test"
    assert ok("https://perf.example.test") == "https://perf.example.test", "allow-list match is case-insensitive"
    assert ok("https://staging.example.test.") == "https://staging.example.test", "trailing dot"


@pytest.mark.parametrize(
    "url,reason",
    [
        ("", "empty"),
        ("http://staging.example.test", "https"),
        ("ftp://staging.example.test", "https"),
        ("//staging.example.test", "https"),
        ("https://user:pass@staging.example.test", "credentials"),
        ("https://user@staging.example.test", "credentials"),
        ("https://staging.example.test@evil.example.test", "credentials"),
        ("https://evil.example.test\\@staging.example.test", "whitespace"),
        ("https://staging.example.test/path", "path"),
        ("https://staging.example.test/?q=1", "query"),
        ("https://staging.example.test#frag", "query"),
        ("https://staging.example.test:8443", "port"),
        ("https://staging.example.test:99999", "port"),
        ("https://127.0.0.1", "IP"),
        ("https://10.0.0.5", "IP"),
        ("https://169.254.169.254", "IP"),
        ("https://[::1]", "IP"),
        ("https://[fd00::1]", "IP"),
        ("https://2130706433", "IP"),
        ("https://0x7f.1", "IP"),
        ("https://0177.0.0.1", "IP"),
        ("https://localhost", "local"),
        ("https://db.internal", "local"),
        ("https://svc.cluster.local", "local"),
        ("https://intranet", "fully qualified"),
        ("https://other.example.test", "LOAD_TEST_HOSTS"),
        ("https://staging.example.test.evil.test", "LOAD_TEST_HOSTS"),
        ("https://staging.example.test\n", "whitespace"),
        (" https://staging.example.test", "whitespace"),
    ],
)
def test_unsafe_targets_are_rejected(url, reason):
    with pytest.raises(v.InvalidBaseUrl):
        ok(url)


def test_an_empty_allow_list_rejects_everything():
    with pytest.raises(v.InvalidBaseUrl, match="LOAD_TEST_HOSTS is empty"):
        v.validate("https://staging.example.test", ["", "  "], PUBLIC)


@pytest.mark.parametrize("address", ["10.1.2.3", "192.168.0.9", "172.16.0.1", "127.0.0.1", "169.254.169.254",
                                     "100.64.0.1", "0.0.0.0", "224.0.0.1", "::1", "fe80::1", "fd00::1",
                                     "::ffff:10.0.0.1"])
def test_an_allow_listed_name_that_resolves_internally_is_rejected(address):
    with pytest.raises(v.InvalidBaseUrl, match="non-public"):
        ok("https://staging.example.test", resolver=lambda host: ["93.184.216.34", address])


def test_unresolvable_hosts_are_rejected():
    def fail(host):
        raise OSError("nxdomain")

    with pytest.raises(v.InvalidBaseUrl, match="does not resolve"):
        ok("https://staging.example.test", resolver=fail)
    with pytest.raises(v.InvalidBaseUrl, match="does not resolve"):
        ok("https://staging.example.test", resolver=lambda host: [])


def test_dns_is_skipped_only_when_no_resolver_is_given():
    assert v.validate("https://staging.example.test", ALLOWED, None) == "https://staging.example.test"


def test_main_reads_the_environment_and_signals_failure(monkeypatch, capsys):
    monkeypatch.setattr(v, "system_resolver", PUBLIC)
    monkeypatch.setenv("BASE_URL", "https://staging.example.test")
    monkeypatch.setenv("LOAD_TEST_HOSTS", "staging.example.test, other.example.test")
    assert v.main() == 0
    assert capsys.readouterr().out.strip() == "https://staging.example.test"
    monkeypatch.setenv("BASE_URL", "https://127.0.0.1")
    assert v.main() == 1
    assert "base_url rejected" in capsys.readouterr().out
    monkeypatch.delenv("LOAD_TEST_HOSTS")
    monkeypatch.setenv("BASE_URL", "https://staging.example.test")
    assert v.main() == 1
