import { apiService } from './api';

/**
 * Service for language operations
 */
export const languageService = {
  /**
   * Detect language of text
   */
  detectLanguage: async (text: string) => {
    return apiService.post('/languages/detect', { text });
  },

  /**
   * Preprocess text based on language
   */
  preprocessText: async (
    text: string, 
    options?: { 
      language?: string, 
      removeStopwords?: boolean,
      normalizeChars?: boolean,
      stem?: boolean
    }
  ) => {
    return apiService.post('/languages/preprocess', {
      text,
      language: options?.language,
      remove_stopwords: options?.removeStopwords,
      normalize_chars: options?.normalizeChars,
      stem: options?.stem
    });
  },

  /**
   * Translate text
   */
  translateText: async (
    text: string,
    targetLanguage: string,
    sourceLanguage?: string,
    forceRefresh?: boolean
  ) => {
    return apiService.post('/languages/translate', {
      text,
      target_language: targetLanguage,
      source_language: sourceLanguage,
      force_refresh: forceRefresh
    });
  },

  /**
   * Get supported languages
   */
  getSupportedLanguages: async (includeDetails: boolean = false) => {
    return apiService.get('/languages/supported', {
      params: { include_details: includeDetails }
    });
  }
};