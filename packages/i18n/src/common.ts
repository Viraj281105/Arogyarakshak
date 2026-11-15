// Shared strings used by both web and mobile. Source of truth: packages/i18n (vendored into apps/*/shared/i18n).
//
// Membership rule: a key lives here ONLY if its EN, HI and MR values are byte-identical in the
// web catalogue (apps/web/app/translations.ts) and the mobile catalogue
// (apps/mobile/src/translations/strings.ts). Values were moved verbatim; nothing was translated
// or reworded. Keys that exist on both platforms with different wording (e.g. tagline, tabs.*,
// module titles) stay local to each platform until a human reviewer picks one wording.
//
// Moved keys (25):
//   appName
//   resolution.title
//   resolution.intro
//   resolution.mentionLabel
//   resolution.existingLabel
//   resolution.confidenceLabel
//   resolution.confirmBtn
//   resolution.rejectBtn
//   resolution.uncalibratedNote
//   modules.bimanyay.policyNumber
//   modules.bimanyay.denialCategoryPedNonDisclosure
//   modules.bimanyay.denialCategoryRoomRentCapping
//   modules.bimanyay.denialCategoryInvestigationOnly
//   modules.bimanyay.denialCategoryDelayedIntimation
//   modules.bimanyay.heuristicDisclosure
//   modules.schemesetu.criteriaEvaluated
//   modules.schemesetu.criteriaNotEvaluated
//   modules.schemesetu.provisionalNotice
//   modules.schemesetu.provisionallyEligible
//   modules.schemesetu.howToVerify
//   modules.schemesetu.nonDeterminative
//   modules.schemesetu.officialSources
//   modules.dawacheck.prescriptionTranslatorTitle
//   modules.dawacheck.prescriptionInputPlaceholder
//   modules.dawacheck.unrecognizedNotice

import type { Language } from "./types";

export type CommonStrings = {
  appName: string;
  resolution: {
    title: string;
    intro: string;
    mentionLabel: string;
    existingLabel: string;
    confidenceLabel: string;
    confirmBtn: string;
    rejectBtn: string;
    uncalibratedNote: string;
  };
  modules: {
    bimanyay: {
      policyNumber: string;
      denialCategoryPedNonDisclosure: string;
      denialCategoryRoomRentCapping: string;
      denialCategoryInvestigationOnly: string;
      denialCategoryDelayedIntimation: string;
      heuristicDisclosure: string;
    };
    schemesetu: {
      criteriaEvaluated: string;
      criteriaNotEvaluated: string;
      provisionalNotice: string;
      provisionallyEligible: string;
      howToVerify: string;
      nonDeterminative: string;
      officialSources: string;
    };
    dawacheck: {
      prescriptionTranslatorTitle: string;
      prescriptionInputPlaceholder: string;
      unrecognizedNotice: string;
    };
  };
};

export const common: Record<Language, CommonStrings> = {
  en: {
    appName: "ArogyaRakshak",
    resolution: {
      title: "Please confirm possible duplicates",
      intro: "Kadi found entries in your documents that may refer to the same thing. Nothing is merged until you confirm.",
      mentionLabel: "New entry",
      existingLabel: "Already in this case",
      confidenceLabel: "Match score",
      confirmBtn: "Same — merge",
      rejectBtn: "Different — keep both",
      uncalibratedNote: "Match scores are similarity estimates, not probabilities.",
    },
    modules: {
      bimanyay: {
        policyNumber: "Policy Number",
        denialCategoryPedNonDisclosure: "Pre-Existing Disease Non-Disclosure",
        denialCategoryRoomRentCapping: "Room Rent Proportionate Deduction",
        denialCategoryInvestigationOnly: "Observation / Diagnostic Hospitalization Only",
        denialCategoryDelayedIntimation: "Delayed Claim Intimation / Submission",
        heuristicDisclosure: "Rule-based estimate for this denial category — not derived from historical dispute outcomes.",
      },
      schemesetu: {
        criteriaEvaluated: "Evaluated for this result",
        criteriaNotEvaluated: "NOT evaluated — verify with official records",
        provisionalNotice: "Provisional estimate only. The criteria listed as not evaluated (such as SECC-2011 listing, age and documents) are not checked by this tool, so this is not a final eligibility decision.",
        provisionallyEligible: "Provisionally eligible",
        howToVerify: "How to verify:",
        nonDeterminative: "Recorded but not used to decide (no official income ceiling)",
        officialSources: "Official sources",
      },
      dawacheck: {
        prescriptionTranslatorTitle: "Prescription Shorthand Translator",
        prescriptionInputPlaceholder: "Paste doctor's instructions, e.g. Tab. Dolo 650mg TDS x 5 days",
        unrecognizedNotice: "Not recognized (not a standard abbreviation this tool knows): {tokens}",
      },
    },
  },
  hi: {
    appName: "आरोग्यरक्षक",
    resolution: {
      title: "संभावित दोहराव की पुष्टि करें",
      intro: "Kadi को आपके दस्तावेज़ों में ऐसी प्रविष्टियाँ मिलीं जो एक ही चीज़ हो सकती हैं। आपकी पुष्टि के बिना कुछ भी मिलाया नहीं जाता।",
      mentionLabel: "नई प्रविष्टि",
      existingLabel: "इस केस में पहले से",
      confidenceLabel: "मिलान स्कोर",
      confirmBtn: "एक ही हैं — मिलाएँ",
      rejectBtn: "अलग हैं — दोनों रखें",
      uncalibratedNote: "मिलान स्कोर समानता का अनुमान है, संभावना नहीं।",
    },
    modules: {
      bimanyay: {
        policyNumber: "पॉलिसी संख्या",
        denialCategoryPedNonDisclosure: "पूर्व-मौजूदा बीमारी की जानकारी न देना",
        denialCategoryRoomRentCapping: "कमरे के किराए की आनुपातिक कटौती",
        denialCategoryInvestigationOnly: "केवल जांच / निदान हेतु अस्पताल में भर्ती",
        denialCategoryDelayedIntimation: "दावे की देर से सूचना / प्रस्तुति",
        heuristicDisclosure: "इस अस्वीकृति श्रेणी के लिए नियम-आधारित अनुमान — पिछले विवादों के वास्तविक परिणामों पर आधारित नहीं।",
      },
      schemesetu: {
        criteriaEvaluated: "इस परिणाम हेतु जाँचे गए आधार",
        criteriaNotEvaluated: "जाँचे नहीं गए — आधिकारिक रिकॉर्ड से पुष्टि करें",
        provisionalNotice: "यह केवल एक अस्थायी अनुमान है। “जाँचे नहीं गए” के रूप में सूचीबद्ध मानदंड (जैसे SECC-2011 सूची, आयु और दस्तावेज़) इस टूल द्वारा नहीं जाँचे जाते, इसलिए यह अंतिम पात्रता निर्णय नहीं है।",
        provisionallyEligible: "अस्थायी रूप से पात्र",
        howToVerify: "पात्रता की पुष्टि कैसे करें:",
        nonDeterminative: "दर्ज किया गया, पर निर्णय में उपयोग नहीं (कोई आधिकारिक आय-सीमा नहीं)",
        officialSources: "आधिकारिक स्रोत",
      },
      dawacheck: {
        prescriptionTranslatorTitle: "पर्ची संक्षिप्त शब्द अनुवादक",
        prescriptionInputPlaceholder: "डॉक्टर के निर्देश यहाँ चिपकाएँ, जैसे Tab. Dolo 650mg TDS x 5 days",
        unrecognizedNotice: "पहचान नहीं हुई (यह मानक संक्षिप्त शब्द नहीं है): {tokens}",
      },
    },
  },
  mr: {
    appName: "आरोग्यरक्षक",
    resolution: {
      title: "संभाव्य दुहेरी नोंदींची खात्री करा",
      intro: "Kadi ला तुमच्या कागदपत्रांमध्ये अशा नोंदी सापडल्या ज्या एकाच गोष्टीबद्दल असू शकतात. तुमच्या खात्रीशिवाय काहीही एकत्र केले जात नाही.",
      mentionLabel: "नवीन नोंद",
      existingLabel: "या केसमध्ये आधीपासून",
      confidenceLabel: "जुळणी गुण",
      confirmBtn: "एकच आहेत — एकत्र करा",
      rejectBtn: "वेगळे आहेत — दोन्ही ठेवा",
      uncalibratedNote: "जुळणी गुण हे साम्याचा अंदाज आहेत, संभाव्यता नाही.",
    },
    modules: {
      bimanyay: {
        policyNumber: "पॉलिसी क्रमांक",
        denialCategoryPedNonDisclosure: "आधीच्या आजाराची माहिती न दिल्याने नकार",
        denialCategoryRoomRentCapping: "खोलीच्या भाड्याची प्रमाणशीर कपात",
        denialCategoryInvestigationOnly: "केवळ तपासणी / निदानासाठी रुग्णालयात दाखल",
        denialCategoryDelayedIntimation: "दाव्याची उशिरा सूचना / सादरीकरण",
        heuristicDisclosure: "या नाकारण्याच्या प्रकारासाठी नियमांवर आधारित अंदाज — मागील वादांच्या प्रत्यक्ष निकालांवर आधारित नाही.",
      },
      schemesetu: {
        criteriaEvaluated: "या निकालासाठी तपासलेले निकष",
        criteriaNotEvaluated: "तपासले गेलेले नाहीत — अधिकृत नोंदींद्वारे पडताळणी करा",
        provisionalNotice: "हा फक्त प्राथमिक अंदाज आहे. “तपासले गेलेले नाहीत” म्हणून दिलेले निकष (उदा. SECC-2011 यादी, वय आणि कागदपत्रे) या साधनाद्वारे तपासले जात नाहीत, त्यामुळे हा अंतिम पात्रता निर्णय नाही.",
        provisionallyEligible: "तात्पुरते पात्र",
        howToVerify: "पात्रतेची पडताळणी कशी करावी:",
        nonDeterminative: "नोंदवले, पण निर्णयासाठी वापरले नाही (अधिकृत उत्पन्न मर्यादा नाही)",
        officialSources: "अधिकृत स्रोत",
      },
      dawacheck: {
        prescriptionTranslatorTitle: "प्रिस्क्रिप्शन संक्षिप्त शब्द भाषांतरक",
        prescriptionInputPlaceholder: "डॉक्टरांच्या सूचना येथे चिकटवा, उदा. Tab. Dolo 650mg TDS x 5 days",
        unrecognizedNotice: "ओळखले गेले नाही (हा प्रमाणित संक्षेप नाही): {tokens}",
      },
    },
  },
};
