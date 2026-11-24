// The upload panel's copy (DocumentUploader), moved verbatim out of translations.ts (Wave 3 M4) so
// the case desk does not ship the whole page dictionary; translations.ts re-uses it, so each
// string still has one source. Hindi and Marathi notes from translations.ts are kept as they were.
import type { Language } from "../shared/i18n/types";

export interface UploadCopy {
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
}

export const uploadCopy: Record<Language, UploadCopy> = {
  en: {
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
  hi: {
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
  mr: {
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
};
