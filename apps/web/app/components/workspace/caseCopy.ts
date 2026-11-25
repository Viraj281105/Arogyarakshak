// Copy for the case frame and module pages (every /app/case route) (Wave 3 M4). One file per page area so each route ships only its own
// strings (split from one workspace dictionary to hold the route bundle budgets).
//
// UNREVIEWED: every Hindi (hi) and Marathi (mr) string in this file is a machine-assisted draft
// and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md) before it is presented as final. Text that
// comes from the API stays in the API's English and is marked lang="en" where it is shown.
import type { Language } from "../../shared/i18n/types";

const en = {
  common: {
    loading: "Loading…",
    retry: "Try again",
    cancel: "Cancel",
    yes: "Yes",
    no: "No",
    owned: "In your account",
    guest: "Older case",
  },
  nav: {
    label: "Case pages",
    overview: "Overview",
    reports: "Reports",
  },
  frame: {
    kicker: "Open case",
    caseTitle: "Case {id}",
    created: "Started {date}",
    noCase: "No case is open",
    addDocument: "Add a document",
    addWhenReady: "Available once the current document has been read",
    deleting: "Deleting…",
    deleteCase: "Delete this case",
    deleteTitle: "Delete this case permanently?",
    deleteConsequence: "This erases everything derived from the case on the server: extracted details, the redacted excerpt, audits, appeal letters and claim forms. It cannot be undone.",
    deleteConfirm: "Delete the case",
    addFailed: "Could not add the document. {reason}",
    deleteFailed: "Could not delete the case. {reason}",
    backToDesk: "Back to my cases",
    refreshStatus: "Refresh status",
    streamTimeout: "Processing is taking longer than expected. The document may still be being read; nothing has been checked yet.",
    streamLost: "Lost contact with the processing status. The document may still be processing.",
    processingFailed: "Document processing failed: {reason}",
  },
  problem: {
    gone: "This case no longer exists: it was deleted or it expired (cases are erased 90 days after they start).",
    forbidden: "This case cannot be opened from here. If it was moved into an account, sign in to that account.",
    "signed-out": "Your session ended, so this case (it belongs to your account) cannot be opened. Sign in again.",
    unreachable: "Could not reach the ArogyaRakshak server to open this case.",
  },
  module: {
    standalone: "No case is open. This check works with the details you type in; open a case to use its documents.",
    noCaseTitle: "No case is open",
    noCaseBody: "Open a case from your list, or start a new one. The case is never put in the page address.",
    goToDesk: "Go to my cases",
    processing: "The document is still being read. Results appear here when extraction finishes.",
  },
};

export type CaseCopy = typeof en;

export const caseCopy: Record<Language, CaseCopy> = {
  en,
  hi: {
    common: {
      loading: "लोड हो रहा है…",
      retry: "फिर कोशिश करें",
      cancel: "रद्द करें",
      yes: "हाँ",
      no: "नहीं",
      owned: "आपके खाते में",
      guest: "पुराना केस",
    },
    nav: {
      label: "केस पेज",
      overview: "सारांश",
      reports: "रिपोर्ट",
    },
    frame: {
      kicker: "खुला केस",
      caseTitle: "केस {id}",
      created: "शुरू: {date}",
      noCase: "कोई केस खुला नहीं है",
      addDocument: "दस्तावेज़ जोड़ें",
      addWhenReady: "मौजूदा दस्तावेज़ पढ़ लिए जाने के बाद उपलब्ध",
      deleting: "हटाया जा रहा है…",
      deleteCase: "यह केस हटाएँ",
      deleteTitle: "यह केस स्थायी रूप से हटाएँ?",
      deleteConsequence: "इससे सर्वर पर केस से बनी हर चीज़ मिट जाती है: निकाली गई जानकारी, संपादित अंश, ऑडिट, अपील पत्र और दावा फ़ॉर्म। इसे वापस नहीं किया जा सकता।",
      deleteConfirm: "केस हटाएँ",
      addFailed: "दस्तावेज़ नहीं जोड़ा जा सका। {reason}",
      deleteFailed: "केस नहीं हटाया जा सका। {reason}",
      backToDesk: "मेरे केस पर वापस",
      refreshStatus: "स्थिति ताज़ा करें",
      streamTimeout: "प्रोसेसिंग में अपेक्षा से अधिक समय लग रहा है। दस्तावेज़ अभी भी पढ़ा जा रहा हो सकता है; अभी कुछ भी जाँचा नहीं गया है।",
      streamLost: "प्रोसेसिंग स्थिति से संपर्क टूट गया। दस्तावेज़ अभी भी प्रोसेस हो रहा हो सकता है।",
      processingFailed: "दस्तावेज़ प्रोसेसिंग विफल: {reason}",
    },
    problem: {
      gone: "यह केस अब मौजूद नहीं है: इसे हटा दिया गया या यह समाप्त हो गया (केस शुरू होने के 90 दिन बाद मिटा दिए जाते हैं)।",
      forbidden: "यह केस यहाँ से नहीं खोला जा सकता। यदि इसे किसी खाते में ले जाया गया है, तो उस खाते से साइन इन करें।",
      "signed-out": "आपका सत्र समाप्त हो गया, इसलिए यह केस (आपके खाते का) नहीं खुल सकता। फिर से साइन इन करें।",
      unreachable: "यह केस खोलने के लिए आरोग्यरक्षक सर्वर से संपर्क नहीं हो सका।",
    },
    module: {
      standalone: "कोई केस खुला नहीं है। यह जाँच आपके द्वारा लिखी जानकारी से काम करती है; दस्तावेज़ उपयोग करने के लिए केस खोलें।",
      noCaseTitle: "कोई केस खुला नहीं है",
      noCaseBody: "अपनी सूची से केस खोलें, या नया शुरू करें। केस कभी पेज के पते में नहीं डाला जाता।",
      goToDesk: "मेरे केस पर जाएँ",
      processing: "दस्तावेज़ अभी पढ़ा जा रहा है। निष्कर्षण पूरा होने पर परिणाम यहाँ दिखेंगे।",
    },
  },
  mr: {
    common: {
      loading: "लोड होत आहे…",
      retry: "पुन्हा प्रयत्न करा",
      cancel: "रद्द करा",
      yes: "होय",
      no: "नाही",
      owned: "तुमच्या खात्यात",
      guest: "जुनी केस",
    },
    nav: {
      label: "केस पाने",
      overview: "सारांश",
      reports: "अहवाल",
    },
    frame: {
      kicker: "उघडलेली केस",
      caseTitle: "केस {id}",
      created: "सुरू: {date}",
      noCase: "कोणतीही केस उघडलेली नाही",
      addDocument: "दस्तऐवज जोडा",
      addWhenReady: "सध्याचा दस्तऐवज वाचून झाल्यावर उपलब्ध",
      deleting: "हटवत आहे…",
      deleteCase: "ही केस हटवा",
      deleteTitle: "ही केस कायमची हटवायची?",
      deleteConsequence: "यामुळे सर्व्हरवरील केसमधून तयार झालेले सर्व पुसले जाते: काढलेली माहिती, संपादित उतारा, ऑडिट, अपील पत्रे आणि दावा फॉर्म. हे परत करता येत नाही.",
      deleteConfirm: "केस हटवा",
      addFailed: "दस्तऐवज जोडता आला नाही. {reason}",
      deleteFailed: "केस हटवता आली नाही. {reason}",
      backToDesk: "माझ्या केसकडे परत",
      refreshStatus: "स्थिती ताजी करा",
      streamTimeout: "प्रक्रियेला अपेक्षेपेक्षा जास्त वेळ लागत आहे. दस्तऐवज अजून वाचला जात असू शकतो; अजून काहीही तपासलेले नाही.",
      streamLost: "प्रक्रिया स्थितीशी संपर्क तुटला. दस्तऐवज अजून प्रक्रियेत असू शकतो.",
      processingFailed: "दस्तऐवज प्रक्रिया अयशस्वी: {reason}",
    },
    problem: {
      gone: "ही केस आता अस्तित्वात नाही: ती हटवली गेली किंवा कालबाह्य झाली (केस सुरू झाल्यानंतर 90 दिवसांनी पुसल्या जातात).",
      forbidden: "ही केस येथून उघडता येत नाही. ती एखाद्या खात्यात हलवली असल्यास त्या खात्याने साइन इन करा.",
      "signed-out": "तुमचे सत्र संपले, त्यामुळे ही केस (तुमच्या खात्याची) उघडता येत नाही. पुन्हा साइन इन करा.",
      unreachable: "ही केस उघडण्यासाठी आरोग्यरक्षक सर्व्हरशी संपर्क झाला नाही.",
    },
    module: {
      standalone: "कोणतीही केस उघडलेली नाही. ही तपासणी तुम्ही लिहिलेल्या माहितीवर चालते; दस्तऐवज वापरण्यासाठी केस उघडा.",
      noCaseTitle: "कोणतीही केस उघडलेली नाही",
      noCaseBody: "तुमच्या यादीतून केस उघडा, किंवा नवी सुरू करा. केस कधीही पानाच्या पत्त्यात टाकली जात नाही.",
      goToDesk: "माझ्या केसवर जा",
      processing: "दस्तऐवज अजून वाचला जात आहे. माहिती काढून झाल्यावर निकाल येथे दिसतील.",
    },
  },
};
