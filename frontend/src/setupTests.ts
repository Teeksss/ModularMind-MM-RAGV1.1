// jest-dom, DOM node'ları için custom jest matchers ekler
import '@testing-library/jest-dom';

// Mock Service Worker'ı başlat
import { server } from './mocks/server';

// Testleri yalıtmak için MSW'yi kuruyoruz
beforeAll(() => server.listen());
// Her testten sonra işleyicileri sıfırla
afterEach(() => server.resetHandlers());
// Testler bittiğinde sunucuyu kapat
afterAll(() => server.close());

// LocalStorage mock
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value.toString();
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// IntersectionObserver mock
global.IntersectionObserver = class IntersectionObserver {
  constructor(callback: IntersectionObserverCallback) {}
  observe() { return null; }
  unobserve() { return null; }
  disconnect() { return null; }
};

// Çeviri fonksiyonu mock (i18n için)
global.i18n = (key: string) => key;

// Konsol hata uyarılarını bastır
const originalConsoleError = console.error;
console.error = (...args) => {
  if (
    typeof args[0] === 'string' && 
    (args[0].includes('Warning: An update to') || 
     args[0].includes('Warning: React does not recognize'))
  ) {
    return;
  }
  originalConsoleError(...args);
};