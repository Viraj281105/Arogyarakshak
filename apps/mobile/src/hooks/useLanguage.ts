import { useSyncExternalStore } from 'react';
import { getLanguage, setLanguage, subscribeLanguage } from '../services/languageStore';
import { Language, translations, MobileTranslations } from '../translations';

/**
 * The app-wide UI language. One shared store: changing it in the header changes every screen
 * (each screen used to keep its own copy, so only the header and title followed the switch).
 */
export function useLanguage(_initialLang: Language = 'en') {
  const language = useSyncExternalStore(subscribeLanguage, getLanguage, getLanguage);
  const t: MobileTranslations = translations[language] || translations.en;

  return {
    language,
    setLanguage,
    t,
  };
}
