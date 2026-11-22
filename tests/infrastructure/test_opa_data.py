"""The OPA data document built from the shared policy fixtures.

OPA merges every data file into one root, so the per-case fixture directory cannot be passed to
`opa test` directly (the first CI run failed with 47 'conflicting values at data.bad.kind'
errors). infrastructure/policy/build_opa_data.py mounts each fixture under data.good.<name> and
data.bad.<name>, which is what rego/fixtures_test.rego reads."""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
POLICY = ROOT / "infrastructure" / "policy"
sys.path.insert(0, str(POLICY))

import build_opa_data  # noqa: E402


def test_every_fixture_is_mounted_once_under_its_file_name():
    data = build_opa_data.build()
    for verdict in ("good", "bad"):
        on_disk = sorted(p.stem for p in (POLICY / "fixtures" / verdict).glob("*.y*ml"))
        assert sorted(data[verdict]) == on_disk and on_disk, verdict
    assert len(data["good"]) >= 10 and len(data["bad"]) >= 30  # the floors the Rego test also asserts
    # the structure OPA needs: each case keeps its own top-level `kind`, no collision at the root
    assert set(data) == {"good", "bad"}
    assert all("kind" in doc and "object" in doc for docs in data.values() for doc in docs.values())


def test_the_cli_writes_a_json_document_opa_can_load(tmp_path):
    out = tmp_path / "opa-fixtures.json"
    subprocess.run([sys.executable, str(POLICY / "build_opa_data.py"), "--out", str(out)], check=True, capture_output=True)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert set(loaded) == {"good", "bad"} and "kind" not in loaded  # nothing at the data root to collide


def test_the_workflow_uses_the_builder_and_never_passes_the_fixture_directory():
    text = (ROOT / ".github" / "workflows" / "policy-test.yml").read_text(encoding="utf-8")
    assert "build_opa_data.py" in text
    assert "opa test infrastructure/policy/rego infrastructure/policy/fixtures" not in text


def test_policy_engine_versions_are_pinned_not_floating():
    """Kyverno 1.20 removed execution of the legacy ClusterPolicy type these policies use, and the
    Kyverno action's own default (v1.10.3) predates the generated tests: both CLIs stay pinned to the
    versions verified against the official images (OPA 1.22.4, Kyverno CLI v1.19.0)."""
    text = (ROOT / ".github" / "workflows" / "policy-test.yml").read_text(encoding="utf-8")
    assert "version: 1.22.4" in text
    assert "release: v1.19.0" in text
    assert "release: latest" not in text and "version: latest" not in text
