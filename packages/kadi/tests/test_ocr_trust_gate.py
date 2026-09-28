"""OCR trust pipeline (ADR-011, demo-hardening pass): every uncertain reading is carried
forward, and the single medicine trust gate blocks every unsettled state.

Each test names the failure it guards against. Before this pass, readings that linked to
no medicine, to several, or beyond the task cap were dropped and the medicine was
benchmarked as an ordinary AI_DERIVED extraction.
"""

from kadi.clinical_review.medicine_trust import (
    MedicineTrustState,
    PendingTask,
    decide_medicine_trust,
)
from kadi.clinical_review.transcription import (
    MedicineRef,
    OcrSegment,
    OcrUncertaintyReason,
    link_candidate_to_entity,
    merge_ocr_uncertainty,
    names_a_drug,
    plan_ocr_uncertainty,
    select_uncertain_segments,
    similar_medicine_candidates,
    substitute_reading,
    token_link_candidates,
)


def _payloads(*texts, confidence=0.3):
    return select_uncertain_segments([OcrSegment(t, confidence) for t in texts])


def _reasons(plan, entity_id):
    return [h["reason"] for h in plan.held_back.get(entity_id, [])]


# --- 1. Zero-match readings --------------------------------------------------------

def test_unplaced_medication_reading_holds_back_ungrounded_medicines():
    """An unclear medication line that names no extracted medicine must not let a medicine
    whose name is not in the clearly-read text be benchmarked."""
    meds = [MedicineRef("E1", "Zyloric 100"), MedicineRef("E2", "Dolo 650")]
    plan = plan_ocr_uncertainty(
        _payloads("Tab Xqrtz 1-0-1"), meds, confident_texts=["Tab Dolo 650 1-0-1"]
    )
    assert plan.linked == []
    assert len(plan.unplaced) == 1
    assert _reasons(plan, "E1") == [OcrUncertaintyReason.UNGROUNDED.value]
    assert "E2" not in plan.held_back, "a medicine clearly read on the page stays benchmarkable"


def test_unplaced_reading_only_affects_medicines_of_the_same_document():
    meds = [MedicineRef("E1", "Zyloric 100"), MedicineRef("OLD", "Metformin 500")]
    plan = plan_ocr_uncertainty(_payloads("Tab Xqrtz 1-0-1"), meds, document_medicine_ids=["E1"])
    assert "E1" in plan.held_back and "OLD" not in plan.held_back


def test_non_medication_noise_is_counted_not_held():
    plan = plan_ocr_uncertainty(
        [{"ocr_candidate": "Room 12", "risk_level": "STANDARD"}], [MedicineRef("E1", "Dolo 650")]
    )
    assert plan.held_back == {} and plan.ignored == 1


# --- 2. Ambiguous readings ---------------------------------------------------------

def test_ambiguous_reading_blocks_every_candidate_and_links_none():
    meds = [MedicineRef("E1", "Pan 40"), MedicineRef("E2", "Pan-D")]
    assert link_candidate_to_entity("Pan", meds) is None
    assert sorted(token_link_candidates("Pan", meds)) == ["E1", "E2"]
    plan = plan_ocr_uncertainty(_payloads("Pan"), meds)
    assert plan.linked == []
    assert _reasons(plan, "E1") == ["AMBIGUOUS"] and _reasons(plan, "E2") == ["AMBIGUOUS"]


def test_two_fitting_medicines_are_ambiguous_even_if_one_matches_exactly():
    meds = [MedicineRef("E1", "Dolo"), MedicineRef("E2", "Dolo 650")]
    assert link_candidate_to_entity("Dolo", meds) is None


# --- 3. Over-cap readings ----------------------------------------------------------

def test_linked_readings_beyond_the_cap_stay_uncertain():
    meds = [MedicineRef(f"E{i}", f"Drugname{chr(97 + i)}x") for i in range(4)]
    payloads = _payloads(*[f"Drugname{chr(97 + i)}x" for i in range(4)])
    plan = plan_ocr_uncertainty(payloads, meds, cap=2)
    assert [eid for _, eid in plan.linked] == ["E0", "E1"]
    assert _reasons(plan, "E2") == ["OVER_CAP"] and _reasons(plan, "E3") == ["OVER_CAP"]


# --- 4. LLM-rewritten names --------------------------------------------------------

def test_llm_normalised_name_keeps_the_uncertainty():
    """OCR unsure of "Amoxycilin"; the extractor wrote "Amoxicillin 500". Not a token
    match, so no task — but the medicine must not become a trusted fact."""
    meds = [MedicineRef("E1", "Amoxicillin 500")]
    assert link_candidate_to_entity("Amoxycilin", meds) is None
    assert similar_medicine_candidates("Amoxycilin", meds) == ["E1"]
    plan = plan_ocr_uncertainty(_payloads("Amoxycilin"), meds)
    assert _reasons(plan, "E1") == ["POSSIBLE_MATCH"]


def test_abbreviated_reading_resembles_the_full_name():
    assert similar_medicine_candidates("Cap Amoxy 500", [MedicineRef("E1", "Amoxycillin 500")]) == ["E1"]


def test_uncertain_strength_stored_separately_is_a_possible_match():
    meds = [MedicineRef("E1", "Augmntn", dosage="625mg"), MedicineRef("E2", "Dolo", dosage="650mg")]
    assert similar_medicine_candidates("625mg", meds) == ["E1"]


# --- 6. Marker-only readings -------------------------------------------------------

def test_marker_only_readings_never_become_medicine_names():
    assert substitute_reading("Pan 40", "Pan", "Tab.") is None, "would give 'Tab. 40'"
    assert substitute_reading("Pan 40", "Pan 40", "Cap.") is None, "whole entry replaced by a marker"
    assert substitute_reading("Pan 40", "Pan 40", "Tab. 40") is None, "no drug name left"
    assert substitute_reading("Pan 40", "Pan 40", "Rx") is None
    assert substitute_reading("Pan 40", "Pan", "") is None
    assert not names_a_drug("Tab. 40 mg OD") and names_a_drug("Pantoprazole 40")
    assert link_candidate_to_entity("Tab.", [MedicineRef("E1", "Tab Dolo")]) is None
    assert select_uncertain_segments([OcrSegment("Cap.", 0.2), OcrSegment("Rx", 0.2)]) == []


# --- 7. Whole-line linking ---------------------------------------------------------

def test_realistic_whole_lines_link_to_exactly_one_medicine():
    meds = [MedicineRef("E1", "Augmntn"), MedicineRef("E2", "Amoxy 500"), MedicineRef("E3", "Dolo 650")]
    assert link_candidate_to_entity("Tab Augmntn 625mg 1-0-1", meds) == "E1"
    assert link_candidate_to_entity("Cap Amoxy 500", meds) == "E2"
    assert link_candidate_to_entity("Dolo 650", meds) == "E3"
    assert link_candidate_to_entity("Dolo", [MedicineRef("E1", "Dolo 650"), MedicineRef("E2", "Dolo 500")]) is None
    assert link_candidate_to_entity("40", [MedicineRef("E1", "Pan 40")]) is None, "a number alone names nothing"
    assert link_candidate_to_entity("Pan", [MedicineRef("E1", "Pantop 40")]) is None, "no substring matching"


def test_units_do_not_cross_match():
    assert link_candidate_to_entity("Thyrox 50mcg", [MedicineRef("E1", "Thyrox 50mg")]) is None


# --- 8. The trust gate -------------------------------------------------------------

def _state(meta=None, pending=None):
    return decide_medicine_trust("Dolo 650", meta or {}, pending).state


def test_gate_blocks_every_unsettled_state():
    assert _state(pending=PendingTask("T1", "OPEN")) == MedicineTrustState.AWAITING_HUMAN_READING
    assert _state(pending=PendingTask("T1", "AWAITING_SECOND_REVIEW")) == MedicineTrustState.AWAITING_HUMAN_READING
    assert _state(pending=PendingTask("T1", "HUMAN_ESCALATION_REQUIRED")) == MedicineTrustState.READERS_DISAGREED
    assert _state({"human_transcription": {"status": "NOT_APPLIED", "human_reading": "X"}}) == MedicineTrustState.READING_NOT_APPLIED
    for reason in ("AMBIGUOUS", "POSSIBLE_MATCH", "OVER_CAP", "UNGROUNDED"):
        meta = {"ocr_uncertainty": merge_ocr_uncertainty(None, [{"reason": reason, "reading": "Pan"}])}
        decision = decide_medicine_trust("Pan 40", meta)
        assert decision.state == MedicineTrustState.OCR_UNCERTAIN and not decision.benchmarkable
        assert decision.reasons == [reason]
    for blocked in (
        decide_medicine_trust("X", {}, PendingTask("T", "OPEN")),
        decide_medicine_trust("X", {"human_transcription": {"status": "NOT_APPLIED"}}),
    ):
        assert blocked.benchmarkable is False and blocked.name_provenance == "AI_DERIVED"


def test_gate_trusts_only_settled_entries():
    resolved = decide_medicine_trust(
        "Tab Augmntn", {"human_transcription": {"status": "RESOLVED", "value": "Tab Augmentin"}}
    )
    assert resolved.benchmarkable and resolved.name == "Tab Augmentin" and resolved.name_provenance == "HUMAN_REVIEWED"
    plain = decide_medicine_trust("Dolo 650", {})
    assert plain.benchmarkable and plain.name_provenance == "AI_DERIVED"


def test_partial_resolution_does_not_clear_ocr_uncertainty():
    meta = {
        "human_transcription": {"status": "RESOLVED", "value": "Pan 40", "whole_entry": False},
        "ocr_uncertainty": merge_ocr_uncertainty(None, [{"reason": "AMBIGUOUS", "reading": "Pan"}]),
    }
    assert _state(meta) == MedicineTrustState.OCR_UNCERTAIN


def test_settled_uncertainty_no_longer_blocks():
    meta = {
        "human_transcription": {"status": "RESOLVED", "value": "Pan 40", "whole_entry": True},
        "ocr_uncertainty": {"status": "SETTLED_BY_HUMAN_READING", "reasons": ["AMBIGUOUS"]},
    }
    assert _state(meta) == MedicineTrustState.HUMAN_RESOLVED


def test_only_a_later_whole_entry_reading_overrides_an_escalation():
    escalated = PendingTask("T1", "HUMAN_ESCALATION_REQUIRED", resolved_at="2026-09-27T10:00:00")
    later_whole = {"human_transcription": {"status": "RESOLVED", "value": "Pan 40", "whole_entry": True,
                                           "resolved_at": "2026-09-27T11:00:00"}}
    earlier_whole = {"human_transcription": {"status": "RESOLVED", "value": "Pan 40", "whole_entry": True,
                                             "resolved_at": "2026-09-27T09:00:00"}}
    later_partial = {"human_transcription": {"status": "RESOLVED", "value": "Pan 40", "whole_entry": False,
                                             "resolved_at": "2026-09-27T11:00:00"}}
    assert _state(later_whole, escalated) == MedicineTrustState.HUMAN_RESOLVED
    assert _state(earlier_whole, escalated) == MedicineTrustState.READERS_DISAGREED
    assert _state(later_partial, escalated) == MedicineTrustState.READERS_DISAGREED


def test_merge_never_clears_reasons():
    first = merge_ocr_uncertainty(None, [{"reason": "OVER_CAP", "reading": "A", "ocr_confidence": 0.4}])
    second = merge_ocr_uncertainty(first, [{"reason": "AMBIGUOUS", "reading": "B", "ocr_confidence": 0.2}])
    assert second["reasons"] == ["OVER_CAP", "AMBIGUOUS"]
    assert second["readings"] == ["A", "B"] and second["min_ocr_confidence"] == 0.2


# --- Entity resolution must not merge a combination product into its base drug -------

def test_combination_variant_is_not_merged_into_the_base_medicine():
    """Found while building the ambiguity tests: "Pan-D" (pantoprazole + domperidone)
    was auto-MERGED into "Pan 40" (lexical 1.0), silently dropping one medicine from the
    case and from DawaCheck. A variant letter on one side is a different product."""
    from kadi.resolution import CandidateEntity, EntityMention, resolve_mention

    def action(existing, mention, entity_type="medicine"):
        return resolve_mention(
            EntityMention(name=mention, entity_type=entity_type),
            [CandidateEntity(id="E1", name=existing, entity_type=entity_type, aliases=[])],
        ).action

    assert action("Pan 40", "Pan-D") == "NEW"
    assert action("Glycomet", "Glycomet-GP") != "MERGE"
    assert action("Amoxicillin 500 mg", "Amoxicillin 0.5 g") == "MERGE", "a unit letter is not a variant"
    assert action("Dolo 650", "Tab Dolo 650mg") == "MERGE"


# --- Whole-line readings can be placed when the line is exactly the entry ---------

def test_agreed_whole_line_reading_is_placed_when_the_line_is_exactly_the_entry():
    """Found while building Scenario C: the realistic uncertain reading is a whole line,
    and an agreed transcription of it always ended NOT_APPLIED."""
    line = "Tab Augmntn 625mg 1-0-1 x 5 days"
    assert substitute_reading("Augmntn 625mg", line, "Tab Augmentin 625mg 1-0-1 x 5 days") == "Augmentin 625mg"
    assert substitute_reading("Augmntn 625mg", line, "tab augmentin 625 mg 1-0-1 x 5 days") == "augmentin 625 mg"


def test_whole_line_reading_stays_unplaced_when_the_line_carries_more_than_the_entry():
    # Strength stored separately: where the name ends in the reading is a guess.
    assert substitute_reading("Augmntn", "Tab Augmntn 625mg 1-0-1", "Tab Augmentin 625mg 1-0-1") is None
    # A reading that is only markers / dose pattern names no drug.
    assert substitute_reading("Augmntn 625mg", "Tab Augmntn 625mg 1-0-1 x 5 days", "Tab. 1-0-1 x 5 days") is None
