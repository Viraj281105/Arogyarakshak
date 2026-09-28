"""
Deterministic demo fixtures for the clinical-review layer (ADR-011).

Only reachable when CLINICAL_DEMO_MODE is on AND the caller holds the governance key.
Every record is flagged is_demo and labelled as a fixture: demo reviewers are
DEMO_VERIFIED ("not checked against any real registry"), the demo playbook's provenance
says it is illustrative, and the demo safety rules name their published source by title
only, for a real board to verify before any real use.

Re-running the seed rotates the demo credentials (they are shown once per run) and does
not duplicate records.
"""

from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from kadi.clinical_review.verification import DEMO_VERIFICATION_SOURCE

from app.clinical import safety_service
from app.clinical.auth import generate_credential
from app.daavisetu_playbooks import create_playbook
from app.models import DaaviSetuInstitution, DaaviSetuPlaybook, KadiClinicalReviewer, KadiSafetyRule

DEMO_AUTHORITY = "Demo fixture — not a real medical or pharmacy council"

DEMO_REVIEWERS: List[Dict[str, Any]] = [
    {
        "key": "clinician_a",
        "name": "Dr. Demo Clinician A",
        "category": "DOCTOR",
        "designation": "Consultant surgeon (demo persona)",
        "specialty": "General Surgery",
        "registration_number": "DEMO-0001",
        "verification_status": "DEMO_VERIFIED",
        "board": True,
    },
    {
        "key": "clinician_b",
        "name": "Dr. Demo Clinician B",
        "category": "DOCTOR",
        "designation": "Consultant physician (demo persona)",
        "specialty": "Internal Medicine",
        "registration_number": "DEMO-0002",
        "verification_status": "DEMO_VERIFIED",
        "board": True,
    },
    {
        "key": "pharmacist",
        "name": "Demo Pharmacist",
        "category": "PHARMACIST",
        "designation": "Registered pharmacist (demo persona)",
        "specialty": None,
        "registration_number": "DEMO-PH-0003",
        "verification_status": "SELF_DECLARED",
        "board": False,
    },
    {
        "key": "transcriptionist",
        "name": "Demo Medical Transcriptionist",
        "category": "MEDICAL_TRANSCRIPTIONIST",
        "designation": "Medical transcriptionist (demo persona)",
        "specialty": None,
        "registration_number": None,
        "verification_status": "UNVERIFIED",
        "board": False,
    },
]

EMERGENCY_MESSAGE = (
    "Some words in your documents match emergency warning signs. If this is happening now, "
    "call 108 or go to the nearest emergency department immediately. Billing and insurance "
    "questions can wait."
)

DEMO_RULES: List[Dict[str, Any]] = [
    {
        "rule_key": "demo-stroke-fast-signs",
        "title": "Possible stroke warning signs (FAST)",
        "description": (
            "Adapts the FAST stroke warning-sign mnemonic (Face drooping, Arm weakness, Speech "
            "difficulty, Time to call emergency services) to ArogyaRakshak's administrative "
            "context: if case documents mention these signs, show an emergency-care prompt "
            "before any billing workflow."
        ),
        "trigger": {
            "match_any": ["facial droop", "face drooping", "arm weakness", "slurred speech", "speech difficulty"],
            "context_types": ["document_text", "diagnosis"],
        },
        "action": {"type": "SHOW_SAFETY_ESCALATION", "severity": "URGENT", "message": EMERGENCY_MESSAGE},
        "source_name": "F.A.S.T. stroke warning-sign mnemonic (public stroke-awareness education material)",
        "source_reference": "Referenced by title only. A governance board must verify wording against the current published source before real use.",
        "source_version": "Title reference only",
        "source_section": "Warning signs",
        "limitations": "Covers only the FAST warning signs. It does not assess stroke risk and cannot rule stroke out.",
    },
    {
        "rule_key": "demo-emergency-signs-etat",
        "title": "Emergency signs (adapted from WHO ETAT)",
        "description": (
            "Adapts the emergency signs of the WHO Emergency Triage Assessment and Treatment "
            "(ETAT) approach to ArogyaRakshak's administrative context: if case documents "
            "mention these signs, show an emergency-care prompt before any billing workflow."
        ),
        "trigger": {
            "match_any": ["convulsion", "convulsions", "seizure", "unconscious", "unresponsive",
                          "not breathing", "central cyanosis", "severe respiratory distress"],
            "context_types": ["document_text", "diagnosis"],
        },
        "action": {"type": "SHOW_SAFETY_ESCALATION", "severity": "URGENT", "message": EMERGENCY_MESSAGE},
        "source_name": "WHO Emergency Triage Assessment and Treatment (ETAT) — emergency signs",
        "source_reference": "Referenced by title only. A governance board must verify against the current WHO guidance before real use.",
        "source_version": "WHO paediatric ETAT guidance (title reference only)",
        "source_section": "Emergency signs",
        "limitations": (
            "ETAT emergency signs are defined for children and require hands-on clinical triage. "
            "A keyword in a document is not triage."
        ),
    },
]

DEMO_PLAYBOOK = {
    "playbook_key": "demo-lap-cholecystectomy",
    "title": "Laparoscopic cholecystectomy — documentation checklist (demo)",
    "insurer": "Demo Health Insurer (fictional)",
    "policy_product": None,
    "procedure_category": "Laparoscopic cholecystectomy",
    "items": [
        {
            "item_id": "pb_usg_abdomen",
            "label": "Ultrasound (USG) abdomen report",
            "evidence_rule": {"kind": "document_keywords", "keywords": ["usg", "ultrasound"]},
        },
        {
            "item_id": "pb_lft_report",
            "label": "Liver function test report",
            "evidence_rule": {"kind": "document_keywords", "keywords": ["lft", "liver function"]},
        },
        {
            "item_id": "pb_conservative_management",
            "label": "Documentation of conservative management tried",
            "evidence_rule": {"kind": "document_keywords", "keywords": ["conservative", "analgesic", "antispasmodic"]},
            "clinical_fact": True,
            "clinical_fact_question": (
                "Do the records you reviewed document conservative management tried before "
                "surgery? Confirm only what the records show."
            ),
        },
    ],
    "commonly_requested_evidence": ["Surgeon's admission note", "Itemised cost estimate"],
    "internal_notes": "Demo fixture for walkthroughs.",
    "source_provenance": "Demo fixture — illustrative only, not real insurer guidance",
    "owner": "Demo insurance desk lead",
}


async def _demo_reviewer(db: AsyncSession, spec: Dict[str, Any]) -> "tuple[KadiClinicalReviewer, str]":
    token, token_hash = generate_credential()
    row = await db.execute(
        select(KadiClinicalReviewer).where(
            KadiClinicalReviewer.name == spec["name"], KadiClinicalReviewer.is_demo.is_(True)
        )
    )
    reviewer = row.scalar_one_or_none()
    if reviewer is None:
        reviewer = KadiClinicalReviewer(
            id=f"REV-demo-{spec['key'].replace('_', '')[:10]}",
            name=spec["name"],
            category=spec["category"],
            designation=spec["designation"],
            specialty=spec["specialty"],
            registration_number=spec["registration_number"],
            registration_authority=DEMO_AUTHORITY if spec["registration_number"] else None,
            verification_status=spec["verification_status"],
            verification_source=DEMO_VERIFICATION_SOURCE if spec["verification_status"] == "DEMO_VERIFIED" else None,
            verification_timestamp=datetime.utcnow() if spec["verification_status"] == "DEMO_VERIFIED" else None,
            affiliation="Demo fixture",
            is_safety_board_member=spec["board"],
            is_demo=True,
            credential_hash=token_hash,
        )
        db.add(reviewer)
    else:
        reviewer.credential_hash = token_hash
        reviewer.is_active = True
    return reviewer, token


async def seed_demo(db: AsyncSession) -> Dict[str, Any]:
    reviewers: Dict[str, Any] = {}
    objs: Dict[str, KadiClinicalReviewer] = {}
    for spec in DEMO_REVIEWERS:
        reviewer, token = await _demo_reviewer(db, spec)
        objs[spec["key"]] = reviewer
        reviewers[spec["key"]] = {"reviewer_id": reviewer.id, "name": reviewer.name, "reviewer_token": token}
    await db.flush()

    today = date.today()
    rules_out = []
    for spec in DEMO_RULES:
        exists = await db.execute(select(KadiSafetyRule).where(KadiSafetyRule.rule_key == spec["rule_key"]))
        if exists.scalars().first():
            continue
        data = {**spec, "effective_date": today - timedelta(days=1), "review_due_date": today + timedelta(days=180), "changelog": "Initial demo version."}
        rule = await safety_service.create_rule(db, objs["clinician_a"], data, is_demo=True)
        await db.flush()
        await safety_service.submit_rule(db, objs["clinician_a"], rule)
        await db.flush()
        await safety_service.decide_rule(db, objs["clinician_b"], rule, "APPROVE", "Demo approval.")
        await db.flush()
        await safety_service.activate_rule(db, objs["clinician_a"], rule)
        rules_out.append({"rule_id": rule.id, "rule_key": rule.rule_key, "status": rule.status})

    inst_token, inst_hash = generate_credential()
    row = await db.execute(select(DaaviSetuInstitution).where(DaaviSetuInstitution.is_demo.is_(True)))
    institution = row.scalars().first()
    if institution is None:
        institution = DaaviSetuInstitution(
            id="INST-demo-desk", name="Demo Hospital Insurance Desk", credential_hash=inst_hash, is_demo=True
        )
        db.add(institution)
        await db.flush()
    else:
        institution.credential_hash = inst_hash
    pb_row = await db.execute(
        select(DaaviSetuPlaybook).where(
            DaaviSetuPlaybook.institution_id == institution.id,
            DaaviSetuPlaybook.playbook_key == DEMO_PLAYBOOK["playbook_key"],
            DaaviSetuPlaybook.status == "ACTIVE",
        )
    )
    playbook = pb_row.scalars().first()
    if playbook is None:
        playbook = await create_playbook(
            db, institution,
            {**DEMO_PLAYBOOK, "effective_date": today - timedelta(days=1), "review_due_date": today + timedelta(days=180)},
            status_value="ACTIVE",
        )
        playbook.activated_at = datetime.utcnow()

    await db.commit()
    return {
        "warning": "DEMO FIXTURES ONLY. Demo reviewers are not real clinicians and demo rules are not a real governance decision.",
        "reviewers": reviewers,
        "institution": {"institution_id": institution.id, "name": institution.name, "institution_token": inst_token},
        "playbook_id": playbook.id,
        "safety_rules_created": rules_out,
    }
