"""
LLM client for BillNyay's appeal pipeline, and its deterministic offline fallback.

Moved out of ``app.api.v1.endpoints.billnyay`` (restructuring, 2026-10): an outbound HTTP
adapter and canned templates are infrastructure, not routing. Every agent in
``packages/billnyay/billnyay/agents`` receives one of these clients as ``client`` and calls
``client.generate(...)``; ``used_fallback`` tells callers whether anything was actually read
from the document. ``llm_client()`` picks the live client when GROQ_API_KEY is set.
"""

import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger("arogyarakshak.api.billnyay")


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
                    "line of treatment and continuous monitoring are documented. General clinical "
                    "reasoning — not a cited source."
                ),
                # P1-7: was a hardcoded fake PMID presented as a real citation in every
                # offline-mode appeal letter. This system has no PubMed/NCBI lookup, so
                # an invented identifier here is exactly the kind of fabricated,
                # checkable-looking fact the no-fabrication principle forbids. Null,
                # always — clinician.py's _strip_unverifiable_citations() also strips
                # this defensively even if a future edit reintroduces a value here.
                "pubmed_id": None,
            },
            {
                "article_title": "Medical Necessity Determination in Acute Care Admissions",
                "summary_of_finding": (
                    "Treating-physician documentation of an active line of treatment is the accepted "
                    "determinant of medical necessity for inpatient care. General clinical reasoning "
                    "— not a cited source."
                ),
                "pubmed_id": None,
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
standards of care recognise such admission as medically necessary. The treating physician's records, where
available, should be attached to evidence the necessity of the procedures and consumables billed.

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
स्थापित देखभाल मानक ऐसे भर्ती को चिकित्सकीय रूप से आवश्यक मानते हैं। बिल की गई प्रक्रियाओं एवं
उपभोग्य सामग्रियों की आवश्यकता दर्शाने हेतु, उपलब्ध होने पर, उपचार करने वाले चिकित्सक के अभिलेख संलग्न किए जाने चाहिए।

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
काळजी मानके अशा दाखलतेला वैद्यकीयदृष्ट्या आवश्यक मानतात. बिल केलेल्या प्रक्रिया व उपभोग्य
वस्तूंची गरज दर्शवण्यासाठी, उपलब्ध असल्यास, उपचार करणाऱ्या डॉक्टरांच्या नोंदी जोडाव्यात.

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


def llm_client():
    """The live Groq client when GROQ_API_KEY is configured, else the offline fallback."""
    if settings.groq_api_key:
        return GroqClient(api_key=settings.groq_api_key, model=settings.groq_model)
    return GroqClientFallback()
