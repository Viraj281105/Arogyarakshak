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
  };
  modules: {
    billnyay: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
    };
    daavisetu: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
    };
    bimanyay: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
    };
    schemesetu: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
    };
    dawacheck: {
      title: string;
      desc: string;
      statutory: string;
      cta: string;
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
    },
    modules: {
      billnyay: {
        title: 'BillNyay',
        desc: 'Audit hospital discharge bills line-by-line against CGHS government benchmark rates.',
        statutory: 'CGHS 2024 Benchmark Tariffs',
        cta: 'Scan Hospital Bill',
      },
      daavisetu: {
        title: 'DaaviSetu',
        desc: 'Automate cashless pre-authorization and reimbursement claim application forms.',
        statutory: 'IRDAI Standard Claim Templates',
        cta: 'Prepare Claim Form',
      },
      bimanyay: {
        title: 'BimaNyay',
        desc: 'Audit insurance repudiations and draft 3-tier appeals (GRO, Bima Bharosa, Ombudsman).',
        statutory: 'IRDAI Master Circular (May 29, 2024)',
        cta: 'Dispute Insurance Denial',
      },
      schemesetu: {
        title: 'SchemeSetu',
        desc: 'Assess eligibility for PMJAY (National) and MJPJAY (Maharashtra) welfare schemes.',
        statutory: 'AB-PMJAY & MJPJAY 2024 Rules',
        cta: 'Check Scheme Eligibility',
      },
      dawacheck: {
        title: 'DawaCheck',
        desc: 'Verify medicine MRP against NPPA ceiling price caps and find generic bioequivalents.',
        statutory: 'NPPA Schedule-I DPCO 2013',
        cta: 'Scan Medicine Strip',
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
    },
    modules: {
      billnyay: {
        title: 'बिलन्याय',
        desc: 'सीजीएचएस सरकारी दरों के विरुद्ध अस्पताल बिल की प्रत्येक मद की जांच करें।',
        statutory: 'सीजीएचएस 2024 मानक दरें',
        cta: 'अस्पताल बिल स्कैन करें',
      },
      daavisetu: {
        title: 'दावेसेतू',
        desc: 'कैशलेस पूर्व-प्राधिकरण और प्रतिपूर्ति दावा आवेदन प्रपत्र स्वतः तैयार करें।',
        statutory: 'इरडा (IRDAI) मानक दावा प्रपत्र',
        cta: 'दावा प्रपत्र तैयार करें',
      },
      bimanyay: {
        title: 'बीमान्याय',
        desc: 'बीमा अस्वीकृति की जांच करें और 3-स्तरीय अपील (GRO, बीमा भरोसा, लोकपाल) तैयार करें।',
        statutory: 'इरडा मास्टर परिपत्र (29 मई 2024)',
        cta: 'बीमा अस्वीकृति को चुनौती दें',
      },
      schemesetu: {
        title: 'योजनासेतू',
        desc: 'पीएमजेएवाई (राष्ट्रीय) और महात्मा फुले (महाराष्ट्र) योजनाओं की पात्रता जांचें।',
        statutory: 'आयुष्मान भारत एवं एमजेपीजेएवाई नियम',
        cta: 'योजना पात्रता जांचें',
      },
      dawacheck: {
        title: 'दवाचेक',
        desc: 'एनपीपीए अधिकतम मूल्य सीमा के विरुद्ध दवा की कीमत जांचें और जेनेरिक विकल्प खोजें।',
        statutory: 'एनपीपीए अनुसूची-I डीपीसीओ 2013',
        cta: 'दवा का पत्ता स्कैन करें',
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
    },
    modules: {
      billnyay: {
        title: 'बिलन्याय',
        desc: 'सीजीएचएस सरकारी दरांच्या आधारे रुग्णालयाच्या बिलाचे सखोल परीक्षण करा.',
        statutory: 'सीजीएचएस २०२४ शासकीय दर',
        cta: 'रुग्णालय बिल स्कॅन करा',
      },
      daavisetu: {
        title: 'दावेसेतू',
        desc: 'कॅशलेस पूर्व-अधिकृतता आणि प्रतिपूर्ती दावा अर्ज आपोआप तयार करा.',
        statutory: 'आयआरडीएआय प्रमाण दावा अर्ज',
        cta: 'दावा अर्ज तयार करा',
      },
      bimanyay: {
        title: 'बीमान्याय',
        desc: 'विमा दावा नकाराचे परीक्षण करा आणि ३-स्तरीय अपील (GRO, विमा भरोसा, लोकपाल) तयार करा.',
        statutory: 'आयआरडीएआय मास्टर परिपत्रक (२९ मे २०२४)',
        cta: 'विमा नकाराविरुद्ध दाद मागा',
      },
      schemesetu: {
        title: 'योजनासेतू',
        desc: 'पीएमजेएवाय (राष्ट्रीय) आणि महात्मा फुले (महाराष्ट्र) आरोग्य योजनांची पात्रता तपासा.',
        statutory: 'आयुष्मान भारत व एमजेपीजेएवाय नियमावली',
        cta: 'योजना पात्रता तपासा',
      },
      dawacheck: {
        title: 'दवाचेक',
        desc: 'एनपीपीए कमाल किंमत मर्यादेनुसार औषधांचा दर तपासा आणि जेनेरिक पर्याय मिळवा.',
        statutory: 'एनपीपीए अनुसूची-१ डीपीसीओ २०१३',
        cta: 'औषध पाकीट स्कॅन करा',
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
    },
  },
};
