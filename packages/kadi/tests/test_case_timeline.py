from datetime import datetime, timedelta

from kadi.timeline import TimelineInput, build_case_timeline

T0 = datetime(2026, 9, 27, 10, 0, 0)


def _at(minutes):
    return T0 + timedelta(minutes=minutes)


def test_events_come_only_from_records_and_are_ordered_by_their_own_timestamps():
    out = build_case_timeline(
        TimelineInput(
            documents=[{"at": _at(1), "extension": ".png"}],
            entity_counts={"medicine": 5, "billing_item": 0},
            held_back_medicines=4,
            audit_events=[
                {"at": _at(30), "event_type": "TRANSCRIPTION_CONFIRMED", "actor_type": "SYSTEM", "details": {"applied_to_entity": True}},
                {"at": _at(2), "event_type": "TRANSCRIPTION_REQUESTED", "actor_type": "SYSTEM",
                 "details": {"source": "OCR_LOW_CONFIDENCE", "held_back_entities": 4}},
                {"at": _at(20), "event_type": "TRANSCRIPTION_SUBMITTED", "actor_type": "REVIEWER", "details": {}},
            ],
            module_insights=[{"at": _at(3), "module_check": "dawacheck_benchmark", "status": "COMPLETED",
                              "summary": {"medicines": 5, "benchmarked": 1, "price_basis_unclear": 0}}],
        )
    )
    labels = [e["label"] for e in out["events"]]
    assert labels == [
        "Document received and read",
        "Information extracted",
        "Unclear readings could not be tied to one medicine — those medicines are held back",
        "Automatic check ran: DawaCheck medicine price check",
        "A reader submitted a blind reading",
        "Two independent readers agreed",
    ]
    times = [e["at"] for e in out["events"]]
    assert times == sorted(times)
    extracted = out["events"][1]
    assert extracted["detail"] == "5 medicines."
    assert "4 medicines will not be price-checked" in out["events"][2]["detail"]
    assert out["events"][-1]["actor"] == "HUMAN"
    assert "can now be price-checked" in out["events"][-1]["detail"]
    assert out["failure"] is None and out["in_progress"] is None


def test_nothing_is_claimed_for_a_case_with_no_records():
    out = build_case_timeline(TimelineInput())
    assert out["events"] == []


def test_a_reading_that_could_not_be_applied_is_not_presented_as_a_price_check():
    out = build_case_timeline(
        TimelineInput(audit_events=[{"at": _at(5), "event_type": "TRANSCRIPTION_CONFIRMED", "actor_type": "SYSTEM",
                                     "details": {"applied_to_entity": False}}])
    )
    assert "stays held back" in out["events"][0]["detail"]


def test_failure_names_the_stage_and_a_recovery():
    out = build_case_timeline(TimelineInput(live_status={"status": "failed", "log": "The document could not be read."}))
    assert out["failure"]["message"] == "The document could not be read."
    assert "Upload the document again" in out["failure"]["recovery"]


def test_in_progress_stage_is_readable_not_an_enum():
    out = build_case_timeline(TimelineInput(live_status={"status": "extraction_start", "log": "..."}))
    assert out["in_progress"]["stage"] == "Extracting information"


def test_drafting_edits_are_folded_and_no_statement_text_is_exposed():
    out = build_case_timeline(
        TimelineInput(audit_events=[
            {"at": _at(1), "event_type": "STATEMENT_CREATED", "details": {}},
            {"at": _at(2), "event_type": "STATEMENT_EDITED", "details": {}},
            {"at": _at(3), "event_type": "STATEMENT_EDITED", "details": {}},
            {"at": _at(4), "event_type": "STATEMENT_FINALIZED", "details": {}},
            {"at": _at(5), "event_type": "SOMETHING_INTERNAL", "details": {}},
        ])
    )
    assert [e["label"] for e in out["events"]] == [
        "Reviewer started a statement (private draft)",
        "Doctor-authored statement finalized and signed",
    ]


def test_price_basis_gaps_are_named_in_the_dawacheck_step():
    out = build_case_timeline(
        TimelineInput(module_insights=[{"at": _at(1), "module_check": "dawacheck_benchmark", "status": "COMPLETED",
                                        "summary": {"medicines": 2, "benchmarked": 1, "price_basis_unclear": 1}}])
    )
    assert "1 not compared because the price basis" in out["events"][0]["detail"]
