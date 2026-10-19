"""Claim Pack builder (ADR-015): one in-memory ZIP that stitches the modules' results for a case.

Pure functions only: the endpoint (app.api.v1.endpoints.claim_pack) gathers already-stored
and deterministic data and hands it here as plain dicts; this module renders text and
assembles the ZIP in memory. Nothing is written to disk, and the original uploaded
documents are never an input (they are not retained anywhere — ADR-003), so they cannot
appear in the pack. A section with no data says so in plain words ("not available for this
case") instead of inventing content, and the manifest states exactly what is and is not in
the pack, with a provenance class for every section.
"""

import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

NOT_AVAILABLE = "Not available for this case"

# Provenance classes used in the manifest. These describe HOW a section's content came to
# exist, so a helper reading the pack can tell a machine reading of a scan from a fact a
# named human settled.
OCR_EXTRACTED = "OCR_EXTRACTED"  # machine-read from an uploaded document; may contain reading errors
HUMAN_REVIEWED = "HUMAN_REVIEWED"  # a named reviewer or independent transcription settled it
RULE_COMPUTED = "RULE_COMPUTED"  # deterministic comparison against a published reference table
USER_ENTERED = "USER_ENTERED"  # typed in by the person themselves
AI_DRAFTED = "AI_DRAFTED"  # a draft written by software; the person must read it before use

PROVENANCE_DEFINITIONS = {
    OCR_EXTRACTED: "Read automatically from an uploaded document. May contain reading errors.",
    HUMAN_REVIEWED: "A named human reviewer, or an independent human transcription, settled this.",
    RULE_COMPUTED: "Computed by fixed rules against a published reference table. Not a legal or clinical finding.",
    USER_ENTERED: "Typed in by the patient or caregiver themselves.",
    AI_DRAFTED: "A draft written by software. Read and edit it yourself before using it.",
}

PACK_DISCLAIMER = (
    "This pack is paperwork support. It does not interpret clinical values, give medical advice, "
    "or predict whether any claim will be approved. Every figure comes from the case's stored "
    "records; where something is missing it says so."
)


@dataclass
class ClaimPackInput:
    case_id: str
    generated_at: datetime
    readiness_text: Optional[str] = None
    readiness_summary: Optional[Dict[str, Any]] = None
    grievances: List[Dict[str, Any]] = field(default_factory=list)
    audit: Optional[Dict[str, Any]] = None
    appeal_letter: Optional[str] = None
    medicines: List[Dict[str, Any]] = field(default_factory=list)
    preauth_pdf: Optional[bytes] = None
    claim_id: Optional[str] = None


@dataclass
class _Section:
    key: str
    filename: str
    title: str
    included: bool
    provenance: List[str]
    summary: str
    body: str


def _na(reason: str) -> str:
    return f"{NOT_AVAILABLE}.\n{reason}\n"


def _money(value: Optional[float]) -> str:
    return "not available" if value is None else f"Rs {value:,.2f}"


def _checklist_section(data: ClaimPackInput) -> _Section:
    if not data.readiness_text:
        return _Section(
            "documentation_checklist", "01_documentation_checklist.txt", "Documentation checklist", False, [],
            f"{NOT_AVAILABLE}: the checklist could not be built for this case.",
            _na("The documentation checklist could not be built from this case's records."),
        )
    s = data.readiness_summary or {}
    provenance = [OCR_EXTRACTED]
    if s.get("reviewer_decisions"):
        provenance.append(HUMAN_REVIEWED)
    summary = (
        f"{s.get('present', 0)} present, {s.get('missing', 0)} missing, "
        f"{s.get('needs_clinical_confirmation', 0)} need a doctor's confirmation, "
        f"{s.get('reviewer_decisions', 0)} settled by a named reviewer."
    )
    body = (
        "DOCUMENTATION CHECKLIST (paperwork only)\n"
        "PRESENT = a matching document or detail was found in this case's records.\n"
        "MISSING = nothing matching was found; you may need to obtain or add it.\n"
        "NEEDS_CLINICAL_CONFIRMATION = only a doctor can say whether this applies; the software does not decide.\n\n"
        + data.readiness_text
        + "\n"
    )
    return _Section("documentation_checklist", "01_documentation_checklist.txt", "Documentation checklist", True, provenance, summary, body)


def _timeline_section(data: ClaimPackInput) -> _Section:
    if not data.grievances:
        return _Section(
            "deadline_timeline", "02_deadline_timeline.txt", "Statutory deadline timeline", False, [],
            f"{NOT_AVAILABLE}: no BimaNyay grievance tracker is linked to this case.",
            _na(
                "No insurer grievance has been tracked for this case, so there are no deadlines to list. "
                "Start the tracker in BimaNyay with this case to get them."
            ),
        )
    lines = ["STATUTORY DEADLINE TIMELINE (from the BimaNyay tracker)", ""]
    event_count = 0
    for g in data.grievances:
        lines.append(f"Insurer: {g['insurer_name']}")
        if g.get("claim_number"):
            lines.append(f"Claim number: {g['claim_number']}")
        lines.append(f"Grievance started: {g['date_initiated']}    Current tier: {g['current_tier']}")
        for e in g["events"]:
            event_count += 1
            lines.append(f"  - [{e['status']}] {e['title']} -- by {e['deadline_date']} ({e['tier']})")
            lines.append(f"      {e['instructions']}")
        if not g["events"]:
            lines.append(f"  {NOT_AVAILABLE}: no milestone dates were stored for this grievance.")
        lines.append("")
    lines.append(
        "Dates are those stored when the tracker was started. Check them against the insurer's "
        "letters; they are reminders, not legal advice."
    )
    return _Section(
        "deadline_timeline", "02_deadline_timeline.txt", "Statutory deadline timeline", True,
        [USER_ENTERED, RULE_COMPUTED],
        f"{len(data.grievances)} grievance(s), {event_count} milestone(s).", "\n".join(lines) + "\n",
    )


def _audit_section(data: ClaimPackInput) -> _Section:
    a = data.audit
    if not a:
        return _Section(
            "bill_audit", "03_bill_audit.txt", "Hospital bill audit", False, [],
            f"{NOT_AVAILABLE}: no bill line items were extracted for this case.",
            _na("No hospital bill line items are stored for this case, so there is nothing to compare."),
        )
    lines = [
        "HOSPITAL BILL AUDIT (billed amounts vs CGHS reference rates)",
        "A line 'above reference' is a question to put to the hospital, not proof of overcharging.",
        "",
        f"Total charged on the bill lines: {_money(a.get('total_charged'))}",
        f"Lines compared with a reference rate: {a.get('benchmarked_count', 0)}",
        f"Lines above their reference: {a.get('deviations_count', 0)}",
        f"Lines with no usable reference (not checked): {a.get('unmatched_count', 0)} "
        f"({_money(a.get('unmatched_amount'))})",
        "",
    ]
    for it in a.get("audit_items", []):
        label = {
            "overcharged": "ABOVE REFERENCE",
            "within_benchmark": "WITHIN REFERENCE",
            "bundled": "NORMALLY INCLUDED IN ANOTHER CHARGE",
            "not_benchmarked": "NOT CHECKED",
        }.get(it["status"], it["status"])
        lines.append(f"- {it['item_name']}: charged {_money(it['charged'])} -- {label}")
        if it.get("cghs_benchmark") is not None:
            lines.append(f"    reference {_money(it['cghs_benchmark'])}" + (f" ({it['benchmark_basis']})" if it.get("benchmark_basis") else ""))
        if it.get("not_benchmarked_reason"):
            lines.append(f"    why not checked: {it['not_benchmarked_reason']}")
    return _Section(
        "bill_audit", "03_bill_audit.txt", "Hospital bill audit", True, [OCR_EXTRACTED, RULE_COMPUTED],
        f"{a.get('benchmarked_count', 0)} line(s) compared, {a.get('deviations_count', 0)} above reference, "
        f"{a.get('unmatched_count', 0)} not checked.",
        "\n".join(lines) + "\n",
    )


def _appeal_section(data: ClaimPackInput) -> _Section:
    if not data.appeal_letter:
        return _Section(
            "appeal_draft", "04_appeal_draft.txt", "Appeal draft", False, [],
            f"{NOT_AVAILABLE}: no appeal has been drafted for this case (none was generated for this pack).",
            _na("No appeal letter has been drafted for this case. This pack never drafts one on its own."),
        )
    body = (
        "APPEAL DRAFT (drafted earlier in BillNyay; not changed by this pack)\n"
        "Read, correct and sign it yourself before sending it anywhere.\n\n"
        + data.appeal_letter
        + "\n"
    )
    return _Section("appeal_draft", "04_appeal_draft.txt", "Appeal draft", True, [AI_DRAFTED], "1 appeal draft.", body)


def _medicine_section(data: ClaimPackInput) -> _Section:
    if not data.medicines:
        return _Section(
            "medicine_price_check", "05_medicine_price_check.txt", "Medicine price check", False, [],
            f"{NOT_AVAILABLE}: no medicines were extracted for this case.",
            _na("No medicines are stored for this case, so there are no price-check rows."),
        )
    lines = [
        "MEDICINE PRICE CHECK (DawaCheck, vs NPPA reference ceiling prices)",
        "The reference list is a subset; a medicine missing from it is not necessarily uncontrolled.",
        "A medicine whose name was unclear on the scan is listed but was NOT price-checked.",
        "",
    ]
    checked = held = reviewed = 0
    for m in data.medicines:
        b = m.get("benchmark")
        prov = m.get("name_provenance") or "AI_DERIVED"
        if prov == "HUMAN_REVIEWED":
            reviewed += 1
        name_note = "name confirmed by a human" if prov == "HUMAN_REVIEWED" else "name read from the scan"
        if b is None:
            held += 1
            lines.append(f"- {m['brand_name']} ({name_note}): NOT PRICE-CHECKED")
            if m.get("note"):
                lines.append(f"    {m['note']}")
            continue
        checked += 1
        if b.get("comparison_status") == "COMPARED":
            verdict = "ABOVE REFERENCE CEILING" if b.get("is_overcharged") else "WITHIN REFERENCE CEILING"
            lines.append(f"- {m['brand_name']} ({name_note}): {verdict}")
            lines.append(
                f"    billed {_money(b.get('billed_unit_price'))} per {b.get('unit_label', 'unit')}; "
                f"ceiling {_money(b.get('nppa_ceiling_price'))}; basis: {b.get('price_basis_label', 'not stated')}"
            )
        else:
            lines.append(f"- {m['brand_name']} ({name_note}): NO COMPARISON POSSIBLE")
            lines.append(f"    {b.get('comparison_note') or 'The billed price has no comparable per-unit basis.'}")
        lines.append(f"    reference: {b.get('data_source', 'not stated')}")
    prov_classes = [OCR_EXTRACTED, RULE_COMPUTED] + ([HUMAN_REVIEWED] if reviewed else [])
    return _Section(
        "medicine_price_check", "05_medicine_price_check.txt", "Medicine price check", True, prov_classes,
        f"{len(data.medicines)} medicine(s): {checked} matched to a reference, {held} not price-checked, "
        f"{reviewed} with a human-confirmed name.",
        "\n".join(lines) + "\n",
    )


def _preauth_section(data: ClaimPackInput) -> _Section:
    if not data.preauth_pdf:
        return _Section(
            "preauth_form", "preauth_form.pdf", "Pre-authorization form", False, [],
            f"{NOT_AVAILABLE}: no pre-authorization claim was submitted for this case.", "",
        )
    return _Section(
        "preauth_form", "preauth_form.pdf", "Pre-authorization form", True, [USER_ENTERED],
        f"Form generated from the claim details entered for {data.claim_id}.", "",
    )


def _sections(data: ClaimPackInput) -> List[_Section]:
    return [
        _checklist_section(data),
        _timeline_section(data),
        _audit_section(data),
        _appeal_section(data),
        _medicine_section(data),
        _preauth_section(data),
    ]


def _readme(data: ClaimPackInput, sections: List[_Section]) -> str:
    lines = [
        "AROGYARAKSHAK -- CLAIM PACK",
        f"Case: {data.case_id}",
        f"Prepared: {data.generated_at.strftime('%d-%b-%Y %H:%M')}",
        "",
        "WHO THIS IS FOR",
        "A patient has shared this pack with you (a family member, caregiver, insurance agent or hospital",
        "help desk) so you can help with their paperwork. It gathers what ArogyaRakshak worked out for",
        "this one case.",
        "",
        "WHAT IS IN IT",
    ]
    for s in sections:
        mark = "included" if s.included else "not available for this case"
        lines.append(f"  {s.filename}: {s.title} -- {mark}")
    lines += [
        "  manifest.txt / manifest.json: exactly what is and is not in this pack, and where each part came from",
        "",
        "HOW TO READ IT",
        "  1. Start with 01_documentation_checklist.txt: it lists the papers that look present, those that",
        "     look missing, and the points only a doctor can confirm.",
        "  2. Then 02_deadline_timeline.txt for dates the insurer must respond by.",
        "  3. The bill audit, appeal draft and medicine price check are questions to raise, not verdicts.",
        "",
        "WHAT THIS PACK DOES NOT DO",
        f"  {PACK_DISCLAIMER}",
        "  It does not contain the patient's original documents (bills, prescriptions, reports). The",
        "  patient's own copies are needed for any submission. ArogyaRakshak does not keep uploaded files.",
        "",
        "Sections marked 'not available for this case' mean no record exists for that part. Nothing has",
        "been guessed or filled in.",
    ]
    return "\n".join(lines) + "\n"


def _manifest(data: ClaimPackInput, sections: List[_Section]) -> Dict[str, Any]:
    used = sorted({p for s in sections for p in s.provenance})
    return {
        "pack_version": 1,
        "case_id": data.case_id,
        "generated_at": data.generated_at.isoformat(timespec="seconds"),
        "files": [
            {
                "section": s.key,
                "file": s.filename,
                "title": s.title,
                "included": s.included,
                "summary": s.summary,
                "provenance": s.provenance,
            }
            for s in sections
        ],
        "not_included": [
            "The patient's original uploaded documents (bills, prescriptions, reports, letters): "
            "ArogyaRakshak does not retain them, so they cannot be part of the pack.",
            "Any clinical interpretation or prediction of claim approval.",
            "Anything marked 'not available for this case'.",
        ],
        "provenance_classes": {k: PROVENANCE_DEFINITIONS[k] for k in used},
        "disclaimer": PACK_DISCLAIMER,
    }


def _manifest_text(manifest: Dict[str, Any]) -> str:
    lines = [
        "ArogyaRakshak -- Claim Pack Manifest",
        f"Case: {manifest['case_id']}",
        f"Generated: {manifest['generated_at']}",
        "",
        "SECTIONS",
    ]
    for f in manifest["files"]:
        status = "INCLUDED" if f["included"] else "NOT AVAILABLE FOR THIS CASE"
        lines.append(f"- {f['file']} ({f['title']}): {status}")
        lines.append(f"    {f['summary']}")
        if f["provenance"]:
            lines.append(f"    provenance: {', '.join(f['provenance'])}")
    lines += ["", "NOT INCLUDED"] + [f"- {x}" for x in manifest["not_included"]]
    lines += ["", "PROVENANCE CLASSES USED"] + [f"- {k}: {v}" for k, v in manifest["provenance_classes"].items()]
    lines += ["", manifest["disclaimer"]]
    return "\n".join(lines) + "\n"


def build_claim_pack_zip(data: ClaimPackInput) -> bytes:
    """Assembles the claim pack ZIP entirely in memory and returns its bytes."""
    sections = _sections(data)
    manifest = _manifest(data, sections)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", _readme(data, sections))
        for s in sections:
            if s.key == "preauth_form":
                if s.included and data.preauth_pdf:
                    zf.writestr(s.filename, data.preauth_pdf)
                continue
            zf.writestr(s.filename, s.body)
        zf.writestr("manifest.txt", _manifest_text(manifest))
        zf.writestr("manifest.json", json.dumps(manifest, indent=2))
    return buffer.getvalue()
