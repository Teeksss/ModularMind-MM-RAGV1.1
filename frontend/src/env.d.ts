/// <reference types="vite/client" />
/// <reference types="vite-plugin-svgr/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string;
  readonly VITE_APP_NAME: string;
  readonly VITE_SENTRY_DSN: string;
  readonly VITE_ENVIRONMENT: string;
  readonly VITE_ANALYTICS_ID: string;
  readonly VITE_ENABLE_MOCK_API: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare namespace process {
  namespace env {
    const APP_VERSION: string;
    const BUILD_DATE: string;
  }
}