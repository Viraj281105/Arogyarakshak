"""Unit tests for kadi.clinical_review — the DB-agnostic rules behind ADR-011."""

from datetime import date, timedelta

import pytest

from kadi.clinical_review import (
    ProvenanceClass,
    VerificationStatus,
    verification_label,
)
from kadi.clinical_review.evidence import (
    EntityRecord,
    SupplementaryItem,
    build_coi_context,
    build_evidence_packet,
    resolve_scope,
)
from kadi.clinical_review.lifecycle import (
    FINALIZATION_CONFIRMATION_TEXT,
    LifecycleError,
    clean_text,
    ensure_editable,
    ensure_finalizable,
    ensure_revisable,
    require_confirmation,
    statement_content_hash,
    validate_evidence_selection,
)
from kadi.clinical_review.safety import (
    ActiveRule,
    RuleValidationError,
    approvals_satisfied,
    ensure_rule_transition,
    evaluate_rules,
    validate_action,
    validate_trigger,
)
from kadi.clinical_review.transcription import (
    FieldType,
    OcrSegment,
    Reading,
    TaskStatus,
    evaluate_consensus,
    infer_field_type,
    normalize_reading,
    risk_for_field,
    select_uncertain_segments,
)
from kadi.clinical_review.types import SAFETY_FLOOR_DISCLAIMER
from kadi.clinical_review.verification import (
    EXTERNAL_VERIFICATION_UNAVAILABLE,
    UnavailableRegistryAdapter,
    initial_verification_status,
)


# --- Verification -------------------------------------------------------------

def test_no_label_ever_says_verified_doctor():
    for status in VerificationStatus:
        label = verification_label(status.value).lower()
        assert "verified doctor" not in label
    assert "not verified" in verification_label("SELF_DECLARED").lower()
    assert "demo" in verification_label("DEMO_VERIFIED").lower()
    assert "not verified" in verification_label("UNVERIFIED").lower()


def test_self_registration_never_exceeds_self_declared():
    assert initial_verification_status("MMC-12345") == "SELF_DECLARED"
    assert initial_verification_status("   ") == "UNVERIFIED"
    assert initial_verification_status(None) == "UNVERIFIED"


def test_unavailable_adapter_never_changes_status():
    outcome = UnavailableRegistryAdapter().verify(
        registration_number="MMC-1", registration_authority="MMC", name="Dr A"
    )
    assert outcome.outcome == EXTERNAL_VERIFICATION_UNAVAILABLE
    assert outcome.changes_status is False
    assert "unavailable" in outcome.detail.lower()


# --- Statement lifecycle --------------------------------------------------------

def test_confirmation_requires_flag_and_exact_sentence():
    with pytest.raises(LifecycleError):
        require_confirmation(False, FINALIZATION_CONFIRMATION_TEXT, FINALIZATION_CONFIRMATION_TEXT)
    with pytest.raises(LifecycleError):
        require_confirmation(True, None, FINALIZATION_CONFIRMATION_TEXT)
    with pytest.raises(LifecycleError):
        require_confirmation(True, "I agree", FINALIZATION_CONFIRMATION_TEXT)
    require_confirmation(True, FINALIZATION_CONFIRMATION_TEXT, FINALIZATION_CONFIRMATION_TEXT)


def test_finalized_statement_is_not_editable_but_can_be_revised():
    with pytest.raises(LifecycleError):
        ensure_editable("FINALIZED")
    with pytest.raises(LifecycleError):
        ensure_finalizable("FINALIZED")
    ensure_revisable("FINALIZED")
    with pytest.raises(LifecycleError):
        ensure_revisable("DRAFT")


def test_clean_text_strips_control_chars_and_bounds_length():
    assert clean_text("  ok\x00\x07 ", max_chars=10, field="x") == "ok"
    with pytest.raises(LifecycleError):
        clean_text("a" * 11, max_chars=10, field="x")
    with pytest.raises(LifecycleError):
        clean_text("   ", max_chars=10, field="x")


def test_evidence_selection_must_come_from_packet():
    assert validate_evidence_selection(["E1", "E1", "E2"], ["E1", "E2"]) == ["E1", "E2"]
    with pytest.raises(LifecycleError):
        validate_evidence_selection(["E9"], ["E1"])
    with pytest.raises(LifecycleError):
        validate_evidence_selection([], ["E1"])


def test_content_hash_detects_any_change():
    base = {"statement": "a", "version": 1}
    assert statement_content_hash(base) == statement_content_hash(dict(base))
    assert statement_content_hash(base) != statement_content_hash({**base, "statement": "b"})


# --- Evidence packets -------------------------------------------------------------

ENTITIES = [
    EntityRecord("E-diag", "diagnosis", "K35.8 Acute appendicitis", None, {}),
    EntityRecord("E-proc", "procedure", "Laparoscopic appendectomy", "45000", {}),
    EntityRecord("E-hosp", "hospital", "City Care Hospital", None, {}),
    EntityRecord("E-doc", "document_text", "Excerpt", "Patient Name: Asha Rao, Diagnosis K35", {}),
    EntityRecord("E-med", "medicine", "Dolo", "30", {"dosage": "650mg"}),
]


def test_packet_only_contains_scoped_types():
    packet = build_evidence_packet(ENTITIES, ["diagnosis", "procedure"])
    assert {i["kind"] for i in packet} == {"diagnosis", "procedure"}
    assert all(i["provenance"] == ProvenanceClass.AI_DERIVED.value for i in packet)


def test_packet_redacts_identifiers_again():
    packet = build_evidence_packet(ENTITIES, ["document_text"])
    assert "Asha Rao" not in packet[0]["value"]


def test_supplementary_items_keep_their_provenance():
    packet = build_evidence_packet(
        [], ["diagnosis"],
        [SupplementaryItem("S1", "denial_record", "Denial", "Not medically necessary",
                           ProvenanceClass.PATIENT_PROVIDED, "Entered by case holder")],
    )
    assert packet[0]["provenance"] == "PATIENT_PROVIDED"


def test_human_resolved_transcription_is_marked_human_reviewed():
    entity = EntityRecord("E-m2", "medicine", "Augmntn", "0",
                          {"human_transcription": {"status": "RESOLVED", "value": "Augmentin 625"}})
    packet = build_evidence_packet([entity], ["medicine"])
    assert packet[0]["provenance"] == "HUMAN_REVIEWED"
    assert "Augmentin 625" in packet[0]["value"]


def test_scope_validation():
    assert resolve_scope("billnyay", None)[0] == "diagnosis"
    with pytest.raises(ValueError):
        resolve_scope("billnyay", ["patient_name"])
    with pytest.raises(ValueError):
        resolve_scope("billnyay", [])


def test_coi_context_has_no_clinical_content():
    ctx = build_coi_context(ENTITIES, "billnyay", "Acme Health Insurance")
    assert ctx["hospital_names"] == ["City Care Hospital"]
    assert "appendicitis" not in str(ctx).lower()


# --- Safety governance -----------------------------------------------------------

def _rule(**overrides):
    base = dict(
        rule_id="SR-1", rule_key="stroke-fast", version=1, title="Possible stroke signs",
        trigger={"match_any": ["slurred speech", "facial droop"], "context_types": ["document_text"]},
        action={"type": "SHOW_SAFETY_ESCALATION", "severity": "URGENT", "message": "Seek emergency care now."},
        source_name="FAST stroke recognition", source_version="public education material",
        source_section=None, limitations="Covers only FAST signs.",
        effective_date=None, review_due_date=None,
    )
    base.update(overrides)
    return ActiveRule(**base)


def test_rule_matches_terms_and_returns_only_terms():
    ctx = [("document_text", "Patient presented with SLURRED   speech since morning. Name: X")]
    esc = evaluate_rules([_rule()], ctx)
    assert len(esc) == 1
    assert esc[0]["matched_terms"] == ["slurred speech"]
    assert "Name" not in str(esc[0])
    assert esc[0]["disclaimer"] == SAFETY_FLOOR_DISCLAIMER
    assert esc[0]["rule_version"] == 1
    assert esc[0]["source"]["name"] == "FAST stroke recognition"


def test_rule_respects_word_boundaries_and_context_types():
    assert evaluate_rules([_rule()], [("document_text", "no droopiness")]) == []
    assert evaluate_rules([_rule()], [("diagnosis", "slurred speech")]) == []


def test_rule_not_effective_yet_does_not_fire():
    future = date.today() + timedelta(days=3)
    assert evaluate_rules([_rule(effective_date=future)], [("document_text", "facial droop")]) == []


def test_negation_is_disclosed_as_a_limitation():
    esc = evaluate_rules([_rule()], [("document_text", "no facial droop")])
    assert any("negation" in lim.lower() for lim in esc[0]["limitations"])


def test_trigger_and_action_validation():
    with pytest.raises(RuleValidationError):
        validate_trigger({"match_any": []})
    with pytest.raises(RuleValidationError):
        validate_trigger({"match_any": ["ok term"], "context_types": ["patient_name"]})
    with pytest.raises(RuleValidationError):
        validate_action({"type": "RUN_CODE", "message": "x"})
    with pytest.raises(RuleValidationError):
        validate_action({"type": "SHOW_SAFETY_ESCALATION", "message": ""})
    assert validate_trigger({"match_any": [" slurred  speech "]})["match_any"] == ["slurred speech"]


def test_rule_transitions():
    ensure_rule_transition("DRAFT", "UNDER_REVIEW")
    ensure_rule_transition("ACTIVE", "RETIRED")
    with pytest.raises(RuleValidationError):
        ensure_rule_transition("DRAFT", "ACTIVE")
    with pytest.raises(RuleValidationError):
        ensure_rule_transition("RETIRED", "ACTIVE")


def test_four_eyes_approval():
    assert not approvals_satisfied(["REV-a"], "REV-a", 1)
    assert approvals_satisfied(["REV-a", "REV-b"], "REV-a", 1)
    assert not approvals_satisfied(["REV-b"], "REV-a", 2)


# --- OCR human resolution ------------------------------------------------------

def test_field_inference():
    assert infer_field_type("650 mg") == FieldType.STRENGTH
    assert infer_field_type("TDS") == FieldType.FREQUENCY
    assert infer_field_type("1-0-1") == FieldType.FREQUENCY
    assert infer_field_type("x 5 days") == FieldType.DURATION
    assert infer_field_type("IV") == FieldType.ROUTE
    assert infer_field_type("Rs 450") == FieldType.NON_CLINICAL
    assert infer_field_type("Augmntn", "Tab. 625mg") == FieldType.MEDICINE_NAME
    assert infer_field_type("zzqx") == FieldType.UNCLASSIFIED


def test_possible_medication_fields_are_high_risk():
    for ft in ("MEDICINE_NAME", "STRENGTH", "FREQUENCY", "ROUTE", "DURATION", "UNCLASSIFIED"):
        assert risk_for_field(ft).value == "HIGH"
    assert risk_for_field("NON_CLINICAL").value == "STANDARD"


def test_uncertain_segments_are_masked_and_redacted():
    segs = [
        OcrSegment("Patient Name: Asha Rao", 0.2),
        OcrSegment("Tab.", 0.9),
        OcrSegment("Augmntn", 0.2, [[1, 2], [3, 4], [5, 6], [7, 8]]),
        OcrSegment("625mg BD", 0.95),
    ]
    tasks = select_uncertain_segments(segs, threshold=0.5)
    assert len(tasks) == 1, "a segment that is only a redacted identifier must not become a task"
    task = tasks[0]
    assert task["ocr_candidate"] == "Augmntn"
    assert "▢▢▢" in task["masked_context"] and "Augmntn" not in task["masked_context"]
    assert "Asha" not in str(tasks)
    assert task["risk_level"] == "HIGH" and task["required_reviews"] == 2
    assert task["location_hint"]["bbox"][0] == [1.0, 2.0]


def test_normalization_ignores_formatting_only():
    assert normalize_reading("Dolo 650 mg") == normalize_reading("dolo 650MG")
    assert normalize_reading("Dolo 650") != normalize_reading("Dolo 500")


def _r(rid, value, unreadable=False, conf="HIGH"):
    return Reading(rid, value, unreadable, conf)


def test_high_risk_never_accepts_a_single_reading():
    res = evaluate_consensus("HIGH", [_r("A", "Augmentin 625")])
    assert res.status == TaskStatus.AWAITING_SECOND_REVIEW and res.final_value is None


def test_same_reviewer_twice_does_not_count_as_two():
    res = evaluate_consensus("HIGH", [_r("A", "Augmentin"), _r("A", "Augmentin")])
    assert res.status == TaskStatus.AWAITING_SECOND_REVIEW


def test_high_risk_agreement_resolves():
    res = evaluate_consensus("HIGH", [_r("A", "Augmentin 625 mg"), _r("B", "augmentin 625mg")])
    assert res.status == TaskStatus.RESOLVED and res.final_value == "Augmentin 625 mg"


def test_high_risk_disagreement_escalates():
    res = evaluate_consensus("HIGH", [_r("A", "Augmentin 625"), _r("B", "Azithral 500")])
    assert res.status == TaskStatus.HUMAN_ESCALATION_REQUIRED and res.final_value is None


def test_unreadable_escalates():
    res = evaluate_consensus("STANDARD", [_r("A", None, unreadable=True)])
    assert res.status == TaskStatus.HUMAN_ESCALATION_REQUIRED


def test_standard_low_confidence_needs_second_reading():
    assert evaluate_consensus("STANDARD", [_r("A", "450", conf="LOW")]).status == TaskStatus.AWAITING_SECOND_REVIEW
    assert evaluate_consensus("STANDARD", [_r("A", "450")]).status == TaskStatus.RESOLVED


# --- Audit fixes (issue 1): no noise tasks, no prescriber data, whole-token linking ---

from kadi.clinical_review.transcription import link_candidate_to_entity, substitute_reading  # noqa: E402


def test_realistic_prescription_does_not_flood_or_leak():
    segs = [
        OcrSegment("CITY CARE HOSPITAL", 0.3),
        OcrSegment("Dr. Mehta MBBS", 0.4),
        OcrSegment("Rx", 0.2),
        OcrSegment("Tab.", 0.3),
        OcrSegment("Augmntn", 0.3),
        OcrSegment("625mg", 0.95),
        OcrSegment("1-0-1", 0.4),
        OcrSegment("Date 12/03/2026", 0.3),
    ]
    tasks = select_uncertain_segments(segs)
    candidates = [t["ocr_candidate"] for t in tasks]
    assert "Rx" not in candidates and "Tab." not in candidates, "prescription markers are noise"
    assert "Dr. Mehta MBBS" not in candidates, "prescriber identity is never a task"
    assert "Date 12/03/2026" not in candidates, "non-clinical fields have no consumer"
    assert "Mehta" not in str(tasks), "prescriber name never reaches a reader, even as context"
    assert all("CITY CARE" not in t["masked_context"] for t in tasks), "non-medication neighbours are elided"
    assert "Augmntn" in candidates
    # A letterhead can survive selection as UNCLASSIFIED, but it links to no medicine,
    # so the API never turns it into a task (tested end to end in the API suite).
    meds = [("E1", "Tab Augmntn 625mg")]
    linked = [t for t in tasks if link_candidate_to_entity(t["ocr_candidate"], meds)]
    assert [t["ocr_candidate"] for t in linked] == ["Augmntn"]


def test_linking_is_whole_token_and_unambiguous():
    meds = [("E1", "Tab Augmntn 625mg"), ("E2", "Tab Dolo 650mg")]
    assert link_candidate_to_entity("Augmntn", meds) == "E1"
    assert link_candidate_to_entity("Tab.", meds) is None
    assert link_candidate_to_entity("0", meds) is None
    assert link_candidate_to_entity("Aug", meds) is None, "no substring matches"
    assert link_candidate_to_entity("Tab", [("E1", "Tab Dolo"), ("E2", "Tab Dolo 500")]) is None


def test_substitution_replaces_only_the_uncertain_part():
    assert substitute_reading("Tab Augmntn 625mg", "Augmntn", "Augmentin") == "Tab Augmentin 625mg"
    assert substitute_reading("Tab Dolo 650mg", "Tab Dolo 650mg", "Dolo 650") == "Dolo 650", "whole-entry flag"
    assert substitute_reading("Tab Dolo 650mg", "Xyz", "Abc") is None, "cannot place it: leave entry untouched"
    assert substitute_reading("Dolo Dolo", "Dolo", "X") is None, "ambiguous position: leave entry untouched"


def test_full_text_scan_returns_only_rule_ids_and_terms():
    from kadi.clinical_review.safety import scan_full_text

    text = "x" * 3000 + " patient had slurred speech. Name: Asha Rao"
    result = scan_full_text([_rule()], text)
    assert result == [{"rule_id": "SR-1", "rule_version": 1, "matched_terms": ["slurred speech"]}]


# --- Second audit: linking/substitution false negatives, re-versioned rules ---------

def test_cap_is_not_applied_during_selection():
    segs = [OcrSegment(f"Wellness Clinic Branch {i}", 0.3) for i in range(15)] + [OcrSegment("Augmntn", 0.3)]
    assert "Augmntn" in [t["ocr_candidate"] for t in select_uncertain_segments(segs)]


def test_whole_uncertain_line_links_to_the_medicine_it_names():
    assert link_candidate_to_entity("Tab Augmntn 625mg 1-0-1", [("E1", "Augmntn")]) == "E1"
    # Every token counts: "Pan 40 mg OD" names "Pan 40" ("40" == "40mg") but not "Pan-D"
    # (its "D" is absent). The bare "Pan" names both and stays ambiguous.
    assert link_candidate_to_entity("Pan 40 mg OD", [("E1", "Pan 40"), ("E2", "Pan-D")]) == "E1"
    assert link_candidate_to_entity("Pan", [("E1", "Pan 40"), ("E2", "Pan-D")]) is None, "ambiguous"
    assert link_candidate_to_entity("City Care Clinic", [("E1", "Augmntn")]) is None


def test_leading_dosage_form_marker_does_not_block_substitution():
    assert substitute_reading("Pantop 40", "Tab. Pantop", "Tab. Pantoprazole") == "Pantoprazole 40"
    assert substitute_reading("Augmntn", "Tab Augmntn 625mg 1-0-1", "Augmentin") is None, "cannot place a whole line"


def test_superseded_rule_terms_carry_forward_only_when_still_listed():
    from kadi.clinical_review.safety import carried_forward_terms

    v2 = _rule(trigger={"match_any": ["Slurred  Speech", "facial droop"], "context_types": ["document_text"]})
    assert carried_forward_terms(v2, ["slurred speech"]) == ["slurred speech"]
    assert carried_forward_terms(_rule(trigger={"match_any": ["facial droop"], "context_types": ["document_text"]}),
                                 ["slurred speech"]) == []
    assert carried_forward_terms(_rule(trigger={"match_any": ["slurred speech"], "context_types": ["diagnosis"]}),
                                 ["slurred speech"]) == [], "a successor that no longer scans document text"


def test_a_marker_only_reading_never_replaces_the_drug_name():
    assert substitute_reading("Pantop 40", "Tab. Pantop", "Tab.") is None
