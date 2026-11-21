"""
SchemeSetu — Hindi / Marathi explanations of the deterministic reasoning trace (Wave 2, B).

Each sentence is a fixed template selected by the scheme and its already-computed verdict
(``schemesetu.reasoning_agent``). There is NO machine translation and no model call: the
facts in a sentence (scheme name, age, cover amount) are the ones in the cited source text,
and every sentence carries a citation key that resolves to that cited text, so
``schemesetu.citations.verify_citation`` can check it.

Citation keys:
- ``<SCHEME>:S<n>``                  the n-th cited official source of the scheme (1-based);
- ``<SCHEME>:TRACE:<criterion>``     a step of the deterministic reasoning trace;
- ``TRACE:provisional``              the provisional-result notice (not a factual claim).

Every checkable sentence is verified with ``schemesetu.citations.verify_citation`` before it is
returned; an unsupported or uncheckable one is dropped (and listed in ``dropped_citation_keys``),
and a scheme whose cited sources or trace steps are missing is listed in ``omitted_schemes``
instead of raising. Honest limit: ``TRACE:`` sentences carry no figure, so their check is only
the scheme attribution (status ``scheme_only``); the figures in the ``<SCHEME>:S<n>`` sentences
are the ones really verified against the cited source text.

NEEDS NATIVE-SPEAKER QA: every Hindi and Marathi string below was written by an engineer
(and an AI assistant), not by a native-speaker reviewer. Treat all of it as UNREVIEWED. It
must not be shown to a patient as final copy until reviewed (tracked with #37).
"""

from typing import Dict, List

from pydantic import BaseModel

from schemesetu.citations import CitedSpan, verify_citation
from schemesetu.reasoning_agent import EligibilityReasoning
from schemesetu.thresholds import MJPJAY, PMJAY

NEEDS_QA = "NEEDS NATIVE-SPEAKER QA"
SUPPORTED_LANGS = ("hi", "mr")

_SHORT = {PMJAY.scheme_name: PMJAY.short_name, MJPJAY.scheme_name: MJPJAY.short_name}

# NEEDS NATIVE-SPEAKER QA — all templates. {S} is the scheme's short name (Latin script).
_TEMPLATES: Dict[str, Dict[str, str]] = {
    "hi": {
        "PMJAY:S2": "PMJAY की पात्रता आय पर आधारित नहीं है; 70 वर्ष या उससे अधिक आयु के सभी वरिष्ठ नागरिक आय की परवाह किए बिना पात्र हैं।",
        "PMJAY:TRACE:beneficiary_identification": "PMJAY: आपका परिवार लाभार्थी सूची में है या नहीं, यह इस जानकारी से तय नहीं हो सकता; अस्पताल के हेल्प डेस्क पर पुष्टि करें।",
        "MJPJAY:S1": "महाराष्ट्र के निवासी सभी परिवार MJPJAY के अंतर्गत आते हैं; प्रति परिवार प्रति वर्ष 5 लाख रुपये तक का कवर है।",
        "MJPJAY:TRACE:state_of_residence": "MJPJAY: यह परिणाम आपके बताए गए राज्य पर आधारित है; निवास की पुष्टि दस्तावेज़ों से नहीं हुई है।",
        "income": "{S}: आय दर्ज की गई है, पर वह पात्रता तय नहीं करती; उद्धृत आधिकारिक मानदंडों में आय की कोई सीमा नहीं है।",
        "provisional": "यह परिणाम अनंतिम है; आधिकारिक अभिलेखों से पुष्टि होने तक इसे अंतिम निर्णय न मानें।",
    },
    "mr": {
        "PMJAY:S2": "PMJAY ची पात्रता उत्पन्नावर आधारित नाही; ७० वर्षे किंवा त्याहून अधिक वयाचे सर्व ज्येष्ठ नागरिक उत्पन्नाचा विचार न करता पात्र आहेत.",
        "PMJAY:TRACE:beneficiary_identification": "PMJAY: तुमचे कुटुंब लाभार्थी यादीत आहे की नाही, हे या माहितीवरून ठरवता येत नाही; रुग्णालयाच्या हेल्प डेस्कवर खात्री करा.",
        "MJPJAY:S1": "महाराष्ट्रातील सर्व कुटुंबे MJPJAY अंतर्गत येतात; प्रति कुटुंब प्रति वर्ष ५ लाख रुपयांपर्यंत संरक्षण आहे.",
        "MJPJAY:TRACE:state_of_residence": "MJPJAY: हा निकाल तुम्ही सांगितलेल्या राज्यावर आधारित आहे; निवासाची खात्री कागदपत्रांवरून झालेली नाही.",
        "income": "{S}: उत्पन्न नोंदवले आहे, परंतु ते पात्रता ठरवत नाही; उद्धृत अधिकृत निकषांमध्ये उत्पन्नाची कोणतीही मर्यादा नाही.",
        "provisional": "हा निकाल तात्पुरता आहे; अधिकृत नोंदींद्वारे खात्री होईपर्यंत तो अंतिम निर्णय मानू नका.",
    },
}

# (scheme short name, verdict) -> keys of the templates that state that verdict.
_VERDICT_SENTENCES = {
    ("PMJAY", "ambiguous"): ["PMJAY:S2", "PMJAY:TRACE:beneficiary_identification"],
    ("MJPJAY", "eligible"): ["MJPJAY:S1", "MJPJAY:TRACE:state_of_residence"],
}


class LocalizedSentence(BaseModel):
    text: str
    citation_key: str
    lang: str
    checkable: bool = True
    review_status: str = NEEDS_QA


class LocalizedExplanation(BaseModel):
    lang: str
    sentences: List[LocalizedSentence]
    omitted_schemes: List[str]
    dropped_citation_keys: List[str] = []
    review_status: str = NEEDS_QA


def build_citation_hits(reasoning: EligibilityReasoning) -> Dict[str, CitedSpan]:
    """Citation key -> the cited text: a source's stated support, or a trace step's rule.
    Built only from the engine's own cited sources and trace. The source's document title is
    kept in ``title`` (ignored by the verifier) and the scheme it is filed under in ``scheme``."""
    hits: Dict[str, CitedSpan] = {}
    for result in reasoning.scheme_results:
        short = _SHORT.get(result.scheme_name)
        if short is None:
            continue
        for n, cit in enumerate(result.sources, 1):
            hits[f"{short}:S{n}"] = CitedSpan(
                source=cit.url, page=n, quote=cit.supports, scheme=short, title=cit.document
            )
    for n, step in enumerate(reasoning.reasoning_trace, 1):
        short = _SHORT.get(step.scheme)
        if short is None:
            continue
        hits[f"{short}:TRACE:{step.criterion}"] = CitedSpan(
            source="reasoning_trace", page=n, quote=step.threshold_or_rule, scheme=short
        )
    hits["TRACE:provisional"] = CitedSpan(
        source="reasoning_trace", page=0, quote="Result is provisional: unevaluated criteria remain."
    )
    return hits


_KEPT_STATUSES = ("supported", "scheme_only")


def explain_eligibility(reasoning: EligibilityReasoning, lang: str) -> LocalizedExplanation:
    """Templated explanation of ``reasoning`` in Hindi (``hi``) or Marathi (``mr``).
    ``lang`` must be exactly ``"hi"`` or ``"mr"`` (anything else raises ``ValueError``)."""
    if not isinstance(lang, str) or lang not in SUPPORTED_LANGS:
        raise ValueError(f"unsupported language {lang!r}; supported: {', '.join(SUPPORTED_LANGS)}")
    templates = _TEMPLATES[lang]
    hits = build_citation_hits(reasoning)
    sentences: List[LocalizedSentence] = []
    omitted: List[str] = []
    dropped: List[str] = []

    trace_criteria = {(_SHORT.get(s.scheme), s.criterion) for s in reasoning.reasoning_trace}
    for result in reasoning.scheme_results:
        short = _SHORT.get(result.scheme_name)
        keys = list(_VERDICT_SENTENCES.get((short, result.estimated_eligibility), [])) if short else []
        if (short, "annual_income") in trace_criteria:
            keys.append(f"{short}:TRACE:annual_income")
        verdict_keys = keys[:-1] if keys and keys[-1].endswith(":annual_income") else keys
        if not verdict_keys or any(k not in hits for k in keys):
            omitted.append(result.scheme_name)  # unknown scheme/verdict, or the trace/sources changed
            continue
        kept = 0
        for key in keys:
            text = templates["income"].format(S=short) if key.endswith(":annual_income") else templates[key]
            verdict = verify_citation(text, hits[key])
            if verdict.status not in _KEPT_STATUSES:
                dropped.append(key)
                continue
            kept += 1
            sentences.append(LocalizedSentence(text=text, citation_key=key, lang=lang))
        if not kept:
            omitted.append(result.scheme_name)
    sentences.append(
        LocalizedSentence(text=templates["provisional"], citation_key="TRACE:provisional", lang=lang, checkable=False)
    )
    return LocalizedExplanation(
        lang=lang, sentences=sentences, omitted_schemes=omitted, dropped_citation_keys=dropped
    )
