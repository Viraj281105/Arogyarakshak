"""
ABDM / ABHA health records -> Kadi case context (#54).

Parses a FHIR R4 ``Bundle`` — the format ABDM Health Information Providers share records
in (NRCeS profiles such as DischargeSummaryRecord and PrescriptionRecord) — into Kadi
entity mentions, which the API then resolves against the case's existing entities.

Scope, stated plainly:

- This parses a bundle the client supplies. It does **not** pull records from the ABDM
  gateway: that needs ABDM sandbox/HIU registration and consent-manager integration, which
  this project does not have (tracked separately, #46/#56).
- It does not validate bundles against NRCeS FHIR profiles or verify HIE-CM signatures.

Mapping:

    Condition                                -> diagnosis
    Procedure                                -> procedure
    MedicationRequest / MedicationStatement  -> medicine (dosage text kept in meta)
    Encounter.period                         -> admission / discharge dates
    Organization (Encounter.serviceProvider,
                  Composition.custodian)     -> hospital

Deliberate omissions:

- Patient, Practitioner, RelatedPerson and Person resources are dropped (counted, never
  read), as are identifiers, addresses and every resource's narrative ``text.div``, which
  routinely repeats demographics (ADR-003).
- Entries recorded as entered-in-error, refuted, not-done, cancelled or not-taken are skipped.
- A coded entry with no human-readable ``text`` or ``display`` is skipped with a warning;
  a name is never invented from a bare code.

Everything read from the bundle is treated as data: nothing here is sent to an LLM, and
text is length-capped and stripped of control characters.
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

MAX_ENTRIES = 500
MAX_TEXT_LENGTH = 256

DROPPED_FOR_PRIVACY = frozenset({"Patient", "Practitioner", "PractitionerRole", "RelatedPerson", "Person"})

_EXCLUDED_STATUS = {
    "Condition": {"entered-in-error", "refuted"},
    "Procedure": {"entered-in-error", "not-done"},
    "MedicationRequest": {"entered-in-error", "cancelled"},
    "MedicationStatement": {"entered-in-error", "not-taken"},
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


class FhirBundleError(ValueError):
    """The payload is not a FHIR Bundle this importer can read."""


class ImportedEntity(BaseModel):
    entity_type: str
    name: str
    value: Optional[str] = None
    meta: Dict[str, Any] = Field(default_factory=dict)


class FhirImportResult(BaseModel):
    bundle_type: Optional[str] = None
    record_types: List[str] = Field(default_factory=list)
    entities: List[ImportedEntity] = Field(default_factory=list)
    admission_date: Optional[str] = None
    discharge_date: Optional[str] = None
    skipped: Dict[str, int] = Field(default_factory=dict)
    dropped_for_privacy: Dict[str, int] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


def _clean_text(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    kept = "".join(ch for ch in value if unicodedata.category(ch) not in ("Cc", "Cs", "Co") or ch in "\t\n")
    collapsed = re.sub(r"\s+", " ", kept).strip()
    return collapsed[:MAX_TEXT_LENGTH] or None


def _concept(concept: Any) -> Tuple[Optional[str], List[Dict[str, str]]]:
    if not isinstance(concept, dict):
        return None, []
    codings = []
    display = None
    for coding in concept.get("coding") or []:
        if not isinstance(coding, dict):
            continue
        system, code = _clean_text(coding.get("system")), _clean_text(coding.get("code"))
        if code:
            codings.append({"system": system or "", "code": code})
        display = display or _clean_text(coding.get("display"))
    return _clean_text(concept.get("text")) or display, codings[:5]


def _status_code(resource: Dict[str, Any]) -> Optional[str]:
    if resource.get("resourceType") == "Condition":
        _, codings = _concept(resource.get("verificationStatus"))
        return codings[0]["code"] if codings else None
    return _clean_text(resource.get("status"))


def _date(value: Any) -> Optional[str]:
    text = _clean_text(value)
    return text[:10] if text and _DATE_RE.match(text) else None


def _bump(counter: Dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def parse_fhir_bundle(bundle: Any, source_label: str = "abdm_fhir_import") -> FhirImportResult:
    if not isinstance(bundle, dict) or bundle.get("resourceType") != "Bundle":
        raise FhirBundleError("payload is not a FHIR Bundle")
    entries = bundle.get("entry")
    if not isinstance(entries, list):
        raise FhirBundleError("Bundle has no entry list")
    if len(entries) > MAX_ENTRIES:
        raise FhirBundleError(f"Bundle has more than {MAX_ENTRIES} entries")

    result = FhirImportResult(bundle_type=_clean_text(bundle.get("type")))
    resources: List[Dict[str, Any]] = []
    index: Dict[str, Dict[str, Any]] = {}

    for entry in entries:
        resource = entry.get("resource") if isinstance(entry, dict) else None
        if not isinstance(resource, dict) or not isinstance(resource.get("resourceType"), str):
            _bump(result.skipped, "malformed_entry")
            continue
        resources.append(resource)
        rid = resource.get("id")
        if isinstance(rid, str):
            index[f"{resource['resourceType']}/{rid}"] = resource
        full_url = entry.get("fullUrl")
        if isinstance(full_url, str):
            index[full_url] = resource

    if result.skipped.get("malformed_entry"):
        result.warnings.append(f"{result.skipped['malformed_entry']} malformed bundle entries were skipped.")

    def resolve(reference: Any) -> Optional[Dict[str, Any]]:
        ref = reference.get("reference") if isinstance(reference, dict) else None
        return index.get(ref) if isinstance(ref, str) else None

    meta_base = {"source": "abdm_fhir", "source_file": source_label}
    hospitals: List[str] = []
    encounter_periods: List[Tuple[Optional[str], Optional[str]]] = []
    code_only = 0

    for resource in resources:
        rtype = resource["resourceType"]

        if rtype in DROPPED_FOR_PRIVACY:
            _bump(result.dropped_for_privacy, rtype)
            continue

        if rtype in _EXCLUDED_STATUS and _status_code(resource) in _EXCLUDED_STATUS[rtype]:
            _bump(result.skipped, f"{rtype}:{_status_code(resource)}")
            continue

        if rtype == "Composition":
            title = _clean_text(resource.get("title")) or _concept(resource.get("type"))[0]
            if title:
                result.record_types.append(title)
            custodian = resolve(resource.get("custodian"))
            if custodian and custodian.get("resourceType") == "Organization":
                name = _clean_text(custodian.get("name"))
                if name:
                    hospitals.append(name)
            continue

        if rtype in ("Condition", "Procedure"):
            name, codings = _concept(resource.get("code"))
            if not name:
                code_only += 1
                continue
            meta = {**meta_base, "fhir_resource": rtype, "codings": codings}
            if rtype == "Procedure":
                performed = _date(resource.get("performedDateTime")) or _date(
                    (resource.get("performedPeriod") or {}).get("start") if isinstance(resource.get("performedPeriod"), dict) else None
                )
                if performed:
                    meta["performed_date"] = performed
            result.entities.append(
                ImportedEntity(entity_type="diagnosis" if rtype == "Condition" else "procedure", name=name, value=name, meta=meta)
            )
            continue

        if rtype in ("MedicationRequest", "MedicationStatement"):
            concept = resource.get("medicationCodeableConcept")
            if concept is None:
                medication = resolve(resource.get("medicationReference"))
                concept = medication.get("code") if medication else None
            name, codings = _concept(concept)
            if not name:
                code_only += 1
                continue
            dosage_list = resource.get("dosageInstruction" if rtype == "MedicationRequest" else "dosage") or []
            dosage = _clean_text(dosage_list[0].get("text")) if dosage_list and isinstance(dosage_list[0], dict) else None
            meta = {**meta_base, "fhir_resource": rtype, "codings": codings}
            if dosage:
                meta["dosage"] = dosage
            result.entities.append(ImportedEntity(entity_type="medicine", name=name, value=None, meta=meta))
            continue

        if rtype == "Encounter":
            period = resource.get("period") if isinstance(resource.get("period"), dict) else {}
            encounter_periods.append((_date(period.get("start")), _date(period.get("end"))))
            provider = resolve(resource.get("serviceProvider"))
            if provider and provider.get("resourceType") == "Organization":
                name = _clean_text(provider.get("name"))
                if name:
                    hospitals.append(name)
            continue

        if rtype in ("Organization", "Medication"):
            continue  # read only through references

        _bump(result.skipped, rtype)

    if code_only:
        result.warnings.append(
            f"{code_only} coded entries had no human-readable name and were not imported "
            "(names are never invented from codes)."
        )

    for name in dict.fromkeys(hospitals):
        result.entities.append(
            ImportedEntity(entity_type="hospital", name=name, value=name, meta={**meta_base, "fhir_resource": "Organization"})
        )

    distinct_periods = {p for p in encounter_periods if p != (None, None)}
    if len(distinct_periods) == 1:
        result.admission_date, result.discharge_date = next(iter(distinct_periods))
    elif len(distinct_periods) > 1:
        result.warnings.append(
            "The bundle contains several encounters with different dates; admission and "
            "discharge dates were not set."
        )

    return result
