"""DaaviSetu preauth readiness (ADR-011): completeness, never approval claims."""

import re

import pytest
from pydantic import ValidationError

from daavisetu.readiness import (
    BASELINE_ITEMS,
    CaseEvidence,
    ChecklistItem,
    EvidenceRule,
    FactDecisionRef,
    evaluate_readiness,
    render_readiness_text,
    validate_items,
)


def _case(**kw):
    base = dict(
        entities={
            "diagnosis": [{"id": "E1", "value": "K35 Acute appendicitis"}],
            "procedure": [{"id": "E2", "value": "Appendectomy"}],
        },
        document_text="Chief complaint: pain. USG report attached.",
        case_total=45000.0,
    )
    base.update(kw)
    return CaseEvidence(**base)


def _by_id(report):
    return {i.item_id: i for i in report.items}


def test_present_and_missing_items_come_from_case_evidence():
    report = evaluate_readiness(_case(), BASELINE_ITEMS)
    items = _by_id(report)
    assert items["diagnosis_documented"].status == "PRESENT"
    assert items["diagnosis_documented"].evidence_strength == "EXTRACTED_ENTITY"
    assert items["hospital_identified"].status == "MISSING"
    assert items["investigation_reports"].status == "PRESENT"
    assert items["investigation_reports"].evidence_strength == "KEYWORD_MATCH"
    assert any("Request the missing documentation before submission" in a for a in report.recommended_actions)


def test_clinical_fact_is_never_satisfied_by_software():
    report = evaluate_readiness(_case(document_text="Past history: treated with NSAIDs"), BASELINE_ITEMS)
    item = _by_id(report)["previous_treatment_history"]
    assert item.status == "NEEDS_CLINICAL_CONFIRMATION"
    assert report.ready_to_submit is False


def test_reviewer_confirmation_and_rejection_are_reflected():
    confirmed = evaluate_readiness(
        _case(), BASELINE_ITEMS,
        fact_decisions={"previous_treatment_history": FactDecisionRef(decision="CONFIRMED", fact_id="CF-1", reviewer_name="Dr A")},
    )
    assert _by_id(confirmed)["previous_treatment_history"].status == "CONFIRMED_BY_REVIEWER"

    rejected = evaluate_readiness(
        _case(), BASELINE_ITEMS,
        fact_decisions={"previous_treatment_history": FactDecisionRef(decision="REJECTED", fact_id="CF-1")},
    )
    assert _by_id(rejected)["previous_treatment_history"].status == "REJECTED_BY_REVIEWER"
    assert any("Do not state these as facts" in a for a in rejected.recommended_actions)


def test_missing_evidence_is_missing_not_fabricated():
    report = evaluate_readiness(CaseEvidence(), BASELINE_ITEMS)
    assert all(i.status == "MISSING" for i in report.items)
    assert all(i.evidence == [] for i in report.items)


def test_no_approval_claims_anywhere():
    report = evaluate_readiness(_case(), BASELINE_ITEMS)
    text = report.model_dump_json() + render_readiness_text(report)
    assert not re.search(r"approval (probability|rate|chance|likelihood)|improve[sd]? (the )?approval", text, re.I)
    assert "does not predict" in report.disclaimer


def test_playbook_labels_cannot_assert_claimant_facts():
    with pytest.raises(ValidationError):
        ChecklistItem(
            item_id="bad", label="Claimant had failed conservative treatment",
            evidence_rule=EvidenceRule(kind="document_keywords", keywords=["conservative"]),
        )
    ok = ChecklistItem(
        item_id="conservative_mgmt", label="Documentation of conservative management tried",
        evidence_rule=EvidenceRule(kind="document_keywords", keywords=["conservative"]),
        clinical_fact=True, clinical_fact_question="Do the records document conservative management?",
    )
    assert validate_items([ok])


def test_item_validation():
    with pytest.raises(ValueError):
        validate_items([ChecklistItem(item_id="x1", label="A", evidence_rule=EvidenceRule(kind="entity", entity_type="patient_name"))])
    with pytest.raises(ValueError):
        validate_items([ChecklistItem(item_id="x1", label="A", evidence_rule=EvidenceRule(kind="document_keywords"))])
    with pytest.raises(ValueError):
        validate_items([ChecklistItem(item_id="x1", label="A", evidence_rule=EvidenceRule(kind="case_total"), clinical_fact=True)])


def test_playbook_items_are_labelled_by_origin():
    extra = ChecklistItem(
        item_id="pb_implant_invoice", label="Implant invoice or quotation",
        evidence_rule=EvidenceRule(kind="document_keywords", keywords=["implant"]),
    )
    report = evaluate_readiness(_case(), BASELINE_ITEMS, [extra])
    assert _by_id(report)["pb_implant_invoice"].origin == "INSTITUTION_PLAYBOOK"
    assert _by_id(report)["pb_implant_invoice"].status == "MISSING"


def test_report_discloses_what_text_was_searched():
    report = evaluate_readiness(_case(), BASELINE_ITEMS)
    assert "1,000 characters" in report.evidence_scope_note
    assert "1,000 characters" in render_readiness_text(report)
