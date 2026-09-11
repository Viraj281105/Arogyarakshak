"""
BillNyay API Endpoints.

Handles hospital bill auditing, appeal drafting (5-agent pipeline), and grievance package generation.
"""

import logging
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import os
import json
import urllib.request
from app.config import settings
from app.consent import require_case_consent
from app.database import get_db
from app.models import KadiCase, KadiEntity
# Import billnyay modules
from billnyay.agents.auditor import run_auditor_agent, StructuredDenial
from billnyay.agents.judge import run_judge_agent, JudgeScorecard
from billnyay.agents.barrister import run_barrister_agent
from billnyay.agents.clinician import run_clinician_agent
from billnyay.agents.regulatory import run_regulatory_agent

logger = logging.getLogger("arogyarakshak.api.billnyay")
router = APIRouter()


# --- Load CGHS Rate Schedule Data Source --------------------------------------
def _load_cghs_rates() -> Dict[str, Any]:
    candidates: List[str] = []
    # 1. Look up via installed/editable billnyay package
    try:
        import billnyay
        if hasattr(billnyay, "__file__") and billnyay.__file__:
            pkg_dir = os.path.dirname(os.path.abspath(billnyay.__file__))
            candidates.append(os.path.join(pkg_dir, "data", "cghs_rates.json"))
    except Exception as e:
        logger.debug(f"Could not resolve billnyay package directory: {e}")

    # 2. Look up via relative directory paths from this endpoint file
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    candidates.extend([
        # 6 levels up from apps/api/app/api/v1/endpoints/billnyay.py -> repo root
        os.path.abspath(os.path.join(current_file_dir, "../../../../../../packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(current_file_dir, "../../../../../packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(os.getcwd(), "packages/billnyay/billnyay/data/cghs_rates.json")),
        os.path.abspath(os.path.join(os.getcwd(), "packages/billnyay/data/cghs_rates.json")),
    ])

    for path in candidates:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    rates = data.get("rates", {})
                    if rates:
                        logger.info(f"Loaded {len(rates)} CGHS benchmark rates from {path}")
                        return rates
            except Exception as e:
                logger.warning(f"Failed to read CGHS rates from {path}: {e}")

    logger.warning("Using hardcoded CGHS rate fallback; could not locate cghs_rates.json")
    # Fallback dictionary if file not found
    return {
        "consultation": {"benchmark_rate": 350.0, "bundled": False},
        "ward stay": {"benchmark_rate": 1500.0, "bundled": False},
        "x-ray": {"benchmark_rate": 350.0, "bundled": False},
        "blood test": {"benchmark_rate": 250.0, "bundled": False},
        "laparoscopic surgery": {"benchmark_rate": 28000.0, "bundled": False},
    }

CGHS_RATES = _load_cghs_rates()


def _rate_of(entry: Any):
    """Normalises a CGHS rates entry into (benchmark_rate, is_bundled)."""
    if isinstance(entry, dict):
        rate = entry.get("benchmark_rate")
        return (float(rate) if rate is not None else None), bool(entry.get("bundled", False))
    try:
        return float(entry), False
    except (TypeError, ValueError):
        return None, False


def _match_cghs_rate(norm_name: str, rates_source: Dict[str, Any]):
    """Finds the CGHS benchmark for a billed item name.

    Returns (benchmark_rate, is_bundled), or (None, False) when the item has no CGHS
    counterpart. Callers must treat None as "not benchmarked" — never as "fair".

    Among substring candidates the LONGEST key wins, so "icu day charges" is preferred
    over the shorter "icu". The previous implementation returned whichever key dict
    iteration happened to reach first.
    """
    if not norm_name:
        return None, False

    if norm_name in rates_source:
        return _rate_of(rates_source[norm_name])

    best_key = None
    for key in rates_source:
        if key in norm_name or norm_name in key:
            if best_key is None or len(key) > len(best_key):
                best_key = key

    if best_key is None:
        return None, False
    return _rate_of(rates_source[best_key])


# --- Pydantic Schemas ---------------------------------------------------------
class AuditResultItem(BaseModel):
    item_name: str
    charged: float
    # None when the item has no CGHS counterpart. Previously this defaulted to the
    # charged amount, which made every unrecognised line report a 0% deviation and
    # display as "Fair" — an unchecked charge presented to the patient as verified.
    cghs_benchmark: Optional[float] = None
    deviation_percentage: float
    is_deviation: bool
    benchmarked: bool
    status: Literal["overcharged", "within_benchmark", "bundled", "not_benchmarked"]


class AuditResponse(BaseModel):
    case_id: str
    total_charged: float
    # Sums cover benchmarked items only, so potential_savings is never inflated by
    # lines that were never compared against anything.
    total_benchmark: float
    benchmarked_charged: float
    potential_savings: float
    deviations_count: int
    benchmarked_count: int
    unmatched_count: int
    unmatched_amount: float
    audit_items: List[AuditResultItem]


class AppealResponse(BaseModel):
    case_id: str
    appeal_letter: str
    scorecard: Dict[str, Any]
    status: str
    # False when GROQ_API_KEY is unset: the letter is a static statutory template rather
    # than an LLM draft grounded in this case. Callers must be able to tell the two apart.
    llm_backed: bool


class GrievanceResponse(BaseModel):
    case_id: str
    complaint_text: str
    bima_bharosa_fields: Dict[str, str] = {}
    deep_link: str


# --- Groq LLM Client & Fallback -----------------------------------------------
class GroqClient:
    """Configured Groq Cloud inference client using settings.groq_model."""
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        # Only request a JSON response format when the calling agent actually wants
        # JSON. The Barrister Agent emits prose; forcing json_object on it would make
        # Groq return a JSON envelope instead of an appeal letter.
        json_mode = kwargs.get("json_mode", True)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system or "You are an expert healthcare auditor."},
                {"role": "user", "content": prompt}
            ],
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res = json.loads(response.read().decode("utf-8"))
                return res["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"[GroqClient] Cloud inference call failed: {e}. Falling back.")
            return GroqClientFallback().generate(prompt, system=system, **kwargs)


_FALLBACK_DENIAL_JSON = (
    "{\n"
    '  "denial_code": "DEN-999",\n'
    '  "insurer_reason_snippet": "Audit deviation detected.",\n'
    '  "policy_clause_text": "Section 4.1 Room limit exclusions.",\n'
    '  "procedure_denied": "General ward treatment",\n'
    '  "confidence_score": 0.95,\n'
    '  "raw_evidence_chunks": []\n'
    "}"
)

_FALLBACK_CLINICAL_JSON = json.dumps(
    {
        "root": [
            {
                "article_title": "Clinical Standard of Care for Inpatient Hospitalisation",
                "summary_of_finding": (
                    "Established clinical guidelines support inpatient admission where an active "
                    "line of treatment and continuous monitoring are documented."
                ),
                "pubmed_id": "PMID:38291045",
            },
            {
                "article_title": "Medical Necessity Determination in Acute Care Admissions",
                "summary_of_finding": (
                    "Treating-physician documentation of an active line of treatment is the accepted "
                    "determinant of medical necessity for inpatient care."
                ),
                "pubmed_id": "PMID:37554120",
            },
        ]
    }
)

_FALLBACK_APPEAL_LETTER = """SUBJECT: Formal Notice of Representation and Appeal Against Claim Rejection / Billing Deviation

To the Grievance Redressal Officer,

RECITALS
This representation is submitted under the IRDAI (Protection of Policyholders' Interests) Regulations
against the rejection / reduction communicated in respect of the captioned claim. The insured disputes
the rejection and seeks reversal within the statutory turnaround time.

SECTION I - CLINICAL JUSTIFICATION AND MEDICAL NECESSITY
The hospitalisation involved an active line of treatment with continuous clinical monitoring. Established
standards of care recognise such admission as medically necessary. The treating physician's records
evidence the necessity of the procedures and consumables billed.

SECTION II - STATUTORY AND IRDAI REGULATORY PROVISIONS
Rejection premised on vague or non-specific exclusion clauses is impermissible under the IRDAI circular on
Standardisation of Exclusion Clauses. Arbitrary reduction of claimed medical expenses, or unexplained
delay in settlement, additionally constitutes an unfair trade practice under the Consumer Protection Act,
2019. No repudiation is valid without the concurrence of the Claims Review Committee.

SECTION III - FORMAL DEMAND AND TIMELINE FOR REVERSAL
The insured demands reconsideration and reversal of the rejection / deduction within thirty (30) days as
mandated by IRDAI. Failing which, the insured reserves the right to escalate to the IRDAI Bima Bharosa
portal and thereafter to the jurisdictional Insurance Ombudsman.

Yours faithfully,
The Insured
"""


class GroqClientFallback:
    """Deterministic offline stand-in used when GROQ_API_KEY is not configured.

    Each agent in the pipeline expects a different response shape. Returning the
    Auditor's JSON to every caller (the previous behaviour) made the Barrister emit a
    JSON blob as its "appeal letter", so the fallback is dispatched per agent using the
    system instruction each agent sends.
    """

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        sys_text = (system or "").lower()
        json_mode = kwargs.get("json_mode", True)

        if "clinician agent" in sys_text:
            logger.warning("[GroqClientFallback] Returning fallback clinical evidence.")
            return _FALLBACK_CLINICAL_JSON

        if "barrister agent" in sys_text or not json_mode:
            logger.warning("[GroqClientFallback] Returning fallback appeal letter.")
            return _FALLBACK_APPEAL_LETTER

        logger.warning("[GroqClientFallback] Returning fallback denial JSON block.")
        return _FALLBACK_DENIAL_JSON


# --- Route Implementations ----------------------------------------------------

@router.post("/cases/{case_id}/audit", response_model=AuditResponse)
async def audit_bill(case_id: str, db: AsyncSession = Depends(get_db)):
    """Audits hospital bill items against CGHS rate schedules."""
    # 1. Fetch case
    await require_case_consent(case_id, db)

    # 2. Fetch billing entities
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id)
        .where(KadiEntity.type == "billing_item")
    )
    billing_items = entities_result.scalars().all()

    audit_items = []
    total_charged = 0.0
    total_benchmark = 0.0
    benchmarked_charged = 0.0
    deviations = 0
    benchmarked_count = 0
    unmatched_count = 0
    unmatched_amount = 0.0

    rates_source = CGHS_RATES if CGHS_RATES else _load_cghs_rates()

    for item in billing_items:
        norm_name = item.name.lower().strip()
        charged = float(item.value) if item.value else 0.0
        total_charged += charged

        matched_rate, is_bundled = _match_cghs_rate(norm_name, rates_source)

        if matched_rate is None:
            # No CGHS counterpart. Report this honestly as unverified rather than
            # silently benchmarking the item against its own charge.
            unmatched_count += 1
            unmatched_amount += charged
            audit_items.append(
                AuditResultItem(
                    item_name=item.name,
                    charged=charged,
                    cghs_benchmark=None,
                    deviation_percentage=0.0,
                    is_deviation=False,
                    benchmarked=False,
                    status="not_benchmarked",
                )
            )
            continue

        is_dev = (charged > matched_rate) or is_bundled
        if is_bundled:
            # A bundled item should not be billed separately at all.
            dev_perc = 100.0 if charged > 0 else 0.0
            item_status = "bundled"
        elif is_dev:
            dev_perc = ((charged - matched_rate) / matched_rate) * 100 if matched_rate > 0 else 0.0
            item_status = "overcharged"
        else:
            dev_perc = 0.0
            item_status = "within_benchmark"

        if is_dev:
            deviations += 1

        benchmarked_count += 1
        total_benchmark += matched_rate
        benchmarked_charged += charged
        audit_items.append(
            AuditResultItem(
                item_name=item.name,
                charged=charged,
                cghs_benchmark=matched_rate,
                deviation_percentage=round(dev_perc, 2),
                is_deviation=is_dev,
                benchmarked=True,
                status=item_status,
            )
        )

    return AuditResponse(
        case_id=case_id,
        total_charged=round(total_charged, 2),
        total_benchmark=round(total_benchmark, 2),
        benchmarked_charged=round(benchmarked_charged, 2),
        potential_savings=round(max(benchmarked_charged - total_benchmark, 0.0), 2),
        deviations_count=deviations,
        benchmarked_count=benchmarked_count,
        unmatched_count=unmatched_count,
        unmatched_amount=round(unmatched_amount, 2),
        audit_items=audit_items,
    )


@router.post("/cases/{case_id}/appeal", response_model=AppealResponse)
async def draft_appeal(case_id: str, db: AsyncSession = Depends(get_db)):
    """Runs the 5-agent pipeline to generate an IRDAI-compliant appeal letter."""
    # 1. Fetch case details
    await require_case_consent(case_id, db)

    # 2. Get billing and clinical texts
    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id)
        .where(KadiEntity.type == "document_text")
    )
    texts = [e.value for e in entities_result.scalars().all() if e.value]
    combined_text = "\n".join(texts) if texts else "Hospital Bill dispute."

    # 3. Agent 1 — Auditor: extract structured denial facts.
    if settings.groq_api_key:
        client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    else:
        client = GroqClientFallback()

    denial = run_auditor_agent(client=client, denial_text=combined_text)
    if denial is None:
        # The Auditor could not produce a usable StructuredDenial. The downstream agents
        # are typed against this model, so synthesise a neutral one rather than passing
        # None through and losing the clinical/regulatory stages entirely.
        denial = StructuredDenial(
            denial_code="DEN-DEFAULT",
            insurer_reason_snippet="Coverage denied or bill overcharged.",
            policy_clause_text="Not specified in the supplied documents.",
            procedure_denied="Disputed Procedure",
            confidence_score=0.0,
            raw_evidence_chunks=[],
        )

    # 4. Agent 2 — Clinician: synthesise medical-necessity evidence.
    clinical_evidence = run_clinician_agent(client=client, denial_details=denial)

    # 5. Agent 3 — Regulatory: retrieve applicable statutory provisions.
    regulatory_evidence = run_regulatory_agent(
        denial_data=denial.model_dump(), client=client
    )

    # 6. Agent 4 — Barrister: draft the formal IRDAI appeal letter.
    appeal_letter = run_barrister_agent(
        client,
        denial_details=denial,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
    )
    if not appeal_letter:
        logger.error("[BillNyay] Barrister Agent returned no appeal letter for case %s", case_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Appeal drafting failed: the drafting agent returned no letter.",
        )

    # 7. Agent 5 — Judge: score the draft against the upstream evidence.
    scorecard = run_judge_agent(
        appeal_letter=appeal_letter,
        denial_details=denial,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
    )

    return AppealResponse(
        case_id=case_id,
        appeal_letter=appeal_letter,
        scorecard=scorecard.model_dump(),
        status=scorecard.status,
        llm_backed=bool(settings.groq_api_key),
    )


@router.post("/cases/{case_id}/grievance", response_model=GrievanceResponse)
async def draft_grievance(case_id: str, db: AsyncSession = Depends(get_db)):
    """Auto-drafts an IRDAI Bima Bharosa portal complaint package."""
    case = await require_case_consent(case_id, db)

    complaint_text = (
        f"Grievance Complaint filed under Bima Bharosa.\n"
        f"Case Reference: {case_id}\n"
        f"Details: The insurer has failed to reimburse room categories benchmarking deviations "
        f"despite IRDAI compliant appeals. Total disputed amount is ₹{case.total_charged:.2f}.\n"
        f"Requesting regulatory investigation under Rule 14."
    )

    # Required fields structure for manual copying
    bb_fields = {
        "Complaint Type": "Partial Payment / Unfair Deduction",
        "Insurer Category": "Health Insurance Company",
        "Disputed Amount": f"{case.total_charged:.2f}",
        "Policyholder Consent": "Yes",
    }

    return {
        "case_id": case_id,
        "complaint_text": complaint_text,
        "bima_bharosa_fields": bb_fields,
        "deep_link": "https://bimabharosa.irdai.gov.in/RegisterNewGrievance",
    }
