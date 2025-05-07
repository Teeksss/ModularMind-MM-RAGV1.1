/**
 * Application Configuration
 * 
 * This file contains the global configuration for the ModularMind
 * frontend application. Environment-specific values can be
 * overridden with environment variables.
 */

// Environment detection
const isProd = import.meta.env.VITE_APP_ENV === 'production';
const isDev = import.meta.env.VITE_APP_ENV === 'development' || !isProd;

// API configuration
const apiUrl = import.meta.env.VITE_API_URL || (
  isProd ? '/api/v1' : 'http://localhost:8000/api/v1'
);

export const config = {
  // Application info
  app: {
    name: 'ModularMind MM-RAG',
    version: '1.1.0',
    environment: isProd ? 'production' : 'development',
    isDev,
    isProd
  },
  
  // API configuration
  api: {
    baseUrl: apiUrl,
    timeout: 30000, // 30 seconds
    retryCount: 3,
    retryDelay: 1000, // 1 second
  },
  
  // Authentication
  auth: {
    // Storage keys
    tokenStorageKey: 'modularmind_token',
    refreshTokenStorageKey: 'modularmind_refresh_token',
    
    // Auth behavior
    autoRefresh: true,
    tokenExpiryMargin: 60, // seconds before expiry to refresh token
  },
  
  // UI Configuration
  ui: {
    // Default values
    defaultLanguage: 'tr',
    defaultTheme: 'system', // 'light', 'dark', 'system'
    defaultItemsPerPage: 10,
    
    // Date formatting
    dateFormat: 'DD.MM.YYYY',
    timeFormat: 'HH:mm',
    
    // Animation settings
    animationsEnabled: true,
    
    // Responsive breakpoints
    breakpoints: {
      xs: 0,
      sm: 640,
      md: 768,
      lg: 1024,
      xl: 1280,
      xxl: 1536,
    },
  },
  
  // Feature flags
  features: {
    darkMode: true,
    multiLanguage: true,
    notifications: true,
    analytics: isProd,
    debugMode: isDev,
    demoMode: false,
    webSocketSupport: true,
    syntheticQA: true,
    documentRelations: true,
  },
  
  // Limits and constraints
  limits: {
    maxUploadSize: 50 * 1024 * 1024, // 50MB
    maxQueryLength: 5000,
    maxDocumentTitleLength: 255,
  },
  
  // Websocket configuration
  websocket: {
    enabled: true,
    reconnectInterval: 3000,
    reconnectAttempts: 5,
    url: import.meta.env.VITE_WS_URL || (
      apiUrl.replace(/^http/, 'ws') + '/ws'
    ),
  },
};

export default config;