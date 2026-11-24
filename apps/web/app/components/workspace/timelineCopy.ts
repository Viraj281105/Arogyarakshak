// Copy for the timeline explorer (loaded with its chunk) (Wave 3 M4). One file per page area so each route ships only its own
// strings (split from one workspace dictionary to hold the route bundle budgets).
//
// UNREVIEWED: every Hindi (hi) and Marathi (mr) string in this file is a machine-assisted draft
// and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md) before it is presented as final. Text that
// comes from the API stays in the API's English and is marked lang="en" where it is shown.
import type { Language } from "../../shared/i18n/types";

const en = {
  timeline: {
    title: "Timeline",
    lede: "What has happened to this case. Each step comes from a stored record with its own time.",
    error: "Could not load the timeline",
    inProgress: "In progress: {stage}",
    empty: "Nothing has been recorded for this case yet.",
    filterLabel: "Show only",
    kinds: {
      document: "Documents",
      extraction: "Extraction",
      reading: "Readings",
      review: "Reviews",
      module: "Checks",
      safety: "Safety",
      appeal: "Appeal",
      claim: "Claim",
    },
    newestFirst: "Newest first",
    count: "Showing {shown} of {total} steps",
    actors: {
      MACHINE: "Software",
      HUMAN: "Human reviewer",
      PATIENT: "You",
    },
    now: "Now: {checkable} of {total} medicines can be price-checked; {held} held back until a person reads the entry.",
  },
};

export type TimelineCopy = typeof en;

export const timelineCopy: Record<Language, TimelineCopy> = {
  en,
  hi: {
    timeline: {
      title: "समयरेखा",
      lede: "इस केस के साथ क्या हुआ। हर चरण अपने समय वाले संग्रहीत रिकॉर्ड से आता है।",
      error: "समयरेखा लोड नहीं हो सकी",
      inProgress: "जारी: {stage}",
      empty: "इस केस के लिए अभी कुछ दर्ज नहीं हुआ।",
      filterLabel: "केवल दिखाएँ",
      kinds: {
        document: "दस्तावेज़",
        extraction: "निष्कर्षण",
        reading: "पठन",
        review: "समीक्षा",
        module: "जाँचें",
        safety: "सुरक्षा",
        appeal: "अपील",
        claim: "दावा",
      },
      newestFirst: "नए पहले",
      count: "{total} में से {shown} चरण",
      actors: {
        MACHINE: "सॉफ़्टवेयर",
        HUMAN: "मानव समीक्षक",
        PATIENT: "आप",
      },
      now: "अभी: {total} में से {checkable} दवाओं की कीमत जाँची जा सकती है; {held} तब तक रोकी गईं जब तक कोई व्यक्ति प्रविष्टि न पढ़े।",
    },
  },
  mr: {
    timeline: {
      title: "कालरेषा",
      lede: "या केसचे काय झाले. प्रत्येक टप्पा स्वतःच्या वेळेसह साठवलेल्या नोंदीतून येतो.",
      error: "कालरेषा लोड झाली नाही",
      inProgress: "सुरू आहे: {stage}",
      empty: "या केससाठी अजून काहीही नोंदलेले नाही.",
      filterLabel: "फक्त दाखवा",
      kinds: {
        document: "दस्तऐवज",
        extraction: "माहिती काढणे",
        reading: "वाचन",
        review: "पुनरावलोकन",
        module: "तपासण्या",
        safety: "सुरक्षा",
        appeal: "अपील",
        claim: "दावा",
      },
      newestFirst: "नवीन आधी",
      count: "{total} पैकी {shown} टप्पे",
      actors: {
        MACHINE: "सॉफ्टवेअर",
        HUMAN: "मानवी परीक्षक",
        PATIENT: "तुम्ही",
      },
      now: "आता: {total} पैकी {checkable} औषधांची किंमत तपासता येते; {held} एखादी व्यक्ती नोंद वाचेपर्यंत थांबवली.",
    },
  },
};
