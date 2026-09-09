import { useState, useCallback } from 'react';
import { Language, translations, MobileTranslations } from '../translations';

export function useLanguage(initialLang: Language = 'en') {
  const [language, setLanguageState] = useState<Language>(initialLang);

  const setLanguage = useCallback((newLang: Language) => {
    setLanguageState(newLang);
  }, []);

  const t: MobileTranslations = translations[language] || translations.en;

  return {
    language,
    setLanguage,
    t,
  };
}
