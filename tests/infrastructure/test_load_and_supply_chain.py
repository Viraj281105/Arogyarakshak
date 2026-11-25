"""Structure checks for the k6 scripts and the new workflows (Wave 2 stream E).

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
DOC = (REPO / "docs" / "operations" / "load-and-chaos.md").read_text(encoding="utf-8")
SCRIPTS = ["health.js", "case_create.js", "upload.js", "sse_stream.js"]
BUILTIN_METRICS = {"http_req_duration", "http_req_failed", "http_reqs", "iterations", "checks", "vus"}


def _workflow(name):
    data = yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))
    triggers = data.get("on", data.get(True))  # PyYAML reads the bare key `on` as True
    return data, triggers


def _steps(name):
    data, _ = _workflow(name)
    return [step for job in data["jobs"].values() for step in job["steps"]]


# ---------------------------------------------------------------- k6 scripts


@pytest.mark.parametrize("name", SCRIPTS)
def test_load_script_has_thresholds_labelled_proposed(name):
    text = (LOAD / name).read_text(encoding="utf-8")
    assert "export const options" in text and "thresholds" in text
    assert "export default function" in text
    assert "server_errors" in text, "availability SLI (99.5 % not 5xx) must be a threshold"
    assert re.search(r"PROPOSED, NOT MEASURED", text) and re.search(r"proposed, not measured", text)


@pytest.mark.parametrize("name", SCRIPTS)
def test_a_run_that_measured_nothing_cannot_pass(name):
    """A 120 req/min rate limit would otherwise let the run pass on early returns and 429s."""
    text = (LOAD / name).read_text(encoding="utf-8")
    assert "rate_limited: [`rate<${SLO.maxRateLimitedShare}`]" in text
    assert re.search(r"accepted_requests: \['count>\d+'\]", text)
    assert re.search(r"iterations: \['count>\d+'\]", text)


def _emitted_metrics(name):
    text = (LOAD / "lib.js").read_text(encoding="utf-8") + (LOAD / name).read_text(encoding="utf-8")
    return set(re.findall(r"new (?:Rate|Counter|Trend|Gauge)\('([a-z_]+)'", text)) | BUILTIN_METRICS


@pytest.mark.parametrize("name", SCRIPTS)
def test_thresholds_reference_only_metrics_the_script_emits(name):
    text = (LOAD / name).read_text(encoding="utf-8")
    block = text[text.index("thresholds:"):]
    block = block[: block.index("\n  },") if "\n  }," in block else len(block)]
    referenced = {re.sub(r"\{.*\}$", "", m) for m in re.findall(r"^\s+'?([A-Za-z_][\w{}:/ .']*?)'?: \[", block, flags=re.M)}
    assert referenced, "no thresholds parsed"
    assert referenced <= _emitted_metrics(name), referenced - _emitted_metrics(name)


def _slo():
    lib = (LOAD / "lib.js").read_text(encoding="utf-8")
    block = lib[lib.index("export const SLO = {"): lib.index("};", lib.index("export const SLO = {"))]
    return {k: float(v) for k, v in re.findall(r"^\s+(\w+): ([0-9.]+),", block, flags=re.M)}


def test_every_slo_value_is_documented_with_its_unit():
    slo = _slo()
    assert set(slo) == {"maxServerErrorRate", "maxRateLimitedShare", "caseProcessingP95Ms", "healthP95Ms",
                        "createCaseP95Ms", "uploadAcceptP95Ms"}
    documented = {
        "maxServerErrorRate": f"5xx < {slo['maxServerErrorRate'] * 100:g} %",
        "maxRateLimitedShare": f"429s < {slo['maxRateLimitedShare'] * 100:g} %",
        "caseProcessingP95Ms": f"end-to-end < {slo['caseProcessingP95Ms'] / 1000:g} s",
        "healthP95Ms": f"p95 < {slo['healthP95Ms']:g} ms",
        "createCaseP95Ms": f"p95 < {slo['createCaseP95Ms'] / 1000:g} s",
        "uploadAcceptP95Ms": f"p95 < {slo['uploadAcceptP95Ms'] / 1000:g} s",
    }
    for key, text in documented.items():
        assert text in DOC, f"{key}: docs/operations/load-and-chaos.md must contain {text!r}"


def test_slo_sources_exist_in_observability_docs():
    docs = (REPO / "docs" / "operations" / "observability.md").read_text(encoding="utf-8")
    assert "99.5 %" in docs and "within 10 s" in docs
    assert _slo()["maxServerErrorRate"] == 0.005 and _slo()["caseProcessingP95Ms"] == 10000


def test_lib_field_names_match_the_api_contract():
    from app.api.v1.endpoints.kadi.schemas import CaseCreate, CaseCreatedResponse
    from app.main import app

    lib = (LOAD / "lib.js").read_text(encoding="utf-8")
    # ADR-029: the scripts sign in and send the session, never a per-case token.
    assert "Authorization: `Bearer ${bearer}`" in lib and "/auth/login" in lib
    assert "X-Case-Access-Token" not in lib
    assert "body.id" in lib and "id" in CaseCreatedResponse.model_fields
    assert "consent_opt_in" in CaseCreate.model_fields and "consent_opt_in" in lib
    routes = set(app.openapi()["paths"])
    assert "/api/v1/kadi/cases" in routes and "/api/v1/kadi/auth/login" in routes
    assert "/api/v1/kadi/cases/{case_id}/upload" in routes
    assert "/api/v1/kadi/cases/{case_id}/stream" in routes
    sse = (LOAD / "sse_stream.js").read_text(encoding="utf-8")
    ingestion = (REPO / "apps" / "api" / "app" / "services" / "case_ingestion.py").read_text(encoding="utf-8")
    assert "'completed'" in sse and '"status": "completed"' in ingestion
    assert "/cases/${id}/upload" in sse and "/cases/${id}/stream" in sse


def test_scripts_default_to_loopback_and_never_embed_credentials_or_phi():
    assert "http://127.0.0.1:8000" in (LOAD / "lib.js").read_text(encoding="utf-8")
    for path in LOAD.glob("*.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"https?://(?!127\.0\.0\.1|localhost)", text), path.name
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


# ---------------------------------------------------------------- load-test workflow


def test_load_workflow_is_manual_only_read_only_and_validates_its_target():
    data, triggers = _workflow("load-test.yml")
    assert set(triggers) == {"workflow_dispatch"}
    assert data["permissions"] == {"contents": "read"}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert inputs["base_url"]["required"] is True and "default" not in inputs["base_url"]
    assert set(inputs["script"]["options"]) == set(SCRIPTS)
    steps = _steps("load-test.yml")
    names = [s.get("name", s.get("uses")) for s in steps]
    assert names.index("Validate the target") < names.index("Run k6"), "validation precedes any traffic"
    validate = next(s for s in steps if s.get("name") == "Validate the target")
    assert "validate_base_url.py" in validate["run"]
    assert validate["env"]["LOAD_TEST_HOSTS"] == "${{ vars.LOAD_TEST_HOSTS }}"
    k6 = next(s for s in steps if s.get("name") == "Run k6")
    assert k6["env"]["BASE_URL"] == "${{ env.VALIDATED_BASE_URL }}", "k6 gets the validated URL, not the raw input"


# ---------------------------------------------------------------- supply-chain workflow


def test_supply_chain_runs_only_on_semver_tags_never_on_pull_requests():
    data, triggers = _workflow("supply-chain.yml")
    assert set(triggers) == {"push"}
    assert triggers["push"] == {"tags": ["v[0-9]+.[0-9]+.[0-9]+*"]}
    job = data["jobs"]["release-image"]
    assert "startsWith(github.ref, 'refs/tags/v')" in job["if"]
    assert job["environment"] == "release"
    assert data["permissions"] == {"contents": "read"}, "workflow level stays read-only"


def test_supply_chain_job_permissions_are_exactly_these():
    job = _workflow("supply-chain.yml")[0]["jobs"]["release-image"]
    assert job["permissions"] == {"contents": "read", "packages": "write", "id-token": "write"}


def test_supply_chain_refuses_tags_that_are_not_on_main_and_does_not_persist_credentials():
    steps = _steps("supply-chain.yml")
    checkout = steps[0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["persist-credentials"] is False and checkout["with"]["fetch-depth"] == 0
    guard = steps[1]
    assert "merge-base --is-ancestor" in guard["run"] and "origin/main" in guard["run"]
    assert guard["env"]["TAG"] == "${{ github.ref_name }}"
    for step in steps[2:]:  # nothing builds, logs in or signs before the guard
        assert step is not guard


def test_supply_chain_signs_keylessly_by_digest_without_cache_or_stored_key():
    text = (WORKFLOWS / "supply-chain.yml").read_text(encoding="utf-8")
    assert "anchore/sbom-action@" in text and "sigstore/cosign-installer@" in text
    assert re.search(r'cosign sign --yes "\$\{IMAGE\}@\$\{DIGEST\}"', text)
    assert "cosign attest --yes" in text and "spdxjson" in text
    for forbidden in ("--key", "COSIGN_PRIVATE_KEY", "COSIGN_PASSWORD", "COSIGN_EXPERIMENTAL", "attestations:",
                      "cache-from", "cache-to", "type=gha"):
        assert forbidden not in text.replace("# No type=gha cache here", ""), forbidden


def test_supply_chain_states_its_decisions_and_the_verifier_commands():
    text = (WORKFLOWS / "supply-chain.yml").read_text(encoding="utf-8")
    assert "PUBLIC Rekor log" in text
    assert "does NOT mean the commit was reviewed" in text
    assert "cosign verify ghcr.io/viraj281105/arogyarakshak/api@sha256:" in text
    assert "cosign verify-attestation --type spdxjson" in text
    assert text.count("--certificate-oidc-issuer https://token.actions.githubusercontent.com") == 2
    assert text.count("Viraj281105/Arogyarakshak/\\.github/workflows/supply-chain\\.yml@refs/tags/v[0-9]+") == 2
    assert text.count("--certificate-identity-regexp '^https://github\\.com/") == 2, "anchored identity"


# ---------------------------------------------------------------- action pinning policy


def _all_workflow_refs(name):
    return re.findall(r"uses:\s*(\S+)", (WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["supply-chain.yml", "load-test.yml", "policy-test.yml"])
def test_actions_carry_an_explicit_version_and_the_mutable_pin_note_exists(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    refs = _all_workflow_refs(name)
    assert refs
    for ref in refs:
        assert re.fullmatch(r"[\w./-]+@(v\d+(\.\d+){0,2}|[0-9a-f]{40})", ref), f"unpinned action {ref}"
    mutable = [r for r in refs if not re.search(r"@[0-9a-f]{40}$", r)]
    if mutable:
        # Major tags are mutable. That is accepted only with the written maintainer duty to SHA-pin.
        assert re.search(r"mutable", text, flags=re.I), f"{name} must say its pins are mutable"
    assert "SHA-pin" in DOC and "before the first release" in DOC


def test_supply_chain_note_demands_sha_pinning_before_the_first_release():
    text = (WORKFLOWS / "supply-chain.yml").read_text(encoding="utf-8")
    assert "must SHA-pin each of them before the first" in text.replace("\n# ", " ")


def test_dependabot_keeps_github_actions_current():
    data = yaml.safe_load((REPO / ".github" / "dependabot.yml").read_text(encoding="utf-8"))
    assert data["version"] == 2
    ecosystems = {u["package-ecosystem"]: u for u in data["updates"]}
    assert ecosystems["github-actions"]["directory"] == "/"


# ---------------------------------------------------------------- policy-test workflow


def test_policy_test_workflow_is_report_only_and_least_privilege():
    data, triggers = _workflow("policy-test.yml")
    assert data["permissions"] == {"contents": "read"}
    job = data["jobs"]["policy"]
    assert job["continue-on-error"] is True
    runs = "\n".join(s.get("run", "") for s in _steps("policy-test.yml"))
    # OPA merges every data file into one root, so the fixtures go in as ONE generated document
    assert "build_opa_data.py --out" in runs and "opa test infrastructure/policy/rego" in runs
    assert "opa test infrastructure/policy/rego infrastructure/policy/fixtures" not in runs
    assert "kyverno test infrastructure/policy/kyverno-tests" in runs
    assert "build_kyverno_tests.py --check" in runs
    assert "secrets." not in (WORKFLOWS / "policy-test.yml").read_text(encoding="utf-8")


# ---------------------------------------------------------------- expression injection


@pytest.mark.parametrize("name", ["supply-chain.yml", "load-test.yml", "policy-test.yml"])
def test_no_run_block_contains_an_expression(name):
    """Untrusted values reach shell code only through `env:`. Checks single-line and multi-line
    (`run: |`) blocks alike by inspecting the parsed `run` strings."""
    for step in _steps(name):
        run = step.get("run")
        if run is not None:
            assert "${{" not in run, f"{name}: expression inside run block: {run[:80]!r}"
