"""Structure checks for the k6 scripts and the two new workflows (Wave 2 stream E).

k6 is not installed, so the scripts are only parsed (``node --check`` on an .mjs copy, when node
is available) and inspected as text. These tests do not, and cannot, say anything about
latency: every threshold is labelled "proposed, not measured".
"""

import pathlib
import re
import shutil
import subprocess

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
LOAD = REPO / "tests" / "load"
WORKFLOWS = REPO / ".github" / "workflows"
SCRIPTS = ["health.js", "case_create.js", "upload.js", "sse_stream.js"]


def _workflow(name):
    data = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))  # PyYAML reads the bare key `on` as True
    return data, triggers


@pytest.mark.parametrize("name", SCRIPTS)
def test_load_script_has_thresholds_labelled_proposed(name):
    text = (LOAD / name).read_text(encoding="utf-8")
    assert "export const options" in text and "thresholds" in text
    assert "export default function" in text
    assert "server_errors" in text, "availability SLI (99.5 % not 5xx) must be a threshold"
    assert re.search(r"PROPOSED, NOT MEASURED", text, flags=re.I)
    assert re.search(r"proposed, not measured", text)


def test_thresholds_trace_to_the_documented_slos():
    lib = (LOAD / "lib.js").read_text(encoding="utf-8")
    assert "maxServerErrorRate: 0.005" in lib  # 99.5 % availability
    assert "caseProcessingP95Ms: 10000" in lib  # 95 % within 10 s
    docs = (REPO / "docs" / "operations" / "observability.md").read_text(encoding="utf-8")
    assert "99.5 %" in docs and "within 10 s" in docs
    assert "case_processing_ms" in (LOAD / "sse_stream.js").read_text(encoding="utf-8")


def test_scripts_default_to_loopback_and_never_embed_credentials_or_phi():
    lib = (LOAD / "lib.js").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000" in lib
    for path in LOAD.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"https?://(?!127\.0\.0\.1|localhost)", text.replace("https://github", "")), path.name
        assert "GROQ" not in text and "api_key" not in text.lower(), path.name


def test_no_script_claims_a_measured_number():
    for path in LOAD.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"\bmeasured (at|p95|latency)\b|\bachieved\b|\brps\b", text, flags=re.I), path.name


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
@pytest.mark.parametrize("name", SCRIPTS + ["lib.js"])
def test_load_scripts_are_valid_ecmascript_modules(name, tmp_path):
    copy = tmp_path / (pathlib.Path(name).stem + ".mjs")
    copy.write_text((LOAD / name).read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(["node", "--check", str(copy)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_every_script_import_resolves_to_k6_or_the_local_lib():
    for path in LOAD.glob("*.js"):
        for target in re.findall(r"from '([^']+)'", path.read_text(encoding="utf-8")):
            assert target.startswith("k6") or (LOAD / target).exists(), f"{path.name}: {target}"


def test_load_workflow_is_manual_only_and_read_only():
    data, triggers = _workflow("load-test.yml")
    assert set(triggers) == {"workflow_dispatch"}
    assert data["permissions"] == {"contents": "read"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["base_url"]["required"] is True and "default" not in inputs["base_url"]
    assert set(inputs["script"]["options"]) == set(SCRIPTS)
    text = (WORKFLOWS / "load-test.yml").read_text(encoding="utf-8")
    assert "inputs.script }}\"" not in text.split("run:")[1].split("\n")[0], "inputs must go through env, not the shell"


def test_supply_chain_runs_only_on_release_tags_never_on_pull_requests():
    data, triggers = _workflow("supply-chain.yml")
    assert set(triggers) == {"push"}
    assert triggers["push"] == {"tags": ["v*"]}
    job = data["jobs"]["release-image"]
    assert "startsWith(github.ref, 'refs/tags/v')" in job["if"]
    assert "pull_request" not in str(triggers)
    # id-token is only granted at job level, to this tag-only job.
    assert "id-token" not in (data.get("permissions") or {})
    assert job["permissions"]["id-token"] == "write"


def test_supply_chain_generates_an_sbom_and_signs_keylessly_without_a_stored_key():
    text = (WORKFLOWS / "supply-chain.yml").read_text(encoding="utf-8")
    assert "anchore/sbom-action@" in text and "sigstore/cosign-installer@" in text
    assert re.search(r'cosign sign --yes "\$\{IMAGE\}@\$\{DIGEST\}"', text), "sign the digest, not a mutable tag"
    assert "cosign attest --yes" in text and "spdxjson" in text
    assert "--key" not in text and "COSIGN_PRIVATE_KEY" not in text and "COSIGN_PASSWORD" not in text
    assert "COSIGN_EXPERIMENTAL" not in text  # obsolete flag; keyless is the default


@pytest.mark.parametrize("name", ["supply-chain.yml", "load-test.yml"])
def test_actions_are_version_pinned_in_the_repo_style(name):
    uses = re.findall(r"uses:\s*(\S+)", (WORKFLOWS / name).read_text(encoding="utf-8"))
    assert uses
    for ref in uses:
        assert re.fullmatch(r"[\w./-]+@(v\d+(\.\d+){0,2}|[0-9a-f]{40})", ref), f"unpinned action {ref}"


@pytest.mark.parametrize("name", ["supply-chain.yml", "load-test.yml"])
def test_workflow_has_no_untrusted_expression_in_a_run_line(name):
    for line in (WORKFLOWS / name).read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(("run:", "- run:")):
            assert "${{" not in line, f"pass expressions through env: {line.strip()}"
