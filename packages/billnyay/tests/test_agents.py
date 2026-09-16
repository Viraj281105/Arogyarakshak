import pytest
from billnyay.agents.auditor import run_auditor_agent, find_relevant_policy_snippet, extract_first_json
from billnyay.agents.judge import run_judge_agent


class MockLLMClient:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def generate(self, *args, **kwargs) -> str:
        return self.response_text


def test_find_relevant_policy_snippet():
    policy_text = (
        "Some general terms here.\n"
        "EXCLUSIONS: We do not cover experimental procedures or unproven therapies.\n"
        "More general terms here."
    )
    snippet = find_relevant_policy_snippet(policy_text)
    assert "EXCLUSIONS" in snippet


def test_extract_first_json():
    text = "Some prefix text here {\"key\": \"value\"} suffix text"
    result = extract_first_json(text)
    assert result == {"key": "value"}


def test_run_auditor_agent():
    mock_json = (
        "{\n"
        '  "denial_code": "DEN-101",\n'
        '  "insurer_reason_snippet": "Not medically necessary",\n'
        '  "policy_clause_text": "Clause 4.2 Exclusions",\n'
        '  "procedure_denied": "Experimental therapy",\n'
        '  "confidence_score": 0.95,\n'
        '  "raw_evidence_chunks": []\n'
        "}"
    )
    client = MockLLMClient(response_text=mock_json)
    denial_text = "This is a denial letter. The patient received a bill for experimental therapy. It was denied."
    result = run_auditor_agent(client=client, denial_text=denial_text, policy_text="Policy excludes experimental therapy.")
    
    assert result is not None
    assert result.denial_code == "DEN-101"
    assert result.procedure_denied == "Experimental therapy"


def test_run_judge_agent():
    """P1-8: with no denial_details supplied, the Judge has nothing to verify factual
    accuracy against — it must disclose that as low confidence, not report the same
    fixed 0.90 it used to return regardless of whether any verification happened."""
    appeal_letter = "Dear Insurer,\n\nWe are writing to appeal the denial of coverage...\n\nSincerely,\nPatient"
    result = run_judge_agent(appeal_letter=appeal_letter)

    assert result.status in ["approve", "needs_revision"]
    assert result.overall_score >= 0
    assert result.confidence_estimate == 0.35
    assert any(issue.id == "FACT-0" for issue in result.issues)


# ---------------------------------------------------------------------------
# Barrister / Clinician / Regulatory agents.
# These three had no coverage at all; the Barrister call site in the API was
# broken for exactly that reason.
# ---------------------------------------------------------------------------

from billnyay.agents.auditor import StructuredDenial
from billnyay.agents.barrister import run_barrister_agent, format_clinical_evidence
from billnyay.agents.clinician import run_clinician_agent, ClinicalEvidence, EvidenceList
from billnyay.agents.regulatory import run_regulatory_agent


def _denial() -> StructuredDenial:
    return StructuredDenial(
        denial_code="DEN-4471",
        insurer_reason_snippet="Hospitalisation deemed for investigation only.",
        policy_clause_text="Section 4.1 excludes diagnostic admissions.",
        procedure_denied="Laparoscopic Appendectomy",
        confidence_score=0.9,
        raw_evidence_chunks=[],
    )


def test_run_barrister_agent_accepts_pipeline_objects():
    """Guards the exact signature the API endpoint uses.

    The endpoint previously called this with denial_code=/procedure_denied= and no
    client, raising TypeError and returning HTTP 500.
    """
    client = MockLLMClient(response_text="A" * 400)
    evidence = EvidenceList(
        root=[
            ClinicalEvidence(
                article_title="Standard of Care",
                summary_of_finding="Procedure is medically necessary.",
                pubmed_id="PMID:1",
            )
        ]
    )
    regulatory = {"legal_points": [{"statute": "IRDAI Circular", "summary": "Vague exclusions invalid."}]}

    letter = run_barrister_agent(
        client,
        denial_details=_denial(),
        clinical_evidence=evidence,
        regulatory_evidence=regulatory,
    )
    assert letter is not None
    assert len(letter) >= 400


def test_run_barrister_agent_rejects_too_short_output():
    letter = run_barrister_agent(
        MockLLMClient(response_text="too short"),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(root=[]),
        regulatory_evidence={"legal_points": []},
    )
    assert letter is None


def test_run_barrister_agent_passes_prose_mode_to_client():
    """The Barrister must not ask the LLM for JSON — it emits a letter."""
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured.update(kwargs)
            captured["system"] = system
            return "B" * 400

    run_barrister_agent(
        CapturingClient(),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(root=[]),
        regulatory_evidence={"legal_points": []},
    )
    assert captured["json_mode"] is False
    assert "Barrister Agent" in captured["system"]


def test_run_barrister_agent_defaults_to_english_with_no_language_instruction():
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured.update(kwargs)
            captured["system"] = system
            return "C" * 400

    run_barrister_agent(
        CapturingClient(),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(root=[]),
        regulatory_evidence={"legal_points": []},
    )
    assert captured["language"] == "en"
    assert "Hindi" not in captured["system"]
    assert "Marathi" not in captured["system"]


@pytest.mark.parametrize("lang,lang_name", [("hi", "Hindi"), ("mr", "Marathi")])
def test_run_barrister_agent_instructs_the_llm_to_write_in_the_requested_language(lang, lang_name):
    """#39: the Phase 0 finding was that LLM-generated output stayed English-only
    regardless of the user's chosen language. The system prompt must carry an explicit
    instruction, and the `language` kwarg must reach client.generate so the offline
    fallback (GroqClientFallback) can pick the matching canned letter."""
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured.update(kwargs)
            captured["system"] = system
            return "D" * 400

    run_barrister_agent(
        CapturingClient(),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(root=[]),
        regulatory_evidence={"legal_points": []},
        language=lang,
    )
    assert captured["language"] == lang
    assert lang_name in captured["system"]
    # Proper nouns, figures and citations must survive translation, not be transliterated.
    assert "do not translate proper nouns, citations, or figures" in captured["system"]


def test_run_barrister_agent_language_is_case_insensitive():
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured.update(kwargs)
            return "E" * 400

    run_barrister_agent(
        CapturingClient(),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(root=[]),
        regulatory_evidence={"legal_points": []},
        language="HI",
    )
    assert captured["language"] == "hi"


def test_format_clinical_evidence_handles_evidence_list_and_empty():
    evidence = EvidenceList(
        root=[
            ClinicalEvidence(
                article_title="Trial X", summary_of_finding="Efficacy shown.", pubmed_id="PMID:99"
            )
        ]
    )
    formatted = format_clinical_evidence(evidence)
    assert "Trial X" in formatted
    assert "PMID:99" in formatted

    # Must degrade to a usable sentence rather than raising.
    assert format_clinical_evidence(EvidenceList(root=[])).strip().startswith("-")
    assert format_clinical_evidence(None).strip().startswith("-")


def test_run_clinician_agent_parses_valid_json():
    payload = (
        '{"root": [{"article_title": "Guideline A", '
        '"summary_of_finding": "Necessary.", "pubmed_id": "PMID:5"}]}'
    )
    result = run_clinician_agent(MockLLMClient(response_text=payload), denial_details=_denial())
    assert isinstance(result, EvidenceList)
    assert result.root[0].article_title == "Guideline A"
    # P1-7: even a well-formed LLM response asserting a pubmed_id must not have it
    # survive — this system has no real PubMed/NCBI lookup, so any pubmed_id an LLM
    # returns is an unverifiable, likely-fabricated identifier and is always discarded.
    assert result.root[0].pubmed_id is None


def test_run_clinician_agent_falls_back_on_garbage():
    """Must always return usable evidence so the Barrister has something to cite."""
    result = run_clinician_agent(MockLLMClient(response_text="not json at all"), denial_details=_denial())
    assert isinstance(result, EvidenceList)
    assert len(result.root) >= 1
    assert "Laparoscopic Appendectomy" in result.root[0].article_title
    # P1-7: the fallback used to hardcode a fake "PMID:38291045" into every default
    # response — must never present a fabricated citation as real evidence.
    assert result.root[0].pubmed_id is None


def test_run_regulatory_agent_returns_statutes():
    result = run_regulatory_agent(denial_data=_denial().model_dump())
    assert result["statute_count"] >= 1
    assert len(result["legal_points"]) == result["statute_count"]
    for point in result["legal_points"]:
        assert point["statute"]
        assert point["summary"]
    # The query is echoed back so callers can see what was searched.
    assert "laparoscopic appendectomy" in result["query_used"]


def test_barrister_prompt_carries_all_upstream_agent_evidence():
    """Proves the chain passes data, not just that it does not crash.

    The API previously fed the Barrister hardcoded strings while the Clinician and
    Regulatory agents were never invoked at all.
    """
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured["prompt"] = prompt
            return "X" * 400

    evidence = EvidenceList(
        root=[
            ClinicalEvidence(
                article_title="Guideline A",
                summary_of_finding="Medically necessary.",
                pubmed_id="PMID:7",
            )
        ]
    )
    regulatory = {
        "legal_points": [
            {"statute": "IRDAI Master Circular", "summary": "Moratorium bar applies."}
        ]
    }

    run_barrister_agent(
        CapturingClient(),
        denial_details=_denial(),
        clinical_evidence=evidence,
        regulatory_evidence=regulatory,
    )

    prompt = captured["prompt"]
    # Auditor output
    assert "DEN-4471" in prompt
    assert "Laparoscopic Appendectomy" in prompt
    assert "Section 4.1 excludes diagnostic admissions." in prompt
    # Clinician output
    assert "Guideline A" in prompt
    assert "PMID:7" in prompt
    # Regulatory output
    assert "IRDAI Master Circular" in prompt
    assert "Moratorium bar applies." in prompt
