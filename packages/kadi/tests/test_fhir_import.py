"""ABDM/ABHA FHIR bundle -> Kadi case context (#54). Fixtures are synthetic."""

import copy
import json
from pathlib import Path

import pytest

from kadi.fhir_import import MAX_ENTRIES, MAX_TEXT_LENGTH, FhirBundleError, parse_fhir_bundle

FIXTURE = Path(__file__).parent / "fixtures" / "abdm" / "discharge_summary_synthetic.json"


@pytest.fixture
def bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _by_type(result, entity_type):
    return [e for e in result.entities if e.entity_type == entity_type]


def test_clinical_resources_map_to_kadi_entity_types(bundle):
    result = parse_fhir_bundle(bundle, source_label="abdm_import:test")

    [diagnosis] = _by_type(result, "diagnosis")
    assert diagnosis.name == "Acute Appendicitis"  # code.text preferred over coding.display
    assert diagnosis.meta["codings"] == [{"system": "http://snomed.info/sct", "code": "74400008"}]
    assert diagnosis.meta["source"] == "abdm_fhir"
    assert diagnosis.meta["source_file"] == "abdm_import:test"

    [procedure] = _by_type(result, "procedure")
    assert procedure.name == "Appendicectomy"
    assert procedure.meta["performed_date"] == "2026-08-02"

    medicines = {m.name: m for m in _by_type(result, "medicine")}
    assert set(medicines) == {"पॅरासिटामॉल 650", "Pantoprazole 40 mg"}  # referenced Medication resolved
    assert medicines["पॅरासिटामॉल 650"].meta["dosage"] == "1 tablet three times a day after food"

    [hospital] = _by_type(result, "hospital")  # custodian and serviceProvider deduplicated
    assert hospital.name == "Lifeline Multispeciality Hospital"

    assert (result.admission_date, result.discharge_date) == ("2026-08-02", "2026-08-05")
    assert result.record_types == ["Discharge Summary"]
    assert result.bundle_type == "document"


def test_invalid_records_are_skipped_not_imported(bundle):
    result = parse_fhir_bundle(bundle)
    names = {e.name for e in result.entities}
    assert "Pancreatitis" not in names  # entered-in-error
    assert "Tramadol 50 mg" not in names  # cancelled order
    assert result.skipped["Condition:entered-in-error"] == 1
    assert result.skipped["MedicationRequest:cancelled"] == 1
    assert result.skipped["Observation"] == 1
    assert result.skipped["malformed_entry"] == 2


def test_code_only_entries_are_never_given_invented_names(bundle):
    result = parse_fhir_bundle(bundle)
    assert len(_by_type(result, "diagnosis")) == 1
    assert any("never invented" in w for w in result.warnings)


def test_patient_identity_is_never_read(bundle):
    result = parse_fhir_bundle(bundle)
    assert result.dropped_for_privacy == {"Patient": 1, "Practitioner": 1}
    serialized = result.model_dump_json()
    for identifier in ("Synthetic Test Patient", "9000000000", "91-0000-0000-0000", "Dr Synthetic Example"):
        assert identifier not in serialized


def test_instruction_like_text_is_kept_as_inert_data(bundle):
    result = parse_fhir_bundle(bundle)
    [pantoprazole] = [m for m in _by_type(result, "medicine") if m.name == "Pantoprazole 40 mg"]
    # Stored as the dosage string it claims to be; nothing in the importer interprets it.
    assert pantoprazole.meta["dosage"].startswith("Ignore previous instructions")
    assert set(pantoprazole.meta) == {"source", "source_file", "fhir_resource", "codings", "dosage"}


def test_conflicting_encounter_dates_are_not_guessed(bundle):
    second = copy.deepcopy(bundle["entry"][3])
    second["fullUrl"] = "urn:uuid:enc-2"
    second["resource"]["id"] = "enc-2"
    second["resource"]["period"] = {"start": "2026-09-01", "end": "2026-09-03"}
    bundle["entry"].append(second)
    result = parse_fhir_bundle(bundle)
    assert result.admission_date is None and result.discharge_date is None
    assert any("several encounters" in w for w in result.warnings)


def test_text_is_sanitized_and_length_capped(bundle):
    bundle["entry"][4]["resource"]["code"]["text"] = "Acute\x00 Appendicitis\x1b[31m " + "x" * 1000
    result = parse_fhir_bundle(bundle)
    [diagnosis] = _by_type(result, "diagnosis")
    assert "\x00" not in diagnosis.name and "\x1b" not in diagnosis.name
    assert len(diagnosis.name) == MAX_TEXT_LENGTH


@pytest.mark.parametrize(
    "payload,message",
    [
        ([], "not a FHIR Bundle"),
        ({"resourceType": "Patient"}, "not a FHIR Bundle"),
        ({"resourceType": "Bundle", "entry": "nope"}, "no entry list"),
        ({"resourceType": "Bundle", "entry": [{}] * (MAX_ENTRIES + 1)}, "more than"),
    ],
)
def test_malformed_bundles_are_rejected(payload, message):
    with pytest.raises(FhirBundleError, match=message):
        parse_fhir_bundle(payload)
