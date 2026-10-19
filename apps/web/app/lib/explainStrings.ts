import type { Language } from "../translations";

export interface ExplainStrings {
  summary: string;
  headingEvidence: string;
  headingRule: string;
  headingTrust: string;
  headingUndetermined: string;
  headingNotRecorded: string;
  notRecorded: string;
  document: string;
  sourceText: string;
  source: string;
  noEvidence: string;
  noRule: string;
  noModel: string;
  provenance: Record<string, string>;
}

// English is the reviewed copy. The hi/mr strings below are first drafts and
// NEED NATIVE-SPEAKER QA before release. Text that comes from the server (headline, rule
// names, reasons) is English only for now and is shown as received.
export const EXPLAIN_STRINGS: Record<Language, ExplainStrings> = {
  en: {
    summary: "Why am I seeing this?",
    headingEvidence: "Source evidence",
    headingRule: "Rule or reference used",
    headingTrust: "Confidence",
    headingUndetermined: "What could not be determined",
    headingNotRecorded: "Not recorded by the system",
    notRecorded: "not recorded",
    document: "Document",
    sourceText: "Text it was read from",
    source: "Source",
    noEvidence: "No source evidence was recorded for this result.",
    noRule: "No rule or reference row was applied.",
    noModel: "Written by fixed rules from stored data — no AI model wrote this explanation.",
    provenance: {
      OCR_EXTRACTED: "Read from your document",
      LLM_NORMALISED: "Wording may have been normalised by the extractor",
      HUMAN_REVIEWED: "Reviewed by a human",
      USER_ENTERED: "Entered by you",
      REFERENCE_DATA: "Public reference table",
      RULE_COMPUTED: "Computed by a fixed rule",
      NOT_RECORDED: "Origin not recorded",
    },
  },
  hi: {
    // NEEDS NATIVE-SPEAKER QA
    summary: "मुझे यह क्यों दिख रहा है?",
    headingEvidence: "स्रोत प्रमाण",
    headingRule: "उपयोग किया गया नियम या संदर्भ",
    headingTrust: "विश्वसनीयता",
    headingUndetermined: "जो तय नहीं हो सका",
    headingNotRecorded: "सिस्टम ने दर्ज नहीं किया",
    notRecorded: "दर्ज नहीं",
    document: "दस्तावेज़",
    sourceText: "जिस पाठ से पढ़ा गया",
    source: "स्रोत",
    noEvidence: "इस परिणाम के लिए कोई स्रोत प्रमाण दर्ज नहीं है।",
    noRule: "कोई नियम या संदर्भ पंक्ति लागू नहीं हुई।",
    noModel: "यह स्पष्टीकरण संग्रहीत डेटा से तय नियमों द्वारा बना है — किसी AI मॉडल ने नहीं लिखा।",
    provenance: {
      OCR_EXTRACTED: "आपके दस्तावेज़ से पढ़ा गया",
      LLM_NORMALISED: "निष्कर्षक ने शब्दों को बदला हो सकता है",
      HUMAN_REVIEWED: "व्यक्ति द्वारा जाँचा गया",
      USER_ENTERED: "आपके द्वारा दर्ज",
      REFERENCE_DATA: "सार्वजनिक संदर्भ तालिका",
      RULE_COMPUTED: "तय नियम से गणना",
      NOT_RECORDED: "स्रोत दर्ज नहीं",
    },
  },
  mr: {
    // NEEDS NATIVE-SPEAKER QA
    summary: "मला हे का दिसत आहे?",
    headingEvidence: "स्रोत पुरावा",
    headingRule: "वापरलेला नियम किंवा संदर्भ",
    headingTrust: "विश्वासार्हता",
    headingUndetermined: "जे ठरवता आले नाही",
    headingNotRecorded: "प्रणालीने नोंदवले नाही",
    notRecorded: "नोंद नाही",
    document: "दस्तऐवज",
    sourceText: "ज्या मजकुरातून वाचले",
    source: "स्रोत",
    noEvidence: "या निकालासाठी कोणताही स्रोत पुरावा नोंदवलेला नाही.",
    noRule: "कोणताही नियम किंवा संदर्भ ओळ लागू झाली नाही.",
    noModel: "हे स्पष्टीकरण साठवलेल्या डेटावरून ठरावीक नियमांनी तयार केले आहे — कोणत्याही AI मॉडेलने लिहिले नाही.",
    provenance: {
      OCR_EXTRACTED: "तुमच्या दस्तऐवजातून वाचले",
      LLM_NORMALISED: "निष्कर्षकाने शब्द बदलले असू शकतात",
      HUMAN_REVIEWED: "व्यक्तीने तपासले",
      USER_ENTERED: "तुम्ही नोंदवले",
      REFERENCE_DATA: "सार्वजनिक संदर्भ तक्ता",
      RULE_COMPUTED: "ठरावीक नियमाने गणना",
      NOT_RECORDED: "स्रोत नोंदवलेला नाही",
    },
  },
};
