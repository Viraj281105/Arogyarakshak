export type Language = 'en' | 'hi' | 'mr';

export interface MobileTranslations {
  appName: string;
  tagline: string;
  byodBadge: string;
  byodDescription: string;
  offlineNotice: string;
  offlineSubtext: string;
  tabs: {
    home: string;
    billnyay: string;
    daavisetu: string;
    bimanyay: string;
    schemesetu: string;
    dawacheck: string;
  };
  scanner: {
    title: string;
    subtitle: string;
    instruction: string;
    billMode: string;
    denialMode: string;
    prescriptionMode: string;
    capture: string;
    retake: string;
    process: string;
    cameraPermissionTitle: string;
    cameraPermissionMsg: string;
    grantPermission: string;
    transientMemoryNotice: string;
    consentText: string;
    consentRequired: string;
    scanFirst: string;
  };
  resolution: {
    title: string;
    intro: string;
    mentionLabel: string;
    existingLabel: string;
    confidenceLabel: string;
    confirmBtn: string;
    rejectBtn: string;
    unavailable: string;
    uncalibratedNote: string;
  };
  modules: {
    billnyay: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
      cardTitle: string;
      cardBody: string;
      auditing: string;
      auditResults: string;
      charged: string;
      cghsCap: string;
      flagged: string;
      fair: string;
      notBenchmarked: string;
      unmatchedNotice: string;
      scanBillBtn: string;
      activeCaseReady: string;
      deleteCaseBtn: string;
      deleteCaseConfirmTitle: string;
      deleteCaseConfirmBody: string;
      draftAppealBtn: string;
      drafting: string;
      appealTitle: string;
      appealApprove: string;
      appealNeedsRevision: string;
      appealLlmBacked: string;
      appealTemplateNotice: string;
      appealFactsNotExtracted: string;
      downloadAppealPdf: string;
      shareAppealBtn: string;
    };
    daavisetu: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
      cardTitle: string;
      patientName: string;
      policyId: string;
      hospitalName: string;
      treatmentPlan: string;
      generating: string;
      generateBtn: string;
      scanFirstPrompt: string;
      generatedTitle: string;
      patient: string;
      policy: string;
      hospital: string;
      diagnosis: string;
      treatment: string;
      cost: string;
      status: string;
      readyForReview: string;
      downloadPdf: string;
      downloadPackage: string;
    };
    bimanyay: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
      cardTitle: string;
      policyNumber: string;
      insurerName: string;
      policyAge: string;
      claimedAmount: string;
      deniedAmount: string;
      denialCategoryLabel: string;
      denialCategoryPedNonDisclosure: string;
      denialCategoryRoomRentCapping: string;
      denialCategoryInvestigationOnly: string;
      denialCategoryDelayedIntimation: string;
      denialReason: string;
      diagnosis: string;
      auditBtn: string;
      auditing: string;
      reversalScore: string;
      heuristicDisclosure: string;
      wrongful: string;
      copyDraft: string;
      groTab: string;
      bharosaTab: string;
      ombudsmanTab: string;
      timelineTitle: string;
    };
    schemesetu: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
      cardTitle: string;
      income: string;
      state: string;
      category: string;
      medicalNeed: string;
      checkBtn: string;
      checking: string;
      provisionallyEligible: string;
      needsVerification: string;
      notEligible: string;
      howToClaim: string;
      howToVerify: string;
      nonDeterminative: string;
      officialSources: string;
      noMatches: string;
      criteriaEvaluated: string;
      criteriaNotEvaluated: string;
      provisionalNotice: string;
    };
    dawacheck: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
      cardTitle: string;
      brandOrGeneric: string;
      chargedMrp: string;
      quickSamples: string;
      checkBtn: string;
      checking: string;
      scanStrip: string;
      activeApi: string;
      overcharged: string;
      fairPrice: string;
      nppaCap: string;
      deviation: string;
      genericAvailable: string;
      statutoryNoticeTitle: string;
      statutoryNoticeBody: string;
      dataSourceNotice: string;
      prescriptionTranslatorTitle: string;
      prescriptionInputPlaceholder: string;
      translateBtn: string;
      unrecognizedNotice: string;
    };
  };
  common: {
    language: string;
    theme: string;
    light: string;
    dark: string;
    cancel: string;
    close: string;
    loading: string;
    delete: string;
    deleteCaseBtn: string;
    deleteCaseConfirmTitle: string;
    deleteCaseConfirmBody: string;
  };
}

export const translations: Record<Language, MobileTranslations> = {
  en: {
    appName: 'ArogyaRakshak',
    tagline: 'Healthcare Protection, Claim Justice & Welfare Access',
    byodBadge: 'Zero Retention (BYOD)',
    byodDescription: 'Processed in transient memory. No permanent medical document storage.',
    offlineNotice: 'No Internet Connection',
    offlineSubtext: 'Some features may be limited until connection is restored.',
    tabs: {
      home: 'Home',
      billnyay: 'BillNyay',
      daavisetu: 'DaaviSetu',
      bimanyay: 'BimaNyay',
      schemesetu: 'SchemeSetu',
      dawacheck: 'DawaCheck',
    },
    scanner: {
      title: 'Document Scanner',
      subtitle: 'Align bill, prescription, or denial letter within the frame',
      instruction: 'Hold camera steady with good lighting',
      billMode: 'Hospital Bill',
      denialMode: 'Denial Letter',
      prescriptionMode: 'Prescription',
      capture: 'Capture Document',
      retake: 'Retake',
      process: 'Analyze Document',
      cameraPermissionTitle: 'Camera Permission Needed',
      cameraPermissionMsg: 'ArogyaRakshak uses your camera to scan medical bills and denial letters. Images are processed transiently without permanent storage.',
      grantPermission: 'Allow Camera',
      transientMemoryNotice: 'BYOD Guard: Images expunged immediately after OCR extraction.',
      consentText: 'I consent to transient analysis of this document.',
      consentRequired: 'Please give consent before scanning.',
      scanFirst: 'Scan a document first — consent is captured during the scan.',
    },
    resolution: {
      title: 'Please confirm possible duplicates',
      intro: 'Kadi found entries in your documents that may refer to the same thing. Nothing is merged until you confirm.',
      mentionLabel: 'New entry',
      existingLabel: 'Already in this case',
      confidenceLabel: 'Match score',
      confirmBtn: 'Same — merge',
      rejectBtn: 'Different — keep both',
      unavailable: 'not available',
      uncalibratedNote: 'Match scores are similarity estimates, not probabilities.',
    },
    modules: {
      billnyay: {
        title: 'BillNyay',
        desc: 'Audit hospital discharge bills line-by-line against CGHS government benchmark rates.',
        statutory: 'CGHS 2024 Benchmark Tariffs',
        cta: 'Audit Discharge Bill',
        cardTitle: 'Hospital Discharge Bill Audit',
        cardBody: 'Scan any IPD/OPD hospital bill to detect inflated room rent charges, unbundled surgical consumables, and tariff rates exceeding the official CGHS 2024 benchmarks.',
        auditing: 'Auditing Line-Items...',
        auditResults: 'CGHS Tariff Audit Results',
        charged: 'Charged',
        cghsCap: 'CGHS reference',
        flagged: 'Flagged',
        fair: '✓ Fair',
        notBenchmarked: 'ⓘ Not benchmarked',
        unmatchedNotice: '{count} item(s) totalling ₹{amount} have no CGHS benchmark and were NOT verified.',
        scanBillBtn: '📷 Scan Bill with Camera',
        activeCaseReady: 'Active case loaded from camera scan.',
        deleteCaseBtn: 'Delete case',
        deleteCaseConfirmTitle: 'Delete this case?',
        deleteCaseConfirmBody: 'This permanently deletes this case and everything derived from it — extracted entities, audits, and any generated documents. This cannot be undone.',
        draftAppealBtn: '⚖️ Draft IRDAI Appeal Letter',
        drafting: 'Running 5-Agent Appeal Pipeline...',
        appealTitle: 'Appeal Letter Drafted',
        appealApprove: '✓ Passed automated quality check',
        appealNeedsRevision: 'ⓘ Flagged for Revision',
        appealLlmBacked: 'Grounded by a live LLM analysis of this case\'s documents.',
        appealTemplateNotice: 'ⓘ Offline template: no AI backend configured, so this is a static statutory draft, not a case-specific analysis. Review carefully before sending.',
        appealFactsNotExtracted: 'ⓘ Denial details could not be extracted from your document. Fill in the denial code, insurer reason, and policy clause yourself before sending.',
        downloadAppealPdf: '📥 Download Signed Appeal PDF',
        shareAppealBtn: '📤 Share Appeal Letter',
      },
      daavisetu: {
        title: 'DaaviSetu',
        desc: 'Automate cashless pre-authorization and reimbursement claim application forms.',
        statutory: 'IRDAI Standard Claim Templates',
        cta: 'Prepare Claim Form',
        cardTitle: 'Pre-Authorization Details (Annexure-B)',
        patientName: 'Patient Full Name',
        policyId: 'Health Policy / TPA Card ID',
        hospitalName: 'Network Hospital Name',
        treatmentPlan: 'Planned Clinical Treatment / Procedure',
        generating: 'Generating IRDAI Pre-Auth Package...',
        generateBtn: '📄 Auto-Fill Pre-Authorization Form',
        scanFirstPrompt: 'Tip: Scan your admission slip or policy first for instant extraction.',
        generatedTitle: '✓ Generated Pre-Auth Package',
        patient: 'Patient:',
        policy: 'Policy:',
        hospital: 'Hospital:',
        diagnosis: 'Diagnosis:',
        treatment: 'Treatment:',
        cost: 'Estimated Cost:',
        status: 'Status:',
        readyForReview: 'Ready for Review',
        downloadPdf: '📥 Download IRDAI Standard Form PDF',
        downloadPackage: '🗂️ Download Full Claim Package (ZIP)',
      },
      bimanyay: {
        title: 'BimaNyay',
        desc: 'Audit insurance repudiations and draft 3-tier appeals (GRO, Bima Bharosa, Ombudsman).',
        statutory: 'IRDAI Master Circular (May 29, 2024)',
        cta: 'Dispute Insurance Denial',
        cardTitle: 'Claim Repudiation Dossier',
        policyNumber: 'Policy Number',
        insurerName: 'Insurer / TPA Name',
        policyAge: 'Policy Age (Years)',
        claimedAmount: 'Claimed Amount (₹)',
        deniedAmount: 'Denied / Deducted Amount (₹)',
        denialCategoryLabel: 'Denial Category',
        denialCategoryPedNonDisclosure: 'Pre-Existing Disease Non-Disclosure',
        denialCategoryRoomRentCapping: 'Room Rent Proportionate Deduction',
        denialCategoryInvestigationOnly: 'Observation / Diagnostic Hospitalization Only',
        denialCategoryDelayedIntimation: 'Delayed Claim Intimation / Submission',
        denialReason: 'Reason for Denial (from rejection letter)',
        diagnosis: 'Clinical Diagnosis',
        auditBtn: '⚖️ Audit Grounds & Draft 3-Tier Appeals',
        auditing: 'Auditing Regulatory Precedents...',
        reversalScore: 'Reversal Probability:',
        heuristicDisclosure: 'Rule-based estimate for this denial category — not derived from historical dispute outcomes.',
        wrongful: 'Wrongful Repudiation Detected',
        copyDraft: '📋 Copy Selected Appeal Draft',
        groTab: 'Tier 1: GRO',
        bharosaTab: 'Tier 2: Bima Bharosa',
        ombudsmanTab: 'Tier 3: Ombudsman',
        timelineTitle: '⏳ IRDAI Statutory SLA Timeline',
      },
      schemesetu: {
        title: 'SchemeSetu',
        desc: 'Assess eligibility for PMJAY (National) and MJPJAY (Maharashtra) welfare schemes.',
        statutory: 'AB-PMJAY & MJPJAY 2024 Rules',
        cta: 'Check Scheme Eligibility',
        cardTitle: 'Government Welfare Eligibility Assessment',
        income: 'Annual Family Income (₹)',
        state: 'State of Residence',
        category: 'Social Category (General / SC / ST / OBC)',
        medicalNeed: 'Required Medical Procedure / Specialty',
        checkBtn: '🔍 Check Government Health Schemes',
        checking: 'Assessing Scheme Guidelines...',
        provisionallyEligible: 'Provisionally eligible',
        needsVerification: 'Verification needed',
        notEligible: 'Not Eligible',
        howToClaim: 'How to Claim at Empaneled Hospital:',
        howToVerify: 'How to verify:',
        nonDeterminative: 'Recorded but not used to decide (no official income ceiling)',
        officialSources: 'Official sources',
        noMatches: 'No government health scheme matches found for the given criteria.',
        criteriaEvaluated: 'Evaluated for this result',
        criteriaNotEvaluated: 'NOT evaluated — verify with official records',
        provisionalNotice: 'Provisional estimate only. The criteria listed as not evaluated (such as SECC-2011 listing, age and documents) are not checked by this tool, so this is not a final eligibility decision.',
      },
      dawacheck: {
        title: 'DawaCheck',
        desc: 'Verify medicine MRP against NPPA ceiling price caps and find generic bioequivalents.',
        statutory: 'NPPA Schedule-I DPCO 2013',
        cta: 'Check Medicine Pricing',
        cardTitle: 'NPPA Schedule-I Ceiling Rate Check',
        brandOrGeneric: 'Brand / Generic Formulation Name',
        chargedMrp: 'Charged MRP / Unit Price (₹)',
        quickSamples: 'Quick verification samples:',
        checkBtn: '🔍 Verify NPPA Price Compliance',
        checking: 'Verifying NPPA Gazettes...',
        scanStrip: '📷 Scan Medicine Packaging / Strip',
        activeApi: 'Active Ingredient:',
        overcharged: 'Overcharged Above Ceiling',
        fairPrice: 'Fair Price Compliant',
        nppaCap: 'NPPA Ceiling Cap',
        deviation: 'Deviation',
        genericAvailable: '💊 Low-Cost Generic Substitute Available (Jan Aushadhi)',
        statutoryNoticeTitle: '💡 Statutory Consumer Right (DPCO 2013)',
        statutoryNoticeBody: 'Under the Drugs (Prices Control) Order, 2013 and the Essential Commodities Act, 1955, charging above the notified NPPA ceiling price is an illegal punishable offence. Retail pharmacies are statutorily required to dispense equivalent generic formulations upon request.',
        dataSourceNotice: 'Checked against a curated subset of {count} NPPA Schedule-I formulations, not the full national list. A medicine absent from this tool is not confirmed uncontrolled.',
        prescriptionTranslatorTitle: 'Prescription Shorthand Translator',
        prescriptionInputPlaceholder: "Paste doctor's instructions, e.g. Tab. Dolo 650mg TDS x 5 days",
        translateBtn: 'Translate Instructions',
        unrecognizedNotice: 'Not recognized (not a standard abbreviation this tool knows): {tokens}',
      },
    },
    common: {
      language: 'Language',
      theme: 'Theme',
      light: 'Light',
      dark: 'Dark',
      cancel: 'Cancel',
      close: 'Close',
      loading: 'Loading...',
      delete: 'Delete',
      deleteCaseBtn: 'Delete case',
      deleteCaseConfirmTitle: 'Delete this case?',
      deleteCaseConfirmBody: 'This permanently deletes this case and everything derived from it — extracted entities, audits, and any generated documents. This cannot be undone.',
    },
  },
  hi: {
    appName: 'आरोग्यरक्षक',
    tagline: 'स्वास्थ्य सुरक्षा, दावा न्याय एवं योजना सहायता',
    byodBadge: 'शून्य दस्तावेज़ संचयन (BYOD)',
    byodDescription: 'अस्थायी मेमोरी में संसाधित। कोई स्थायी मेडिकल दस्तावेज़ संचित नहीं होता।',
    offlineNotice: 'इंटरनेट कनेक्शन नहीं है',
    offlineSubtext: 'कनेक्शन बहाल होने तक कुछ सुविधाएं सीमित हो सकती हैं।',
    tabs: {
      home: 'मुख्य',
      billnyay: 'बिलन्याय',
      daavisetu: 'दावेसेतू',
      bimanyay: 'बीमान्याय',
      schemesetu: 'योजनासेतू',
      dawacheck: 'दवाचेक',
    },
    scanner: {
      title: 'दस्तावेज़ स्कैनर',
      subtitle: 'फ्रेम के भीतर बिल, नुस्खा या अस्वीकृति पत्र रखें',
      instruction: 'अच्छी रोशनी में कैमरा स्थिर रखें',
      billMode: 'अस्पताल बिल',
      denialMode: 'अस्वीकृति पत्र',
      prescriptionMode: 'दवा का पर्चा',
      capture: 'दस्तावेज़ कैप्चर करें',
      retake: 'पुनः लें',
      process: 'दस्तावेज़ का विश्लेषण करें',
      cameraPermissionTitle: 'कैमरा अनुमति आवश्यक',
      cameraPermissionMsg: 'आरोग्यरक्षक मेडिकल बिलों को स्कैन करने के लिए कैमरे का उपयोग करता है। छवियां बिना स्थायी संचयन के अस्थायी रूप से संसाधित होती हैं।',
      grantPermission: 'अनुमति दें',
      transientMemoryNotice: 'BYOD सुरक्षा: ओसीआर निष्कर्षण के बाद छवियां तुरंत हटा दी जाती हैं।',
      consentText: 'मैं इस दस्तावेज़ के अस्थायी विश्लेषण की सहमति देता हूँ।',
      consentRequired: 'कृपया स्कैन करने से पहले सहमति दें।',
      scanFirst: 'पहले दस्तावेज़ स्कैन करें — सहमति स्कैन के समय ली जाती है।',
    },
    resolution: {
      title: 'संभावित दोहराव की पुष्टि करें',
      intro: 'Kadi को आपके दस्तावेज़ों में ऐसी प्रविष्टियाँ मिलीं जो एक ही चीज़ हो सकती हैं। आपकी पुष्टि के बिना कुछ भी मिलाया नहीं जाता।',
      mentionLabel: 'नई प्रविष्टि',
      existingLabel: 'इस केस में पहले से',
      confidenceLabel: 'मिलान स्कोर',
      confirmBtn: 'एक ही हैं — मिलाएँ',
      rejectBtn: 'अलग हैं — दोनों रखें',
      unavailable: 'उपलब्ध नहीं',
      uncalibratedNote: 'मिलान स्कोर समानता का अनुमान है, संभावना नहीं।',
    },
    modules: {
      billnyay: {
        title: 'बिलन्याय',
        desc: 'सीजीएचएस सरकारी दरों के विरुद्ध अस्पताल बिल की प्रत्येक मद की जांच करें।',
        statutory: 'सीजीएचएस 2024 मानक दरें',
        cta: 'अस्पताल बिल जांचें',
        cardTitle: 'अस्पताल डिस्चार्ज बिल ऑडिट',
        cardBody: 'अतिरिक्त रूम रेंट, अनाधिकृत सर्जिकल उपभोग्य शुल्क और सीजीएचएस 2024 से अधिक दरों का पता लगाने के लिए बिल स्कैन करें।',
        auditing: 'मदों का विश्लेषण हो रहा है...',
        auditResults: 'सीजीएचएस टैरिफ ऑडिट परिणाम',
        charged: 'वसूल किया गया',
        cghsCap: 'सीजीएचएस संदर्भ दर',
        flagged: 'संदिग्ध दरें',
        fair: '✓ उचित दर',
        notBenchmarked: 'ⓘ जाँच नहीं हुई',
        unmatchedNotice: '{count} मदों (₹{amount}) के लिए CGHS मानक नहीं है, इनकी जाँच नहीं हुई।',
        scanBillBtn: '📷 कैमरे से बिल स्कैन करें',
        activeCaseReady: 'स्कैन से सक्रिय केस लोड हो गया है।',
        deleteCaseBtn: 'केस हटाएं',
        deleteCaseConfirmTitle: 'क्या यह केस हटाना है?',
        deleteCaseConfirmBody: 'यह इस केस और इससे प्राप्त सभी डेटा — निकाली गई जानकारी, ऑडिट, और जनरेट किए गए दस्तावेज़ — को स्थायी रूप से हटा देगा। इसे पूर्ववत नहीं किया जा सकता।',
        draftAppealBtn: '⚖️ इरडा अपील पत्र तैयार करें',
        drafting: '5-एजेंट अपील पाइपलाइन चल रही है...',
        appealTitle: 'अपील पत्र तैयार हुआ',
        appealApprove: '✓ स्वचालित गुणवत्ता जाँच में उत्तीर्ण', // needs native-speaker QA
        appealNeedsRevision: 'ⓘ संशोधन हेतु चिह्नित',
        appealLlmBacked: 'इस केस के दस्तावेज़ों के लाइव एआई विश्लेषण पर आधारित।',
        appealTemplateNotice: 'ⓘ ऑफ़लाइन टेम्पलेट: कोई एआई बैकएंड कॉन्फ़िगर नहीं है, इसलिए यह एक स्थिर सांविधिक मसौदा है, केस-विशिष्ट विश्लेषण नहीं। भेजने से पहले ध्यान से समीक्षा करें।',
        appealFactsNotExtracted: 'ⓘ आपके दस्तावेज़ से अस्वीकृति विवरण नहीं निकाला जा सका। भेजने से पहले अस्वीकृति कोड, बीमाकर्ता का कारण और पॉलिसी खंड स्वयं भरें।',
        downloadAppealPdf: '📥 हस्ताक्षरित अपील पीडीएफ डाउनलोड करें',
        shareAppealBtn: '📤 अपील पत्र साझा करें',
      },
      daavisetu: {
        title: 'दावेसेतू',
        desc: 'कैशलेस पूर्व-प्राधिकरण और प्रतिपूर्ति दावा आवेदन प्रपत्र स्वतः तैयार करें।',
        statutory: 'इरडा (IRDAI) मानक दावा प्रपत्र',
        cta: 'दावा प्रपत्र तैयार करें',
        cardTitle: 'पूर्व-प्राधिकरण विवरण (परिशिष्ट-बी)',
        patientName: 'मरीज़ का पूरा नाम',
        policyId: 'स्वास्थ्य बीमा / टीपीए कार्ड संख्या',
        hospitalName: 'अस्पताल का नाम',
        treatmentPlan: 'प्रस्तावित उपचार या सर्जरी',
        generating: 'इरडा मानक प्रपत्र तैयार हो रहा है...',
        generateBtn: '📄 पूर्व-प्राधिकरण प्रपत्र स्वतः भरें',
        scanFirstPrompt: 'सुझाव: त्वरित विवरण निष्कर्षण के लिए पहले प्रवेश पर्ची स्कैन करें।',
        generatedTitle: '✓ तैयार पूर्व-प्राधिकरण पैकेज',
        patient: 'मरीज़:',
        policy: 'पॉलिसी:',
        hospital: 'अस्पताल:',
        diagnosis: 'निदान:',
        treatment: 'उपचार:',
        cost: 'अनुमानित लागत:',
        status: 'स्थिति:',
        readyForReview: 'समीक्षा हेतु तैयार',
        downloadPdf: '📥 मानक दावा प्रपत्र पीडीएफ डाउनलोड करें',
        downloadPackage: '🗂️ पूर्ण दावा पैकेज डाउनलोड करें (ZIP)',
      },
      bimanyay: {
        title: 'बीमान्याय',
        desc: 'बीमा अस्वीकृति की जांच करें और 3-स्तरीय अपील (GRO, बीमा भरोसा, लोकपाल) तैयार करें।',
        statutory: 'इरडा मास्टर परिपत्र (29 मई 2024)',
        cta: 'बीमा अस्वीकृति को चुनौती दें',
        cardTitle: 'दावा अस्वीकृति विवरण',
        policyNumber: 'पॉलिसी संख्या',
        insurerName: 'बीमा कंपनी / टीपीए का नाम',
        policyAge: 'पॉलिसी की अवधि (वर्ष)',
        claimedAmount: 'दावा की गई राशि (₹)',
        deniedAmount: 'अस्वीकृत / काटी गई राशि (₹)',
        denialCategoryLabel: 'अस्वीकृति श्रेणी',
        denialCategoryPedNonDisclosure: 'पूर्व-मौजूदा बीमारी की जानकारी न देना',
        denialCategoryRoomRentCapping: 'कमरे के किराए की आनुपातिक कटौती',
        denialCategoryInvestigationOnly: 'केवल जांच / निदान हेतु अस्पताल में भर्ती',
        denialCategoryDelayedIntimation: 'दावे की देर से सूचना / प्रस्तुति',
        denialReason: 'अस्वीकृति का कारण (पत्र अनुसार)',
        diagnosis: 'रोग का निदान',
        auditBtn: '⚖️ अस्वीकृति की जांच करें व 3-स्तरीय अपील बनाएं',
        auditing: 'विधिक नियमों की जांच हो रही है...',
        reversalScore: 'अपील सफलता संभावना:',
        heuristicDisclosure: 'इस अस्वीकृति श्रेणी के लिए नियम-आधारित अनुमान — पिछले विवादों के वास्तविक परिणामों पर आधारित नहीं।',
        wrongful: 'अनुचित अस्वीकृति पाई गई',
        copyDraft: '📋 चयनित अपील ड्राफ्ट कॉपी करें',
        groTab: 'स्तर 1: जीआरओ (GRO)',
        bharosaTab: 'स्तर 2: बीमा भरोसा',
        ombudsmanTab: 'स्तर 3: लोकपाल',
        timelineTitle: '⏳ इरडा वैधानिक समयसीमा (SLA)',
      },
      schemesetu: {
        title: 'योजनासेतू',
        desc: 'पीएमजेएवाई (राष्ट्रीय) और महात्मा फुले (महाराष्ट्र) योजनाओं की पात्रता जांचें।',
        statutory: 'आयुष्मान भारत एवं एमजेपीजेएवाई नियम',
        cta: 'योजना पात्रता जांचें',
        cardTitle: 'सरकारी स्वास्थ्य योजना पात्रता मूल्यांकन',
        income: 'वार्षिक पारिवारिक आय (₹)',
        state: 'निवास का राज्य',
        category: 'सामाजिक श्रेणी (सामान्य / अजा / अजजा / अपिव)',
        medicalNeed: 'आवश्यक चिकित्सा उपचार / विशेषज्ञता',
        checkBtn: '🔍 स्वास्थ्य योजना पात्रता जांचें',
        checking: 'योजना नियमों की समीक्षा हो रही है...',
        provisionallyEligible: 'अस्थायी रूप से पात्र',
        needsVerification: 'पुष्टि आवश्यक',
        notEligible: 'पात्र नहीं',
        howToClaim: 'अस्पताल में लाभ कैसे प्राप्त करें:',
        howToVerify: 'पात्रता की पुष्टि कैसे करें:',
        nonDeterminative: 'दर्ज किया गया, पर निर्णय में उपयोग नहीं (कोई आधिकारिक आय-सीमा नहीं)',
        officialSources: 'आधिकारिक स्रोत',
        noMatches: 'दी गई जानकारी के आधार पर कोई योजना मेल नहीं खाई।',
        criteriaEvaluated: 'इस परिणाम हेतु जाँचे गए आधार',
        criteriaNotEvaluated: 'जाँचे नहीं गए — आधिकारिक रिकॉर्ड से पुष्टि करें',
        provisionalNotice: 'यह केवल एक अस्थायी अनुमान है। “जाँचे नहीं गए” के रूप में सूचीबद्ध मानदंड (जैसे SECC-2011 सूची, आयु और दस्तावेज़) इस टूल द्वारा नहीं जाँचे जाते, इसलिए यह अंतिम पात्रता निर्णय नहीं है।',
      },
      dawacheck: {
        title: 'दवाचेक',
        desc: 'एनपीपीए अधिकतम मूल्य सीमा के विरुद्ध दवा की कीमत जांचें और जेनेरिक विकल्प खोजें।',
        statutory: 'एनपीपीए अनुसूची-I डीपीसीओ 2013',
        cta: 'दवा की कीमत जांचें',
        cardTitle: 'एनपीपीए अनुसूची-I मूल्य सीमा जांच',
        brandOrGeneric: 'दवा या ब्रांड का नाम',
        chargedMrp: 'वसूल की गई एमआरपी / इकाई मूल्य (₹)',
        quickSamples: 'त्वरित परीक्षण नमूने:',
        checkBtn: '🔍 एनपीपीए मूल्य अनुपालन जांचें',
        checking: 'सरकारी अधिसूचनाओं की जांच हो रही है...',
        scanStrip: '📷 दवा का पत्ता स्कैन करें',
        activeApi: 'सक्रिय घटक (API):',
        overcharged: 'अधिकतम सीमा से अधिक शुल्क',
        fairPrice: 'उचित वैधानिक मूल्य',
        nppaCap: 'एनपीपीए मूल्य सीमा',
        deviation: 'अंतर',
        genericAvailable: '💊 कम लागत वाला जेनेरिक विकल्प उपलब्ध (जन औषधि)',
        statutoryNoticeTitle: '💡 वैधानिक उपभोक्ता अधिकार (डीपीसीओ 2013)',
        statutoryNoticeBody: 'ड्रग्स प्राइस कंट्रोल ऑर्डर, 2013 एवं आवश्यक वस्तु अधिनियम के तहत एनपीपीए मूल्य सीमा से अधिक वसूलना एक दंडनीय अपराध है। फार्मेसी द्वारा जेनेरिक विकल्प उपलब्ध कराना अनिवार्य है।',
        dataSourceNotice: 'यह जांच NPPA अनुसूची-I की {count} चयनित दवाओं की सूची पर आधारित है, पूरी राष्ट्रीय सूची पर नहीं। इस सूची में न होने का अर्थ यह नहीं कि दवा मूल्य-नियंत्रण से मुक्त है।',
        prescriptionTranslatorTitle: 'पर्ची संक्षिप्त शब्द अनुवादक',
        prescriptionInputPlaceholder: 'डॉक्टर के निर्देश यहाँ चिपकाएँ, जैसे Tab. Dolo 650mg TDS x 5 days',
        translateBtn: 'निर्देश अनुवाद करें',
        unrecognizedNotice: 'पहचान नहीं हुई (यह मानक संक्षिप्त शब्द नहीं है): {tokens}',
      },
    },
    common: {
      language: 'भाषा',
      theme: 'थीम',
      light: 'लाइट',
      dark: 'डार्क',
      cancel: 'रद्द करें',
      close: 'बंद करें',
      loading: 'लोड हो रहा है...',
      delete: 'हटाएं',
      deleteCaseBtn: 'केस हटाएं',
      deleteCaseConfirmTitle: 'क्या यह केस हटाना है?',
      deleteCaseConfirmBody: 'यह इस केस और इससे प्राप्त सभी डेटा — निकाली गई जानकारी, ऑडिट, और जनरेट किए गए दस्तावेज़ — को स्थायी रूप से हटा देगा। इसे पूर्ववत नहीं किया जा सकता।',
    },
  },
  mr: {
    appName: 'आरोग्यरक्षक',
    tagline: 'आरोग्य संरक्षण, दावा न्याय आणि योजना सहाय्य',
    byodBadge: 'शून्य दस्तऐवज साठवण (BYOD)',
    byodDescription: 'अल्पकालीन मेमरीमध्ये प्रक्रिया. वैद्यकीय दस्तऐवज कायमस्वरूपी साठवले जात नाहीत.',
    offlineNotice: 'इंटरनेट कनेक्शन नाही',
    offlineSubtext: 'कनेक्शन पूर्ववत होईपर्यंत काही सुविधा मर्यादित असू शकतात.',
    tabs: {
      home: 'मुख्य',
      billnyay: 'बिलन्याय',
      daavisetu: 'दावेसेतू',
      bimanyay: 'बीमान्याय',
      schemesetu: 'योजनासेतू',
      dawacheck: 'दवाचेक',
    },
    scanner: {
      title: 'दस्तऐवज स्कॅनर',
      subtitle: 'चौकटीत बिल, प्रिस्क्रिप्शन किंवा नकार पत्र व्यवस्थित ठेवा',
      instruction: 'चांगल्या प्रकाशात कॅमेरा स्थिर धरा',
      billMode: 'रुग्णालय बिल',
      denialMode: 'विमा नकार पत्र',
      prescriptionMode: 'डॉक्टरांचे प्रिस्क्रिप्शन',
      capture: 'दस्तऐवज फोटो घ्या',
      retake: 'पुन्हा घ्या',
      process: 'दस्तऐवज तपासा',
      cameraPermissionTitle: 'कॅमेरा परवानगी आवश्यक',
      cameraPermissionMsg: 'आरोग्यरक्षक वैद्यकीय बिले स्कॅन करण्यासाठी कॅमेरा वापरतो. चित्रे कायमस्वरूपी साठवणुकीशिवाय तात्पुरती तपासली जातात.',
      grantPermission: 'परवानगी द्या',
      transientMemoryNotice: 'BYOD सुरक्षा: ओसीआर प्रक्रियेनंतर चित्रे तात्काळ नष्ट केली जातात.',
      consentText: 'मी या दस्तऐवजाच्या तात्पुरत्या विश्लेषणास संमती देतो.',
      consentRequired: 'कृपया स्कॅन करण्यापूर्वी संमती द्या.',
      scanFirst: 'आधी दस्तऐवज स्कॅन करा — संमती स्कॅनवेळी घेतली जाते.',
    },
    resolution: {
      title: 'संभाव्य दुहेरी नोंदींची खात्री करा',
      intro: 'Kadi ला तुमच्या कागदपत्रांमध्ये अशा नोंदी सापडल्या ज्या एकाच गोष्टीबद्दल असू शकतात. तुमच्या खात्रीशिवाय काहीही एकत्र केले जात नाही.',
      mentionLabel: 'नवीन नोंद',
      existingLabel: 'या केसमध्ये आधीपासून',
      confidenceLabel: 'जुळणी गुण',
      confirmBtn: 'एकच आहेत — एकत्र करा',
      rejectBtn: 'वेगळे आहेत — दोन्ही ठेवा',
      unavailable: 'उपलब्ध नाही',
      uncalibratedNote: 'जुळणी गुण हे साम्याचा अंदाज आहेत, संभाव्यता नाही.',
    },
    modules: {
      billnyay: {
        title: 'बिलन्याय',
        desc: 'सीजीएचएस सरकारी दरांच्या आधारे रुग्णालयाच्या बिलाचे सखोल परीक्षण करा.',
        statutory: 'सीजीएचएस २०२४ शासकीय दर',
        cta: 'रुग्णालय बिल तपासा',
        cardTitle: 'रुग्णालय डिस्चार्ज बिल परीक्षण',
        cardBody: 'वाढीव रूम भाडे, अनावश्यक सर्जिकल साहित्य शुल्क आणि सीजीएचएस २०२४ सरकारी दरांपेक्षा अधिक शुल्क तपासण्यासाठी बिल स्कॅन करा.',
        auditing: 'दरांचे परीक्षण सुरू आहे...',
        auditResults: 'सीजीएचएस दर तपासणी निकाल',
        charged: 'आकारलेले शुल्क',
        cghsCap: 'सीजीएचएस संदर्भ दर',
        flagged: 'जादा आकारणी',
        fair: '✓ योग्य दर',
        notBenchmarked: 'ⓘ पडताळणी झाली नाही',
        unmatchedNotice: '{count} नोंदींसाठी (₹{amount}) CGHS मानक नाही, त्यांची पडताळणी झाली नाही.',
        scanBillBtn: '📷 कॅमेऱ्याने बिल स्कॅन करा',
        activeCaseReady: 'स्कॅनवरून सक्रिय केस लोड झाली आहे.',
        deleteCaseBtn: 'केस हटवा',
        deleteCaseConfirmTitle: 'ही केस हटवायची आहे का?',
        deleteCaseConfirmBody: 'यामुळे ही केस आणि त्यातून मिळालेला सर्व डेटा — काढलेल्या नोंदी, ऑडिट्स, आणि तयार केलेली कागदपत्रे — कायमची हटवली जातील. ही क्रिया पूर्ववत करता येणार नाही.',
        draftAppealBtn: '⚖️ आयआरडीएआय अपील पत्र तयार करा',
        drafting: '5-एजंट अपील पाइपलाइन सुरू आहे...',
        appealTitle: 'अपील पत्र तयार झाले',
        appealApprove: '✓ स्वयंचलित गुणवत्ता तपासणी उत्तीर्ण', // needs native-speaker QA
        appealNeedsRevision: 'ⓘ सुधारणेसाठी चिन्हांकित',
        appealLlmBacked: 'या केसच्या कागदपत्रांच्या थेट एआय विश्लेषणावर आधारित.',
        appealTemplateNotice: 'ⓘ ऑफलाइन टेम्पलेट: कोणतेही एआय बॅकएंड कॉन्फिगर केलेले नाही, त्यामुळे हा एक स्थिर वैधानिक मसुदा आहे, केस-विशिष्ट विश्लेषण नाही. पाठवण्यापूर्वी काळजीपूर्वक पुनरावलोकन करा.',
        appealFactsNotExtracted: 'ⓘ तुमच्या कागदपत्रातून नकाराचा तपशील काढता आला नाही. पाठवण्यापूर्वी नकार कोड, विमा कंपनीचे कारण आणि पॉलिसी कलम स्वतः भरा.',
        downloadAppealPdf: '📥 स्वाक्षरीकृत अपील पीडीएफ डाउनलोड करा',
        shareAppealBtn: '📤 अपील पत्र सामायिक करा',
      },
      daavisetu: {
        title: 'दावेसेतू',
        desc: 'कॅशलेस पूर्व-अधिकृतता आणि प्रतिपूर्ती दावा अर्ज आपोआप तयार करा.',
        statutory: 'आयआरडीएआय प्रमाण दावा अर्ज',
        cta: 'दावा अर्ज तयार करा',
        cardTitle: 'पूर्व-अधिकृतता तपशील (परिशिष्ट-बी)',
        patientName: 'रुग्णाचे पूर्ण नाव',
        policyId: 'आरोग्य विमा / टीपीए कार्ड क्रमांक',
        hospitalName: 'रुग्णालयाचे नाव',
        treatmentPlan: 'नियोजित उपचार किंवा शस्त्रक्रिया',
        generating: 'आयआरडीएआय दावा अर्ज तयार होत आहे...',
        generateBtn: '📄 पूर्व-अधिकृतता अर्ज आपोआप भरा',
        scanFirstPrompt: 'टीप: जलद तपशील मिळवण्यासाठी प्रथम ॲडमिशन पावती स्कॅन करा.',
        generatedTitle: '✓ तयार पूर्व-अधिकृतता पॅकेज',
        patient: 'रुग्ण:',
        policy: 'विमा पॉलिसी:',
        hospital: 'रुग्णालय:',
        diagnosis: 'रोगनिदान:',
        treatment: 'उपचार:',
        cost: 'अंदाजे खर्च:',
        status: 'स्थिती:',
        readyForReview: 'तपासणीसाठी सज्ज',
        downloadPdf: '📥 प्रमाण दावा अर्ज पीडीएफ डाउनलोड करा',
        downloadPackage: '🗂️ संपूर्ण दावा पॅकेज डाउनलोड करा (ZIP)',
      },
      bimanyay: {
        title: 'बीमान्याय',
        desc: 'विमा दावा नकाराचे परीक्षण करा आणि ३-स्तरीय अपील (GRO, विमा भरोसा, लोकपाल) तयार करा.',
        statutory: 'आयआरडीएआय मास्टर परिपत्रक (२९ मे २०२४)',
        cta: 'विमा नकाराविरुद्ध दाद मागा',
        cardTitle: 'विमा दावा नकार तपशील',
        policyNumber: 'पॉलिसी क्रमांक',
        insurerName: 'विमा कंपनी / टीपीएचे नाव',
        policyAge: 'पॉलिसीचे वय (वर्षे)',
        claimedAmount: 'मागणी केलेली रक्कम (₹)',
        deniedAmount: 'नाकारलेली / कापलेली रक्कम (₹)',
        denialCategoryLabel: 'नकाराचा प्रकार',
        denialCategoryPedNonDisclosure: 'आधीच्या आजाराची माहिती न दिल्याने नकार',
        denialCategoryRoomRentCapping: 'खोलीच्या भाड्याची प्रमाणशीर कपात',
        denialCategoryInvestigationOnly: 'केवळ तपासणी / निदानासाठी रुग्णालयात दाखल',
        denialCategoryDelayedIntimation: 'दाव्याची उशिरा सूचना / सादरीकरण',
        denialReason: 'नकाराचे कारण (पत्रातील)',
        diagnosis: 'रोगनिदान',
        auditBtn: '⚖️ नकाराचे परीक्षण करा व ३-स्तरीय अपील बनवा',
        auditing: 'कायदेशीर नियमांची तपासणी सुरू आहे...',
        reversalScore: 'अपील यशाची शक्यता:',
        heuristicDisclosure: 'या नाकारण्याच्या प्रकारासाठी नियमांवर आधारित अंदाज — मागील वादांच्या प्रत्यक्ष निकालांवर आधारित नाही.',
        wrongful: 'अयोग्य नकार आढळला',
        copyDraft: '📋 निवडलेला अपील मसुदा कॉपी करा',
        groTab: 'स्तर १: जीआरओ (GRO)',
        bharosaTab: 'स्तर २: विमा भरोसा',
        ombudsmanTab: 'स्तर ३: लोकपाल',
        timelineTitle: '⏳ आयआरडीएआय वैधानिक मुदत (SLA)',
      },
      schemesetu: {
        title: 'योजनासेतू',
        desc: 'पीएमजेएवाय (राष्ट्रीय) आणि महात्मा फुले (महाराष्ट्र) आरोग्य योजनांची पात्रता तपासा.',
        statutory: 'आयुष्मान भारत व एमजेपीजेएवाय नियमावली',
        cta: 'योजना पात्रता तपासा',
        cardTitle: 'शासकीय आरोग्य योजना पात्रता चाचणी',
        income: 'वार्षिक कौटुंबिक उत्पन्न (₹)',
        state: 'राज्य',
        category: 'सामाजिक प्रवर्ग (खुला / अनु. जाती / अनु. जमाती / इमाव)',
        medicalNeed: 'आवश्यक वैद्यकीय उपचार / शस्त्रक्रिया',
        checkBtn: '🔍 शासकीय योजना पात्रता तपासा',
        checking: 'योजनेच्या अटी तपासल्या जात आहेत...',
        provisionallyEligible: 'तात्पुरते पात्र',
        needsVerification: 'पडताळणी आवश्यक',
        notEligible: 'अपात्र',
        howToClaim: 'रुग्णालयात लाभ कसा मिळवावा:',
        howToVerify: 'पात्रतेची पडताळणी कशी करावी:',
        nonDeterminative: 'नोंदवले, पण निर्णयासाठी वापरले नाही (अधिकृत उत्पन्न मर्यादा नाही)',
        officialSources: 'अधिकृत स्रोत',
        noMatches: 'दिलेल्या माहितीनुसार कोणतीही शासकीय योजना आढळली नाही.',
        criteriaEvaluated: 'या निकालासाठी तपासलेले निकष',
        criteriaNotEvaluated: 'तपासले गेलेले नाहीत — अधिकृत नोंदींद्वारे पडताळणी करा',
        provisionalNotice: 'हा फक्त प्राथमिक अंदाज आहे. “तपासले गेलेले नाहीत” म्हणून दिलेले निकष (उदा. SECC-2011 यादी, वय आणि कागदपत्रे) या साधनाद्वारे तपासले जात नाहीत, त्यामुळे हा अंतिम पात्रता निर्णय नाही.',
      },
      dawacheck: {
        title: 'दवाचेक',
        desc: 'एनपीपीए कमाल किंमत मर्यादेनुसार औषधांचा दर तपासा आणि जेनेरिक पर्याय मिळवा.',
        statutory: 'एनपीपीए अनुसूची-१ डीपीसीओ २०१३',
        cta: 'औषधांची किंमत तपासा',
        cardTitle: 'एनपीपीए अनुसूची-१ कमाल दर पडताळणी',
        brandOrGeneric: 'औषध किंवा ब्रँडचे नाव',
        chargedMrp: 'आकारलेला दर / एमआरपी (₹)',
        quickSamples: 'जलद पडताळणी नमुने:',
        checkBtn: '🔍 एनपीपीए दर नियमावली तपासा',
        checking: 'शासकीय दरांची पडताळणी सुरू आहे...',
        scanStrip: '📷 औषध पाकीट स्कॅन करा',
        activeApi: 'सक्रिय घटक (API):',
        overcharged: 'कमाल मर्यादेपेक्षा जास्त दर',
        fairPrice: 'योग्य शासकीय दर',
        nppaCap: 'एनपीपीए कमाल मर्यादा',
        deviation: 'फरक',
        genericAvailable: '💊 परवडणारा जेनेरिक पर्याय उपलब्ध (जन औषधी)',
        statutoryNoticeTitle: '💡 वैधानिक ग्राहक हक्क (डीपीसीओ २०१३)',
        statutoryNoticeBody: 'औषध किंमत नियंत्रण आदेश (डीपीसीओ २०१३) आणि अत्यावश्यक वस्तू कायद्यानुसार एनपीपीए कमाल दरापेक्षा जास्त आकारणे हा गुन्हा आहे. औषध विक्रेत्यांनी विचारणा केल्यास जेनेरिक पर्याय देणे बंधनकारक आहे.',
        dataSourceNotice: 'ही तपासणी NPPA अनुसूची-१ मधील निवडक {count} औषधांच्या यादीवर आधारित आहे, संपूर्ण राष्ट्रीय यादीवर नाही. या यादीत नसणे म्हणजे औषध किंमत-नियंत्रणमुक्त आहे असे नाही.',
        prescriptionTranslatorTitle: 'प्रिस्क्रिप्शन संक्षिप्त शब्द भाषांतरक',
        prescriptionInputPlaceholder: 'डॉक्टरांच्या सूचना येथे चिकटवा, उदा. Tab. Dolo 650mg TDS x 5 days',
        translateBtn: 'सूचनांचे भाषांतर करा',
        unrecognizedNotice: 'ओळखले गेले नाही (हा प्रमाणित संक्षेप नाही): {tokens}',
      },
    },
    common: {
      language: 'भाषा',
      theme: 'थीम',
      light: 'लाइट',
      dark: 'डार्क',
      cancel: 'रद्द करा',
      close: 'बंद करा',
      loading: 'लोड होत आहे...',
      delete: 'हटवा',
      deleteCaseBtn: 'केस हटवा',
      deleteCaseConfirmTitle: 'ही केस हटवायची आहे का?',
      deleteCaseConfirmBody: 'यामुळे ही केस आणि त्यातून मिळालेला सर्व डेटा — काढलेल्या नोंदी, ऑडिट्स, आणि तयार केलेली कागदपत्रे — कायमची हटवली जातील. ही क्रिया पूर्ववत करता येणार नाही.',
    },
  },
};
