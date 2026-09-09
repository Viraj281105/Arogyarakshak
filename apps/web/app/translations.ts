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
      disputeGrounds: string;
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
      denialReason: string;
      diagnosis: string;
      analyzeBtn: string;
      analyzing: string;
      reversalScore: string;
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
    };
    daavisetu: {
      title: string;
      desc: string;
      patientName: string;
      policyId: string;
      hospital: string;
      treatment: string;
      generateBtn: string;
      preAuthSummary: string;
      downloadPackage: string;
    };
    schemesetu: {
      title: string;
      desc: string;
      annualIncome: string;
      state: string;
      medicalNeed: string;
      checkBtn: string;
      eligibleSchemes: string;
      pmjayCard: string;
      mjpjayCard: string;
      maxCoverage: string;
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
    };
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
      processBtn: "Run Multi-Agent Audit",
      processing: "Analyzing with Multi-Agent Pipeline...",
      zeroRetentionNotice: "No documents are stored on any persistent server disk. Conforms to DPDP Act 2023.",
    },
    stream: {
      statusHeading: "Live Agent Pipeline Stream",
      agentOrchestration: "Orchestrating autonomous agents across CGHS, NPPA & IRDAI benchmarks...",
      stepOcr: "Document OCR & Devanagari Transliteration",
      stepEntities: "Cross-Lingual Entity Resolution (IndicSBERT)",
      stepAudit: "CGHS Rate Benchmark & Regulatory Clause Audit",
      stepComplete: "Dossier & Statutory Grievance Package Ready",
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
        disputeGrounds: "Dispute Grounds: Overcharging violates Supreme Court Consumer Protection precedents and standardized CGHS tariff guidelines.",
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
        denialReason: "Repudiation Reason Quoted by Insurer",
        diagnosis: "Primary Clinical Diagnosis",
        analyzeBtn: "Audit Denial Grounds & Draft Appeals",
        analyzing: "Auditing Clauses against IRDAI Mandates...",
        reversalScore: "Reversal Likelihood Probability",
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
      },
      daavisetu: {
        title: "DaaviSetu — Cashless Pre-Authorization Automation",
        desc: "Rapid cashless pre-authorization form generation conforming to standardized IRDAI claim formats.",
        patientName: "Patient Full Name",
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
        medicalNeed: "Required Medical Procedure / Specialty",
        checkBtn: "Check Scheme Eligibility",
        eligibleSchemes: "Eligible Government Health Schemes",
        pmjayCard: "Ayushman Bharat PM-JAY (₹5 Lakh / Year / Family)",
        mjpjayCard: "Mahatma Jyotirao Phule Jan Arogya Yojana (MJPJAY)",
        maxCoverage: "Maximum Financial Protection",
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
      processBtn: "मल्टी-एजेंट ऑडिट शुरू करें",
      processing: "मल्टी-एजेंट पाइपलाइन द्वारा विश्लेषण जारी है...",
      zeroRetentionNotice: "सर्वर डिस्क पर कोई दस्तावेज़ सुरक्षित नहीं रखा जाता। DPDP अधिनियम 2023 के अनुरूप।",
    },
    stream: {
      statusHeading: "लाइव एजेंट पाइपलाइन स्थिति",
      agentOrchestration: "CGHS, NPPA एवं IRDAI मानकों के आधार पर स्वायत्त विश्लेषण जारी...",
      stepOcr: "दस्तावेज़ ओसीआर एवं देवनागरी लिप्यंतरण",
      stepEntities: "क्रॉस-भाषाई मेडिकल एंटिटी पहचान (IndicSBERT)",
      stepAudit: "CGHS दर एवं विनियामक खंड ऑडिट",
      stepComplete: "विधिक अपील एवं शिकायत पत्र तैयार",
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
        disputeGrounds: "आपत्ति का आधार: अत्यधिक शुल्क सर्वोच्च न्यायालय के उपभोक्ता संरक्षण निर्णयों और CGHS नियमों का उल्लंघन करता है।",
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
      },
      daavisetu: {
        title: "दावेसेतु — कैशलेस प्री-ऑथराइजेशन ऑटोमेशन",
        desc: "IRDAI मानकीकृत प्रारूप में कैशलेस अस्पताल भर्ती प्री-ऑथराइजेशन फॉर्म स्वतः भरना।",
        patientName: "मरीज का पूरा नाम",
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
        medicalNeed: "चिकित्सीय उपचार की आवश्यकता",
        checkBtn: "पात्रता जांचें",
        eligibleSchemes: "पात्र सरकारी योजनाएं",
        pmjayCard: "आयुष्मान भारत PM-JAY (₹5 लाख प्रति वर्ष/परिवार)",
        mjpjayCard: "महात्मा ज्योतिराव फुले जन आरोग्य योजना (MJPJAY)",
        maxCoverage: "अधिकतम वित्तीय सुरक्षा",
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
      processBtn: "मल्टी-एजंट ऑडिट सुरू करा",
      processing: "मल्टी-एजंट प्रणालीद्वारे तपासणी चालू आहे...",
      zeroRetentionNotice: "कोणताही डेटा सर्व्हर डिस्कवर साठवला जात नाही. DPDP कायदा 2023 चे पालन.",
    },
    stream: {
      statusHeading: "थेट एजंट प्रणाली स्थिती",
      agentOrchestration: "CGHS, NPPA आणि IRDAI मानकांनुसार तपासणी सुरू...",
      stepOcr: "दस्तऐवज OCR आणि देवनागरी लिप्यंतरण",
      stepEntities: "क्रॉस-भाषिक वैद्यकीय माहिती संकलन (IndicSBERT)",
      stepAudit: "CGHS दर व कायदेशीर नियमांचे ऑडिट",
      stepComplete: "कायदेशीर तक्रार व अपील संच तयार",
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
        disputeGrounds: "तक्रारीचा आधार: जास्त दर आकारणी सर्वोच्च न्यायालयाच्या ग्राहक संरक्षण नियमांचा व CGHS दरांचा भंग करते.",
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
      },
      daavisetu: {
        title: "दावेसेतु — कॅशलेस प्री-ऑथरायझेशन ऑटोमेशन",
        desc: "IRDAI मानकीकृत स्वरूपात कॅशलेस रुग्णालय भरती प्री-ऑथरायझेशन फॉर्म त्वरित तयार करणे.",
        patientName: "रुग्णाचे संपूर्ण नाव",
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
        medicalNeed: "आवश्यक वैद्यकीय उपचार",
        checkBtn: "पात्रता तपासा",
        eligibleSchemes: "पात्र शासकीय योजना",
        pmjayCard: "आयुष्मान भारत PM-JAY (₹5 लाख प्रति वर्ष/कुटुंब)",
        mjpjayCard: "महात्मा ज्योतिराव फुले जन आरोग्य योजना (MJPJAY)",
        maxCoverage: "कमाल आर्थिक संरक्षण",
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
