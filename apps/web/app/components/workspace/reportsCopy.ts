// Copy for the report viewer (/app/case/reports) (Wave 3 M4). One file per page area so each route ships only its own
// strings (split from one workspace dictionary to hold the route bundle budgets).
//
// UNREVIEWED: every Hindi (hi) and Marathi (mr) string in this file is a machine-assisted draft
// and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md) before it is presented as final. Text that
// comes from the API stays in the API's English and is marked lang="en" where it is shown.
import type { Language } from "../../shared/i18n/types";

const en = {
  reports: {
    title: "Reports",
    lede: "The files that exist for this case. Each is built from what is stored now; none contains your original document.",
    noCase: "Open a case to see its reports.",
    appealTitle: "Appeal letter (PDF)",
    appealBody: "The BillNyay appeal draft, signed by ArogyaRakshak so changes can be detected.",
    appealAbsent: "Not available for this case: no appeal has been drafted yet.",
    openBillNyay: "Draft one in BillNyay",
    downloadPdf: "Download PDF",
    claimTitle: "Pre-authorisation form and claim package",
    claimBody: "The IRDAI pre-authorisation form prepared in DaaviSetu, and a ZIP with it, a redacted summary and a manifest. Prepared only; nothing is sent to an insurer.",
    claimAbsent: "Not available for this case: no pre-authorisation form has been prepared yet.",
    openDaaviSetu: "Prepare one in DaaviSetu",
    downloadPackage: "Download package (ZIP)",
    packTitle: "Claim Pack",
    packBody: "One ZIP for the person helping with the paperwork. Sections that do not exist for this case say so inside the pack.",
    noConsent: "Not available for this case: it was started without consent to share details across the checks.",
    downloadFailed: "Download failed. {reason}",
    checkFailed: "Could not check whether this file exists",
    downloading: "Downloading…",
    verifyTitle: "Integrity check of the stored PDF",
    hashMatches: "Stored bytes match their fingerprint",
    signatureValid: "ArogyaRakshak signature valid",
  },
};

export type ReportsCopy = typeof en;

export const reportsCopy: Record<Language, ReportsCopy> = {
  en,
  hi: {
    reports: {
      title: "रिपोर्ट",
      lede: "इस केस के लिए मौजूद फ़ाइलें। हर फ़ाइल अभी संग्रहीत जानकारी से बनती है; किसी में आपका मूल दस्तावेज़ नहीं है।",
      noCase: "रिपोर्ट देखने के लिए केस खोलें।",
      appealTitle: "अपील पत्र (PDF)",
      appealBody: "बिलन्याय का अपील मसौदा, आरोग्यरक्षक द्वारा हस्ताक्षरित ताकि बदलाव पकड़े जा सकें।",
      appealAbsent: "इस केस के लिए उपलब्ध नहीं: अभी कोई अपील नहीं बनी।",
      openBillNyay: "बिलन्याय में बनाएँ",
      downloadPdf: "PDF डाउनलोड करें",
      claimTitle: "प्री-ऑथराइज़ेशन फ़ॉर्म और दावा पैकेज",
      claimBody: "दावेसेतु में तैयार IRDAI प्री-ऑथराइज़ेशन फ़ॉर्म, और उसके साथ संपादित सारांश व सूची वाली ZIP। केवल तैयार; बीमा कंपनी को कुछ नहीं भेजा जाता।",
      claimAbsent: "इस केस के लिए उपलब्ध नहीं: अभी कोई प्री-ऑथराइज़ेशन फ़ॉर्म तैयार नहीं हुआ।",
      openDaaviSetu: "दावेसेतु में तैयार करें",
      downloadPackage: "पैकेज डाउनलोड करें (ZIP)",
      packTitle: "क्लेम पैक",
      packBody: "कागज़ी काम में मदद करने वाले व्यक्ति के लिए एक ZIP। जो हिस्से इस केस के लिए नहीं हैं, वे पैक में ऐसा बताते हैं।",
      noConsent: "इस केस के लिए उपलब्ध नहीं: यह जाँचों में जानकारी साझा करने की सहमति के बिना शुरू हुआ था।",
      downloadFailed: "डाउनलोड विफल। {reason}",
      checkFailed: "यह फ़ाइल मौजूद है या नहीं, जाँचा नहीं जा सका",
      downloading: "डाउनलोड हो रहा है…",
      verifyTitle: "संग्रहीत PDF की अखंडता जाँच",
      hashMatches: "संग्रहीत बाइट्स अपने फ़िंगरप्रिंट से मेल खाते हैं",
      signatureValid: "आरोग्यरक्षक हस्ताक्षर मान्य",
    },
  },
  mr: {
    reports: {
      title: "अहवाल",
      lede: "या केससाठी असलेल्या फाइल्स. प्रत्येक फाइल आत्ता साठवलेल्या माहितीतून बनते; कोणत्याही फाइलमध्ये तुमचा मूळ दस्तऐवज नाही.",
      noCase: "अहवाल पाहण्यासाठी केस उघडा.",
      appealTitle: "अपील पत्र (PDF)",
      appealBody: "बिलन्यायचा अपील मसुदा, बदल ओळखता यावेत म्हणून आरोग्यरक्षकने स्वाक्षरी केलेला.",
      appealAbsent: "या केससाठी उपलब्ध नाही: अजून अपील तयार झालेले नाही.",
      openBillNyay: "बिलन्यायमध्ये तयार करा",
      downloadPdf: "PDF डाउनलोड करा",
      claimTitle: "प्री-ऑथरायझेशन फॉर्म आणि दावा पॅकेज",
      claimBody: "दावेसेतुमध्ये तयार केलेला IRDAI प्री-ऑथरायझेशन फॉर्म, आणि त्यासह संपादित सारांश व यादी असलेली ZIP. फक्त तयार; विमा कंपनीला काहीही पाठवले जात नाही.",
      claimAbsent: "या केससाठी उपलब्ध नाही: अजून प्री-ऑथरायझेशन फॉर्म तयार झालेला नाही.",
      openDaaviSetu: "दावेसेतुमध्ये तयार करा",
      downloadPackage: "पॅकेज डाउनलोड करा (ZIP)",
      packTitle: "क्लेम पॅक",
      packBody: "कागदपत्रांत मदत करणाऱ्या व्यक्तीसाठी एक ZIP. या केससाठी नसलेले भाग पॅकमध्ये तसे सांगतात.",
      noConsent: "या केससाठी उपलब्ध नाही: ती तपासण्यांमध्ये माहिती सामायिक करण्याच्या संमतीशिवाय सुरू झाली होती.",
      downloadFailed: "डाउनलोड अयशस्वी. {reason}",
      checkFailed: "ही फाइल आहे की नाही हे तपासता आले नाही",
      downloading: "डाउनलोड होत आहे…",
      verifyTitle: "साठवलेल्या PDF ची अखंडता तपासणी",
      hashMatches: "साठवलेले बाइट्स त्यांच्या फिंगरप्रिंटशी जुळतात",
      signatureValid: "आरोग्यरक्षक स्वाक्षरी वैध",
    },
  },
};
