"""
Tests proving the Judge Agent performs real, deterministic verification (P1-8).

Before this fix, every sub-score was either a hardcoded constant or toggled only by raw
text length; denial_details/clinical_evidence were accepted as parameters and never
read. These tests prove the Judge now actually looks at what it is given, and that its
`needs_revision` status — previously unreachable via the public API for any letter over
~300 characters, per this repo's own prior audit trail — is genuinely reachable again
for a letter with real defects.
"""

from billnyay.agents.auditor import StructuredDenial
from billnyay.agents.clinician import ClinicalEvidence, EvidenceList
from billnyay.agents.judge import run_judge_agent

GOOD_DENIAL = StructuredDenial(
    denial_code="DEN-4471",
    insurer_reason_snippet="Hospitalisation deemed for investigation only.",
    policy_clause_text="Section 4.1 excludes diagnostic admissions.",
    procedure_denied="Laparoscopic Appendectomy",
    confidence_score=0.9,
    raw_evidence_chunks=[],
)

UNSPECIFIED_DENIAL = StructuredDenial(
    denial_code="Not specified in the supplied documents",
    insurer_reason_snippet="Not specified in the supplied documents",
    policy_clause_text="Not specified in the supplied documents",
    procedure_denied="Not specified in the supplied documents",
    confidence_score=0.0,
    raw_evidence_chunks=[],
)

WELL_GROUNDED_LETTER = """TO:
The Grievance Redressal Officer

SUBJECT: Formal Appeal Against Wrongful Repudiation of Claim

Dear Sir / Madam,

I am appealing the denial referenced as DEN-4471 concerning Laparoscopic Appendectomy.
The insurer's stated reason — hospitalisation deemed for investigation only — is
contested on the following grounds.

SECTION I: CLINICAL JUSTIFICATION AND MEDICAL NECESSITY
The hospitalisation involved active treatment, not mere observation.

SECTION II: STATUTORY AND IRDAI REGULATORY VIOLATIONS
Rejection under vague exclusion clauses violates the IRDAI Master Circular.

SECTION III: FORMAL DEMAND AND TIMELINE FOR REVERSAL
We demand reversal within the statutory 30-day window.

Yours faithfully,
The Insured
"""

GENERIC_BOILERPLATE_LETTER = """Dear Sir,

We are writing regarding your recent decision. We believe it should be reconsidered.
Please let us know your decision soon.

Thank you.
"""

PLACEHOLDER_RIDDEN_LETTER = """TO: [POLICYHOLDER NAME]

SUBJECT: Appeal

Dear Sir/Madam,

TODO: insert clinical justification here.

SECTION I: CLINICAL JUSTIFICATION
[XXXX]

SECTION II: STATUTORY GROUNDS
The exclusion is invalid under IRDAI regulations.

SECTION III: DEMAND
We demand reversal within 30 days.

Yours faithfully,
[INSURER NAME]
"""


# ---------------------------------------------------------------------------
# Factual accuracy
# ---------------------------------------------------------------------------


def test_letter_grounded_in_real_denial_facts_scores_well_on_factual_accuracy():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.factual_accuracy >= 90
    assert not any(i.id.startswith("FACT-") for i in result.issues)


def test_generic_letter_not_referencing_real_denial_facts_is_flagged():
    result = run_judge_agent(GENERIC_BOILERPLATE_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.factual_accuracy < 90
    assert any(i.id.startswith("FACT-") for i in result.issues)


def test_no_denial_details_is_disclosed_as_unverifiable_not_scored_high():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=None)
    assert result.sub_scores.factual_accuracy == 40
    assert any(i.id == "FACT-0" for i in result.issues)
    assert result.confidence_estimate < 0.5


def test_unspecified_placeholder_denial_details_is_treated_as_unavailable():
    """UNSPECIFIED_FIELD placeholders (real Auditor extraction failure) must not be
    treated as real facts to check the letter against."""
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=UNSPECIFIED_DENIAL)
    assert result.sub_scores.factual_accuracy == 40
    assert any(i.id == "FACT-0" for i in result.issues)


# ---------------------------------------------------------------------------
# Citation consistency (works with P1-7's citation-fabrication fix)
# ---------------------------------------------------------------------------


def test_letter_with_no_citations_is_not_penalized():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.citation_consistency == 100


def test_letter_citing_evidence_that_was_actually_supplied_scores_well():
    evidence = EvidenceList(
        root=[ClinicalEvidence(article_title="Real Study", summary_of_finding="Finding", pubmed_id="PMID:12345")]
    )
    letter = WELL_GROUNDED_LETTER + "\nSee PMID:12345 for supporting evidence.\n"
    result = run_judge_agent(letter, denial_details=GOOD_DENIAL, clinical_evidence=evidence)
    assert result.sub_scores.citation_consistency == 100


def test_letter_citing_a_source_not_in_the_supplied_evidence_is_flagged():
    """The core P1-7/P1-8 interaction: a citation appearing in the final letter with no
    matching entry in the evidence actually supplied is a likely fabrication and must
    tank the score, not be assumed consistent."""
    letter = WELL_GROUNDED_LETTER + "\nSee PMID:99999999 for supporting evidence.\n"
    result = run_judge_agent(letter, denial_details=GOOD_DENIAL, clinical_evidence=EvidenceList(root=[]))
    assert result.sub_scores.citation_consistency <= 20
    assert any(i.id == "CITE-1" for i in result.issues)


# ---------------------------------------------------------------------------
# Structural adequacy
# ---------------------------------------------------------------------------


def test_letter_with_all_required_sections_scores_well_structurally():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.logical_adequacy >= 90
    assert not any(i.id.startswith("STRUCT-") for i in result.issues)


def test_letter_missing_required_sections_is_flagged():
    result = run_judge_agent(GENERIC_BOILERPLATE_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.logical_adequacy < 90
    assert any(i.id.startswith("STRUCT-") for i in result.issues)


# ---------------------------------------------------------------------------
# Tone / placeholder proxy
# ---------------------------------------------------------------------------


def test_leftover_template_placeholders_are_flagged():
    result = run_judge_agent(PLACEHOLDER_RIDDEN_LETTER, denial_details=GOOD_DENIAL)
    assert any(i.id == "TONE-1" for i in result.issues)
    assert result.sub_scores.tone_professionalism < 90


def test_well_formed_letter_has_no_placeholder_flags():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert not any(i.id == "TONE-1" for i in result.issues)


# ---------------------------------------------------------------------------
# Hallucination risk: denial-code consistency
# ---------------------------------------------------------------------------


def test_letter_citing_the_correct_denial_code_has_low_hallucination_risk():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.sub_scores.hallucination_risk <= 5
    assert not any(i.id == "HALLUC-1" for i in result.issues)


def test_letter_citing_a_mismatched_denial_code_is_flagged_as_hallucination_risk():
    letter = WELL_GROUNDED_LETTER.replace("DEN-4471", "DEN-9999")
    result = run_judge_agent(letter, denial_details=GOOD_DENIAL)
    assert result.sub_scores.hallucination_risk >= 70
    assert any(i.id == "HALLUC-1" for i in result.issues)


# ---------------------------------------------------------------------------
# End-to-end: needs_revision must be genuinely reachable again
# ---------------------------------------------------------------------------


def test_well_grounded_complete_letter_is_approved():
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.status == "approve"


def test_defective_letter_triggers_needs_revision():
    """Regression guard: this repo's own prior audit found the Judge's formula made
    needs_revision structurally unreachable via the public API (every realistic letter
    scored >= 83). A letter with real, multiple defects (generic, unstructured, wrong
    denial code) must now genuinely trigger it."""
    defective = GENERIC_BOILERPLATE_LETTER.replace("your recent decision", "your recent decision (ref DEN-0000)")
    result = run_judge_agent(defective, denial_details=GOOD_DENIAL)
    assert result.status == "needs_revision"
    assert result.overall_score < 80


def test_meta_discloses_the_verification_method_honestly():
    """The scorecard must not silently imply full NLP evaluation of logic/tone."""
    result = run_judge_agent(WELL_GROUNDED_LETTER, denial_details=GOOD_DENIAL)
    assert result.meta is not None
    method = result.meta["method"].lower()
    assert "structural proxies" in method or "not an nlp judgment" in method
