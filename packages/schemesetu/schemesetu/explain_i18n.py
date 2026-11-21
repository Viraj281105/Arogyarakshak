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

NEEDS NATIVE-SPEAKER QA: every Hindi and Marathi string below was written by an engineer
(and an AI assistant), not by a native-speaker reviewer. Treat all of it as UNREVIEWED. It
must not be shown to a patient as final copy until reviewed (tracked with #37).
"""

from typing import Dict, List

from pydantic import BaseModel

from schemesetu.citations import CitedSpan
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
    review_status: str = NEEDS_QA


def build_citation_hits(reasoning: EligibilityReasoning) -> Dict[str, CitedSpan]:
    """Citation key -> the cited text (source title plus the source's stated support, or the
    trace step's rule). Built only from the engine's own cited sources and trace."""
    hits: Dict[str, CitedSpan] = {}
    for result in reasoning.scheme_results:
        short = _SHORT.get(result.scheme_name)
        if short is None:
            continue
        for n, cit in enumerate(result.sources, 1):
            hits[f"{short}:S{n}"] = CitedSpan(source=cit.url, page=n, quote=f"{cit.document}. {cit.supports}")
    for n, step in enumerate(reasoning.reasoning_trace, 1):
        short = _SHORT.get(step.scheme)
        if short is None:
            continue
        hits[f"{short}:TRACE:{step.criterion}"] = CitedSpan(
            source="reasoning_trace", page=n, quote=f"{step.scheme}. {step.threshold_or_rule}"
        )
    hits["TRACE:provisional"] = CitedSpan(
        source="reasoning_trace", page=0, quote="Result is provisional: unevaluated criteria remain."
    )
    return hits


def explain_eligibility(reasoning: EligibilityReasoning, lang: str) -> LocalizedExplanation:
    """Templated explanation of ``reasoning`` in Hindi (``hi``) or Marathi (``mr``)."""
    if lang not in SUPPORTED_LANGS:
        raise ValueError(f"unsupported language {lang!r}; supported: {', '.join(SUPPORTED_LANGS)}")
    templates = _TEMPLATES[lang]
    hits = build_citation_hits(reasoning)
    sentences: List[LocalizedSentence] = []
    omitted: List[str] = []

    def add(key: str, text: str, checkable: bool = True) -> None:
        if key not in hits:  # never emit a sentence whose citation cannot be resolved
            raise KeyError(f"citation key {key} has no cited text")
        sentences.append(LocalizedSentence(text=text, citation_key=key, lang=lang, checkable=checkable))

    trace_criteria = {(_SHORT.get(s.scheme), s.criterion) for s in reasoning.reasoning_trace}
    for result in reasoning.scheme_results:
        short = _SHORT.get(result.scheme_name)
        keys = _VERDICT_SENTENCES.get((short, result.estimated_eligibility)) if short else None
        if not keys:
            omitted.append(result.scheme_name)
            continue
        for key in keys:
            add(key, templates[key])
        if (short, "annual_income") in trace_criteria:
            add(f"{short}:TRACE:annual_income", templates["income"].format(S=short))
    add("TRACE:provisional", templates["provisional"], checkable=False)
    return LocalizedExplanation(lang=lang, sentences=sentences, omitted_schemes=omitted)
