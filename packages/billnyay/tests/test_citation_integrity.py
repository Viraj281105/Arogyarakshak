"""
Adversarial tests for fabricated-citation prevention (P1-7).

This system has no real PubMed/NCBI literature-search capability anywhere. Before this
fix, the Clinician Agent's system prompt literally instructed the LLM to "Generate
realistic, evidence-backed clinical justifications" and to include a pubmed_id per item
— an instruction to invent plausible-but-fake citation identifiers, which then flowed
into real appeal letters presented as genuine sources. The offline fallback and the
Clinician's own default both additionally hardcoded a fake "PMID:38291045".

These tests prove no pubmed_id — LLM-claimed or hardcoded — can reach a final
ClinicalEvidence object or an appeal letter, under any code path.
"""

import re

from billnyay.agents.auditor import StructuredDenial
from billnyay.agents.barrister import format_clinical_evidence, run_barrister_agent
from billnyay.agents.clinician import (
    ClinicalEvidence,
    EvidenceList,
    _strip_unverifiable_citations,
    run_clinician_agent,
)

_FORMER_HARDCODED_FAKE_PMIDS = ["PMID:38291045", "PMID:37554120"]


def _denial() -> StructuredDenial:
    return StructuredDenial(
        denial_code="DEN-1",
        insurer_reason_snippet="Not medically necessary.",
        policy_clause_text="Clause 4.1",
        procedure_denied="Appendectomy",
        confidence_score=0.9,
        raw_evidence_chunks=[],
    )


class _AdversarialClient:
    """An LLM client that, despite the system prompt's explicit instruction not to,
    tries to assert fabricated PubMed IDs anyway — modeling an LLM that does not
    reliably follow its own instructions (the same reality that makes prompt injection
    unsolved, P0-4)."""

    def __init__(self, response_text: str):
        self.response_text = response_text

    def generate(self, *args, **kwargs) -> str:
        return self.response_text


# ---------------------------------------------------------------------------
# The system prompt itself must not instruct fabrication
# ---------------------------------------------------------------------------


def test_clinician_system_prompt_no_longer_asks_for_evidence_backed_generation():
    captured = {}

    class CapturingClient:
        def generate(self, prompt, system="", **kwargs):
            captured["system"] = system
            return '{"root": [{"article_title": "A", "summary_of_finding": "B", "pubmed_id": null}]}'

    run_clinician_agent(CapturingClient(), denial_details=_denial())

    system_prompt = captured["system"].lower()
    # The old instruction told the model to fabricate.
    assert "generate realistic, evidence-backed" not in system_prompt
    # The new instruction must explicitly forbid inventing an identifier.
    assert "must set pubmed_id to null" in system_prompt or "do not invent" in system_prompt


# ---------------------------------------------------------------------------
# An LLM that ignores the instruction and claims a citation anyway is overridden
# ---------------------------------------------------------------------------


def test_llm_claimed_pubmed_id_is_stripped_despite_instructions():
    adversarial_response = (
        '{"root": [{"article_title": "Fabricated Study", '
        '"summary_of_finding": "Invented finding.", "pubmed_id": "PMID:99999999"}]}'
    )
    result = run_clinician_agent(_AdversarialClient(adversarial_response), denial_details=_denial())

    assert result.root[0].article_title == "Fabricated Study"  # reasoning is preserved
    assert result.root[0].pubmed_id is None  # the fabricated citation is not


def test_multiple_fabricated_citations_are_all_stripped():
    adversarial_response = (
        '{"root": ['
        '{"article_title": "A", "summary_of_finding": "x", "pubmed_id": "PMID:11111111"},'
        '{"article_title": "B", "summary_of_finding": "y", "pubmed_id": "12345678"},'
        '{"article_title": "C", "summary_of_finding": "z", "pubmed_id": null}'
        "]}"
    )
    result = run_clinician_agent(_AdversarialClient(adversarial_response), denial_details=_denial())
    assert all(item.pubmed_id is None for item in result.root)
    assert len(result.root) == 3


def test_strip_unverifiable_citations_is_pure_and_only_touches_pubmed_id():
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="T", summary_of_finding="S", pubmed_id="PMID:1")]
    )
    cleaned = _strip_unverifiable_citations(evidence)
    assert cleaned.root[0].pubmed_id is None
    assert cleaned.root[0].article_title == "T"
    assert cleaned.root[0].summary_of_finding == "S"


def test_strip_unverifiable_citations_is_a_no_op_when_already_clean():
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="T", summary_of_finding="S", pubmed_id=None)]
    )
    cleaned = _strip_unverifiable_citations(evidence)
    assert cleaned.root[0].pubmed_id is None


# ---------------------------------------------------------------------------
# The former hardcoded fake PMIDs must never reappear, from any path
# ---------------------------------------------------------------------------


def test_default_fallback_contains_no_hardcoded_fake_pmid():
    result = run_clinician_agent(_AdversarialClient("not valid json"), denial_details=_denial())
    for item in result.root:
        assert item.pubmed_id is None
        for fake_pmid in _FORMER_HARDCODED_FAKE_PMIDS:
            assert fake_pmid not in (item.article_title + item.summary_of_finding)


# ---------------------------------------------------------------------------
# The rendered appeal-letter text must never present an unverified item as a citation
# ---------------------------------------------------------------------------


def test_format_clinical_evidence_omits_the_parenthetical_when_no_citation_exists():
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="Standard of Care", summary_of_finding="Necessary.", pubmed_id=None)]
    )
    formatted = format_clinical_evidence(evidence)
    assert "Standard of Care: Necessary." in formatted
    assert "(N/A)" not in formatted
    assert "()" not in formatted


def test_format_clinical_evidence_still_renders_a_genuine_citation_if_one_exists():
    """If pubmed_id is ever legitimately populated in the future (real verification),
    formatting must still be able to show it — this fix removes fabrication, not the
    capability to cite a real source."""
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="Real Study", summary_of_finding="Finding.", pubmed_id="PMID:12345")]
    )
    formatted = format_clinical_evidence(evidence)
    assert "PMID:12345" in formatted


def test_appeal_letter_generated_via_offline_fallback_contains_no_fake_pmid():
    """End-to-end: the Barrister's letter (via the template fallback path — same one
    used when GROQ_API_KEY is unset) must not contain any of the previously-hardcoded
    fake PMIDs, or any PMID-shaped string at all, since no real citation exists."""
    letter = run_barrister_agent(
        _AdversarialClient("A" * 400),
        denial_details=_denial(),
        clinical_evidence=EvidenceList(
            root=[ClinicalEvidence(article_title="X", summary_of_finding="Y", pubmed_id=None)]
        ),
        regulatory_evidence={"legal_points": []},
    )
    assert letter is not None
    for fake_pmid in _FORMER_HARDCODED_FAKE_PMIDS:
        assert fake_pmid not in letter
