import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

import enTranslation from './locales/en/translation.json';
import trTranslation from './locales/tr/translation.json';

// Initialize i18next
i18n
  // Load translations using http backend
  // (In production, translations would be loaded from server or CDN)
  .use(Backend)
  
  // Detect user language
  .use(LanguageDetector)
  
  // Pass the i18n instance to react-i18next
  .use(initReactI18next)
  
  // Initialize i18next
  .init({
    // Fallback language
    fallbackLng: 'en',
    
    // Debug mode in development
    debug: process.env.NODE_ENV === 'development',
    
    // Namespace for translations
    ns: ['translation'],
    defaultNS: 'translation',
    
    // Detect language from browser
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
    
    // Interpolation options
    interpolation: {
      escapeValue: false, // Not needed for React
    },
    
    // Preloaded translations (will be overridden by Backend if loaded)
    resources: {
      en: {
        translation: enTranslation,
      },
      tr: {
        translation: trTranslation,
      },
    },
  });

export default i18n;