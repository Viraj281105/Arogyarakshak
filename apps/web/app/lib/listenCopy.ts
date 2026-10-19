/**
 * Curated, static copy for the read-aloud / simple-language feature (ADR-015).
 *
 * No LLM and no runtime translation: every sentence a person hears is a fixed string below,
 * filled with structured values (counts, dates, amounts) from the result. Kept in a separate
 * file from translations.ts so the two stay independently editable; the shape is identical
 * across en/hi/mr and tests/listen.test.ts enforces key and {placeholder} parity.
 *
 * NEEDS NATIVE-SPEAKER QA: every Hindi (hi) and Marathi (mr) string in this file is a
 * machine-assisted draft and must be reviewed by a native speaker before being presented as
 * final. In particular the simple-language variants must stay short and must not change the
 * meaning (what is a deadline, what is only an estimate) of the standard variant.
 */

import type { Language } from "../translations";

/** A sentence in two registers: `standard` (formal) and `simple` (short, everyday words). */
export interface Register {
  standard: string;
  simple: string;
}

export interface ListenCopy {
  ui: {
    listen: string;
    stop: string;
    /** {panel} is the panel's title. */
    listenAria: string;
    stopAria: string;
    reading: string;
    noLocalVoice: string;
    unsupported: string;
    onDeviceNote: string;
    simpleToggle: string;
    simpleToggleHelp: string;
    summaryLabel: string;
  };
  panels: {
    deadline: string;
    readiness: string;
    medicine: string;
    appeal: string;
  };
  deadline: {
    intro: Register;
    /** {tier} {status} {date} */
    event: Register;
    /** {tier} {status} */
    eventNoDate: Register;
    tiers: { LEVEL_1_GRO: Register; LEVEL_2_BIMA_BHAROSA: Register; LEVEL_3_OMBUDSMAN: Register };
    /** {n} */
    tierFallback: Register;
    status: { ACTIVE: Register; OVERDUE: Register; COMPLETED: Register; PENDING: Register };
    statusFallback: Register;
  };
  readiness: {
    /** {found} {total} */
    headline: Register;
    /** {n} */
    missing: Register;
    /** {n} */
    needsDoctor: Register;
    /** {n} */
    notConfirmed: Register;
    allPresent: Register;
    scope: Register;
  };
  medicine: {
    /** {brand} {ingredient} */
    intro: Register;
    /** {billed} {ceiling} */
    above: Register;
    /** {billed} {ceiling} */
    within: Register;
    cannotCompare: Register;
    genericListed: Register;
  };
  appeal: {
    wrongful: Register;
    notWrongful: Register;
    /** {n} */
    violations: Register;
    noViolations: Register;
    drafts: Register;
    /** {pct} */
    estimate: Register;
    checkBeforeSending: Register;
  };
}

export const listenCopy: Record<Language, ListenCopy> = {
  en: {
    ui: {
      listen: "Listen",
      stop: "Stop",
      listenAria: "Listen to the summary: {panel}",
      stopAria: "Stop reading aloud",
      reading: "Reading aloud…",
      noLocalVoice:
        "No on-device voice for this language, so reading aloud is unavailable. Nothing is sent to an online voice service.",
      unsupported: "This browser cannot read aloud. Nothing is sent to an online voice service.",
      onDeviceNote: "Reading aloud uses a voice on this device. Nothing is sent online.",
      simpleToggle: "Simple language",
      simpleToggleHelp: "Short, plain sentences in the summaries that can be read aloud.",
      summaryLabel: "Summary",
    },
    panels: {
      deadline: "Deadlines",
      readiness: "Document check",
      medicine: "Medicine price",
      appeal: "Appeal",
    },
    deadline: {
      intro: {
        standard: "Statutory grievance escalation timeline for this claim.",
        simple: "Here are your next steps and the last date for each.",
      },
      event: {
        standard: "{tier} Status: {status}. Deadline: {date}.",
        simple: "{tier} {status}. Last date: {date}.",
      },
      eventNoDate: {
        standard: "{tier} Status: {status}.",
        simple: "{tier} {status}.",
      },
      tiers: {
        LEVEL_1_GRO: {
          standard: "Level 1: representation to the insurer's Grievance Redressal Officer.",
          simple: "Step 1: write to the insurance company's complaints officer.",
        },
        LEVEL_2_BIMA_BHAROSA: {
          standard: "Level 2: escalation through the Bima Bharosa grievance portal.",
          simple: "Step 2: complain on the Bima Bharosa website.",
        },
        LEVEL_3_OMBUDSMAN: {
          standard: "Level 3: complaint to the Insurance Ombudsman.",
          simple: "Step 3: complain to the Insurance Ombudsman.",
        },
      },
      tierFallback: { standard: "Stage {n}.", simple: "Step {n}." },
      status: {
        ACTIVE: { standard: "current stage", simple: "Do this now" },
        OVERDUE: { standard: "deadline has passed", simple: "The last date has gone by" },
        COMPLETED: { standard: "completed", simple: "Done" },
        PENDING: { standard: "a later stage", simple: "For later" },
      },
      statusFallback: { standard: "status not recognised", simple: "Status not clear" },
    },
    readiness: {
      headline: {
        standard: "Documentation readiness: {found} of {total} commonly requested documents were found.",
        simple: "{found} of {total} papers were found.",
      },
      missing: {
        standard: "{n} not found in the case text.",
        simple: "{n} could not be found.",
      },
      needsDoctor: {
        standard: "{n} clinical facts need a doctor's confirmation.",
        simple: "{n} need a doctor to confirm.",
      },
      notConfirmed: {
        standard: "{n} were not confirmed by a reviewer.",
        simple: "{n} were not confirmed by the reviewer.",
      },
      allPresent: {
        standard: "No documents are missing from this check.",
        simple: "Nothing is missing in this check.",
      },
      scope: {
        standard: "This checks documentation only. It does not predict whether the claim will be approved.",
        simple: "This only checks papers. It does not say if the claim will be approved.",
      },
    },
    medicine: {
      intro: {
        standard: "Price check for {brand}, containing {ingredient}.",
        simple: "Price check for {brand}, which has {ingredient}.",
      },
      above: {
        standard:
          "The billed price is {billed} rupees per unit. The NPPA ceiling is {ceiling} rupees per unit. The billed price is above the ceiling.",
        simple:
          "You were charged {billed} rupees for each unit. The government limit is {ceiling} rupees. You were charged more than the limit.",
      },
      within: {
        standard:
          "The billed price is {billed} rupees per unit. The NPPA ceiling is {ceiling} rupees per unit. The billed price is within the ceiling.",
        simple:
          "You were charged {billed} rupees for each unit. The government limit is {ceiling} rupees. You were not charged more than the limit.",
      },
      cannotCompare: {
        standard: "The price per unit could not be established, so no comparison with the ceiling was made.",
        simple: "We could not work out the price for one unit, so we cannot say if the price is fair.",
      },
      genericListed: {
        standard: "A generic alternative is listed on the screen.",
        simple: "A cheaper generic medicine is shown on the screen.",
      },
    },
    appeal: {
      wrongful: {
        standard: "On the rules checked, this denial appears to be wrongful.",
        simple: "On the rules we checked, this denial looks wrong.",
      },
      notWrongful: {
        standard: "The rules checked did not find a clear ground to call this denial wrongful.",
        simple: "The rules we checked did not find a clear reason to call this denial wrong.",
      },
      violations: {
        standard: "{n} possible regulatory violations were identified.",
        simple: "We found {n} places where the insurer may have broken the rules.",
      },
      noViolations: {
        standard: "No regulatory violations were identified.",
        simple: "We did not find places where the insurer broke the rules.",
      },
      drafts: {
        standard: "Draft appeals are prepared for the grievance officer, Bima Bharosa and the Ombudsman.",
        simple: "Draft letters are ready for the complaints officer, Bima Bharosa and the Ombudsman.",
      },
      estimate: {
        standard: "The figure of {pct} percent is a rule-based starting estimate, not a probability from past cases.",
        simple: "The {pct} percent figure is only a rough guess from fixed rules. It is not based on past cases.",
      },
      checkBeforeSending: {
        standard: "Check every detail of the drafts before sending them.",
        simple: "Please check every detail before you send the letters.",
      },
    },
  },

  hi: {
    // NEEDS NATIVE-SPEAKER QA (whole block)
    ui: {
      listen: "सुनें",
      stop: "रोकें",
      listenAria: "सारांश सुनें: {panel}",
      stopAria: "पढ़कर सुनाना रोकें",
      reading: "पढ़कर सुनाया जा रहा है…",
      noLocalVoice:
        "इस भाषा के लिए इस डिवाइस पर कोई आवाज़ नहीं है, इसलिए पढ़कर सुनाना उपलब्ध नहीं है। कुछ भी ऑनलाइन आवाज़ सेवा को नहीं भेजा जाता।",
      unsupported: "यह ब्राउज़र पढ़कर नहीं सुना सकता। कुछ भी ऑनलाइन आवाज़ सेवा को नहीं भेजा जाता।",
      onDeviceNote: "पढ़कर सुनाने के लिए इसी डिवाइस की आवाज़ इस्तेमाल होती है। कुछ भी ऑनलाइन नहीं भेजा जाता।",
      simpleToggle: "सरल भाषा",
      simpleToggleHelp: "सुनाए जा सकने वाले सारांशों में छोटे, सादे वाक्य।",
      summaryLabel: "सारांश",
    },
    panels: {
      deadline: "समय-सीमाएँ",
      readiness: "दस्तावेज़ जाँच",
      medicine: "दवा की कीमत",
      appeal: "अपील",
    },
    deadline: {
      intro: {
        standard: "इस दावे के लिए शिकायत बढ़ाने की वैधानिक समय-सारणी।",
        simple: "ये आपके अगले कदम हैं और हर कदम की आखिरी तारीख।",
      },
      event: {
        standard: "{tier} स्थिति: {status}। अंतिम तिथि: {date}।",
        simple: "{tier} {status}। आखिरी तारीख: {date}।",
      },
      eventNoDate: {
        standard: "{tier} स्थिति: {status}।",
        simple: "{tier} {status}।",
      },
      tiers: {
        LEVEL_1_GRO: {
          standard: "स्तर 1: बीमाकर्ता के शिकायत निवारण अधिकारी को प्रतिवेदन।",
          simple: "पहला कदम: बीमा कंपनी के शिकायत अधिकारी को लिखें।",
        },
        LEVEL_2_BIMA_BHAROSA: {
          standard: "स्तर 2: बीमा भरोसा शिकायत पोर्टल के माध्यम से आगे बढ़ाना।",
          simple: "दूसरा कदम: बीमा भरोसा वेबसाइट पर शिकायत करें।",
        },
        LEVEL_3_OMBUDSMAN: {
          standard: "स्तर 3: बीमा लोकपाल को शिकायत।",
          simple: "तीसरा कदम: बीमा लोकपाल से शिकायत करें।",
        },
      },
      tierFallback: { standard: "चरण {n}।", simple: "कदम {n}।" },
      status: {
        ACTIVE: { standard: "वर्तमान चरण", simple: "अभी यह करें" },
        OVERDUE: { standard: "समय-सीमा बीत चुकी है", simple: "आखिरी तारीख निकल गई है" },
        COMPLETED: { standard: "पूर्ण", simple: "हो गया" },
        PENDING: { standard: "आगे का चरण", simple: "बाद के लिए" },
      },
      statusFallback: { standard: "स्थिति पहचानी नहीं गई", simple: "स्थिति साफ़ नहीं है" },
    },
    readiness: {
      headline: {
        standard: "दस्तावेज़ तैयारी: सामान्यतः माँगे जाने वाले {total} दस्तावेज़ों में से {found} मिले।",
        simple: "{total} कागज़ों में से {found} मिले।",
      },
      missing: {
        standard: "{n} केस के पाठ में नहीं मिले।",
        simple: "{n} नहीं मिले।",
      },
      needsDoctor: {
        standard: "{n} चिकित्सीय तथ्यों के लिए डॉक्टर की पुष्टि चाहिए।",
        simple: "{n} के लिए डॉक्टर की पुष्टि चाहिए।",
      },
      notConfirmed: {
        standard: "{n} की समीक्षक ने पुष्टि नहीं की।",
        simple: "{n} की समीक्षक ने पुष्टि नहीं की।",
      },
      allPresent: {
        standard: "इस जाँच में कोई दस्तावेज़ कम नहीं है।",
        simple: "इस जाँच में कुछ भी कम नहीं है।",
      },
      scope: {
        standard: "यह केवल दस्तावेज़ों की जाँच है। यह नहीं बताती कि दावा स्वीकृत होगा या नहीं।",
        simple: "यह सिर्फ़ कागज़ों की जाँच है। यह नहीं बताती कि दावा मंज़ूर होगा या नहीं।",
      },
    },
    medicine: {
      intro: {
        standard: "{brand} की कीमत की जाँच, जिसमें {ingredient} है।",
        simple: "{brand} की कीमत की जाँच। इसमें {ingredient} है।",
      },
      above: {
        standard:
          "बिल में प्रति इकाई कीमत {billed} रुपये है। एनपीपीए की अधिकतम सीमा प्रति इकाई {ceiling} रुपये है। बिल की कीमत सीमा से ऊपर है।",
        simple:
          "आपसे हर एक दवा के {billed} रुपये लिए गए। सरकारी सीमा {ceiling} रुपये है। आपसे सीमा से ज़्यादा लिया गया।",
      },
      within: {
        standard:
          "बिल में प्रति इकाई कीमत {billed} रुपये है। एनपीपीए की अधिकतम सीमा प्रति इकाई {ceiling} रुपये है। बिल की कीमत सीमा के भीतर है।",
        simple:
          "आपसे हर एक दवा के {billed} रुपये लिए गए। सरकारी सीमा {ceiling} रुपये है। आपसे सीमा से ज़्यादा नहीं लिया गया।",
      },
      cannotCompare: {
        standard: "प्रति इकाई कीमत तय नहीं हो सकी, इसलिए सीमा से तुलना नहीं की गई।",
        simple: "एक दवा की कीमत पता नहीं चल सकी, इसलिए हम नहीं कह सकते कि कीमत ठीक है या नहीं।",
      },
      genericListed: {
        standard: "स्क्रीन पर एक जेनेरिक विकल्प दिखाया गया है।",
        simple: "स्क्रीन पर सस्ती जेनेरिक दवा दिखाई गई है।",
      },
    },
    appeal: {
      wrongful: {
        standard: "जाँचे गए नियमों के अनुसार यह अस्वीकृति अनुचित प्रतीत होती है।",
        simple: "जो नियम हमने देखे, उनके हिसाब से यह इनकार गलत लगता है।",
      },
      notWrongful: {
        standard: "जाँचे गए नियमों में इस अस्वीकृति को अनुचित कहने का कोई स्पष्ट आधार नहीं मिला।",
        simple: "जो नियम हमने देखे, उनमें इस इनकार को गलत कहने की कोई साफ़ वजह नहीं मिली।",
      },
      violations: {
        standard: "{n} संभावित नियामकीय उल्लंघन पहचाने गए।",
        simple: "हमें {n} जगह मिलीं जहाँ बीमा कंपनी ने नियम तोड़े हो सकते हैं।",
      },
      noViolations: {
        standard: "कोई नियामकीय उल्लंघन नहीं पहचाना गया।",
        simple: "हमें ऐसी कोई जगह नहीं मिली जहाँ बीमा कंपनी ने नियम तोड़े हों।",
      },
      drafts: {
        standard: "शिकायत अधिकारी, बीमा भरोसा और लोकपाल के लिए अपील के मसौदे तैयार हैं।",
        simple: "शिकायत अधिकारी, बीमा भरोसा और लोकपाल के लिए पत्र के मसौदे तैयार हैं।",
      },
      estimate: {
        standard: "{pct} प्रतिशत का आँकड़ा नियमों पर आधारित शुरुआती अनुमान है, पिछले मामलों से निकली संभावना नहीं।",
        simple: "{pct} प्रतिशत सिर्फ़ तय नियमों से लगाया मोटा अंदाज़ा है। यह पिछले मामलों पर आधारित नहीं है।",
      },
      checkBeforeSending: {
        standard: "भेजने से पहले मसौदों की हर जानकारी जाँच लें।",
        simple: "पत्र भेजने से पहले हर जानकारी ज़रूर जाँच लें।",
      },
    },
  },

  mr: {
    // NEEDS NATIVE-SPEAKER QA (whole block)
    ui: {
      listen: "ऐका",
      stop: "थांबवा",
      listenAria: "सारांश ऐका: {panel}",
      stopAria: "वाचून दाखवणे थांबवा",
      reading: "वाचून दाखवत आहे…",
      noLocalVoice:
        "या भाषेसाठी या डिव्हाइसवर आवाज उपलब्ध नाही, त्यामुळे वाचून दाखवणे शक्य नाही. काहीही ऑनलाइन आवाज सेवेला पाठवले जात नाही.",
      unsupported: "हा ब्राउझर वाचून दाखवू शकत नाही. काहीही ऑनलाइन आवाज सेवेला पाठवले जात नाही.",
      onDeviceNote: "वाचून दाखवण्यासाठी याच डिव्हाइसचा आवाज वापरला जातो. काहीही ऑनलाइन पाठवले जात नाही.",
      simpleToggle: "सोपी भाषा",
      simpleToggleHelp: "ऐकवता येणाऱ्या सारांशांमध्ये लहान, सोपी वाक्ये.",
      summaryLabel: "सारांश",
    },
    panels: {
      deadline: "अंतिम मुदती",
      readiness: "कागदपत्र तपासणी",
      medicine: "औषधाची किंमत",
      appeal: "अपील",
    },
    deadline: {
      intro: {
        standard: "या दाव्यासाठी तक्रार पुढे नेण्याचे वैधानिक वेळापत्रक.",
        simple: "हे तुमचे पुढचे टप्पे आणि प्रत्येकाची शेवटची तारीख आहे.",
      },
      event: {
        standard: "{tier} स्थिती: {status}. अंतिम तारीख: {date}.",
        simple: "{tier} {status}. शेवटची तारीख: {date}.",
      },
      eventNoDate: {
        standard: "{tier} स्थिती: {status}.",
        simple: "{tier} {status}.",
      },
      tiers: {
        LEVEL_1_GRO: {
          standard: "स्तर १: विमा कंपनीच्या तक्रार निवारण अधिकाऱ्याकडे निवेदन.",
          simple: "पहिला टप्पा: विमा कंपनीच्या तक्रार अधिकाऱ्याला लिहा.",
        },
        LEVEL_2_BIMA_BHAROSA: {
          standard: "स्तर २: बिमा भरोसा तक्रार पोर्टलद्वारे पुढे नेणे.",
          simple: "दुसरा टप्पा: बिमा भरोसा संकेतस्थळावर तक्रार करा.",
        },
        LEVEL_3_OMBUDSMAN: {
          standard: "स्तर ३: विमा लोकपालाकडे तक्रार.",
          simple: "तिसरा टप्पा: विमा लोकपालाकडे तक्रार करा.",
        },
      },
      tierFallback: { standard: "टप्पा {n}.", simple: "टप्पा {n}." },
      status: {
        ACTIVE: { standard: "सध्याचा टप्पा", simple: "आता हे करा" },
        OVERDUE: { standard: "मुदत संपली आहे", simple: "शेवटची तारीख उलटून गेली आहे" },
        COMPLETED: { standard: "पूर्ण", simple: "झाले" },
        PENDING: { standard: "पुढील टप्पा", simple: "नंतरसाठी" },
      },
      statusFallback: { standard: "स्थिती ओळखता आली नाही", simple: "स्थिती स्पष्ट नाही" },
    },
    readiness: {
      headline: {
        standard: "कागदपत्र तयारी: सहसा मागितल्या जाणाऱ्या {total} कागदपत्रांपैकी {found} सापडली.",
        simple: "{total} कागदांपैकी {found} सापडले.",
      },
      missing: {
        standard: "{n} केसच्या मजकुरात सापडली नाहीत.",
        simple: "{n} सापडले नाहीत.",
      },
      needsDoctor: {
        standard: "{n} वैद्यकीय तथ्यांसाठी डॉक्टरांची पुष्टी आवश्यक आहे.",
        simple: "{n} साठी डॉक्टरांनी पुष्टी करणे गरजेचे आहे.",
      },
      notConfirmed: {
        standard: "{n} ची समीक्षकाने पुष्टी केली नाही.",
        simple: "{n} ची समीक्षकाने पुष्टी केली नाही.",
      },
      allPresent: {
        standard: "या तपासणीत कोणतेही कागदपत्र कमी नाही.",
        simple: "या तपासणीत काहीही कमी नाही.",
      },
      scope: {
        standard: "ही फक्त कागदपत्रांची तपासणी आहे. दावा मंजूर होईल की नाही हे ती सांगत नाही.",
        simple: "ही फक्त कागदांची तपासणी आहे. दावा मंजूर होईल का ते ती सांगत नाही.",
      },
    },
    medicine: {
      intro: {
        standard: "{brand} या औषधाची किंमत तपासणी; त्यात {ingredient} आहे.",
        simple: "{brand} ची किंमत तपासणी. त्यात {ingredient} आहे.",
      },
      above: {
        standard:
          "बिलातील प्रति नग किंमत {billed} रुपये आहे. एनपीपीएची कमाल मर्यादा प्रति नग {ceiling} रुपये आहे. बिलातील किंमत मर्यादेपेक्षा जास्त आहे.",
        simple:
          "तुमच्याकडून प्रत्येक नगामागे {billed} रुपये घेतले. सरकारी मर्यादा {ceiling} रुपये आहे. तुमच्याकडून मर्यादेपेक्षा जास्त घेतले.",
      },
      within: {
        standard:
          "बिलातील प्रति नग किंमत {billed} रुपये आहे. एनपीपीएची कमाल मर्यादा प्रति नग {ceiling} रुपये आहे. बिलातील किंमत मर्यादेत आहे.",
        simple:
          "तुमच्याकडून प्रत्येक नगामागे {billed} रुपये घेतले. सरकारी मर्यादा {ceiling} रुपये आहे. तुमच्याकडून मर्यादेपेक्षा जास्त घेतले नाही.",
      },
      cannotCompare: {
        standard: "प्रति नग किंमत निश्चित करता आली नाही, म्हणून मर्यादेशी तुलना केली नाही.",
        simple: "एका नगाची किंमत समजली नाही, म्हणून किंमत योग्य आहे की नाही हे सांगता येत नाही.",
      },
      genericListed: {
        standard: "स्क्रीनवर जेनेरिक पर्याय दाखवला आहे.",
        simple: "स्क्रीनवर स्वस्त जेनेरिक औषध दाखवले आहे.",
      },
    },
    appeal: {
      wrongful: {
        standard: "तपासलेल्या नियमांनुसार हा नकार अयोग्य दिसतो.",
        simple: "आम्ही पाहिलेल्या नियमांनुसार हा नकार चुकीचा वाटतो.",
      },
      notWrongful: {
        standard: "तपासलेल्या नियमांमध्ये या नकाराला अयोग्य म्हणण्याचा स्पष्ट आधार सापडला नाही.",
        simple: "आम्ही पाहिलेल्या नियमांमध्ये या नकाराला चुकीचा म्हणण्याचे स्पष्ट कारण सापडले नाही.",
      },
      violations: {
        standard: "{n} संभाव्य नियामक उल्लंघने ओळखली गेली.",
        simple: "विमा कंपनीने नियम मोडले असू शकतात अशा {n} जागा आम्हाला सापडल्या.",
      },
      noViolations: {
        standard: "कोणतेही नियामक उल्लंघन ओळखले गेले नाही.",
        simple: "विमा कंपनीने नियम मोडले अशी कोणतीही जागा आम्हाला सापडली नाही.",
      },
      drafts: {
        standard: "तक्रार अधिकारी, बिमा भरोसा आणि लोकपाल यांच्यासाठी अपीलचे मसुदे तयार आहेत.",
        simple: "तक्रार अधिकारी, बिमा भरोसा आणि लोकपाल यांच्यासाठी पत्रांचे मसुदे तयार आहेत.",
      },
      estimate: {
        standard: "{pct} टक्के हा आकडा नियमांवर आधारित सुरुवातीचा अंदाज आहे, मागील प्रकरणांवरून काढलेली शक्यता नाही.",
        simple: "{pct} टक्के हा फक्त ठरलेल्या नियमांवरून काढलेला ढोबळ अंदाज आहे. तो मागील प्रकरणांवर आधारित नाही.",
      },
      checkBeforeSending: {
        standard: "पाठवण्यापूर्वी मसुद्यांतील प्रत्येक तपशील तपासा.",
        simple: "पत्रे पाठवण्यापूर्वी प्रत्येक तपशील नक्की तपासा.",
      },
    },
  },
};
