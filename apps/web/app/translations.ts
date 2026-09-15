export type Language = "en" | "hi" | "mr";

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
    appName: "ArogyaRakshak",
    tagline: "Statutory Healthcare Cost & Insurance Rights Intelligence",
    byodBadge: "BYOD: Zero Document Retention",
    byodDescription: "Files are parsed in transient RAM memory and purged immediately after extraction.",
    tabs: {
      billnyay: "BillNyay (Bill Audit)",
      bimanyay: "BimaNyay (Claim Denials)",
      daavisetu: "DaaviSetu (Pre-Auth)",
      schemesetu: "SchemeSetu (Schemes)",
      dawacheck: "DawaCheck (Medicine Ceiling)",
    },
    upload: {
      title: "Transient Document Intake",
      subtitle: "Upload hospital bills, discharge summaries, or claim rejection letters",
      dragDrop: "Drag & drop files here, or",
      browse: "Browse Files",
      cameraCapture: "Snap Photo / Camera",
      consentText: "I consent to transient algorithmic analysis under ArogyaRakshak's Zero-Retention Policy.",
      consentRequired: "You must give consent before your document can be analysed.",
      processBtn: "Extract Document Entities",
      processing: "Running OCR & entity extraction...",
      zeroRetentionNotice: "No documents are stored on any persistent server disk. Conforms to DPDP Act 2023.",
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
      title: "Please confirm possible duplicates",
      intro: "Kadi found entries in your documents that may refer to the same thing. Nothing is merged until you confirm.",
      mentionLabel: "New entry",
      existingLabel: "Already in this case",
      confidenceLabel: "Match score",
      confirmBtn: "Same — merge",
      rejectBtn: "Different — keep both",
      signalLexical: "Spelling similarity",
      signalPhonetic: "Sound-alike (across scripts)",
      signalSemantic: "Meaning similarity",
      signalUnavailable: "not available",
      uncalibratedNote: "Match scores are similarity estimates, not probabilities.",
    },
    modules: {
      billnyay: {
        title: "BillNyay — Hospital Bill Forensic Audit",
        desc: "Automated 5-agent line-item benchmark against notified CGHS rates & Supreme Court fair billing norms.",
        chargedTotal: "Total Hospital Charged",
        cghsBenchmark: "CGHS Mandated Cap",
        potentialSavings: "Unjustified Discrepancy",
        overchargesTitle: "Flagged Hospital Line Items",
        itemCol: "Line Item",
        chargedCol: "Hospital Charged",
        cghsCol: "Statutory Benchmark",
        varianceCol: "Excess Surcharge",
        statusCol: "Audit Status",
        disputeGrounds: "Dispute Grounds: Overcharging violates Supreme Court Consumer Protection precedents and standardized CGHS tariff guidelines.",
        notBenchmarked: "No CGHS benchmark",
        withinBenchmark: "Within Benchmark",
        notBenchmarkedBadge: "Not benchmarked",
        overchargedBadge: "Overcharged",
        bundledBadge: "Bundled — should not be billed separately",
        fairBadge: "Fair",
        unmatchedNotice: "{count} line item(s) totalling {amount} have no CGHS benchmark and were NOT verified. They are not confirmed fair — review them manually.",
      },
      bimanyay: {
        title: "BimaNyay — Insurance Denial & Grievance Engine",
        desc: "Audits insurance repudiations against IRDAI 2024 Master Circulars, 5-Year Moratorium rule & drafts 3-tier appeals.",
        formTitle: "Claim Repudiation Dossier",
        policyNumber: "Policy Number",
        insurerName: "Insurance Company",
        policyAgeYears: "Continuous Policy Tenure (Years)",
        claimedAmount: "Total Claimed (₹)",
        deniedAmount: "Disallowed / Denied (₹)",
        denialCategory: "Denial Category",
        denialCategoryPedNonDisclosure: "Pre-Existing Disease Non-Disclosure",
        denialCategoryRoomRentCapping: "Room Rent Proportionate Deduction",
        denialCategoryInvestigationOnly: "Observation / Diagnostic Hospitalization Only",
        denialCategoryDelayedIntimation: "Delayed Claim Intimation / Submission",
        denialReason: "Repudiation Reason Quoted by Insurer",
        diagnosis: "Primary Clinical Diagnosis",
        analyzeBtn: "Audit Denial Grounds & Draft Appeals",
        analyzing: "Auditing Clauses against IRDAI Mandates...",
        reversalScore: "Reversal Likelihood Probability",
        heuristicDisclosure: "Rule-based estimate for this denial category — not derived from historical dispute outcomes.",
        wrongfulBadge: "Wrongful Repudiation Ground Detected",
        violationsTitle: "Statutory & Regulatory Violations",
        groTab: "Tier 1: Insurer GRO Appeal",
        bimaBharosaTab: "Tier 2: Bima Bharosa (IGMS)",
        ombudsmanTab: "Tier 3: Ombudsman Form VI",
        copyDraft: "Copy Legal Draft",
        copied: "Copied to Clipboard!",
        timelineTitle: "Statutory SLA Escalation Tracker",
        tier1Label: "Tier 1 (GRO): 15-Day Resolution Window",
        tier2Label: "Tier 2 (Bima Bharosa): 15-Day Regulatory Escalation",
        tier3Label: "Tier 3 (Ombudsman): 365-Day Limitation Period",
        tier1Desc: "Formal appeal pending with {insurer} GRO. Mandatory resolution window: 15 days.",
        tier2Desc: "Escalate via IRDAI Bima Bharosa portal if GRO fails to resolve or rejects claim.",
        tier3Desc: "Complaint to Insurance Ombudsman within 1 year (Ombudsman Rules 2017, r.14(3)(b)). Award binding on insurer; capped at ₹50 lakh incl. expenses (r.17(3)(ii), as amended by G.S.R. 828(E), 09.11.2023).",
        activeBadge: "ACTIVE",
        pendingBadge: "PENDING",
      },
      daavisetu: {
        title: "DaaviSetu — Cashless Pre-Authorization Automation",
        desc: "Rapid cashless pre-authorization form generation conforming to standardized IRDAI claim formats.",
        patientName: "Patient Full Name",
        diagnosis: "Clinical Diagnosis",
        patientNamePlaceholder: "Enter the patient's full name",
        policyIdPlaceholder: "Enter the policy number",
        optionalFromDocument: "Leave blank to use the uploaded document",
        policyId: "Health Policy ID",
        hospital: "Hospital / Provider Name",
        treatment: "Planned Procedure / Surgery",
        generateBtn: "Auto-Fill Pre-Authorization Package",
        preAuthSummary: "Generated Pre-Auth Package",
        downloadPackage: "Download Pre-Auth Package",
      },
      schemesetu: {
        title: "SchemeSetu — Public Health Coverage Navigator",
        desc: "Intelligent eligibility assessment across Ayushman Bharat PM-JAY and State healthcare programs.",
        annualIncome: "Annual Family Income (₹)",
        state: "Domicile State",
        socialCategory: "Social Category",
        medicalNeed: "Required Medical Procedure / Specialty",
        checkBtn: "Check Scheme Eligibility",
        eligibleSchemes: "Eligible Government Health Schemes",
        pmjayCard: "Ayushman Bharat PM-JAY (₹5 Lakh / Year / Family)",
        mjpjayCard: "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
        maxCoverage: "Maximum Financial Protection",
        criteriaEvaluated: "Evaluated for this result",
        criteriaNotEvaluated: "NOT evaluated — verify with official records",
        provisionalNotice: "Provisional estimate only. The criteria listed as not evaluated (such as SECC-2011 listing, age and documents) are not checked by this tool, so this is not a final eligibility decision.",
        provisionallyEligible: "Provisionally eligible",
        verificationNeeded: "Verification needed",
        notEligible: "Not eligible",
        howToClaim: "How to Claim:",
        howToVerify: "How to verify:",
        nonDeterminative: "Recorded but not used to decide (no official income ceiling)",
        officialSources: "Official sources",
        saveToCaseLabel: "Save my annual income and state to this case so eligibility is re-checked when new documents arrive (optional)",
        savedTriggered: "Saved. A scheme now applies to this case — an eligibility check is running.",
        savedNotReady: "Saved. Upload a bill or discharge summary with a diagnosis or procedure to run the scheme check.",
        savedNoChange: "Saved. The same schemes apply as before, and a change in income alone does not change eligibility, so no new check was needed.",
      },
      dawacheck: {
        title: "DawaCheck — NPPA Ceiling Price Benchmark",
        desc: "Verifies pharmacy bill prices against National Pharmaceutical Pricing Authority (NPPA) Schedule-I ceilings.",
        searchPlaceholder: "Enter Medicine / Formulation name (e.g. Paracetamol 650mg, Meropenem 1g)...",
        searchBtn: "Verify Ceiling Price",
        brandName: "Brand Formulation",
        genericName: "Active Generic Salt",
        mrp: "Billed MRP",
        nppaCeiling: "NPPA Ceiling Price",
        statusOvercharged: "Overcharged vs Statutory Cap",
        statusFair: "Compliant with NPPA Cap",
        dataSourceNotice: "Checked against a curated subset of {count} NPPA Schedule-I formulations, not the full national list. A medicine absent from this tool is not confirmed uncontrolled.",
        complianceCol: "Compliance Status",
      },
    },
    footer: {
      disclaimer: "ArogyaRakshak provides statutory auditing intelligence based on public regulatory frameworks (CGHS, NPPA, IRDAI).",
      statutoryNote: "All calculations cite official public data sources. Zero patient health data is retained after your active browser session.",
      cghsRef: "CGHS OM 2024 Tariffs",
      irdaiRef: "IRDAI Master Circular May 2024",
      nppaRef: "NPPA DPCO Schedule-I",
    },
  },
  hi: {
    appName: "आरोग्यरक्षक",
    tagline: "संवैधानिक स्वास्थ्य खर्च और बीमा अधिकार विश्लेषण",
    byodBadge: "BYOD: शून्य दस्तावेज़ संचयन नीति",
    byodDescription: "दस्तावेज़ केवल अस्थायी रैम (RAM) में प्रोसेस होते हैं और निष्कर्षण के तुरंत बाद हटा दिए जाते हैं।",
    tabs: {
      billnyay: "बिलन्याय (बिल ऑडिट)",
      bimanyay: "बीमान्याय (बीमा दावे)",
      daavisetu: "दावेसेतु (प्री-ऑथ फॉर्म)",
      schemesetu: "योजनासेतु (सरकारी योजनाएं)",
      dawacheck: "दवाचेक (दवा मूल्य सीमा)",
    },
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
      zeroRetentionNotice: "सर्वर डिस्क पर कोई दस्तावेज़ सुरक्षित नहीं रखा जाता। DPDP अधिनियम 2023 के अनुरूप।",
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
      title: "संभावित दोहराव की पुष्टि करें",
      intro: "Kadi को आपके दस्तावेज़ों में ऐसी प्रविष्टियाँ मिलीं जो एक ही चीज़ हो सकती हैं। आपकी पुष्टि के बिना कुछ भी मिलाया नहीं जाता।",
      mentionLabel: "नई प्रविष्टि",
      existingLabel: "इस केस में पहले से",
      confidenceLabel: "मिलान स्कोर",
      confirmBtn: "एक ही हैं — मिलाएँ",
      rejectBtn: "अलग हैं — दोनों रखें",
      signalLexical: "वर्तनी समानता",
      signalPhonetic: "उच्चारण समानता (लिपियों के पार)",
      signalSemantic: "अर्थ समानता",
      signalUnavailable: "उपलब्ध नहीं",
      uncalibratedNote: "मिलान स्कोर समानता का अनुमान है, संभावना नहीं।",
    },
    modules: {
      billnyay: {
        title: "बिलन्याय — अस्पताल बिल फॉरेन्सिक ऑडिट",
        desc: "CGHS अधिसूचित दरों एवं सर्वोच्च न्यायालय के दिशा-निर्देशों के अनुसार अस्पताल बिलों का स्वचालित ऑडिट।",
        chargedTotal: "अस्पताल द्वारा लिया गया कुल शुल्क",
        cghsBenchmark: "CGHS वैधानिक दर सीमा",
        potentialSavings: "अन्यायपूर्ण अतिरिक्त शुल्क",
        overchargesTitle: "चिह्नित अधिक शुल्क वाले मद",
        itemCol: "मद का नाम",
        chargedCol: "अस्पताल शुल्क",
        cghsCol: "मानक दर",
        varianceCol: "अतिरिक्त राशि",
        statusCol: "लेखा-परीक्षा स्थिति",
        disputeGrounds: "आपत्ति का आधार: अत्यधिक शुल्क सर्वोच्च न्यायालय के उपभोक्ता संरक्षण निर्णयों और CGHS नियमों का उल्लंघन करता है।",
        notBenchmarked: "कोई CGHS मानक नहीं",
        withinBenchmark: "मानक के भीतर",
        notBenchmarkedBadge: "जाँच नहीं हुई",
        overchargedBadge: "अधिक शुल्क",
        bundledBadge: "पैकेज में शामिल — अलग से शुल्क नहीं",
        fairBadge: "उचित",
        unmatchedNotice: "{count} मद ({amount}) के लिए कोई CGHS मानक नहीं है, इनकी जाँच नहीं हुई। इन्हें उचित नहीं माना गया है — कृपया स्वयं जाँचें।",
      },
      bimanyay: {
        title: "बीमान्याय — बीमा अस्वीकृति ऑडिट एवं शिकायत निवारण",
        desc: "IRDAI 2024 मास्टर सर्कुलर, 5-वर्षीय मोराटोरियम नियम के तहत अनुचित दावों की जांच और 3-स्तरीय अपील तैयार करना।",
        formTitle: "दावा अस्वीकृति विवरण",
        policyNumber: "पॉलिसी संख्या",
        insurerName: "बीमा कंपनी",
        policyAgeYears: "पॉलिसी की निरंतर अवधि (वर्ष)",
        claimedAmount: "कुल दावा राशि (₹)",
        deniedAmount: "अस्वीकृत / काटी गई राशि (₹)",
        denialCategory: "अस्वीकृति श्रेणी",
        denialCategoryPedNonDisclosure: "पूर्व-मौजूदा बीमारी की जानकारी न देना",
        denialCategoryRoomRentCapping: "कमरे के किराए की आनुपातिक कटौती",
        denialCategoryInvestigationOnly: "केवल जांच / निदान हेतु अस्पताल में भर्ती",
        denialCategoryDelayedIntimation: "दावे की देर से सूचना / प्रस्तुति",
        denialReason: "कंपनी द्वारा दिया गया कारण",
        diagnosis: "मुख्य बीमारी / निदान",
        analyzeBtn: "अस्वीकृति की विधिक जांच करें व अपील ड्राफ्ट करें",
        analyzing: "IRDAI नियमों के आधार पर जांच जारी...",
        reversalScore: "दावा पुनः स्वीकृत होने की संभावना",
        heuristicDisclosure: "इस अस्वीकृति श्रेणी के लिए नियम-आधारित अनुमान — पिछले विवादों के वास्तविक परिणामों पर आधारित नहीं।",
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
        criteriaEvaluated: "इस परिणाम हेतु जाँचे गए आधार",
        criteriaNotEvaluated: "जाँचे नहीं गए — आधिकारिक रिकॉर्ड से पुष्टि करें",
        provisionalNotice: "यह केवल एक अस्थायी अनुमान है। “जाँचे नहीं गए” के रूप में सूचीबद्ध मानदंड (जैसे SECC-2011 सूची, आयु और दस्तावेज़) इस टूल द्वारा नहीं जाँचे जाते, इसलिए यह अंतिम पात्रता निर्णय नहीं है।",
        provisionallyEligible: "अस्थायी रूप से पात्र",
        verificationNeeded: "पुष्टि आवश्यक",
        notEligible: "पात्र नहीं",
        howToClaim: "लाभ कैसे प्राप्त करें:",
        howToVerify: "पात्रता की पुष्टि कैसे करें:",
        nonDeterminative: "दर्ज किया गया, पर निर्णय में उपयोग नहीं (कोई आधिकारिक आय-सीमा नहीं)",
        officialSources: "आधिकारिक स्रोत",
        saveToCaseLabel: "मेरी वार्षिक आय और राज्य इस केस में सहेजें ताकि नए दस्तावेज़ आने पर पात्रता दोबारा जाँची जा सके (वैकल्पिक)",
        savedTriggered: "सहेजा गया। इस केस पर अब एक योजना लागू होती है — पात्रता जाँच चल रही है।",
        savedNotReady: "सहेजा गया। योजना जाँच के लिए निदान या प्रक्रिया वाला बिल या डिस्चार्ज सारांश अपलोड करें।",
        savedNoChange: "सहेजा गया। पहले जैसी ही योजनाएं लागू होती हैं, और केवल आय बदलने से पात्रता नहीं बदलती, इसलिए नई जाँच की ज़रूरत नहीं थी।",
      },
      dawacheck: {
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
      },
    },
    footer: {
      disclaimer: "आरोग्यरक्षक सार्वजनिक विनियामक नियमों (CGHS, NPPA, IRDAI) के आधार पर सूचनात्मक विश्लेषण प्रदान करता है।",
      statutoryNote: "सभी गणनाएं आधिकारिक सार्वजनिक स्रोतों पर आधारित हैं। ब्राउज़र सत्र समाप्त होने के बाद कोई डेटा संचित नहीं रहता।",
      cghsRef: "CGHS दरें 2024",
      irdaiRef: "IRDAI मास्टर सर्कुलर मई 2024",
      nppaRef: "NPPA DPCO शेड्यूल-I",
    },
  },
  mr: {
    appName: "आरोग्यरक्षक",
    tagline: "वैधानिक आरोग्य खर्च व विमा हक्क मार्गदर्शन",
    byodBadge: "BYOD: शून्य दस्तऐवज संचयन",
    byodDescription: "दस्तऐवज फक्त तात्पुरत्या रॅम (RAM) मध्ये तपासले जातात आणि लगेच नष्ट केले जातात.",
    tabs: {
      billnyay: "बिलन्याय (बिल ऑडिट)",
      bimanyay: "बीमान्याय (विमा दावे)",
      daavisetu: "दावेसेतु (प्री-ऑथ फॉर्म)",
      schemesetu: "योजनासेतु (सरकारी योजना)",
      dawacheck: "दवाचेक (औषध कमाल किंमत)",
    },
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
      zeroRetentionNotice: "कोणताही डेटा सर्व्हर डिस्कवर साठवला जात नाही. DPDP कायदा 2023 चे पालन.",
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
      title: "संभाव्य दुहेरी नोंदींची खात्री करा",
      intro: "Kadi ला तुमच्या कागदपत्रांमध्ये अशा नोंदी सापडल्या ज्या एकाच गोष्टीबद्दल असू शकतात. तुमच्या खात्रीशिवाय काहीही एकत्र केले जात नाही.",
      mentionLabel: "नवीन नोंद",
      existingLabel: "या केसमध्ये आधीपासून",
      confidenceLabel: "जुळणी गुण",
      confirmBtn: "एकच आहेत — एकत्र करा",
      rejectBtn: "वेगळे आहेत — दोन्ही ठेवा",
      signalLexical: "स्पेलिंग साम्य",
      signalPhonetic: "उच्चार साम्य (लिपींच्या पलीकडे)",
      signalSemantic: "अर्थ साम्य",
      signalUnavailable: "उपलब्ध नाही",
      uncalibratedNote: "जुळणी गुण हे साम्याचा अंदाज आहेत, संभाव्यता नाही.",
    },
    modules: {
      billnyay: {
        title: "बिलन्याय — रुग्णालय बिल फॉरेन्सिक ऑडिट",
        desc: "CGHS अधिसूचित दर आणि सर्वोच्च न्यायालयाच्या मार्गदर्शक तत्त्वांनुसार बिलांची अचूक तपासणी.",
        chargedTotal: "हॉस्पिटलने आकारलेले एकूण शुल्क",
        cghsBenchmark: "CGHS वैधानिक दर मर्यादा",
        potentialSavings: "अवाजवी जादा आकारणी",
        overchargesTitle: "जास्त दर आकारलेले घटक",
        itemCol: "घटकाचे नाव",
        chargedCol: "हॉस्पिटल शुल्क",
        cghsCol: "शासकीय दर",
        varianceCol: "अतिरिक्त रक्कम",
        statusCol: "लेखापरीक्षा स्थिती",
        disputeGrounds: "तक्रारीचा आधार: जास्त दर आकारणी सर्वोच्च न्यायालयाच्या ग्राहक संरक्षण नियमांचा व CGHS दरांचा भंग करते.",
        notBenchmarked: "CGHS मानक उपलब्ध नाही",
        withinBenchmark: "मानकाच्या आत",
        notBenchmarkedBadge: "पडताळणी झाली नाही",
        overchargedBadge: "जादा आकारणी",
        bundledBadge: "पॅकेजमध्ये समाविष्ट — वेगळे शुल्क नाही",
        fairBadge: "योग्य",
        unmatchedNotice: "{count} नोंदी ({amount}) साठी CGHS मानक नाही, त्यांची पडताळणी झालेली नाही. त्या योग्य ठरवलेल्या नाहीत — कृपया स्वतः तपासा.",
      },
      bimanyay: {
        title: "बीमान्याय — विमा दावा नकार तपासणी व निवारण",
        desc: "IRDAI 2024 मास्टर सर्क्युलर, 5 वर्षांच्या मोराटोरियम नियमांतर्गत नकाराची तपासणी आणि 3-स्तरीय अपील.",
        formTitle: "विमा नकार तपशील",
        policyNumber: "पॉलिसी क्रमांक",
        insurerName: "विमा कंपनीचे नाव",
        policyAgeYears: "पॉलिसीचे सलग चालू वर्षे",
        claimedAmount: "एकूण दावा रक्कम (₹)",
        deniedAmount: "नाकारलेली / कपात केलेली रक्कम (₹)",
        denialCategory: "नकाराचा प्रकार",
        denialCategoryPedNonDisclosure: "आधीच्या आजाराची माहिती न दिल्याने नकार",
        denialCategoryRoomRentCapping: "खोलीच्या भाड्याची प्रमाणशीर कपात",
        denialCategoryInvestigationOnly: "केवळ तपासणी / निदानासाठी रुग्णालयात दाखल",
        denialCategoryDelayedIntimation: "दाव्याची उशिरा सूचना / सादरीकरण",
        denialReason: "विमा कंपनीने दिलेले कारण",
        diagnosis: "मुख्य आजार / निदान",
        analyzeBtn: "नकाराची कायदेशीर तपासणी करा व अपील ड्राफ्ट मिळवा",
        analyzing: "IRDAI नियमांनुसार तपासणी सुरू आहे...",
        reversalScore: "दावा मंजूर होण्याची शक्यता",
        heuristicDisclosure: "या नाकारण्याच्या प्रकारासाठी नियमांवर आधारित अंदाज — मागील वादांच्या प्रत्यक्ष निकालांवर आधारित नाही.",
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
        criteriaEvaluated: "या निकालासाठी तपासलेले निकष",
        criteriaNotEvaluated: "तपासले गेलेले नाहीत — अधिकृत नोंदींद्वारे पडताळणी करा",
        provisionalNotice: "हा फक्त प्राथमिक अंदाज आहे. “तपासले गेलेले नाहीत” म्हणून दिलेले निकष (उदा. SECC-2011 यादी, वय आणि कागदपत्रे) या साधनाद्वारे तपासले जात नाहीत, त्यामुळे हा अंतिम पात्रता निर्णय नाही.",
        provisionallyEligible: "तात्पुरते पात्र",
        verificationNeeded: "पडताळणी आवश्यक",
        notEligible: "अपात्र",
        howToClaim: "लाभ कसा मिळवावा:",
        howToVerify: "पात्रतेची पडताळणी कशी करावी:",
        nonDeterminative: "नोंदवले, पण निर्णयासाठी वापरले नाही (अधिकृत उत्पन्न मर्यादा नाही)",
        officialSources: "अधिकृत स्रोत",
        saveToCaseLabel: "नवीन कागदपत्रे आल्यावर पात्रता पुन्हा तपासता यावी म्हणून माझे वार्षिक उत्पन्न आणि राज्य या केसमध्ये जतन करा (ऐच्छिक)",
        savedTriggered: "जतन केले. या केसला आता एक योजना लागू होते — पात्रता तपासणी सुरू आहे.",
        savedNotReady: "जतन केले. योजना तपासणीसाठी निदान किंवा प्रक्रिया असलेले बिल किंवा डिस्चार्ज सारांश अपलोड करा.",
        savedNoChange: "जतन केले. पूर्वीप्रमाणेच योजना लागू होतात, आणि केवळ उत्पन्न बदलल्याने पात्रता बदलत नाही, त्यामुळे नवीन तपासणीची गरज नव्हती.",
      },
      dawacheck: {
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
      },
    },
    footer: {
      disclaimer: "आरोग्यरक्षक सार्वजनिक विनियामक नियमांवर (CGHS, NPPA, IRDAI) आधारित माहितीपर विश्लेषण प्रदान करते.",
      statutoryNote: "सर्व आकडेवारी अधिकृत शासकीय स्रोतांवर आधारित आहे. वापरानंतर कोणताही वैयक्तिक डेटा साठवला जात नाही.",
      cghsRef: "CGHS दर 2024",
      irdaiRef: "IRDAI मास्टर सर्क्युलर मे 2024",
      nppaRef: "NPPA DPCO शेड्यूल-I",
    },
  },
};
