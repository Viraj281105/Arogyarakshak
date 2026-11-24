// Copy for the evidence graph (loaded with its chunk) (Wave 3 M4). One file per page area so each route ships only its own
// strings (split from one workspace dictionary to hold the route bundle budgets).
//
// UNREVIEWED: every Hindi (hi) and Marathi (mr) string in this file is a machine-assisted draft
// and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md) before it is presented as final. Text that
// comes from the API stays in the API's English and is marked lang="en" where it is shown.
import type { Language } from "../../shared/i18n/types";

const en = {
  graph: {
    title: "Evidence graph",
    lede: "How the case's details are connected, and why. Only links the server found are drawn; no medical relationship is assumed.",
    error: "Could not load the evidence graph",
    empty: "Nothing to connect yet",
    emptyBody: "The graph appears once details have been read from a document.",
    stats: "{nodes} items, {edges} links",
    svgLabel: "Evidence graph with {nodes} items and {edges} links. Select an item for its details, or use the table below.",
    kinds: {
      hospital_stay: "Hospital stay",
      hospital: "Hospital",
      diagnosis: "Diagnosis",
      procedure: "Procedure",
      medicine: "Medicine",
      billing_item: "Bill line",
    },
    relations: {
      AT_HOSPITAL: "at hospital",
      RECORDED_DIAGNOSIS: "recorded diagnosis",
      RECORDED_PROCEDURE: "recorded procedure",
      RECORDED_MEDICINE: "recorded medicine",
      BILLED_ITEM: "bill line",
      BILLED_AS: "billed as",
      POSSIBLY_SAME_AS: "possibly the same as (awaiting your answer)",
    },
    evidence: {
      case_membership: "read from the case's documents",
      name_match_same_document: "same name in the same document",
      pending_resolution_decision: "question waiting for you",
    },
    legend: "Item types",
    detailsLabel: "Selected item",
    aliases: "Also written as: {names}",
    sources: "From: {files}",
    tableSummary: "All links as a table",
    colFrom: "From",
    colRelation: "Link",
    colTo: "To",
    colEvidence: "Evidence",
    limitations: "Limitations of this graph",
  },
};

export type GraphCopy = typeof en;

export const graphCopy: Record<Language, GraphCopy> = {
  en,
  hi: {
    graph: {
      title: "साक्ष्य ग्राफ़",
      lede: "केस की जानकारी आपस में कैसे जुड़ी है, और क्यों। केवल सर्वर को मिले संबंध दिखाए गए हैं; कोई चिकित्सीय संबंध माना नहीं गया।",
      error: "साक्ष्य ग्राफ़ लोड नहीं हो सका",
      empty: "अभी जोड़ने को कुछ नहीं",
      emptyBody: "दस्तावेज़ से जानकारी पढ़े जाने के बाद ग्राफ़ दिखता है।",
      stats: "{nodes} आइटम, {edges} संबंध",
      svgLabel: "{nodes} आइटम और {edges} संबंधों वाला साक्ष्य ग्राफ़। विवरण के लिए कोई आइटम चुनें, या नीचे की तालिका देखें।",
      kinds: {
        hospital_stay: "अस्पताल में भर्ती",
        hospital: "अस्पताल",
        diagnosis: "निदान",
        procedure: "प्रक्रिया",
        medicine: "दवा",
        billing_item: "बिल पंक्ति",
      },
      relations: {
        AT_HOSPITAL: "अस्पताल में",
        RECORDED_DIAGNOSIS: "दर्ज निदान",
        RECORDED_PROCEDURE: "दर्ज प्रक्रिया",
        RECORDED_MEDICINE: "दर्ज दवा",
        BILLED_ITEM: "बिल पंक्ति",
        BILLED_AS: "इस रूप में बिल किया गया",
        POSSIBLY_SAME_AS: "शायद वही (आपके उत्तर की प्रतीक्षा)",
      },
      evidence: {
        case_membership: "केस के दस्तावेज़ों से पढ़ा गया",
        name_match_same_document: "एक ही दस्तावेज़ में एक ही नाम",
        pending_resolution_decision: "आपके लिए प्रश्न लंबित",
      },
      legend: "आइटम के प्रकार",
      detailsLabel: "चुना गया आइटम",
      aliases: "ऐसे भी लिखा: {names}",
      sources: "स्रोत: {files}",
      tableSummary: "सभी संबंध तालिका में",
      colFrom: "से",
      colRelation: "संबंध",
      colTo: "तक",
      colEvidence: "साक्ष्य",
      limitations: "इस ग्राफ़ की सीमाएँ",
    },
  },
  mr: {
    graph: {
      title: "पुरावा आलेख",
      lede: "केसची माहिती एकमेकांशी कशी जोडलेली आहे, आणि का. फक्त सर्व्हरला सापडलेले दुवे दाखवले आहेत; कोणताही वैद्यकीय संबंध गृहीत धरलेला नाही.",
      error: "पुरावा आलेख लोड झाला नाही",
      empty: "अजून जोडण्यासारखे काही नाही",
      emptyBody: "दस्तऐवजातून माहिती वाचल्यावर आलेख दिसतो.",
      stats: "{nodes} घटक, {edges} दुवे",
      svgLabel: "{nodes} घटक आणि {edges} दुव्यांचा पुरावा आलेख. तपशिलासाठी घटक निवडा, किंवा खालील तक्ता वापरा.",
      kinds: {
        hospital_stay: "रुग्णालयातील मुक्काम",
        hospital: "रुग्णालय",
        diagnosis: "निदान",
        procedure: "प्रक्रिया",
        medicine: "औषध",
        billing_item: "बिलाची ओळ",
      },
      relations: {
        AT_HOSPITAL: "रुग्णालयात",
        RECORDED_DIAGNOSIS: "नोंदलेले निदान",
        RECORDED_PROCEDURE: "नोंदलेली प्रक्रिया",
        RECORDED_MEDICINE: "नोंदलेले औषध",
        BILLED_ITEM: "बिलाची ओळ",
        BILLED_AS: "या नावाने बिल केले",
        POSSIBLY_SAME_AS: "कदाचित तेच (तुमच्या उत्तराची प्रतीक्षा)",
      },
      evidence: {
        case_membership: "केसच्या दस्तऐवजांतून वाचले",
        name_match_same_document: "एकाच दस्तऐवजात एकच नाव",
        pending_resolution_decision: "तुमच्यासाठी प्रश्न प्रलंबित",
      },
      legend: "घटकांचे प्रकार",
      detailsLabel: "निवडलेला घटक",
      aliases: "असेही लिहिले: {names}",
      sources: "स्रोत: {files}",
      tableSummary: "सर्व दुवे तक्त्यात",
      colFrom: "पासून",
      colRelation: "दुवा",
      colTo: "पर्यंत",
      colEvidence: "पुरावा",
      limitations: "या आलेखाच्या मर्यादा",
    },
  },
};
