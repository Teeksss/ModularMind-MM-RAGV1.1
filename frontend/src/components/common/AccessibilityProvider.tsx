import React, { createContext, useState, useEffect, useContext } from 'react';

// Erişilebilirlik ayarları arayüzü
interface AccessibilitySettings {
  fontSize: 'normal' | 'large' | 'x-large';
  highContrast: boolean;
  reducedMotion: boolean;
  textSpacing: 'normal' | 'wide' | 'wider';
  dyslexiaFont: boolean;
  screenReader: boolean;
}

// Context arayüzü
interface AccessibilityContextType {
  settings: AccessibilitySettings;
  updateSetting: <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => void;
  resetSettings: () => void;
}

// Varsayılan ayarlar
const defaultSettings: AccessibilitySettings = {
  fontSize: 'normal',
  highContrast: false,
  reducedMotion: false,
  textSpacing: 'normal',
  dyslexiaFont: false,
  screenReader: false
};

// Context oluşturma
const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

// Local storage anahtarı
const STORAGE_KEY = 'modularmind-accessibility';

export const AccessibilityProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  // Local storage'dan ayarları yükle veya varsayılanları kullan
  const loadSettings = (): AccessibilitySettings => {
    if (typeof window !== 'undefined') {
      try {
        const storedSettings = localStorage.getItem(STORAGE_KEY);
        if (storedSettings) {
          return JSON.parse(storedSettings);
        }
      } catch (error) {
        console.error('Erişilebilirlik ayarları yüklenirken hata oluştu:', error);
      }
    }
    return defaultSettings;
  };

  // State
  const [settings, setSettings] = useState<AccessibilitySettings>(loadSettings);

  // Ayarları güncelleme fonksiyonu
  const updateSetting = <K extends keyof AccessibilitySettings>(
    key: K,
    value: AccessibilitySettings[K]
  ) => {
    const newSettings = { ...settings, [key]: value };
    setSettings(newSettings);
    
    // Local storage'a kaydet
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newSettings));
    }
  };

  // Ayarları sıfırlama fonksiyonu
  const resetSettings = () => {
    setSettings(defaultSettings);
    
    if (typeof window !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultSettings));
    }
  };

  // Ayarları html elementine uygula
  useEffect(() => {
    const htmlElement = document.documentElement;
    
    // Font boyutu
    htmlElement.style.fontSize = settings.fontSize === 'normal' 
      ? '16px' 
      : settings.fontSize === 'large' 
        ? '20px' 
        : '24px';
    
    // Yüksek kontrast
    if (settings.highContrast) {
      htmlElement.classList.add('high-contrast');
    } else {
      htmlElement.classList.remove('high-contrast');
    }
    
    // Azaltılmış hareket
    if (settings.reducedMotion) {
      htmlElement.classList.add('reduced-motion');
    } else {
      htmlElement.classList.remove('reduced-motion');
    }
    
    // Metin aralığı
    htmlElement.style.letterSpacing = settings.textSpacing === 'normal' 
      ? 'normal' 
      : settings.textSpacing === 'wide' 
        ? '0.05em' 
        : '0.1em';
    
    // Disleksi fontu
    if (settings.dyslexiaFont) {
      htmlElement.classList.add('dyslexia-font');
    } else {
      htmlElement.classList.remove('dyslexia-font');
    }
    
    // Ekran okuyucu
    if (settings.screenReader) {
      // ARIA belirteçleri ekle
      document.querySelectorAll('button, a')
        .forEach(el => {
          if (!el.getAttribute('aria-label') && el.textContent) {
            el.setAttribute('aria-label', el.textContent);
          }
        });
    }
  }, [settings]);

  // Provider değeri
  const value = {
    settings,
    updateSetting,
    resetSettings
  };

  return (
    <AccessibilityContext.Provider value={value}>
      {children}
    </AccessibilityContext.Provider>
  );
};

// Hook
export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  
  if (context === undefined) {
    throw new Error('useAccessibility must be used within an AccessibilityProvider');
  }
  
  return context;
};

// Erişilebilirlik paneli bileşeni
export const AccessibilityPanel: React.FC<{isOpen: boolean; onClose: () => void}> = ({ isOpen, onClose }) => {
  const { settings, updateSetting, resetSettings } = useAccessibility();
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 max-w-md w-full">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">Erişilebilirlik Ayarları</h2>
          <button 
            onClick={onClose}
            className="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700"
            aria-label="Kapat"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Font Boyutu</label>
            <div className="flex space-x-2">
              <button 
                className={`px-3 py-1 border rounded ${settings.fontSize === 'normal' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('fontSize', 'normal')}
              >
                Normal
              </button>
              <button 
                className={`px-3 py-1 border rounded ${settings.fontSize === 'large' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('fontSize', 'large')}
              >
                Büyük
              </button>
              <button 
                className={`px-3 py-1 border rounded ${settings.fontSize === 'x-large' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('fontSize', 'x-large')}
              >
                Çok Büyük
              </button>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-1">Metin Aralığı</label>
            <div className="flex space-x-2">
              <button 
                className={`px-3 py-1 border rounded ${settings.textSpacing === 'normal' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('textSpacing', 'normal')}
              >
                Normal
              </button>
              <button 
                className={`px-3 py-1 border rounded ${settings.textSpacing === 'wide' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('textSpacing', 'wide')}
              >
                Geniş
              </button>
              <button 
                className={`px-3 py-1 border rounded ${settings.textSpacing === 'wider' ? 'bg-blue-100 border-blue-500 dark:bg-blue-900 dark:border-blue-400' : 'border-gray-300 dark:border-gray-600'}`}
                onClick={() => updateSetting('textSpacing', 'wider')}
              >
                Daha Geniş
              </button>
            </div>
          </div>
          
          <div className="flex items-center">
            <input 
              type="checkbox" 
              id="highContrast"
              checked={settings.highContrast}
              onChange={(e) => updateSetting('highContrast', e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <label htmlFor="highContrast" className="ml-2 text-sm">Yüksek Kontrast</label>
          </div>
          
          <div className="flex items-center">
            <input 
              type="checkbox" 
              id="reducedMotion"
              checked={settings.reducedMotion}
              onChange={(e) => updateSetting('reducedMotion', e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <label htmlFor="reducedMotion" className="ml-2 text-sm">Azaltılmış Hareket</label>
          </div>
          
          <div className="flex items-center">
            <input 
              type="checkbox" 
              id="dyslexiaFont"
              checked={settings.dyslexiaFont}
              onChange={(e) => updateSetting('dyslexiaFont', e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <label htmlFor="dyslexiaFont" className="ml-2 text-sm">Disleksi Dostu Font</label>
          </div>
          
          <div className="flex items-center">
            <input 
              type="checkbox" 
              id="screenReader"
              checked={settings.screenReader}
              onChange={(e) => updateSetting('screenReader', e.target.checked)}
              className="h-4 w-4 text-blue-600 rounded border-gray-300 focus:ring-blue-500"
            />
            <label htmlFor="screenReader" className="ml-2 text-sm">Ekran Okuyucu Optimizasyonları</label>
          </div>
          
          <div className="pt-4 flex justify-end space-x-2">
            <button 
              onClick={resetSettings}
              className="px-3 py-1 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              Sıfırla
            </button>
            <button 
              onClick={onClose}
              className="px-3 py-1 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Tamam
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};