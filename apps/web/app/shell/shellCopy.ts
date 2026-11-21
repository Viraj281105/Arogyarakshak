import type { Language } from "../shared/i18n/types";
import type { ModuleTab } from "./nav";

/**
 * Strings the app shell (header, drawer, footer, skip link) needs on EVERY route. Kept apart
 * from translations.ts so the shell does not ship the full page dictionary to every route;
 * translations.ts re-uses tagline, byodBadge/byodDescription, tabs and footer from here, so
 * each string still has one source.
 *
 * tagline, byod*, tabs and footer were moved verbatim from translations.ts. Every other Hindi
 * and Marathi string here is NEW in WS4 and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md).
 */
export interface ShellCopy {
  appName: string;
  tagline: string;
  byodBadge: string;
  byodDescription: string;
  prototype: string;
  prototypeTitle: string;
  skipToContent: string;
  nav: { primary: string; home: string; check: string; modules: string; reviewer: string };
  menu: { open: string; close: string; title: string; checks: string };
  language: { label: string };
  theme: { toDark: string; toLight: string };
  tabs: Record<ModuleTab, string>;
  footer: {
    disclaimer: string;
    statutoryNote: string;
    cghsRef: string;
    irdaiRef: string;
    nppaRef: string;
    sources: string;
    explore: string;
    notAdvice: string;
    zeroRetention: string;
    academic: string;
    copyright: string;
  };
}

// Literals on purpose: importing the vendored shared i18n dictionary for this one string put the
// whole dictionary (~5 KB gzip) into every route. tests/shell.test.ts keeps them equal to it.
const APP_NAME: Record<Language, string> = { en: "ArogyaRakshak", hi: "आरोग्यरक्षक", mr: "आरोग्यरक्षक" };

/** Value for <html lang> per UI language (Devanagari shaping and screen-reader voice). */
export const HTML_LANG: Record<Language, string> = { en: "en", hi: "hi", mr: "mr" };

/** Labels of the language switcher, each written in its own language. */
export const LANGUAGE_LABELS: Record<Language, string> = { en: "EN", hi: "हिंदी", mr: "मराठी" };

export const shellCopy: Record<Language, ShellCopy> = {
  en: {
    appName: APP_NAME.en,
    tagline: "Statutory Healthcare Cost & Insurance Rights Intelligence",
    byodBadge: "BYOD: Zero Document Retention",
    byodDescription: "Files are parsed in transient RAM memory and purged immediately after extraction.",
    prototype: "Prototype",
    prototypeTitle: "Release candidate of an academic project — not a production medical or legal service",
    skipToContent: "Skip to main content",
    nav: {
      primary: "Main",
      home: "Home",
      check: "Check a document",
      modules: "The five checks",
      reviewer: "Reviewer workspace",
    },
    menu: { open: "Open menu", close: "Close menu", title: "Menu", checks: "Checks" },
    language: { label: "Language" },
    theme: { toDark: "Switch to dark theme", toLight: "Switch to light theme" },
    tabs: {
      billnyay: "BillNyay (Bill Audit)",
      bimanyay: "BimaNyay (Claim Denials)",
      daavisetu: "DaaviSetu (Pre-Auth)",
      schemesetu: "SchemeSetu (Schemes)",
      dawacheck: "DawaCheck (Medicine Ceiling)",
    },
    footer: {
      disclaimer: "ArogyaRakshak provides statutory auditing intelligence based on public regulatory frameworks (CGHS, NPPA, IRDAI).",
      statutoryNote:
        "Reference prices come from curated subsets of public data (CGHS, NPPA). A case's extracted details are kept until you delete the case or it expires (90 days by default); your original file is never kept.",
      cghsRef: "CGHS OM 2024 Tariffs",
      irdaiRef: "IRDAI Master Circular May 2024",
      nppaRef: "NPPA DPCO Schedule-I",
      sources: "Reference sources",
      explore: "Explore",
      notAdvice: "Not legal or medical advice",
      zeroRetention: "Zero Document Retention (BYOD)",
      academic: "Academic prototype",
      copyright: "© 2026 ArogyaRakshak (आरोग्यरक्षक) — Open Source MIT License",
    },
  },
  hi: {
    appName: APP_NAME.hi,
    tagline: "संवैधानिक स्वास्थ्य खर्च और बीमा अधिकार विश्लेषण",
    byodBadge: "BYOD: शून्य दस्तावेज़ संचयन नीति",
    byodDescription: "दस्तावेज़ केवल अस्थायी रैम (RAM) में प्रोसेस होते हैं और निष्कर्षण के तुरंत बाद हटा दिए जाते हैं।",
    // NEEDS NATIVE-SPEAKER QA: every string from here to `tabs` is new in WS4.
    prototype: "प्रोटोटाइप",
    prototypeTitle: "एक शैक्षणिक परियोजना का रिलीज़ कैंडिडेट — यह कोई वास्तविक चिकित्सा या कानूनी सेवा नहीं है",
    skipToContent: "मुख्य सामग्री पर जाएँ",
    nav: {
      primary: "मुख्य",
      home: "होम",
      check: "दस्तावेज़ जाँचें",
      modules: "पाँच जाँचें",
      reviewer: "समीक्षक कार्यक्षेत्र",
    },
    menu: { open: "मेनू खोलें", close: "मेनू बंद करें", title: "मेनू", checks: "जाँचें" },
    language: { label: "भाषा" },
    theme: { toDark: "डार्क थीम पर जाएँ", toLight: "लाइट थीम पर जाएँ" },
    tabs: {
      billnyay: "बिलन्याय (बिल ऑडिट)",
      bimanyay: "बीमान्याय (बीमा दावे)",
      daavisetu: "दावेसेतु (प्री-ऑथ फॉर्म)",
      schemesetu: "योजनासेतु (सरकारी योजनाएं)",
      dawacheck: "दवाचेक (दवा मूल्य सीमा)",
    },
    footer: {
      disclaimer: "आरोग्यरक्षक सार्वजनिक विनियामक नियमों (CGHS, NPPA, IRDAI) के आधार पर सूचनात्मक विश्लेषण प्रदान करता है।",
      // NEEDS NATIVE-SPEAKER QA (the previous copy wrongly said nothing is kept after the session).
      statutoryNote:
        "संदर्भ मूल्य सार्वजनिक डेटा (CGHS, NPPA) के चुने हुए अंशों से लिए गए हैं। केस की निकाली गई जानकारी तब तक रखी जाती है जब तक आप केस हटा नहीं देते या वह समाप्त नहीं हो जाता (डिफ़ॉल्ट 90 दिन); आपकी मूल फ़ाइल कभी नहीं रखी जाती।",
      cghsRef: "CGHS दरें 2024",
      irdaiRef: "IRDAI मास्टर सर्कुलर मई 2024",
      nppaRef: "NPPA DPCO शेड्यूल-I",
      // NEEDS NATIVE-SPEAKER QA: the six strings below are new in WS4.
      sources: "संदर्भ स्रोत",
      explore: "देखें",
      notAdvice: "कानूनी या चिकित्सा सलाह नहीं",
      zeroRetention: "शून्य दस्तावेज़ संचयन (BYOD)",
      academic: "शैक्षणिक प्रोटोटाइप",
      copyright: "© 2026 आरोग्यरक्षक (ArogyaRakshak) — ओपन सोर्स MIT लाइसेंस",
    },
  },
  mr: {
    appName: APP_NAME.mr,
    tagline: "वैधानिक आरोग्य खर्च व विमा हक्क मार्गदर्शन",
    byodBadge: "BYOD: शून्य दस्तऐवज संचयन",
    byodDescription: "दस्तऐवज फक्त तात्पुरत्या रॅम (RAM) मध्ये तपासले जातात आणि लगेच नष्ट केले जातात.",
    // NEEDS NATIVE-SPEAKER QA: every string from here to `tabs` is new in WS4.
    prototype: "प्रोटोटाइप",
    prototypeTitle: "शैक्षणिक प्रकल्पाची रिलीज कँडिडेट आवृत्ती — ही प्रत्यक्ष वैद्यकीय किंवा कायदेशीर सेवा नाही",
    skipToContent: "मुख्य मजकुराकडे जा",
    nav: {
      primary: "मुख्य",
      home: "मुख्यपृष्ठ",
      check: "दस्तऐवज तपासा",
      modules: "पाच तपासण्या",
      reviewer: "परीक्षक कार्यक्षेत्र",
    },
    menu: { open: "मेनू उघडा", close: "मेनू बंद करा", title: "मेनू", checks: "तपासण्या" },
    language: { label: "भाषा" },
    theme: { toDark: "डार्क थीम वापरा", toLight: "लाइट थीम वापरा" },
    tabs: {
      billnyay: "बिलन्याय (बिल ऑडिट)",
      bimanyay: "बीमान्याय (विमा दावे)",
      daavisetu: "दावेसेतु (प्री-ऑथ फॉर्म)",
      schemesetu: "योजनासेतु (सरकारी योजना)",
      dawacheck: "दवाचेक (औषध कमाल किंमत)",
    },
    footer: {
      disclaimer: "आरोग्यरक्षक सार्वजनिक विनियामक नियमांवर (CGHS, NPPA, IRDAI) आधारित माहितीपर विश्लेषण प्रदान करते.",
      // NEEDS NATIVE-SPEAKER QA (the previous copy wrongly said no personal data is kept after use).
      statutoryNote:
        "संदर्भ किमती सार्वजनिक डेटाच्या (CGHS, NPPA) निवडक भागांतून घेतल्या आहेत. केसमधून काढलेली माहिती तुम्ही केस हटवेपर्यंत किंवा ती कालबाह्य होईपर्यंत (डीफॉल्ट 90 दिवस) ठेवली जाते; तुमची मूळ फाइल कधीही ठेवली जात नाही.",
      cghsRef: "CGHS दर 2024",
      irdaiRef: "IRDAI मास्टर सर्क्युलर मे 2024",
      nppaRef: "NPPA DPCO शेड्यूल-I",
      // NEEDS NATIVE-SPEAKER QA: the six strings below are new in WS4.
      sources: "संदर्भ स्रोत",
      explore: "पहा",
      notAdvice: "कायदेशीर किंवा वैद्यकीय सल्ला नाही",
      zeroRetention: "शून्य दस्तऐवज संचयन (BYOD)",
      academic: "शैक्षणिक प्रोटोटाइप",
      copyright: "© 2026 आरोग्यरक्षक (ArogyaRakshak) — ओपन सोर्स MIT परवाना",
    },
  },
};
