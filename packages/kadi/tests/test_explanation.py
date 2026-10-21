"""The shared explanation model: 'not recorded' is derived, never guessed (ADR-017)."""

from kadi.clinical_review.medicine_trust import decide_medicine_trust, name_provenance_class
from kadi.explanation import (
    EvidenceItem,
    Explanation,
    ProvenanceClass,
    RuleUsed,
    TrustState,
    fact,
    render_plain_text,
)


def _exp(**kw):
    base = dict(finding_type="BILLNYAY_LINE", headline="h", trust=TrustState(code="X", label="x"))
    base.update(kw)
    return Explanation(**base)


def test_fact_treats_none_and_blank_as_not_recorded():
    assert fact("a", None).value is None
    assert fact("a", "  ").value is None
    assert fact("a", 0).value == "0"


def test_not_recorded_is_derived_from_missing_values():
    exp = _exp(
        evidence=[
            EvidenceItem(label="Amount", value="5", provenance=ProvenanceClass.OCR_EXTRACTED, document=None),
            EvidenceItem(label="Date", value=None, provenance=ProvenanceClass.NOT_RECORDED),
        ],
        rules=[RuleUsed(kind="REFERENCE_TABLE_ROW", name="Row", facts=[fact("Code", None), fact("Rate", "1")])],
    )
    assert exp.not_recorded == ["Amount: source document", "Date", "Row: Code"]


def test_user_entered_evidence_does_not_need_a_document():
    exp = _exp(evidence=[EvidenceItem(label="Price", value="3", provenance=ProvenanceClass.USER_ENTERED)])
    assert exp.not_recorded == []


def test_plain_text_says_not_recorded_instead_of_blank():
    exp = _exp(rules=[RuleUsed(kind="REFERENCE_TABLE_ROW", name="Row", facts=[fact("Code", None)])])
    assert "Code: not recorded" in render_plain_text(exp)


def test_explanation_declares_it_was_not_written_by_a_model():
    assert "no AI model" in _exp().generated_by


def test_medicine_provenance_classes():
    human = decide_medicine_trust("Dolo", {"human_transcription": {"status": "RESOLVED", "value": "Dolo 650"}})
    assert name_provenance_class(human, {}) == ProvenanceClass.HUMAN_REVIEWED
    plain = decide_medicine_trust("Dolo", {})
    assert name_provenance_class(plain, {}) == ProvenanceClass.OCR_EXTRACTED
    meta = {"ocr_uncertainty": {"status": "UNRESOLVED", "reasons": ["POSSIBLE_MATCH"]}}
    held = decide_medicine_trust("Amoxicillin", meta)
    assert name_provenance_class(held, meta) == ProvenanceClass.LLM_NORMALISED
