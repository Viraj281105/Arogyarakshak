// Copy for the account pages (Wave 3 M4, ADR-026). Kept out of translations.ts so only these
// routes ship it.
//
// UNREVIEWED: every Hindi (hi) and Marathi (mr) string in this file is a machine-assisted draft
// and NEEDS NATIVE-SPEAKER QA (apps/web/AGENTS.md) before it is presented as final.
//
// Messages that answer a sign-in or registration attempt come from the API itself where it has
// them (deliberately generic, so nobody can learn whether an address has an account); the strings
// here are only for states the API does not describe (network failure, a mismatch caught in the
// browser, the explanation that email delivery does not exist yet).
import type { Language } from "../../shared/i18n/types";

export interface AuthCopy {
  email: string;
  password: string;
  newPassword: string;
  confirmPassword: string;
  showPassword: string;
  hidePassword: string;
  passwordHint: string;
  working: string;
  unreachable: string;
  untrustedOrigin: string;
  throttled: string;
  /** {seconds} */
  retryIn: string;
  mismatch: string;
  policy: { too_short: string; too_long: string; only_spaces: string; same_as_email: string };
  emailUnavailableTitle: string;
  emailUnavailable: string;
  login: {
    title: string;
    lede: string;
    submit: string;
    forgot: string;
    noAccount: string;
    register: string;
    alreadyIn: string;
    goToCases: string;
    sessionEnded: string;
  };
  register: {
    title: string;
    lede: string;
    submit: string;
    haveAccount: string;
    signIn: string;
    doneTitle: string;
    verifyNote: string;
    whatIsKept: string;
  };
  forgot: {
    title: string;
    lede: string;
    submit: string;
    doneTitle: string;
    backToSignIn: string;
  };
  reset: {
    title: string;
    lede: string;
    token: string;
    tokenHint: string;
    tokenFromLink: string;
    submit: string;
    doneTitle: string;
    done: string;
    signIn: string;
  };
  verify: {
    title: string;
    lede: string;
    token: string;
    tokenFromLink: string;
    submit: string;
    done: string;
    alreadyVerified: string;
    requestTitle: string;
    requestSubmit: string;
  };
}

export const authCopy: Record<Language, AuthCopy> = {
  en: {
    email: "Email address",
    password: "Password",
    newPassword: "New password",
    confirmPassword: "Repeat the password",
    showPassword: "Show password",
    hidePassword: "Hide password",
    passwordHint: "12 to 128 characters. Spaces are allowed; a long phrase is easiest to remember.",
    working: "Please wait…",
    unreachable:
      "Could not reach the ArogyaRakshak server. Check your connection. If you run the server yourself, accounts need its CORS_ORIGINS to list this site.",
    untrustedOrigin: "The server does not accept sign-in requests from this web address (its AUTH_TRUSTED_ORIGINS or CORS_ORIGINS does not list it).",
    throttled: "Too many attempts from this device.",
    retryIn: "Try again in about {seconds} seconds.",
    mismatch: "The two passwords are not the same.",
    policy: {
      too_short: "Use a password of at least 12 characters.",
      too_long: "Use a password of at most 128 characters.",
      only_spaces: "The password cannot be only spaces.",
      same_as_email: "The password cannot be your email address.",
    },
    emailUnavailableTitle: "Email is not available yet",
    emailUnavailable:
      "This server cannot send email yet, so no verification or password-reset message will arrive. If an administrator gave you a link, open it: the confirmation form on that page still works.",
    login: {
      title: "Sign in",
      lede: "Signed in, your cases are kept with your account (until they expire after 90 days or you delete them) instead of only in this browser tab.",
      submit: "Sign in",
      forgot: "Forgot your password?",
      noAccount: "No account yet?",
      register: "Create an account",
      alreadyIn: "You are signed in as {email}.",
      goToCases: "Go to my cases",
      sessionEnded: "Your session ended. Sign in again.",
    },
    register: {
      title: "Create an account",
      lede: "An account keeps your cases together across visits. You can still use ArogyaRakshak without one.",
      submit: "Create account",
      haveAccount: "Already have an account?",
      signIn: "Sign in",
      doneTitle: "Request received",
      verifyNote: "Email verification cannot be completed yet because this server does not send email. You can sign in without it.",
      whatIsKept:
        "Stored for the account: your email address and a salted hash of your password (never the password itself). Your documents are never kept, with or without an account.",
    },
    forgot: {
      title: "Forgot your password",
      lede: "Ask for a password-reset link for your account.",
      submit: "Ask for a reset link",
      doneTitle: "Request received",
      backToSignIn: "Back to sign in",
    },
    reset: {
      title: "Set a new password",
      lede: "Choose a new password. Every device signed in to this account is signed out.",
      token: "Reset code from the link",
      tokenHint: "Paste the code only if this page did not open from the link itself.",
      tokenFromLink: "The reset code from your link has been read. It is no longer shown in the address bar.",
      submit: "Set new password",
      doneTitle: "Password changed",
      done: "Your password has been changed and every session was signed out. Sign in with the new password.",
      signIn: "Sign in",
    },
    verify: {
      title: "Confirm your email address",
      lede: "Confirming shows that the address belongs to you. Signing in does not require it.",
      token: "Verification code from the link",
      tokenFromLink: "The code from your link has been read. It is no longer shown in the address bar.",
      submit: "Confirm email address",
      done: "Your email address is confirmed.",
      alreadyVerified: "The address {email} is already confirmed.",
      requestTitle: "Ask for a new verification link",
      requestSubmit: "Ask for a link",
    },
  },
  hi: {
    email: "ईमेल पता",
    password: "पासवर्ड",
    newPassword: "नया पासवर्ड",
    confirmPassword: "पासवर्ड दोबारा लिखें",
    showPassword: "पासवर्ड दिखाएँ",
    hidePassword: "पासवर्ड छिपाएँ",
    passwordHint: "12 से 128 अक्षर। स्पेस की अनुमति है; लंबा वाक्य याद रखना सबसे आसान होता है।",
    working: "कृपया प्रतीक्षा करें…",
    unreachable:
      "आरोग्यरक्षक सर्वर से संपर्क नहीं हो सका। अपना कनेक्शन जाँचें। यदि सर्वर आप स्वयं चलाते हैं, तो खातों के लिए उसके CORS_ORIGINS में यह साइट होनी चाहिए।",
    untrustedOrigin: "सर्वर इस वेब पते से साइन-इन अनुरोध स्वीकार नहीं करता (उसके AUTH_TRUSTED_ORIGINS या CORS_ORIGINS में यह नहीं है)।",
    throttled: "इस डिवाइस से बहुत अधिक प्रयास हुए।",
    retryIn: "लगभग {seconds} सेकंड बाद फिर कोशिश करें।",
    mismatch: "दोनों पासवर्ड एक जैसे नहीं हैं।",
    policy: {
      too_short: "कम से कम 12 अक्षरों का पासवर्ड रखें।",
      too_long: "अधिकतम 128 अक्षरों का पासवर्ड रखें।",
      only_spaces: "पासवर्ड केवल स्पेस नहीं हो सकता।",
      same_as_email: "पासवर्ड आपका ईमेल पता नहीं हो सकता।",
    },
    emailUnavailableTitle: "ईमेल अभी उपलब्ध नहीं है",
    emailUnavailable:
      "यह सर्वर अभी ईमेल नहीं भेज सकता, इसलिए सत्यापन या पासवर्ड-रीसेट का कोई संदेश नहीं आएगा। यदि किसी व्यवस्थापक ने आपको लिंक दिया है, तो उसे खोलें: उस पेज का पुष्टि फ़ॉर्म अब भी काम करता है।",
    login: {
      title: "साइन इन करें",
      lede: "साइन इन करने पर आपके केस केवल इस ब्राउज़र टैब में नहीं, बल्कि आपके खाते के साथ रखे जाते हैं (90 दिन बाद समाप्त होने या आपके हटाने तक)।",
      submit: "साइन इन करें",
      forgot: "पासवर्ड भूल गए?",
      noAccount: "अभी खाता नहीं है?",
      register: "खाता बनाएँ",
      alreadyIn: "आप {email} के रूप में साइन इन हैं।",
      goToCases: "मेरे केस पर जाएँ",
      sessionEnded: "आपका सत्र समाप्त हो गया। फिर से साइन इन करें।",
    },
    register: {
      title: "खाता बनाएँ",
      lede: "खाता आपके केस को अलग-अलग विज़िट में एक साथ रखता है। आप बिना खाते के भी आरोग्यरक्षक का उपयोग कर सकते हैं।",
      submit: "खाता बनाएँ",
      haveAccount: "पहले से खाता है?",
      signIn: "साइन इन करें",
      doneTitle: "अनुरोध मिल गया",
      verifyNote: "ईमेल सत्यापन अभी पूरा नहीं हो सकता क्योंकि यह सर्वर ईमेल नहीं भेजता। आप इसके बिना साइन इन कर सकते हैं।",
      whatIsKept:
        "खाते के लिए रखा जाता है: आपका ईमेल पता और आपके पासवर्ड का सॉल्टेड हैश (पासवर्ड स्वयं कभी नहीं)। आपके दस्तावेज़ कभी नहीं रखे जाते, खाते के साथ या बिना।",
    },
    forgot: {
      title: "पासवर्ड भूल गए",
      lede: "अपने खाते के लिए पासवर्ड-रीसेट लिंक माँगें।",
      submit: "रीसेट लिंक माँगें",
      doneTitle: "अनुरोध मिल गया",
      backToSignIn: "साइन इन पर वापस जाएँ",
    },
    reset: {
      title: "नया पासवर्ड रखें",
      lede: "नया पासवर्ड चुनें। इस खाते से साइन इन हर डिवाइस साइन आउट हो जाएगा।",
      token: "लिंक का रीसेट कोड",
      tokenHint: "कोड तभी चिपकाएँ जब यह पेज सीधे लिंक से न खुला हो।",
      tokenFromLink: "आपके लिंक का रीसेट कोड पढ़ लिया गया है। अब यह पता बार में नहीं दिखता।",
      submit: "नया पासवर्ड रखें",
      doneTitle: "पासवर्ड बदल गया",
      done: "आपका पासवर्ड बदल गया है और हर सत्र साइन आउट हो गया। नए पासवर्ड से साइन इन करें।",
      signIn: "साइन इन करें",
    },
    verify: {
      title: "अपना ईमेल पता पुष्टि करें",
      lede: "पुष्टि से पता चलता है कि यह पता आपका है। साइन इन के लिए यह ज़रूरी नहीं है।",
      token: "लिंक का सत्यापन कोड",
      tokenFromLink: "आपके लिंक का कोड पढ़ लिया गया है। अब यह पता बार में नहीं दिखता।",
      submit: "ईमेल पता पुष्टि करें",
      done: "आपका ईमेल पता पुष्ट हो गया है।",
      alreadyVerified: "पता {email} पहले से पुष्ट है।",
      requestTitle: "नया सत्यापन लिंक माँगें",
      requestSubmit: "लिंक माँगें",
    },
  },
  mr: {
    email: "ईमेल पत्ता",
    password: "पासवर्ड",
    newPassword: "नवीन पासवर्ड",
    confirmPassword: "पासवर्ड पुन्हा लिहा",
    showPassword: "पासवर्ड दाखवा",
    hidePassword: "पासवर्ड लपवा",
    passwordHint: "12 ते 128 अक्षरे. स्पेस चालतात; लांब वाक्य लक्षात ठेवणे सर्वात सोपे असते.",
    working: "कृपया थांबा…",
    unreachable:
      "आरोग्यरक्षक सर्व्हरशी संपर्क झाला नाही. तुमचे कनेक्शन तपासा. सर्व्हर तुम्ही स्वतः चालवत असल्यास, खात्यांसाठी त्याच्या CORS_ORIGINS मध्ये ही साइट असावी.",
    untrustedOrigin: "सर्व्हर या वेब पत्त्यावरून साइन-इन विनंत्या स्वीकारत नाही (त्याच्या AUTH_TRUSTED_ORIGINS किंवा CORS_ORIGINS मध्ये हा नाही).",
    throttled: "या डिव्हाइसवरून खूप प्रयत्न झाले.",
    retryIn: "सुमारे {seconds} सेकंदांनी पुन्हा प्रयत्न करा.",
    mismatch: "दोन्ही पासवर्ड सारखे नाहीत.",
    policy: {
      too_short: "किमान 12 अक्षरांचा पासवर्ड ठेवा.",
      too_long: "जास्तीत जास्त 128 अक्षरांचा पासवर्ड ठेवा.",
      only_spaces: "पासवर्ड फक्त स्पेस असू शकत नाही.",
      same_as_email: "पासवर्ड तुमचा ईमेल पत्ता असू शकत नाही.",
    },
    emailUnavailableTitle: "ईमेल अजून उपलब्ध नाही",
    emailUnavailable:
      "हा सर्व्हर अजून ईमेल पाठवू शकत नाही, त्यामुळे पडताळणी किंवा पासवर्ड-रीसेटचा कोणताही संदेश येणार नाही. एखाद्या प्रशासकाने तुम्हाला लिंक दिली असल्यास ती उघडा: त्या पानावरील पुष्टी फॉर्म अजूनही चालतो.",
    login: {
      title: "साइन इन करा",
      lede: "साइन इन केल्यावर तुमचे केस फक्त या ब्राउझर टॅबमध्ये नव्हे तर तुमच्या खात्यासोबत ठेवले जातात (90 दिवसांनी कालबाह्य होईपर्यंत किंवा तुम्ही हटवेपर्यंत).",
      submit: "साइन इन करा",
      forgot: "पासवर्ड विसरलात?",
      noAccount: "अजून खाते नाही?",
      register: "खाते तयार करा",
      alreadyIn: "तुम्ही {email} म्हणून साइन इन आहात.",
      goToCases: "माझ्या केसवर जा",
      sessionEnded: "तुमचे सत्र संपले. पुन्हा साइन इन करा.",
    },
    register: {
      title: "खाते तयार करा",
      lede: "खाते तुमचे केस वेगवेगळ्या भेटींमध्ये एकत्र ठेवते. खात्याशिवायही तुम्ही आरोग्यरक्षक वापरू शकता.",
      submit: "खाते तयार करा",
      haveAccount: "आधीच खाते आहे?",
      signIn: "साइन इन करा",
      doneTitle: "विनंती मिळाली",
      verifyNote: "ईमेल पडताळणी अजून पूर्ण होऊ शकत नाही कारण हा सर्व्हर ईमेल पाठवत नाही. तुम्ही त्याशिवाय साइन इन करू शकता.",
      whatIsKept:
        "खात्यासाठी ठेवले जाते: तुमचा ईमेल पत्ता आणि तुमच्या पासवर्डचा सॉल्टेड हॅश (पासवर्ड स्वतः कधीच नाही). तुमचे दस्तऐवज कधीच ठेवले जात नाहीत, खात्यासह किंवा खात्याशिवाय.",
    },
    forgot: {
      title: "पासवर्ड विसरलात",
      lede: "तुमच्या खात्यासाठी पासवर्ड-रीसेट लिंक मागा.",
      submit: "रीसेट लिंक मागा",
      doneTitle: "विनंती मिळाली",
      backToSignIn: "साइन इनकडे परत",
    },
    reset: {
      title: "नवीन पासवर्ड ठेवा",
      lede: "नवीन पासवर्ड निवडा. या खात्याने साइन इन असलेले प्रत्येक डिव्हाइस साइन आउट होईल.",
      token: "लिंकमधील रीसेट कोड",
      tokenHint: "हे पान थेट लिंकवरून उघडले नसेल तरच कोड चिकटवा.",
      tokenFromLink: "तुमच्या लिंकमधील रीसेट कोड वाचला आहे. तो आता पत्ता बारमध्ये दिसत नाही.",
      submit: "नवीन पासवर्ड ठेवा",
      doneTitle: "पासवर्ड बदलला",
      done: "तुमचा पासवर्ड बदलला आहे आणि प्रत्येक सत्र साइन आउट झाले. नवीन पासवर्डने साइन इन करा.",
      signIn: "साइन इन करा",
    },
    verify: {
      title: "तुमचा ईमेल पत्ता निश्चित करा",
      lede: "निश्चितीमुळे हा पत्ता तुमचाच आहे हे दिसते. साइन इनसाठी ते आवश्यक नाही.",
      token: "लिंकमधील पडताळणी कोड",
      tokenFromLink: "तुमच्या लिंकमधील कोड वाचला आहे. तो आता पत्ता बारमध्ये दिसत नाही.",
      submit: "ईमेल पत्ता निश्चित करा",
      done: "तुमचा ईमेल पत्ता निश्चित झाला आहे.",
      alreadyVerified: "पत्ता {email} आधीच निश्चित आहे.",
      requestTitle: "नवीन पडताळणी लिंक मागा",
      requestSubmit: "लिंक मागा",
    },
  },
};

/** Replaces {name} placeholders. */
export function fillCopy(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (m, k: string) => (k in values ? String(values[k]) : m));
}
