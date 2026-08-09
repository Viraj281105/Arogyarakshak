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
    appeal_letter = "Dear Insurer,\n\nWe are writing to appeal the denial of coverage...\n\nSincerely,\nPatient"
    result = run_judge_agent(appeal_letter=appeal_letter)
    
    assert result.status in ["approve", "needs_revision"]
    assert result.overall_score >= 0
    assert result.confidence_estimate == 0.90
