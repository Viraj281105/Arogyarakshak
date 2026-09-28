"""Clinical plausibility review (ADR-011): bounded, cited, never a necessity verdict."""

import re

from billnyay.plausibility import (
    NO_GUIDELINE_NOTE,
    PLAUSIBILITY_DISCLAIMER,
    EvidenceRef,
    assess_clinical_plausibility,
)


def dx(text, item_id="E-dx"):
    return EvidenceRef(item_id=item_id, kind="diagnosis", value=text)


def proc(text, item_id="E-proc"):
    return EvidenceRef(item_id=item_id, kind="procedure", value=text)


def test_plausible_when_procedure_matches_curated_reference():
    a = assess_clinical_plausibility([dx("K35.8 Acute appendicitis")], [proc("Laparoscopic Appendectomy")])
    assert a.status == "PLAUSIBLE"
    assert a.clinical_review_required is False
    assert a.is_necessity_determination is False
    assert a.disclaimer == PLAUSIBILITY_DISCLAIMER
    assert "broadly consistent" in a.summary
    assert a.references[0].icd10_code == "K35"
    assert a.references[0].type == "PROJECT_CURATED_REFERENCE"


def test_inconsistency_triggers_clinical_review():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("MRI Brain")])
    assert a.status == "POTENTIAL_INCONSISTENCY"
    assert a.clinical_review_required is True
    assert "not evidence of wrongdoing" in a.summary


def test_insufficient_when_code_not_in_reference():
    a = assess_clinical_plausibility([dx("J18.9 Pneumonia")], [proc("IV antibiotics")])
    assert a.status == "INSUFFICIENT_INFORMATION"
    assert "not evidence of a mismatch" in a.summary
    assert a.clinical_review_required is True


def test_insufficient_when_no_code_readable():
    a = assess_clinical_plausibility([dx("Abdominal pain")], [proc("Appendectomy")])
    assert a.status == "INSUFFICIENT_INFORMATION"
    assert a.summary.startswith("Insufficient evidence for assessment")


def test_no_evidence_at_all_is_insufficient_without_review():
    a = assess_clinical_plausibility([], [])
    assert a.status == "INSUFFICIENT_INFORMATION"
    assert a.clinical_review_required is False
    assert a.evidence_used == []


def test_conflicting_diagnoses_recommend_review():
    a = assess_clinical_plausibility(
        [dx("K35 Acute appendicitis", "E1"), dx("K80 Cholelithiasis", "E2")],
        [proc("Appendectomy")],
    )
    assert a.status == "CLINICAL_REVIEW_RECOMMENDED"
    assert a.clinical_review_required is True


def test_safety_escalation_raises_review():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Appendectomy")], safety_escalations=1)
    assert a.status == "CLINICAL_REVIEW_RECOMMENDED"
    assert any("safety rule" in r for r in a.review_reasons)


def test_never_fabricates_guideline_citations():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Appendectomy")])
    assert a.guideline_citations == []
    assert a.guideline_note == NO_GUIDELINE_NOTE
    text = a.model_dump_json()
    assert not re.search(r"PMID|pubmed|doi:", text, re.IGNORECASE)


def test_incomplete_registry_records_are_dropped_not_completed():
    registry = [
        {"title": "Some guideline", "issuer": "X", "applies_to_icd10": "K35"},  # no version/section
        {"title": "Registered", "issuer": "Body", "version": "2024", "section": "4.2", "applies_to_icd10": "K35"},
        {"title": "Other code", "issuer": "Body", "version": "1", "section": "1", "applies_to_icd10": "K80"},
    ]
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Appendectomy")], guideline_registry=registry)
    assert [c.title for c in a.guideline_citations] == ["Registered"]


def test_every_conclusion_lists_the_evidence_used():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Appendectomy")])
    assert {e.item_id for e in a.evidence_used} == {"E-dx", "E-proc"}
    assert all(e.provenance == "AI_DERIVED" for e in a.evidence_used)


# --- Audit fixes (issue 3) ---

def test_administrative_lines_are_not_interventions():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Room Rent"), proc("Nursing Charges")])
    assert a.status == "INSUFFICIENT_INFORMATION"
    assert a.excluded_administrative_items == ["Room Rent", "Nursing Charges"]
    assert "administrative" in a.summary


def test_plausible_discloses_unassessed_billed_items():
    a = assess_clinical_plausibility(
        [dx("K35 Acute appendicitis")], [proc("Laparoscopic Appendectomy"), proc("MRI Brain", "E-mri")]
    )
    assert a.status == "PLAUSIBLE"
    assert a.coverage == "PARTIAL"
    assert a.not_assessed_items == ["MRI Brain"]
    assert "NOT assessed" in a.summary and "MRI Brain" in a.summary


def test_full_coverage_when_everything_clinical_was_checked():
    a = assess_clinical_plausibility([dx("K35 Acute appendicitis")], [proc("Appendectomy"), proc("Room Rent")])
    assert a.coverage == "FULL" and a.not_assessed_items == []


def test_unassessable_diagnosis_makes_coverage_partial():
    result = assess_clinical_plausibility(
        [dx("K35.8 Acute appendicitis", "E1"), dx("Z99.9 Unlisted condition", "E2")],
        [proc("Laparoscopic Appendectomy")],
    )
    assert result.status == "PLAUSIBLE"
    assert result.coverage == "PARTIAL", "a diagnosis the reference cannot assess must not be hidden behind FULL"
    assert any("Z99.9" in item for item in result.not_assessed_items)


# --- Demo-hardening pass: adversarial cases ------------------------------------------

def test_one_matching_procedure_does_not_hide_a_conflicting_one():
    """Appendectomy fits appendicitis, but cholecystectomy is what the reference expects
    for gallstones, which is not documented. Previously: PLAUSIBLE."""
    a = assess_clinical_plausibility(
        [dx("K35.8 Acute appendicitis")],
        [proc("Laparoscopic Appendectomy", "P1"), proc("Laparoscopic Cholecystectomy", "P2")],
    )
    assert a.status == "CLINICAL_REVIEW_RECOMMENDED"
    assert a.status != "PLAUSIBLE"
    assert a.clinical_review_required is True
    assert "Cholecystectomy" in a.summary and "not reported as plausible" in a.summary
    assert a.conflicting_items == ["Laparoscopic Cholecystectomy"]
    assert "Laparoscopic Cholecystectomy" not in a.not_assessed_items, "it was assessed — as a conflict"


def test_conflict_is_not_raised_when_its_diagnosis_is_documented():
    a = assess_clinical_plausibility(
        [dx("K35.8 Acute appendicitis", "D1"), dx("K80.2 Gallstones", "D2")],
        [proc("Appendectomy", "P1"), proc("Cholecystectomy", "P2")],
    )
    assert a.status == "PLAUSIBLE" and a.coverage == "FULL"


def test_more_administrative_lines_are_excluded():
    lines = ["Registration Charges", "Administrative Charges", "Medical Records Fee", "GST @ 18%",
             "Linen and Laundry", "OT Charges", "Operation Theatre Charges", "Deposit Adjusted"]
    a = assess_clinical_plausibility([dx("K35.8 Acute appendicitis")], [proc(x, f"P{i}") for i, x in enumerate(lines)])
    assert sorted(a.excluded_administrative_items) == sorted(lines)
    assert a.status == "INSUFFICIENT_INFORMATION", "admin lines are never read as an inconsistency"
    assert a.not_assessed_items == []


def test_admin_exclusion_keeps_clinical_words():
    a = assess_clinical_plausibility([dx("K35.8 Acute appendicitis")], [proc("Laparoscopic Appendectomy")])
    assert a.excluded_administrative_items == [] and a.status == "PLAUSIBLE"


def test_partial_coverage_when_one_of_three_diagnoses_is_assessable():
    a = assess_clinical_plausibility(
        [dx("K35.8 Acute appendicitis", "D1"), dx("Z99.9 Dependence on device", "D2"), dx("Fever", "D3")],
        [proc("Appendectomy")],
    )
    assert a.status == "PLAUSIBLE"
    assert a.coverage == "PARTIAL"
    assert len([i for i in a.not_assessed_items if "diagnosis not covered" in i]) == 2
    assert "NOT treated as compatible" in a.summary


def test_unsupported_diagnosis_alone_is_never_compatible():
    a = assess_clinical_plausibility([dx("J18.9 Pneumonia")], [proc("Appendectomy")])
    assert a.status == "INSUFFICIENT_INFORMATION"
    assert a.coverage == "NONE"
    assert a.is_necessity_determination is False


def test_no_output_claims_necessity_or_approval():
    for dxs, procs in [
        ([dx("K35.8 Acute appendicitis")], [proc("Appendectomy")]),
        ([dx("K35.8 Acute appendicitis")], [proc("MRI Brain")]),
        ([dx("K35.8 Acute appendicitis")], [proc("Appendectomy", "P1"), proc("Cholecystectomy", "P2")]),
    ]:
        a = assess_clinical_plausibility(dxs, procs)
        text = a.summary.lower()
        assert "medically necessary" not in text and "will be approved" not in text
        assert a.disclaimer == PLAUSIBILITY_DISCLAIMER
