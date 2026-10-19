"""DaaviSetu readiness explanation (ADR-015)."""

from daavisetu.readiness import BASELINE_ITEMS, CaseEvidence, FactDecisionRef, evaluate_readiness


def _by_id(report):
    return {r.item_id: r for r in report.items}


def test_entity_item_names_the_rule_and_its_source_document():
    case = CaseEvidence(entities={"diagnosis": [{"id": "E1", "value": "Appendicitis", "source_file": "note.txt"}]})
    exp = _by_id(evaluate_readiness(case, BASELINE_ITEMS))["diagnosis_documented"].explanation
    assert exp.finding_type == "DAAVISETU_ITEM"
    assert exp.rules[0].kind == "ENTITY_PRESENCE_RULE"
    assert exp.evidence[0].value == "Appendicitis" and exp.evidence[0].document == "note.txt"
    assert exp.not_recorded == []


def test_missing_item_says_where_it_looked():
    exp = _by_id(evaluate_readiness(CaseEvidence(), BASELINE_ITEMS))["procedure_documented"].explanation
    assert "not found" in exp.headline
    assert exp.undetermined[0].code == "NOT_FOUND_IN_SEARCHED_SCOPE"
    assert exp.trust.code == "NO_EVIDENCE"


def test_keyword_item_lists_the_rule_keywords_and_is_weak_evidence():
    case = CaseEvidence(document_text="Patient had an MRI report attached")
    exp = _by_id(evaluate_readiness(case, BASELINE_ITEMS))["investigation_reports"].explanation
    rule = exp.rules[0]
    assert rule.kind == "KEYWORD_RULE"
    facts = {f.label: f.value for f in rule.facts}
    assert "mri" in facts["Keywords searched"] and "mri" in facts["Matched keywords"]
    assert exp.trust.code == "WEAK_EVIDENCE"
    # Keyword evidence comes from joined excerpts: the document is honestly unknown.
    assert "document keyword: source document" in exp.not_recorded


def test_clinical_fact_is_unconfirmed_until_a_named_reviewer_decides():
    case = CaseEvidence(document_text="past history of gallstones")
    item = _by_id(evaluate_readiness(case, BASELINE_ITEMS))["previous_treatment_history"]
    assert item.status == "NEEDS_CLINICAL_CONFIRMATION"
    assert "CLINICAL_FACT_UNCONFIRMED" in [u.code for u in item.explanation.undetermined]

    decided = evaluate_readiness(
        case, BASELINE_ITEMS,
        fact_decisions={"previous_treatment_history": FactDecisionRef(
            decision="CONFIRMED", fact_id="F1", reviewer_name="Dr A", reviewer_verification_label=None,
            coi_label="No conflict declared", decided_at="2026-10-01T00:00:00")},
    )
    exp = _by_id(decided)["previous_treatment_history"].explanation
    assert exp.trust.code == "HUMAN_REVIEWED"
    rule = next(r for r in exp.rules if r.kind == "REVIEWER_DECISION")
    assert {f.label: f.value for f in rule.facts}["Reviewer"] == "Dr A"
    # An unrecorded verification label is reported, not filled in.
    assert "Reviewer decision: CONFIRMED: Verification" in exp.not_recorded
