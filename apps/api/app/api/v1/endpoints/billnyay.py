"""
BillNyay API Endpoints.

Handles hospital bill auditing, appeal drafting (5-agent pipeline), and grievance package generation.
"""

import logging
import uuid
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import os
import json
import urllib.request
from app.config import settings
from app.consent import require_case_consent
from app.database import get_db
from app.models import BillNyayAppeal, KadiCase, KadiEntity
# Import billnyay modules
from billnyay.agents.auditor import run_auditor_agent, StructuredDenial
from billnyay.agents.judge import run_judge_agent, JudgeScorecard
from billnyay.agents.barrister import run_barrister_agent
from billnyay.agents.clinician import run_clinician_agent
from billnyay.agents.regulatory import run_regulatory_agent
from billnyay.agents.consensus import (
    ConsensusResult,
    compute_weighted_consensus,
    vote_from_auditor,
    vote_from_clinician,
    vote_from_regulatory,
)
from billnyay.agents.feedback_loop import draft_with_self_correction
from billnyay.agents.icd_audit import audit_icd_procedure_consistency, ICDProcedureAuditItem
from billnyay.tools.pdf_compiler import compile_appeal_packet_bytes
from billnyay.tools.pdf_integrity import compute_sha256, sign_document, verify_signature
from billnyay.tools.bima_bharosa_crawler import check_registration_status_mock, RegistrationStatusResult
from billnyay.outcome import OutcomeEstimate, OutcomeQuery, estimate_outcome, load_registered_dataset

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


# Rendered into the appeal letter wherever a fact could not be extracted. Deliberately
# reads as unknown rather than resembling a real reference.
UNSPECIFIED_FIELD = "Not specified in the supplied documents"


class AppealResponse(BaseModel):
    case_id: str
    appeal_letter: str
    scorecard: Dict[str, Any]
    status: str
    # False when the Auditor could not extract denial facts from the uploaded document.
    # The letter is then built on placeholders and the user must fill in the real denial
    # code, insurer reason and policy clause before sending it.
    denial_facts_extracted: bool = True
    # False when GROQ_API_KEY is unset: the letter is a static statutory template rather
    # than an LLM draft grounded in this case. Callers must be able to tell the two apart.
    llm_backed: bool
    # #65 — cooperative pre-drafting vote across Auditor/Clinician/Regulatory, surfaced
    # alongside (not instead of) the Judge's own scoring of the finished letter.
    consensus: Dict[str, Any]
    # #68 — how many times the Barrister re-drafted after a needs_revision verdict.
    revision_count: int = 0
    revision_history: List[Dict[str, Any]] = []
    # #66 — integrity of the compiled, persisted PDF. See .../appeal/pdf and
    # .../appeal/verify.
    document_sha256: str
    pdf_download_url: str
    # #39 — the language the letter was actually drafted in (en/hi/mr), confirming the
    # request's ?language= was honoured rather than silently ignored.
    language: str = "en"


class GrievanceResponse(BaseModel):
    case_id: str
    complaint_text: str
    bima_bharosa_fields: Dict[str, str] = {}
    deep_link: str
    # False when the Auditor could not extract real denial facts from the uploaded
    # document (no GROQ_API_KEY, or the call fell back). The complaint is then built on
    # UNSPECIFIED_FIELD placeholders instead of a fabricated denial code/reason —
    # mirrors AppealResponse.denial_facts_extracted for the same reason.
    denial_facts_extracted: bool = True


# --- Groq LLM Client & Fallback -----------------------------------------------
class GroqClient:
    """Configured Groq Cloud inference client using settings.groq_model."""
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        # Set when a live call fails and this instance silently served a canned
        # fallback response instead. Callers must check this before claiming any
        # fact drawn from that response was actually extracted from the document.
        self.used_fallback = False

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
            self.used_fallback = True
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

# Hindi/Marathi offline fallback letters (#39): with GROQ_API_KEY unset — the documented
# default deployment state — the LLM path never runs, so without these a user who chose
# Hindi/Marathi in the UI still received the English fallback above regardless of their
# language selection. Same canned-template caveat as the English version: not read from
# the user's document, only a structurally valid placeholder.
_FALLBACK_APPEAL_LETTER_HI = """विषय: दावा अस्वीकृति / बिलिंग विचलन के विरुद्ध औपचारिक प्रतिनिधित्व एवं अपील की सूचना

शिकायत निवारण अधिकारी के नाम,

प्रस्तावना
यह प्रतिनिधित्व IRDAI (पॉलिसीधारक हितों का संरक्षण) विनियमों के अंतर्गत, उल्लिखित दावे के संबंध में सूचित
अस्वीकृति/कटौती के विरुद्ध प्रस्तुत किया जा रहा है। पॉलिसीधारक इस अस्वीकृति पर आपत्ति दर्ज करता है और
सांविधिक समयावधि के भीतर इसकी वापसी की माँग करता है।

खंड I - चिकित्सीय औचित्य एवं चिकित्सा आवश्यकता
अस्पताल में भर्ती होने के दौरान निरंतर चिकित्सीय निगरानी के साथ एक सक्रिय उपचार प्रक्रिया अपनाई गई।
स्थापित देखभाल मानक ऐसे भर्ती को चिकित्सकीय रूप से आवश्यक मानते हैं। उपचार करने वाले चिकित्सक के
अभिलेख बिल की गई प्रक्रियाओं एवं उपभोग्य सामग्रियों की आवश्यकता की पुष्टि करते हैं।

खंड II - सांविधिक एवं IRDAI विनियामक प्रावधान
अस्पष्ट या गैर-विशिष्ट अपवर्जन खंडों के आधार पर अस्वीकृति, अपवर्जन खंडों के मानकीकरण संबंधी IRDAI
परिपत्र के तहत अनुमन्य नहीं है। दावा की गई चिकित्सा व्ययों में मनमानी कमी, या निपटान में अस्पष्टीकृत विलंब,
उपभोक्ता संरक्षण अधिनियम, 2019 के अंतर्गत एक अनुचित व्यापार व्यवहार भी है। दावा समीक्षा समिति की सहमति
के बिना कोई भी अस्वीकृति वैध नहीं है।

खंड III - औपचारिक माँग एवं प्रत्यावर्तन हेतु समयसीमा
पॉलिसीधारक IRDAI द्वारा अनिवार्य तीस (30) दिनों के भीतर अस्वीकृति/कटौती पर पुनर्विचार एवं इसे वापस लेने
की माँग करता है। ऐसा न होने पर, पॉलिसीधारक IRDAI बीमा भरोसा पोर्टल एवं तत्पश्चात संबंधित बीमा लोकपाल
के समक्ष मामला ले जाने का अधिकार सुरक्षित रखता है।

भवदीय,
पॉलिसीधारक
"""

_FALLBACK_APPEAL_LETTER_MR = """विषय: दावा नकार / बिलिंग तफावतीविरुद्ध औपचारिक निवेदन आणि अपील सूचना

तक्रार निवारण अधिकारी यांना,

प्रस्तावना
हे निवेदन IRDAI (पॉलिसीधारक हितसंरक्षण) विनियमांतर्गत, संबंधित दाव्याबाबत कळवलेल्या नकार/कपातीविरुद्ध
सादर केले जात आहे. पॉलिसीधारक या नकाराबाबत आक्षेप नोंदवत असून वैधानिक मुदतीत तो मागे घेण्याची मागणी
करत आहे.

विभाग I - वैद्यकीय औचित्य आणि वैद्यकीय गरज
रुग्णालयात दाखल असताना सातत्यपूर्ण वैद्यकीय देखरेखीसह सक्रिय उपचार प्रक्रिया राबवण्यात आली. प्रस्थापित
काळजी मानके अशा दाखलतेला वैद्यकीयदृष्ट्या आवश्यक मानतात. उपचार करणाऱ्या डॉक्टरांच्या नोंदी बिल
केलेल्या प्रक्रिया व उपभोग्य वस्तूंच्या गरजेस पुष्टी देतात.

विभाग II - वैधानिक आणि IRDAI नियामक तरतुदी
अस्पष्ट किंवा विशिष्ट नसलेल्या वगळणी कलमांच्या आधारे नकार देणे, वगळणी कलमांच्या प्रमाणीकरणाबाबतच्या
IRDAI परिपत्रकांतर्गत अनुज्ञेय नाही. दावा केलेल्या वैद्यकीय खर्चात अनियंत्रित कपात, किंवा निपटाऱ्यात
अस्पष्ट विलंब, ग्राहक संरक्षण कायदा, 2019 अंतर्गत अनुचित व्यापार पद्धत ठरते. दावा पुनरावलोकन समितीच्या
संमतीशिवाय कोणताही नकार वैध नाही.

विभाग III - औपचारिक मागणी आणि परतफेडीसाठी कालमर्यादा
पॉलिसीधारक IRDAI ने अनिवार्य केलेल्या तीस (30) दिवसांच्या आत नकार/कपातीचा पुनर्विचार करून तो मागे
घेण्याची मागणी करत आहे. असे न झाल्यास, पॉलिसीधारक हे प्रकरण IRDAI विमा भरोसा पोर्टलकडे आणि त्यानंतर
संबंधित विमा लोकपालाकडे नेण्याचा अधिकार राखून ठेवतो.

आपला विश्वासू,
पॉलिसीधारक
"""

_FALLBACK_APPEAL_LETTERS = {
    "en": _FALLBACK_APPEAL_LETTER,
    "hi": _FALLBACK_APPEAL_LETTER_HI,
    "mr": _FALLBACK_APPEAL_LETTER_MR,
}


class GroqClientFallback:
    """Deterministic offline stand-in used when GROQ_API_KEY is not configured.

    Each agent in the pipeline expects a different response shape. Returning the
    Auditor's JSON to every caller (the previous behaviour) made the Barrister emit a
    JSON blob as its "appeal letter", so the fallback is dispatched per agent using the
    system instruction each agent sends.

    Every response here (including `_FALLBACK_DENIAL_JSON`) is a canned template, not
    anything read from the user's document. `used_fallback` lets callers tell the two
    apart instead of trusting that a parseable response means real extraction happened.
    """

    used_fallback = True

    def generate(self, prompt: str, system: str = "", **kwargs) -> str:
        sys_text = (system or "").lower()
        json_mode = kwargs.get("json_mode", True)

        if "clinician agent" in sys_text:
            logger.warning("[GroqClientFallback] Returning fallback clinical evidence.")
            return _FALLBACK_CLINICAL_JSON

        if "barrister agent" in sys_text or not json_mode:
            language = (kwargs.get("language") or "en").lower()
            letter = _FALLBACK_APPEAL_LETTERS.get(language, _FALLBACK_APPEAL_LETTER)
            logger.warning("[GroqClientFallback] Returning fallback appeal letter (language=%s).", language)
            return letter

        logger.warning("[GroqClientFallback] Returning fallback denial JSON block.")
        return _FALLBACK_DENIAL_JSON


# --- Route Implementations ----------------------------------------------------

@router.post("/cases/{case_id}/audit", response_model=AuditResponse)
async def audit_bill(case_id: str, db: AsyncSession = Depends(get_db)):
    """Audits hospital bill items against CGHS rate schedules."""
    await require_case_consent(case_id, db)
    return await build_case_audit(case_id, db)


async def build_case_audit(case_id: str, db: AsyncSession) -> AuditResponse:
    """CGHS audit of a case's billing items.

    Shared by the route above and Kadi's auto-triggers (app.auto_triggers, #32) so both
    always compute the same result. Callers must enforce consent first.
    """
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
async def draft_appeal(
    case_id: str,
    language: str = Query("en", description="Appeal letter language: en, hi, or mr (#39)."),
    db: AsyncSession = Depends(get_db),
):
    """Runs the 5-agent pipeline to generate an IRDAI-compliant appeal letter."""
    if language not in ("en", "hi", "mr"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported language '{language}'. Use en, hi, or mr.",
        )
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
    # A canned fallback response always parses into a valid StructuredDenial, so
    # "denial is not None" alone can't distinguish real extraction from a template
    # (e.g. DEN-999 / confidence 0.95) served because no live LLM call happened.
    denial_facts_extracted = denial is not None and not client.used_fallback
    if denial is None:
        # The Auditor could not extract denial facts. Downstream agents are typed against
        # this model, so a neutral placeholder is supplied — but it must read as "unknown",
        # never as a plausible-looking denial code. A letter quoting "DEN-DEFAULT" as the
        # insurer's reference would be sent to a real insurer as though it were genuine.
        denial = StructuredDenial(
            denial_code=UNSPECIFIED_FIELD,
            insurer_reason_snippet=UNSPECIFIED_FIELD,
            policy_clause_text=UNSPECIFIED_FIELD,
            procedure_denied=UNSPECIFIED_FIELD,
            confidence_score=0.0,
            raw_evidence_chunks=[],
        )

    # 4. Agent 2 — Clinician: synthesise medical-necessity evidence.
    clinical_evidence = run_clinician_agent(client=client, denial_details=denial)

    # 5. Agent 3 — Regulatory: retrieve applicable statutory provisions.
    regulatory_evidence = run_regulatory_agent(
        denial_data=denial.model_dump(), client=client
    )

    # 5b. Multi-agent consensus (#65): a transparency/triage vote across the three
    # upstream agents, surfaced alongside — not instead of — the Judge's scoring of
    # the finished letter.
    votes = [
        vote_from_auditor(denial, denial_facts_extracted),
        vote_from_clinician(clinical_evidence),
        vote_from_regulatory(regulatory_evidence),
    ]
    consensus: ConsensusResult = compute_weighted_consensus(votes)

    # 6-7. Agents 4 & 5 — Barrister drafts, Judge scores, with self-correcting
    # revision (#68) when the Judge reports needs_revision.
    drafting_result = draft_with_self_correction(
        client,
        denial_details=denial,
        clinical_evidence=clinical_evidence,
        regulatory_evidence=regulatory_evidence,
        language=language,
    )
    if drafting_result is None:
        logger.error("[BillNyay] Barrister Agent returned no appeal letter for case %s", case_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Appeal drafting failed: the drafting agent returned no letter.",
        )
    appeal_letter = drafting_result.appeal_letter
    scorecard = drafting_result.scorecard

    # 8. Compile, sign, and persist the PDF (#66) — the exact bytes served by
    # .../appeal/pdf and checked by .../appeal/verify, so a later re-draft cannot
    # silently invalidate what was already downloaded.
    pdf_bytes = compile_appeal_packet_bytes(appeal_letter, case_meta={"case_id": case_id})
    document_sha256 = compute_sha256(pdf_bytes)
    hmac_signature = sign_document(pdf_bytes, settings.document_signing_secret)

    existing_appeal = await db.execute(
        select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id)
    )
    appeal_record = existing_appeal.scalar_one_or_none()
    if appeal_record is None:
        appeal_record = BillNyayAppeal(id=f"APPEAL-{uuid.uuid4().hex[:10]}", case_id=case_id)
        db.add(appeal_record)
    appeal_record.appeal_letter = appeal_letter
    appeal_record.pdf_bytes = pdf_bytes
    appeal_record.sha256_hash = document_sha256
    appeal_record.hmac_signature = hmac_signature
    await db.commit()

    return AppealResponse(
        case_id=case_id,
        appeal_letter=appeal_letter,
        scorecard=scorecard.model_dump(),
        status=scorecard.status,
        llm_backed=bool(settings.groq_api_key),
        denial_facts_extracted=denial_facts_extracted,
        consensus=consensus.model_dump(mode="json"),
        revision_count=drafting_result.revision_count,
        revision_history=[r.model_dump() for r in drafting_result.revision_history],
        document_sha256=document_sha256,
        pdf_download_url=f"/api/v1/billnyay/cases/{case_id}/appeal/pdf",
        language=language,
    )


@router.get("/cases/{case_id}/appeal/pdf")
async def download_appeal_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """Downloads the exact signed PDF generated by the most recent POST .../appeal
    for this case (#66). Renders strictly from the stored bytes — never regenerated
    on the fly — so what is downloaded always matches what was hashed and signed."""
    await require_case_consent(case_id, db)

    result = await db.execute(select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    appeal_record = result.scalar_one_or_none()
    if appeal_record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No appeal has been drafted for this case yet. "
                f"POST /api/v1/billnyay/cases/{case_id}/appeal first."
            ),
        )

    return Response(
        content=appeal_record.pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=appeal_{case_id}.pdf"},
    )


@router.get("/cases/{case_id}/appeal/verify")
async def verify_appeal_pdf(case_id: str, db: AsyncSession = Depends(get_db)):
    """Verifies the stored appeal PDF's integrity (#66): recomputes its SHA-256 and
    checks the stored HMAC signature. This proves the stored bytes were not altered
    since ArogyaRakshak generated and signed them — it is NOT a licensed digital
    signature certificate (DSC) under the IT Act, 2000; see
    billnyay.tools.pdf_integrity for what this can and cannot vouch for.
    """
    await require_case_consent(case_id, db)

    result = await db.execute(select(BillNyayAppeal).where(BillNyayAppeal.case_id == case_id))
    appeal_record = result.scalar_one_or_none()
    if appeal_record is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No appeal has been drafted for this case yet. "
                f"POST /api/v1/billnyay/cases/{case_id}/appeal first."
            ),
        )

    recomputed_hash = compute_sha256(appeal_record.pdf_bytes)
    hash_matches_stored = recomputed_hash == appeal_record.sha256_hash
    signature_valid = verify_signature(
        appeal_record.pdf_bytes, appeal_record.hmac_signature, settings.document_signing_secret
    )

    return {
        "case_id": case_id,
        "sha256_hash": appeal_record.sha256_hash,
        "hash_matches_stored_bytes": hash_matches_stored,
        "signature_valid": signature_valid,
        "note": (
            "This confirms the stored PDF is byte-for-byte what ArogyaRakshak generated "
            "and signed. It is not a licensed digital signature certificate (DSC) under "
            "the IT Act, 2000."
        ),
    }


@router.get("/cases/{case_id}/icd-audit", response_model=ICDProcedureAuditItem)
async def audit_icd_procedure(case_id: str, db: AsyncSession = Depends(get_db)):
    """Flags whether the billed procedure(s) look clinically consistent with the
    diagnosis's ICD-10 code (#64), using a curated reference subset — see
    billnyay.agents.icd_audit for its coverage and honesty caveats."""
    await require_case_consent(case_id, db)
    return await build_case_icd_audit(case_id, db)


async def build_case_icd_audit(case_id: str, db: AsyncSession) -> ICDProcedureAuditItem:
    """Shared by the route above and Kadi's auto-triggers (#32). Callers enforce consent."""
    diagnosis_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "diagnosis")
    )
    diagnosis_entity = diagnosis_result.scalars().first()
    diagnosis_text = diagnosis_entity.name if diagnosis_entity else ""

    procedure_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id, KadiEntity.type == "procedure")
    )
    procedures_billed = [e.name for e in procedure_result.scalars().all() if e.name]

    return audit_icd_procedure_consistency(diagnosis_text, procedures_billed)


class OutcomeEstimateRequest(BaseModel):
    dispute_category: str = Field(..., min_length=1, max_length=64, json_schema_extra={"example": "PED_NON_DISCLOSURE"})
    forum: Literal["insurer_grievance", "insurance_ombudsman", "consumer_commission"] = "insurance_ombudsman"


@router.post("/outcome-estimate", response_model=OutcomeEstimate)
async def estimate_dispute_outcome(req: OutcomeEstimateRequest):
    """Historical outcome base rate for a dispute category (#90).

    Returns a probability only when a cited, non-synthetic historical dataset with enough
    decided disputes is registered (billnyay/data/dispute_outcomes). None exists today, so
    the status is INSUFFICIENT_EVIDENCE. Request-body only; reads no case context.
    """
    return estimate_outcome(
        OutcomeQuery(dispute_category=req.dispute_category, forum=req.forum),
        load_registered_dataset(),
    )


@router.get("/grievance/registration-status", response_model=RegistrationStatusResult)
async def grievance_registration_status(
    complaint_reference: str = Query(..., description="Bima Bharosa complaint reference number")
):
    """Mock Bima Bharosa portal registration-status check (#67). See
    billnyay.tools.bima_bharosa_crawler for why this is deliberately mock-only —
    ArogyaRakshak is not authorized to automate interactions with the live portal."""
    return check_registration_status_mock(complaint_reference)


@router.post("/cases/{case_id}/grievance", response_model=GrievanceResponse)
async def draft_grievance(case_id: str, db: AsyncSession = Depends(get_db)):
    """Auto-drafts an IRDAI Bima Bharosa portal complaint package (#51).

    Previously this built a fixed generic sentence ("room categories benchmarking
    deviations") and cited an unverified "Rule 14" for every case, regardless of what
    was actually in the uploaded document — exactly the kind of case-independent
    templating the no-fabrication principle rules out for a document filed with a
    regulator. This now reuses the same Auditor Agent extraction draft_appeal runs, so
    the complaint reflects this case's actual denial code/reason/procedure — or
    honestly reports them as not extracted, via `denial_facts_extracted`.
    """
    case = await require_case_consent(case_id, db)

    entities_result = await db.execute(
        select(KadiEntity).join(KadiCase.entities)
        .where(KadiCase.id == case_id)
        .where(KadiEntity.type == "document_text")
    )
    texts = [e.value for e in entities_result.scalars().all() if e.value]
    combined_text = "\n".join(texts) if texts else ""

    if settings.groq_api_key:
        client = GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    else:
        client = GroqClientFallback()

    denial = run_auditor_agent(client=client, denial_text=combined_text) if combined_text else None
    denial_facts_extracted = denial is not None and not client.used_fallback
    if denial is None:
        denial = StructuredDenial(
            denial_code=UNSPECIFIED_FIELD,
            insurer_reason_snippet=UNSPECIFIED_FIELD,
            policy_clause_text=UNSPECIFIED_FIELD,
            procedure_denied=UNSPECIFIED_FIELD,
            confidence_score=0.0,
            raw_evidence_chunks=[],
        )

    complaint_text = (
        "Grievance Complaint filed under IRDAI Bima Bharosa Portal.\n"
        f"Case Reference: {case_id}\n"
        f"Denial/Reference Code: {denial.denial_code}\n"
        f"Procedure/Service Disputed: {denial.procedure_denied}\n"
        f"Insurer's Stated Reason: {denial.insurer_reason_snippet}\n"
        f"Disputed Amount: Rs. {case.total_charged:.2f}\n"
        "The policyholder disputes the above rejection/deduction and seeks reversal "
        "under the IRDAI (Protection of Policyholders' Interests) Regulations."
    )

    # Required fields structure for manual copying
    bb_fields = {
        "Complaint Type": "Claim Rejection / Unfair Deduction",
        "Insurer Category": "Health Insurance Company",
        "Disputed Amount": f"{case.total_charged:.2f}",
        "Policyholder Consent": "Yes",
    }

    return {
        "case_id": case_id,
        "complaint_text": complaint_text,
        "denial_facts_extracted": denial_facts_extracted,
        "bima_bharosa_fields": bb_fields,
        "deep_link": "https://bimabharosa.irdai.gov.in/RegisterNewGrievance",
    }
