import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

// Import locales
import enTranslations from './locales/en.json';
import trTranslations from './locales/tr.json';

// Resources object with all translations
const resources = {
  en: {
    translation: enTranslations
  },
  tr: {
    translation: trTranslations
  }
};

// Configure i18n
i18n
  // Load translations from HTTP backend (if used)
  .use(Backend)
  // Detect user language
  .use(LanguageDetector)
  // Pass i18n instance to react-i18next
  .use(initReactI18next)
  // Initialize i18n
  .init({
    resources,
    fallbackLng: 'en',
    debug: process.env.NODE_ENV === 'development',
    
    interpolation: {
      escapeValue: false, // React already safes from XSS
    },
    
    // Detection options
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    
    // React specific options
    react: {
      useSuspense: true,
    },
    
    // Other options
    supportedLngs: ['en', 'tr', 'de', 'fr', 'es', 'zh', 'ja', 'ar'],
    load: 'languageOnly',
  });

export default i18n;