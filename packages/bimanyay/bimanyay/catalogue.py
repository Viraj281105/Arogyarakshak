"""
BimaNyay message catalogue: audit grounds, violation text and statute/clause display names
for the five denial categories in English, Hindi and Marathi.

Why this exists: the audit used to return English grounds and English statute names whatever
the letter language, so a Hindi or Marathi appeal embedded English sentences (see
docs/evaluation/terminology-audit.md). The audit now takes a ``language`` and reads its text
from here.

Rules:

* The ENGLISH entries are the original strings, character for character; a golden test
  (``tests/test_catalogue.py``) fails if English output ever changes.
* Hindi and Marathi entries are UNREVIEWED engineering-team text. NEEDS NATIVE-SPEAKER QA
  (tracked in #37). Nothing here claims they are correct, idiomatic or legally precise.
* Official instrument names and citation identifiers (``IRDA/HLTH/MISC/CIR/216/09/2011``) and
  the acronyms IRDAI, GRO, CRC, ICU are kept in Latin script where that is how they are cited.
  The machine marker ``UNVERIFIED`` also stays Latin: the evaluation harness counts
  citations whose clause reference starts with it.
* Text that asserts a fact (a date, a percentage, a day count, a clause number) must also be
  true of the English entry; the grounding harness checks that the letter makes no claim that
  is not in its source. Do not write a clinician word (डॉक्टर / डॉ.) into a ground: the
  harness treats it as a clinician opinion that can never be grounded (ADR-011).
* Parameters are ``str.format`` fields: ``{policy_age_years}``, ``{diagnosis}``.
"""

from typing import Dict

LANGUAGES = ("en", "hi", "mr")

# Ground keys: the primary-dispute text per audit outcome.
#   default         general/other category, nothing specific audited
#   ped_moratorium  pre-existing disease contested after the 5-year moratorium
#   ped_documentary pre-existing disease within 5 years: insurer needs documentary proof
#   investigation   "hospitalised only for investigation"
#   room_rent       proportionate deduction (no verified IRDAI provision, see clause_auditor)
#   delay           delayed intimation / submission
_GROUNDS: Dict[str, Dict[str, str]] = {
    "default": {
        "en": "The denial rationale was audited against general IRDAI fair practices guidelines.",
        "hi": "बीमाकर्ता द्वारा दिए गए निरस्तीकरण कारण का सामान्य IRDAI निष्पक्ष व्यवहार दिशानिर्देशों के विरुद्ध परीक्षण किया गया।",
        "mr": "विमा कंपनीने दिलेल्या नकाराच्या कारणाची सर्वसाधारण IRDAI निष्पक्ष व्यवहार मार्गदर्शक तत्त्वांच्या आधारे तपासणी करण्यात आली.",
    },
    "ped_moratorium": {
        "en": (
            "Policy has been continuously active for {policy_age_years} years. "
            "Under the IRDAI Master Circular on Health Insurance (May 29, 2024), the moratorium "
            "period is 5 years. Contesting this claim on grounds of non-disclosure is barred by law."
        ),
        "hi": (
            "पॉलिसी {policy_age_years} वर्षों से लगातार सक्रिय है। "
            "IRDAI स्वास्थ्य बीमा मास्टर परिपत्र (२९ मई २०२४) के अंतर्गत स्थगन अवधि (मोरेटोरियम) ५ वर्ष की है। "
            "गैर-प्रकटीकरण के आधार पर इस दावे को चुनौती देना विधि द्वारा वर्जित है।"
        ),
        "mr": (
            "पॉलिसी {policy_age_years} वर्षे सलग सुरू आहे. "
            "IRDAI आरोग्य विमा मास्टर परिपत्रकानुसार (२९ मे २०२४) स्थगन कालावधी (मोरेटोरियम) ५ वर्षांचा आहे. "
            "माहिती न दिल्याच्या कारणावरून हा दावा आव्हानित करणे कायद्याने प्रतिबंधित आहे."
        ),
    },
    "ped_documentary": {
        "en": (
            "Insurer must provide verifiable clinical documentary proof of pre-inception diagnosis. "
            "Oral declarations or doctor notes without diagnostic reports prior to inception are legally insufficient."
        ),
        "hi": (
            "बीमाकर्ता को पॉलिसी आरंभ से पूर्व के निदान का सत्यापन योग्य नैदानिक दस्तावेजी प्रमाण देना होगा। "
            "पॉलिसी आरंभ से पहले की निदान रिपोर्ट के बिना मौखिक घोषणाएँ या चिकित्सकीय नोट विधिक रूप से अपर्याप्त हैं।"
        ),
        "mr": (
            "विमा कंपनीने पॉलिसी सुरू होण्यापूर्वीच्या निदानाचा पडताळणीयोग्य वैद्यकीय कागदोपत्री पुरावा देणे आवश्यक आहे. "
            "पॉलिसी सुरू होण्यापूर्वीच्या निदान अहवालांशिवाय तोंडी घोषणा किंवा वैद्यकीय नोंदी कायदेशीरदृष्ट्या अपुऱ्या आहेत."
        ),
    },
    "investigation": {
        "en": (
            "The insurer rejected the claim for '{diagnosis}' claiming hospitalization was "
            "solely for diagnostic evaluation. However, active line of treatment and clinical stabilization "
            "warranted inpatient medical monitoring."
        ),
        "hi": (
            "बीमाकर्ता ने '{diagnosis}' के दावे को यह कहकर अस्वीकार किया कि अस्पताल में भर्ती केवल निदानात्मक मूल्यांकन के लिए थी। "
            "किंतु सक्रिय उपचार प्रक्रिया और नैदानिक स्थिरीकरण के लिए अंतः-रोगी चिकित्सीय निगरानी आवश्यक थी।"
        ),
        "mr": (
            "विमा कंपनीने '{diagnosis}' साठीचा दावा रुग्णालयातील दाखल केवळ निदानात्मक मूल्यमापनासाठी होता असे सांगून नाकारला. "
            "मात्र सक्रिय उपचार पद्धती आणि वैद्यकीय स्थिरीकरणासाठी आंतररुग्ण वैद्यकीय देखरेख आवश्यक होती."
        ),
    },
    "room_rent": {
        "en": (
            "Insurer applied proportionate deductions across medical charges. The IRDAI provision said to "
            "limit proportionate deductions to room-linked charges (excluding ICU charges, medicines and "
            "implants) has NOT been verified against a primary source, so it must not be cited as settled law. "
            "Ask the insurer to identify the policy clause relied on and to show the deduction calculation."
        ),
        "hi": (
            "बीमाकर्ता ने सभी चिकित्सा शुल्कों पर आनुपातिक कटौती लागू की। जिस IRDAI प्रावधान के बारे में कहा जाता है कि वह "
            "आनुपातिक कटौती को कमरे से जुड़े शुल्कों तक सीमित करता है (ICU शुल्क, दवाएँ और इम्प्लांट को छोड़कर), "
            "उसका किसी प्राथमिक स्रोत से सत्यापन नहीं हुआ है, इसलिए उसे स्थापित विधि के रूप में उद्धृत नहीं किया जाना चाहिए। "
            "बीमाकर्ता से कहें कि वह जिस पॉलिसी खंड पर निर्भर है उसे बताए और कटौती की गणना दिखाए।"
        ),
        "mr": (
            "विमा कंपनीने सर्व वैद्यकीय शुल्कांवर प्रमाणशीर कपात लागू केली. प्रमाणशीर कपात केवळ खोलीशी संबंधित शुल्कांपुरती "
            "(ICU शुल्क, औषधे व इम्प्लांट वगळून) मर्यादित ठेवणारी IRDAI तरतूद असल्याचे सांगितले जाते, परंतु तिची "
            "कोणत्याही प्राथमिक स्रोताद्वारे पडताळणी झालेली नाही; त्यामुळे ती प्रस्थापित कायदा म्हणून उद्धृत करू नये. "
            "विमा कंपनीला ती कोणत्या पॉलिसी कलमावर अवलंबून आहे ते सांगण्यास व कपातीची गणना दाखवण्यास सांगा."
        ),
    },
    "delay": {
        "en": (
            "The insurer denied the claim citing delayed submission. Under Supreme Court rulings and "
            "IRDAI Circular Ref: IRDA/HLTH/MISC/CIR/216/09/2011, genuine claims cannot be rejected "
            "solely on technical grounds of delayed submission when valid reasons exist."
        ),
        "hi": (
            "बीमाकर्ता ने विलंबित प्रस्तुति का हवाला देकर दावा अस्वीकार किया। सर्वोच्च न्यायालय के निर्णयों और "
            "IRDAI परिपत्र संदर्भ: IRDA/HLTH/MISC/CIR/216/09/2011 के अनुसार, वैध कारण होने पर वास्तविक दावों को "
            "केवल विलंबित प्रस्तुति की तकनीकी आपत्ति के आधार पर अस्वीकार नहीं किया जा सकता।"
        ),
        "mr": (
            "विमा कंपनीने दावा उशिरा सादर केल्याचे कारण देऊन नाकारला. सर्वोच्च न्यायालयाचे निर्णय आणि "
            "IRDAI परिपत्रक संदर्भ: IRDA/HLTH/MISC/CIR/216/09/2011 नुसार, वैध कारणे असताना केवळ उशिरा सादरीकरणाच्या "
            "तांत्रिक कारणावरून खरे दावे नाकारता येत नाहीत."
        ),
    },
}

# Violation keys -> language -> the four RegulatoryViolation fields.
_VIOLATIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "moratorium": {
        "en": {
            "statute_or_circular": "IRDAI Master Circular on Health Insurance Business (May 29, 2024)",
            "clause_reference": "Clause 16 — Moratorium Period",
            "violation_summary": "Insurer contested claim based on pre-existing condition after 5 continuous renewal years.",
            "legal_remedy": "Invoke 5-year moratorium statutory bar and demand immediate claim settlement with 2% penal interest.",
        },
        "hi": {
            "statute_or_circular": "IRDAI स्वास्थ्य बीमा व्यवसाय मास्टर परिपत्र (२९ मई २०२४)",
            "clause_reference": "खंड 16 — स्थगन (मोरेटोरियम) अवधि",
            "violation_summary": "५ लगातार नवीनीकरण वर्षों के बाद बीमाकर्ता ने पूर्व-विद्यमान रोग के आधार पर दावे का विरोध किया।",
            "legal_remedy": "५ वर्ष की स्थगन अवधि का सांविधिक निषेध लागू करें और २% दंडात्मक ब्याज सहित तत्काल दावा निपटान की माँग करें।",
        },
        "mr": {
            "statute_or_circular": "IRDAI आरोग्य विमा व्यवसाय मास्टर परिपत्रक (२९ मे २०२४)",
            "clause_reference": "कलम 16 — स्थगन (मोरेटोरियम) कालावधी",
            "violation_summary": "सलग ५ नूतनीकरण वर्षांनंतर विमा कंपनीने पूर्वीपासून असलेल्या आजाराच्या कारणावरून दाव्याला विरोध केला.",
            "legal_remedy": "५ वर्षांच्या स्थगन कालावधीचा वैधानिक प्रतिबंध लागू करा आणि २% दंडात्मक व्याजासह तत्काळ दावा निपटाऱ्याची मागणी करा.",
        },
    },
    "investigation": {
        "en": {
            "statute_or_circular": "IRDAI Health Insurance Operations & Claims Circular",
            "clause_reference": "Standard Health Definitions & Claims Settlement Guidelines",
            "violation_summary": "Arbitrary characterization of active clinical inpatient management as diagnostic investigation.",
            "legal_remedy": "Submit treating physician certification of medical necessity for continuous inpatient care.",
        },
        "hi": {
            "statute_or_circular": "IRDAI स्वास्थ्य बीमा संचालन एवं दावा परिपत्र",
            "clause_reference": "मानक स्वास्थ्य परिभाषाएँ एवं दावा निपटान दिशानिर्देश",
            "violation_summary": "सक्रिय नैदानिक अंतः-रोगी प्रबंधन को मनमाने ढंग से निदानात्मक मूल्यांकन बताया गया।",
            "legal_remedy": "निरंतर अंतः-रोगी देखभाल की चिकित्सीय आवश्यकता का उपचारकर्ता चिकित्सक का प्रमाणपत्र प्रस्तुत करें।",
        },
        "mr": {
            "statute_or_circular": "IRDAI आरोग्य विमा संचालन व दावा परिपत्रक",
            "clause_reference": "प्रमाण आरोग्य व्याख्या व दावा निपटारा मार्गदर्शक तत्त्वे",
            "violation_summary": "सक्रिय वैद्यकीय आंतररुग्ण व्यवस्थापनाला मनमानीपणे निदानात्मक मूल्यमापन ठरवले गेले.",
            "legal_remedy": "सलग आंतररुग्ण उपचारांच्या वैद्यकीय आवश्यकतेचे उपचार करणाऱ्या वैद्यकीय व्यावसायिकाचे प्रमाणपत्र सादर करा.",
        },
    },
    "room_rent": {
        "en": {
            "statute_or_circular": "IRDAI provision not verified",
            "clause_reference": "UNVERIFIED — no primary-source citation",
            "violation_summary": "Proportionate deduction applied to non-room-rent items (ICU/implants/medicines).",
            "legal_remedy": "Request the insurer's itemised deduction calculation and the exact policy clause and IRDAI provision relied upon.",
        },
        "hi": {
            "statute_or_circular": "IRDAI प्रावधान सत्यापित नहीं",
            "clause_reference": "UNVERIFIED — कोई प्राथमिक-स्रोत उद्धरण नहीं",
            "violation_summary": "कमरे के किराये से भिन्न मदों (ICU/इम्प्लांट/दवाएँ) पर आनुपातिक कटौती लागू की गई।",
            "legal_remedy": "बीमाकर्ता से मदवार कटौती की गणना तथा जिस पॉलिसी खंड और IRDAI प्रावधान पर निर्भरता है, उसकी माँग करें।",
        },
        "mr": {
            "statute_or_circular": "IRDAI तरतूद पडताळलेली नाही",
            "clause_reference": "UNVERIFIED — प्राथमिक स्रोताचा संदर्भ नाही",
            "violation_summary": "खोली भाड्याव्यतिरिक्त बाबींवर (ICU/इम्प्लांट/औषधे) प्रमाणशीर कपात लागू केली गेली.",
            "legal_remedy": "विमा कंपनीकडून बाबीनिहाय कपातीची गणना तसेच ती ज्या पॉलिसी कलमावर आणि IRDAI तरतुदीवर अवलंबून आहे त्याची मागणी करा.",
        },
    },
    "delay": {
        "en": {
            "statute_or_circular": "IRDAI Circular Ref: IRDA/HLTH/MISC/CIR/216/09/2011",
            "clause_reference": "Claims settlement without mechanical delay rejections",
            "violation_summary": "Repudiation solely on timeline delay without examination of substantive medical merits.",
            "legal_remedy": "Submit affidavit of genuine circumstances causing submission delay and cite IRDAI circular.",
        },
        "hi": {
            "statute_or_circular": "IRDAI परिपत्र संदर्भ: IRDA/HLTH/MISC/CIR/216/09/2011",
            "clause_reference": "विलंब के आधार पर यांत्रिक अस्वीकृति के बिना दावा निपटान",
            "violation_summary": "दावे के चिकित्सीय गुण-दोष का परीक्षण किए बिना केवल समय-विलंब के आधार पर दावा अस्वीकृत किया गया।",
            "legal_remedy": "प्रस्तुति में विलंब के वास्तविक कारणों का शपथ-पत्र प्रस्तुत करें और IRDAI परिपत्र का हवाला दें।",
        },
        "mr": {
            "statute_or_circular": "IRDAI परिपत्रक संदर्भ: IRDA/HLTH/MISC/CIR/216/09/2011",
            "clause_reference": "विलंबाच्या कारणावरून यांत्रिक नकाराशिवाय दावा निपटारा",
            "violation_summary": "दाव्याच्या वैद्यकीय गुणवत्तेची तपासणी न करता केवळ वेळेच्या विलंबावरून दावा नाकारला गेला.",
            "legal_remedy": "सादरीकरणात विलंब होण्याच्या खऱ्या कारणांचे शपथपत्र सादर करा आणि IRDAI परिपत्रकाचा संदर्भ द्या.",
        },
    },
    "crc": {
        "en": {
            "statute_or_circular": "IRDAI Master Circular (May 29, 2024)",
            "clause_reference": "Claims Review Committee (CRC) Requirement",
            "violation_summary": "No claim can be repudiated without prior approval of the 3-member Claims Review Committee.",
            "legal_remedy": "Request proof of Claims Review Committee signed minutes authorizing the repudiation.",
        },
        "hi": {
            "statute_or_circular": "IRDAI मास्टर परिपत्र (२९ मई २०२४)",
            "clause_reference": "दावा समीक्षा समिति (CRC) की आवश्यकता",
            "violation_summary": "३-सदस्यीय दावा समीक्षा समिति के पूर्व अनुमोदन के बिना कोई दावा निरस्त नहीं किया जा सकता।",
            "legal_remedy": "दावा समीक्षा समिति के हस्ताक्षरित कार्यवृत्त का प्रमाण माँगें, जिसमें निरस्तीकरण को अधिकृत किया गया हो।",
        },
        "mr": {
            "statute_or_circular": "IRDAI मास्टर परिपत्रक (२९ मे २०२४)",
            "clause_reference": "दावा पुनरावलोकन समिती (CRC) ची आवश्यकता",
            "violation_summary": "३-सदस्यीय दावा पुनरावलोकन समितीच्या पूर्व मंजुरीशिवाय कोणताही दावा नाकारता येत नाही.",
            "legal_remedy": "दावा नाकारण्यास अधिकृत करणाऱ्या दावा पुनरावलोकन समितीच्या स्वाक्षरीत इतिवृत्ताचा पुरावा मागा.",
        },
    },
}

GROUND_KEYS = tuple(_GROUNDS)
VIOLATION_KEYS = tuple(_VIOLATIONS)


def normalise_language(language: str) -> str:
    """``"hi"``/``"mr"`` when asked (any case), otherwise English, like the drafters."""
    lang = (language or "en").lower()
    return lang if lang in LANGUAGES else "en"


def raw_grounds(key: str, language: str) -> str:
    """The unformatted template text (placeholders intact)."""
    return _GROUNDS[key][normalise_language(language)]


def grounds(key: str, language: str = "en", **params) -> str:
    """Primary-dispute text for ``key`` in ``language`` with ``params`` interpolated."""
    return raw_grounds(key, language).format(**params)


def violation(key: str, language: str = "en") -> Dict[str, str]:
    """The four ``RegulatoryViolation`` fields for ``key`` in ``language`` (a copy)."""
    return dict(_VIOLATIONS[key][normalise_language(language)])
