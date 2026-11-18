import type { Language } from "./shared/i18n/types";
import { common as sharedCommon } from "./shared/i18n/common";
import { shellCopy } from "./shell/shellCopy";

// Single definition lives in packages/i18n; re-exported so existing import paths keep working.
export type { Language };

export interface Translations {
  appName: string;
  tagline: string;
  byodBadge: string;
  byodDescription: string;
  tabs: {
    billnyay: string;
    bimanyay: string;
    daavisetu: string;
    schemesetu: string;
    dawacheck: string;
  };
  upload: {
    title: string;
    subtitle: string;
    dragDrop: string;
    browse: string;
    cameraCapture: string;
    consentText: string;
    consentRequired: string;
    processBtn: string;
    processing: string;
    zeroRetentionNotice: string;
  };
  stream: {
    statusHeading: string;
    agentOrchestration: string;
    stepOcr: string;
    stepEntities: string;
    stepAudit: string;
    stepComplete: string;
  };
  modules: {
    billnyay: {
      title: string;
      desc: string;
      chargedTotal: string;
      cghsBenchmark: string;
      potentialSavings: string;
      overchargesTitle: string;
      itemCol: string;
      chargedCol: string;
      cghsCol: string;
      varianceCol: string;
      statusCol: string;
      disputeGrounds: string;
      notBenchmarked: string;
      withinBenchmark: string;
      notBenchmarkedBadge: string;
      overchargedBadge: string;
      bundledBadge: string;
      fairBadge: string;
      unmatchedNotice: string;
    };
    bimanyay: {
      title: string;
      desc: string;
      formTitle: string;
      policyNumber: string;
      insurerName: string;
      policyAgeYears: string;
      claimedAmount: string;
      deniedAmount: string;
      denialCategory: string;
      denialCategoryPedNonDisclosure: string;
      denialCategoryRoomRentCapping: string;
      denialCategoryInvestigationOnly: string;
      denialCategoryDelayedIntimation: string;
      denialReason: string;
      diagnosis: string;
      analyzeBtn: string;
      analyzing: string;
      reversalScore: string;
      heuristicDisclosure: string;
      wrongfulBadge: string;
      violationsTitle: string;
      groTab: string;
      bimaBharosaTab: string;
      ombudsmanTab: string;
      copyDraft: string;
      copied: string;
      timelineTitle: string;
      tier1Label: string;
      tier2Label: string;
      tier3Label: string;
      tier1Desc: string;
      tier2Desc: string;
      tier3Desc: string;
      activeBadge: string;
      pendingBadge: string;
    };
    daavisetu: {
      title: string;
      desc: string;
      patientName: string;
      policyId: string;
      hospital: string;
      treatment: string;
      diagnosis: string;
      patientNamePlaceholder: string;
      policyIdPlaceholder: string;
      optionalFromDocument: string;
      generateBtn: string;
      preAuthSummary: string;
      downloadPackage: string;
    };
    schemesetu: {
      title: string;
      desc: string;
      annualIncome: string;
      state: string;
      socialCategory: string;
      medicalNeed: string;
      checkBtn: string;
      eligibleSchemes: string;
      pmjayCard: string;
      mjpjayCard: string;
      maxCoverage: string;
      criteriaEvaluated: string;
      criteriaNotEvaluated: string;
      provisionalNotice: string;
      provisionallyEligible: string;
      verificationNeeded: string;
      notEligible: string;
      howToClaim: string;
      howToVerify: string;
      nonDeterminative: string;
      officialSources: string;
      saveToCaseLabel: string;
      savedTriggered: string;
      savedNotReady: string;
      savedNoChange: string;
    };
    dawacheck: {
      title: string;
      desc: string;
      searchPlaceholder: string;
      searchBtn: string;
      brandName: string;
      genericName: string;
      mrp: string;
      nppaCeiling: string;
      statusOvercharged: string;
      statusFair: string;
      dataSourceNotice: string;
      complianceCol: string;
      prescriptionTranslatorTitle: string;
      prescriptionInputPlaceholder: string;
      translateBtn: string;
      unrecognizedNotice: string;
      recognizedBadge: string;
    };
  };
  resolution: {
    title: string;
    intro: string;
    mentionLabel: string;
    existingLabel: string;
    confidenceLabel: string;
    confirmBtn: string;
    rejectBtn: string;
    signalLexical: string;
    signalPhonetic: string;
    signalSemantic: string;
    signalUnavailable: string;
    uncalibratedNote: string;
  };
  footer: {
    disclaimer: string;
    statutoryNote: string;
    cghsRef: string;
    irdaiRef: string;
    nppaRef: string;
  };
}

export const translations: Record<Language, Translations> = {
  en: {
    appName: sharedCommon.en.appName,
    tagline: shellCopy.en.tagline,
    byodBadge: shellCopy.en.byodBadge,
    byodDescription: shellCopy.en.byodDescription,
    tabs: shellCopy.en.tabs,
    upload: {
      title: "Add a document to check",
      subtitle: "A hospital bill, discharge summary, insurer letter or prescription — one file at a time.",
      dragDrop: "Drop a file here, or choose one",
      browse: "Choose a file",
      cameraCapture: "Take a photo",
      consentText: "I consent to transient algorithmic analysis under ArogyaRakshak's Zero-Retention Policy.",
      consentRequired: "You must give consent before your document can be analysed.",
      processBtn: "Read this document",
      processing: "Running OCR & entity extraction...",
      // The original file is never stored; extracted details and a redacted excerpt are, until
      // the case is deleted or expires. No compliance certification is claimed.
      zeroRetentionNotice:
        "Your original file is never stored. Only the extracted details and a redacted text excerpt are kept, and they are deleted with the case.",
    },
    stream: {
      statusHeading: "Live Document Processing Stream",
      agentOrchestration: "Orchestrating autonomous agents across CGHS, NPPA & IRDAI benchmarks...",
      stepOcr: "Document OCR & Text Extraction",
      stepEntities: "Kadi Entity Extraction",
      stepAudit: "Saving Extracted Entities",
      stepComplete: "Extraction Complete — Ready for Module Audit",
    },
    resolution: {
      ...sharedCommon.en.resolution,
      signalLexical: "Spelling similarity",
      signalPhonetic: "Sound-alike (across scripts)",
      signalSemantic: "Meaning similarity",
      signalUnavailable: "not available",
    },
    modules: {
      billnyay: {
        title: "BillNyay — Hospital Bill Forensic Audit",
        desc: "Compares each bill line with CGHS reference rates (a curated subset). A large gap is a reason to ask the hospital for a justification — not proof of wrongdoing.",
        chargedTotal: "Total billed",
        cghsBenchmark: "CGHS reference (compared lines)",
        potentialSavings: "Above CGHS reference",
        overchargesTitle: "Flagged Hospital Line Items",
        itemCol: "Line Item",
        chargedCol: "Hospital Charged",
        cghsCol: "CGHS reference",
        varianceCol: "Above reference",
        statusCol: "Audit Status",
        disputeGrounds: "How to use this: CGHS rates are reference rates for CGHS beneficiaries, not a legal cap on private hospitals. Use a large gap to ask the hospital for an itemised justification or to support a complaint — it is not proof of overcharging.",
        notBenchmarked: "No CGHS benchmark",
        withinBenchmark: "Within CGHS reference",
        notBenchmarkedBadge: "Not benchmarked",
        overchargedBadge: "Above CGHS reference",
        bundledBadge: "Usually included in the room tariff — ask why it is billed separately",
        fairBadge: "Within reference",
        unmatchedNotice: "{count} line item(s) totalling {amount} have no CGHS benchmark and were NOT verified. They are not confirmed fair — review them manually.",
      },
      bimanyay: {
        ...sharedCommon.en.modules.bimanyay,
        title: "BimaNyay — Insurance Denial Appeals",
        desc: "Checks an insurer's denial against the IRDAI rules recorded in this project (including the 5-year moratorium) and drafts an appeal for each escalation step: the insurer's grievance officer, Bima Bharosa, and the Insurance Ombudsman.",
        formTitle: "Describe the denial",
        insurerName: "Insurance Company",
        policyAgeYears: "Continuous Policy Tenure (Years)",
        claimedAmount: "Total Claimed (₹)",
        deniedAmount: "Disallowed / Denied (₹)",
        denialCategory: "Denial Category",
        denialReason: "Repudiation Reason Quoted by Insurer",
        diagnosis: "Primary Clinical Diagnosis",
        analyzeBtn: "Check the denial and draft appeals",
        analyzing: "Checking the denial against IRDAI rules…",
        reversalScore: "Rule-based starting estimate",
        wrongfulBadge: "Grounds to contest found",
        violationsTitle: "Rules this denial may conflict with",
        groTab: "Tier 1: Insurer GRO Appeal",
        bimaBharosaTab: "Tier 2: Bima Bharosa (IGMS)",
        ombudsmanTab: "Tier 3: Ombudsman Form VI",
        copyDraft: "Copy this draft",
        copied: "Copied",
        timelineTitle: "Escalation deadlines",
        tier1Label: "Tier 1 (GRO): 15-Day Resolution Window",
        tier2Label: "Tier 2 (Bima Bharosa): 15-Day Regulatory Escalation",
        tier3Label: "Tier 3 (Ombudsman): 365-Day Limitation Period",
        tier1Desc: "Formal appeal pending with {insurer} GRO. Mandatory resolution window: 15 days.",
        tier2Desc: "Escalate via IRDAI Bima Bharosa portal if GRO fails to resolve or rejects claim.",
        tier3Desc: "Complaint to Insurance Ombudsman within 1 year (Ombudsman Rules 2017, r.14(3)(b)). Award binding on insurer; capped at ₹50 lakh incl. expenses (r.17(3)(ii), as amended by G.S.R. 828(E), 09.11.2023).",
        activeBadge: "Start here",
        pendingBadge: "Later step",
      },
      daavisetu: {
        title: "DaaviSetu — Cashless Pre-Authorisation Form",
        desc: "Checks which documents an insurer usually asks for, then fills a cashless pre-authorisation request laid out after the IRDAI Annexure-B form. You review it before the hospital desk sends it; it does not predict approval.",
        patientName: "Patient Full Name",
        diagnosis: "Clinical Diagnosis",
        patientNamePlaceholder: "Enter the patient's full name",
        policyIdPlaceholder: "Enter the policy number",
        optionalFromDocument: "Leave blank to use the uploaded document",
        policyId: "Health Policy ID",
        hospital: "Hospital / Provider Name",
        treatment: "Planned Procedure / Surgery",
        generateBtn: "Fill the pre-authorisation form",
        preAuthSummary: "Your pre-authorisation form",
        downloadPackage: "Download Pre-Auth Package",
      },
      schemesetu: {
        ...sharedCommon.en.modules.schemesetu,
        title: "SchemeSetu — Government Health Scheme Check",
        desc: "A provisional check against the published rules of Ayushman Bharat PM-JAY and Maharashtra's MJPJAY, with the official sources and the steps to confirm with a hospital help desk.",
        annualIncome: "Annual Family Income (₹)",
        state: "State of residence",
        socialCategory: "Social Category",
        medicalNeed: "Medical need (procedure or specialty)",
        checkBtn: "Check Scheme Eligibility",
        eligibleSchemes: "Schemes checked for you",
        pmjayCard: "Ayushman Bharat PM-JAY (₹5 Lakh / Year / Family)",
        mjpjayCard: "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
        maxCoverage: "Maximum Financial Protection",
        verificationNeeded: "Verification needed",
        notEligible: "Not eligible",
        howToClaim: "How to Claim:",
        saveToCaseLabel: "Save my annual income and state to this case so eligibility is re-checked when new documents arrive (optional)",
        savedTriggered: "Saved. A scheme now applies to this case — an eligibility check is running.",
        savedNotReady: "Saved. Upload a bill or discharge summary with a diagnosis or procedure to run the scheme check.",
        savedNoChange: "Saved. The same schemes apply as before, and a change in income alone does not change eligibility, so no new check was needed.",
      },
      dawacheck: {
        ...sharedCommon.en.modules.dawacheck,
        title: "DawaCheck — Medicine Price Check",
        desc: "Compares what you paid per tablet, capsule or vial with the NPPA ceiling price, for a curated subset of Schedule-I medicines. Medicines outside that subset are reported as not checked.",
        searchPlaceholder: "Enter Medicine / Formulation name (e.g. Paracetamol 650mg, Meropenem 1g)...",
        searchBtn: "Compare with the ceiling",
        brandName: "Medicine",
        genericName: "Matched reference",
        mrp: "What you paid",
        nppaCeiling: "NPPA Ceiling Price",
        statusOvercharged: "Above the NPPA ceiling",
        statusFair: "Within the NPPA ceiling",
        dataSourceNotice: "Checked against a curated subset of {count} NPPA Schedule-I formulations, not the full national list. A medicine absent from this tool is not confirmed uncontrolled.",
        complianceCol: "Compliance Status",
        translateBtn: "Explain the shorthand",
        recognizedBadge: "Recognized",
      },
    },
    footer: shellCopy.en.footer,
  },
  hi: {
    appName: sharedCommon.hi.appName,
    tagline: shellCopy.hi.tagline,
    byodBadge: shellCopy.hi.byodBadge,
    byodDescription: shellCopy.hi.byodDescription,
    tabs: shellCopy.hi.tabs,
    upload: {
      title: "अस्थायी दस्तावेज़ अपलोड",
      subtitle: "अस्पताल बिल, डिस्चार्ज सारांश या बीमा दावा अस्वीकृति पत्र अपलोड करें",
      dragDrop: "फ़ाइलें यहाँ खींचें और छोड़ें, या",
      browse: "फ़ाइल चुनें",
      cameraCapture: "कैमरे से फोटो लें",
      consentText: "मैं आरोग्यरक्षक की शून्य-संचयन नीति के तहत अस्थायी विश्लेषण की सहमति देता हूँ।",
      consentRequired: "आपके दस्तावेज़ के विश्लेषण से पहले आपकी सहमति आवश्यक है।",
      processBtn: "मल्टी-एजेंट ऑडिट शुरू करें",
      processing: "मल्टी-एजेंट पाइपलाइन द्वारा विश्लेषण जारी है...",
      // NEEDS NATIVE-SPEAKER QA (replaces an inaccurate "nothing is stored / DPDP-conformant" claim).
      zeroRetentionNotice:
        "आपकी मूल फ़ाइल कभी संग्रहीत नहीं की जाती। केवल निकाली गई जानकारी और गोपनीय अंश हटाया हुआ पाठ-अंश रखा जाता है, जो केस के साथ हटा दिया जाता है।",
    },
    stream: {
      statusHeading: "लाइव दस्तावेज़ प्रोसेसिंग स्थिति",
      agentOrchestration: "CGHS, NPPA एवं IRDAI मानकों के आधार पर स्वायत्त विश्लेषण जारी...",
      stepOcr: "दस्तावेज़ ओसीआर एवं टेक्स्ट निष्कर्षण",
      stepEntities: "Kadi एंटिटी निष्कर्षण",
      stepAudit: "निकाली गई एंटिटी सहेजी जा रही हैं",
      stepComplete: "निष्कर्षण पूर्ण — मॉड्यूल ऑडिट के लिए तैयार",
    },
    resolution: {
      ...sharedCommon.hi.resolution,
      signalLexical: "वर्तनी समानता",
      signalPhonetic: "उच्चारण समानता (लिपियों के पार)",
      signalSemantic: "अर्थ समानता",
      signalUnavailable: "उपलब्ध नहीं",
    },
    modules: {
      billnyay: {
        title: "बिलन्याय — अस्पताल बिल फॉरेन्सिक ऑडिट",
        // NEEDS NATIVE-SPEAKER QA: rewritten to remove "statutory cap" / Supreme Court claims.
        desc: "हर बिल मद की तुलना CGHS संदर्भ दरों (चुना हुआ अंश) से। बड़ा अंतर अस्पताल से स्पष्टीकरण माँगने का कारण है, गलत काम का प्रमाण नहीं।",
        chargedTotal: "अस्पताल द्वारा लिया गया कुल शुल्क",
        cghsBenchmark: "CGHS संदर्भ दर (तुलना किए गए मद)",
        potentialSavings: "CGHS संदर्भ से अधिक",
        overchargesTitle: "चिह्नित अधिक शुल्क वाले मद",
        itemCol: "मद का नाम",
        chargedCol: "अस्पताल शुल्क",
        cghsCol: "मानक दर",
        varianceCol: "अतिरिक्त राशि",
        statusCol: "लेखा-परीक्षा स्थिति",
        disputeGrounds: "उपयोग कैसे करें: CGHS दरें CGHS लाभार्थियों के लिए संदर्भ दरें हैं, निजी अस्पतालों पर कानूनी सीमा नहीं। बड़ा अंतर अस्पताल से मदवार स्पष्टीकरण माँगने का आधार है — अधिक शुल्क का प्रमाण नहीं।",
        notBenchmarked: "कोई CGHS मानक नहीं",
        withinBenchmark: "मानक के भीतर",
        notBenchmarkedBadge: "जाँच नहीं हुई",
        overchargedBadge: "CGHS संदर्भ से अधिक",
        bundledBadge: "पैकेज में शामिल — अलग से शुल्क नहीं",
        fairBadge: "संदर्भ के भीतर",
        unmatchedNotice: "{count} मद ({amount}) के लिए कोई CGHS मानक नहीं है, इनकी जाँच नहीं हुई। इन्हें उचित नहीं माना गया है — कृपया स्वयं जाँचें।",
      },
      bimanyay: {
        ...sharedCommon.hi.modules.bimanyay,
        title: "बीमान्याय — बीमा अस्वीकृति ऑडिट एवं शिकायत निवारण",
        desc: "IRDAI 2024 मास्टर सर्कुलर, 5-वर्षीय मोराटोरियम नियम के तहत अनुचित दावों की जांच और 3-स्तरीय अपील तैयार करना।",
        formTitle: "दावा अस्वीकृति विवरण",
        insurerName: "बीमा कंपनी",
        policyAgeYears: "पॉलिसी की निरंतर अवधि (वर्ष)",
        claimedAmount: "कुल दावा राशि (₹)",
        deniedAmount: "अस्वीकृत / काटी गई राशि (₹)",
        denialCategory: "अस्वीकृति श्रेणी",
        denialReason: "कंपनी द्वारा दिया गया कारण",
        diagnosis: "मुख्य बीमारी / निदान",
        analyzeBtn: "अस्वीकृति की विधिक जांच करें व अपील ड्राफ्ट करें",
        analyzing: "IRDAI नियमों के आधार पर जांच जारी...",
        reversalScore: "दावा पुनः स्वीकृत होने की संभावना",
        wrongfulBadge: "अनुचित अस्वीकृति का ठोस आधार पाया गया",
        violationsTitle: "संवैधानिक एवं विनियामक उल्लंघन",
        groTab: "स्तर 1: कंपनी GRO अपील पत्र",
        bimaBharosaTab: "स्तर 2: बीमा भरोसा (IGMS) सारांश",
        ombudsmanTab: "स्तर 3: बीमा लोकपाल फॉर्म VI",
        copyDraft: "अपील पत्र कॉपी करें",
        copied: "कॉपी कर लिया गया!",
        timelineTitle: "विधिक समय-सीमा (SLA) ट्रैकर",
        tier1Label: "स्तर 1 (GRO): 15-दिन समाधान विंडो",
        tier2Label: "स्तर 2 (बीमा भरोसा): 15-दिन विनियामक एस्केलेशन",
        tier3Label: "स्तर 3 (लोकपाल): 365-दिन परिसीमा अवधि",
        tier1Desc: "{insurer} GRO के समक्ष औपचारिक अपील लंबित है। अनिवार्य समाधान अवधि: 15 दिन।",
        tier2Desc: "यदि GRO समाधान नहीं करता या दावा अस्वीकार करता है, तो IRDAI बीमा भरोसा पोर्टल के माध्यम से आगे बढ़ाएं।",
        tier3Desc: "1 वर्ष के भीतर बीमा लोकपाल को शिकायत करें (लोकपाल नियम 2017, नियम 14(3)(b))। निर्णय बीमा कंपनी पर बाध्यकारी; खर्च सहित अधिकतम ₹50 लाख तक सीमित (नियम 17(3)(ii), G.S.R. 828(E), दिनांक 09.11.2023 द्वारा संशोधित)।",
        activeBadge: "सक्रिय",
        pendingBadge: "लंबित",
      },
      daavisetu: {
        title: "दावेसेतु — कैशलेस प्री-ऑथराइजेशन ऑटोमेशन",
        desc: "IRDAI मानकीकृत प्रारूप में कैशलेस अस्पताल भर्ती प्री-ऑथराइजेशन फॉर्म स्वतः भरना।",
        patientName: "मरीज का पूरा नाम",
        diagnosis: "नैदानिक निदान",
        patientNamePlaceholder: "रोगी का पूरा नाम दर्ज करें",
        policyIdPlaceholder: "पॉलिसी नंबर दर्ज करें",
        optionalFromDocument: "दस्तावेज़ से लेने के लिए खाली छोड़ें",
        policyId: "स्वास्थ्य पॉलिसी नंबर",
        hospital: "अस्पताल का नाम",
        treatment: "उपचार / प्रक्रिया",
        generateBtn: "प्री-ऑथराइजेशन फॉर्म तैयार करें",
        preAuthSummary: "तैयार प्री-ऑथराइजेशन विवरण",
        downloadPackage: "प्री-ऑथ पैकेज डाउनलोड करें",
      },
      schemesetu: {
        ...sharedCommon.hi.modules.schemesetu,
        title: "योजनासेतु — सरकारी स्वास्थ्य योजना मार्गदर्शन",
        desc: "आयुष्मान भारत PM-JAY एवं राज्य स्तरीय स्वास्थ्य योजनाओं में पात्रता की त्वरित जांच।",
        annualIncome: "वार्षिक पारिवारिक आय (₹)",
        state: "मूल निवासी राज्य",
        socialCategory: "सामाजिक वर्ग",
        medicalNeed: "चिकित्सीय उपचार की आवश्यकता",
        checkBtn: "पात्रता जांचें",
        eligibleSchemes: "पात्र सरकारी योजनाएं",
        pmjayCard: "आयुष्मान भारत PM-JAY (₹5 लाख प्रति वर्ष/परिवार)",
        mjpjayCard: "महात्मा ज्योतिराव फुले जन आरोग्य योजना (MJPJAY)",
        maxCoverage: "अधिकतम वित्तीय सुरक्षा",
        verificationNeeded: "पुष्टि आवश्यक",
        notEligible: "पात्र नहीं",
        howToClaim: "लाभ कैसे प्राप्त करें:",
        saveToCaseLabel: "मेरी वार्षिक आय और राज्य इस केस में सहेजें ताकि नए दस्तावेज़ आने पर पात्रता दोबारा जाँची जा सके (वैकल्पिक)",
        savedTriggered: "सहेजा गया। इस केस पर अब एक योजना लागू होती है — पात्रता जाँच चल रही है।",
        savedNotReady: "सहेजा गया। योजना जाँच के लिए निदान या प्रक्रिया वाला बिल या डिस्चार्ज सारांश अपलोड करें।",
        savedNoChange: "सहेजा गया। पहले जैसी ही योजनाएं लागू होती हैं, और केवल आय बदलने से पात्रता नहीं बदलती, इसलिए नई जाँच की ज़रूरत नहीं थी।",
      },
      dawacheck: {
        ...sharedCommon.hi.modules.dawacheck,
        title: "दवाचेक — NPPA अधिकतम मूल्य जांच",
        desc: "राष्ट्रीय औषधि मूल्य निर्धारण प्राधिकरण (NPPA) शेड्यूल-I के तहत दवा बिल की जांच।",
        searchPlaceholder: "दवा या साल्ट का नाम दर्ज करें (जैसे: Paracetamol 650mg, Meropenem)...",
        searchBtn: "मूल्य सीमा जांचें",
        brandName: "ब्रांड का नाम",
        genericName: "सक्रिय जेनेरिक साल्ट",
        mrp: "बिल किया गया MRP",
        nppaCeiling: "NPPA अधिकतम कानूनी दर",
        statusOvercharged: "अधिकतम सीमा से अधिक वसूला गया",
        statusFair: "NPPA नियमों के अनुसार उचित",
        dataSourceNotice: "यह जांच NPPA शेड्यूल-I की {count} चयनित औषधियों की सूची पर आधारित है, पूरी राष्ट्रीय सूची पर नहीं। इस सूची में न होने का अर्थ यह नहीं कि दवा मूल्य-नियंत्रण से मुक्त है।",
        complianceCol: "अनुपालन स्थिति",
        translateBtn: "निर्देश अनुवाद करें",
        recognizedBadge: "पहचाना गया",
      },
    },
    footer: shellCopy.hi.footer,
  },
  mr: {
    appName: sharedCommon.mr.appName,
    tagline: shellCopy.mr.tagline,
    byodBadge: shellCopy.mr.byodBadge,
    byodDescription: shellCopy.mr.byodDescription,
    tabs: shellCopy.mr.tabs,
    upload: {
      title: "तात्पुरते दस्तऐवज अपलोड",
      subtitle: "हॉस्पिटल बिल, डिस्चार्ज सारांश किंवा विमा नकार पत्र अपलोड करा",
      dragDrop: "फाइल्स येथे ड्रॅग आणि ड्रॉप करा, किंवा",
      browse: "फाइल निवडा",
      cameraCapture: "कॅमेऱ्याने फोटो काढा",
      consentText: "मी आरोग्यरक्षकच्या शून्य-संचयन धोरणांतर्गत तात्पुरत्या विश्लेषणास संमती देतो.",
      consentRequired: "तुमच्या दस्तऐवजाचे विश्लेषण करण्यापूर्वी तुमची संमती आवश्यक आहे.",
      processBtn: "मल्टी-एजंट ऑडिट सुरू करा",
      processing: "मल्टी-एजंट प्रणालीद्वारे तपासणी चालू आहे...",
      // NEEDS NATIVE-SPEAKER QA (replaces an inaccurate "nothing is stored / DPDP-compliant" claim).
      zeroRetentionNotice:
        "तुमची मूळ फाइल कधीही साठवली जात नाही. फक्त काढलेली माहिती आणि गोपनीय भाग काढलेला मजकूर-अंश ठेवला जातो, जो केससोबत हटवला जातो.",
    },
    stream: {
      statusHeading: "थेट दस्तऐवज प्रक्रिया स्थिती",
      agentOrchestration: "CGHS, NPPA आणि IRDAI मानकांनुसार तपासणी सुरू...",
      stepOcr: "दस्तऐवज OCR आणि मजकूर निष्कर्षण",
      stepEntities: "Kadi माहिती निष्कर्षण",
      stepAudit: "काढलेली माहिती जतन करत आहे",
      stepComplete: "निष्कर्षण पूर्ण — मॉड्यूल ऑडिटसाठी सज्ज",
    },
    resolution: {
      ...sharedCommon.mr.resolution,
      signalLexical: "स्पेलिंग साम्य",
      signalPhonetic: "उच्चार साम्य (लिपींच्या पलीकडे)",
      signalSemantic: "अर्थ साम्य",
      signalUnavailable: "उपलब्ध नाही",
    },
    modules: {
      billnyay: {
        title: "बिलन्याय — रुग्णालय बिल फॉरेन्सिक ऑडिट",
        // NEEDS NATIVE-SPEAKER QA: rewritten to remove "statutory cap" / Supreme Court claims.
        desc: "प्रत्येक बिल घटकाची CGHS संदर्भ दरांशी (निवडक भाग) तुलना. मोठा फरक हा रुग्णालयाकडे स्पष्टीकरण मागण्याचे कारण आहे, गैरव्यवहाराचा पुरावा नाही.",
        chargedTotal: "हॉस्पिटलने आकारलेले एकूण शुल्क",
        cghsBenchmark: "CGHS संदर्भ दर (तुलना केलेले घटक)",
        potentialSavings: "CGHS संदर्भापेक्षा जास्त",
        overchargesTitle: "जास्त दर आकारलेले घटक",
        itemCol: "घटकाचे नाव",
        chargedCol: "हॉस्पिटल शुल्क",
        cghsCol: "शासकीय दर",
        varianceCol: "अतिरिक्त रक्कम",
        statusCol: "लेखापरीक्षा स्थिती",
        disputeGrounds: "कसे वापरावे: CGHS दर हे CGHS लाभार्थ्यांसाठीचे संदर्भ दर आहेत, खासगी रुग्णालयांवरील कायदेशीर मर्यादा नाहीत. मोठा फरक रुग्णालयाकडे घटकनिहाय स्पष्टीकरण मागण्याचा आधार आहे — जादा आकारणीचा पुरावा नाही.",
        notBenchmarked: "CGHS मानक उपलब्ध नाही",
        withinBenchmark: "मानकाच्या आत",
        notBenchmarkedBadge: "पडताळणी झाली नाही",
        overchargedBadge: "CGHS संदर्भापेक्षा जास्त",
        bundledBadge: "पॅकेजमध्ये समाविष्ट — वेगळे शुल्क नाही",
        fairBadge: "संदर्भाच्या आत",
        unmatchedNotice: "{count} नोंदी ({amount}) साठी CGHS मानक नाही, त्यांची पडताळणी झालेली नाही. त्या योग्य ठरवलेल्या नाहीत — कृपया स्वतः तपासा.",
      },
      bimanyay: {
        ...sharedCommon.mr.modules.bimanyay,
        title: "बीमान्याय — विमा दावा नकार तपासणी व निवारण",
        desc: "IRDAI 2024 मास्टर सर्क्युलर, 5 वर्षांच्या मोराटोरियम नियमांतर्गत नकाराची तपासणी आणि 3-स्तरीय अपील.",
        formTitle: "विमा नकार तपशील",
        insurerName: "विमा कंपनीचे नाव",
        policyAgeYears: "पॉलिसीचे सलग चालू वर्षे",
        claimedAmount: "एकूण दावा रक्कम (₹)",
        deniedAmount: "नाकारलेली / कपात केलेली रक्कम (₹)",
        denialCategory: "नकाराचा प्रकार",
        denialReason: "विमा कंपनीने दिलेले कारण",
        diagnosis: "मुख्य आजार / निदान",
        analyzeBtn: "नकाराची कायदेशीर तपासणी करा व अपील ड्राफ्ट मिळवा",
        analyzing: "IRDAI नियमांनुसार तपासणी सुरू आहे...",
        reversalScore: "दावा मंजूर होण्याची शक्यता",
        wrongfulBadge: "विमा कंपनीचा नकार बेकायदेशीर असल्याचा पुरावा",
        violationsTitle: "कायदेशीर व विनियामक नियमभंग",
        groTab: "स्तर 1: विमा कंपनी GRO कडे अपील",
        bimaBharosaTab: "स्तर 2: विमा भरोसा (IGMS)",
        ombudsmanTab: "स्तर 3: विमा लोकपाल फॉर्म VI",
        copyDraft: "अपील पत्र कॉपी करा",
        copied: "कॉपी केले!",
        timelineTitle: "कायदेशीर मुदत (SLA) ट्रॅकर",
        tier1Label: "स्तर 1 (GRO): 15-दिवस मुदत",
        tier2Label: "स्तर 2 (विमा भरोसा): 15-दिवस एस्केलेशन",
        tier3Label: "स्तर 3 (लोकपाल): 365-दिवस मुदत",
        tier1Desc: "{insurer} GRO कडे औपचारिक अपील प्रलंबित आहे. अनिवार्य निराकरण कालावधी: 15 दिवस.",
        tier2Desc: "GRO ने निराकरण न केल्यास किंवा दावा नाकारल्यास IRDAI विमा भरोसा पोर्टलद्वारे पुढे न्या.",
        tier3Desc: "1 वर्षाच्या आत विमा लोकपालकडे तक्रार करा (लोकपाल नियम 2017, नियम 14(3)(b)). निर्णय विमा कंपनीवर बंधनकारक; खर्चासह जास्तीत जास्त ₹50 लाखांपर्यंत मर्यादित (नियम 17(3)(ii), G.S.R. 828(E), दिनांक 09.11.2023 नुसार सुधारित).",
        activeBadge: "सक्रिय",
        pendingBadge: "प्रलंबित",
      },
      daavisetu: {
        title: "दावेसेतु — कॅशलेस प्री-ऑथरायझेशन ऑटोमेशन",
        desc: "IRDAI मानकीकृत स्वरूपात कॅशलेस रुग्णालय भरती प्री-ऑथरायझेशन फॉर्म त्वरित तयार करणे.",
        patientName: "रुग्णाचे संपूर्ण नाव",
        diagnosis: "वैद्यकीय निदान",
        patientNamePlaceholder: "रुग्णाचे पूर्ण नाव भरा",
        policyIdPlaceholder: "पॉलिसी क्रमांक भरा",
        optionalFromDocument: "दस्तऐवजातून घेण्यासाठी रिकामे ठेवा",
        policyId: "आरोग्य विमा क्रमांक",
        hospital: "रुग्णालयाचे नाव",
        treatment: "उपचार / शस्त्रक्रिया",
        generateBtn: "प्री-ऑथरायझेशन फॉर्म तयार करा",
        preAuthSummary: "तयार केलेला तपशील",
        downloadPackage: "प्री-ऑथ पॅकेज डाउनलोड करा",
      },
      schemesetu: {
        ...sharedCommon.mr.modules.schemesetu,
        title: "योजनासेतु — शासकीय आरोग्य योजना मार्गदर्शक",
        desc: "आयुष्मान भारत PM-JAY आणि महात्मा ज्योतिराव फुले जन आरोग्य योजनेतील (MJPJAY) पात्रता तपासणी.",
        annualIncome: "वार्षिक कौटुंबिक उत्पन्न (₹)",
        state: "राज्य",
        socialCategory: "सामाजिक प्रवर्ग",
        medicalNeed: "आवश्यक वैद्यकीय उपचार",
        checkBtn: "पात्रता तपासा",
        eligibleSchemes: "पात्र शासकीय योजना",
        pmjayCard: "आयुष्मान भारत PM-JAY (₹5 लाख प्रति वर्ष/कुटुंब)",
        mjpjayCard: "महात्मा ज्योतिराव फुले जन आरोग्य योजना (MJPJAY)",
        maxCoverage: "कमाल आर्थिक संरक्षण",
        verificationNeeded: "पडताळणी आवश्यक",
        notEligible: "अपात्र",
        howToClaim: "लाभ कसा मिळवावा:",
        saveToCaseLabel: "नवीन कागदपत्रे आल्यावर पात्रता पुन्हा तपासता यावी म्हणून माझे वार्षिक उत्पन्न आणि राज्य या केसमध्ये जतन करा (ऐच्छिक)",
        savedTriggered: "जतन केले. या केसला आता एक योजना लागू होते — पात्रता तपासणी सुरू आहे.",
        savedNotReady: "जतन केले. योजना तपासणीसाठी निदान किंवा प्रक्रिया असलेले बिल किंवा डिस्चार्ज सारांश अपलोड करा.",
        savedNoChange: "जतन केले. पूर्वीप्रमाणेच योजना लागू होतात, आणि केवळ उत्पन्न बदलल्याने पात्रता बदलत नाही, त्यामुळे नवीन तपासणीची गरज नव्हती.",
      },
      dawacheck: {
        ...sharedCommon.mr.modules.dawacheck,
        title: "दवाचेक — NPPA औषध कमाल दर तपासणी",
        desc: "राष्ट्रीय औषध मूल्य निर्धारण प्राधिकरण (NPPA) शेड्यूल-I नुसार बिलातील औषध दरांची तपासणी.",
        searchPlaceholder: "औषधाचे नाव टाका (उदा. Paracetamol 650mg, Meropenem)...",
        searchBtn: "कमाल दर तपासा",
        brandName: "ब्रँडचे नाव",
        genericName: "मूळ जेनेरिक घटक",
        mrp: "आकारलेला MRP दर",
        nppaCeiling: "NPPA शासकीय कमाल दर",
        statusOvercharged: "शासकीय कमाल दरापेक्षा जास्त आकारणी",
        statusFair: "NPPA नियमानुसार योग्य दर",
        dataSourceNotice: "ही तपासणी NPPA शेड्यूल-I मधील निवडक {count} औषधांच्या यादीवर आधारित आहे, संपूर्ण राष्ट्रीय यादीवर नाही. या यादीत नसणे म्हणजे औषध किंमत-नियंत्रणमुक्त आहे असे नाही.",
        complianceCol: "अनुपालन स्थिती",
        translateBtn: "सूचनांचे भाषांतर करा",
        recognizedBadge: "ओळखले गेले",
      },
    },
    footer: shellCopy.mr.footer,
  },
};
