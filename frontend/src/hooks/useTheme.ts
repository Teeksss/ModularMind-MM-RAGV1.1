import { useState, useEffect, useContext, createContext } from 'react';

// Tema türleri
type ThemeType = 'light' | 'dark' | 'system';

// Tema context
interface ThemeContextType {
  theme: ThemeType;
  isDark: boolean;
  setTheme: (theme: ThemeType) => void;
}

// Varsayılan context değerleri
const defaultContextValue: ThemeContextType = {
  theme: 'system',
  isDark: false,
  setTheme: () => {}
};

// Context oluşturuluyor
const ThemeContext = createContext<ThemeContextType>(defaultContextValue);

// Local storage key
const STORAGE_KEY = 'modularmind-theme';

// Medya sorgusu oluştur
const createMediaQuery = () => 
  window.matchMedia('(prefers-color-scheme: dark)');

// Tema sağlayıcısı
export const ThemeProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  // Başlangıç temasını belirle
  const getInitialTheme = (): ThemeType => {
    // Local storage'dan tema tercihini kontrol et
    if (typeof window !== 'undefined' && window.localStorage) {
      const storedPreference = window.localStorage.getItem(STORAGE_KEY);
      if (storedPreference) {
        return storedPreference as ThemeType;
      }
      
      // Sistem temasını kullan
      return 'system';
    }
    
    return 'light';
  };
  
  const [theme, setTheme] = useState<ThemeType>(getInitialTheme());
  const [isDark, setIsDark] = useState<boolean>(false);
  
  const applyTheme = (newTheme: ThemeType) => {
    // Tema değerini güncelle
    const root = window.document.documentElement;
    const isDarkMode = 
      newTheme === 'dark' || 
      (newTheme === 'system' && createMediaQuery().matches);
    
    // HTML sınıfını güncelle
    root.classList.remove('light', 'dark');
    root.classList.add(isDarkMode ? 'dark' : 'light');
    
    // Karanlık mod durumunu güncelle
    setIsDark(isDarkMode);
  };
  
  useEffect(() => {
    // Temanın uygulanması
    applyTheme(theme);
    
    // Sistem teması değiştiğinde güncelle
    if (theme === 'system') {
      const mediaQuery = createMediaQuery();
      const handleChange = () => applyTheme('system');
      
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }
  }, [theme]);
  
  // Temayı güncelle ve sakla
  const handleSetTheme = (newTheme: ThemeType) => {
    setTheme(newTheme);
    
    // Local storage'a kaydet
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEY, newTheme);
    }
  };
  
  // Context değerini oluştur
  const contextValue: ThemeContextType = {
    theme,
    isDark,
    setTheme: handleSetTheme
  };
  
  return (
    <ThemeContext.Provider value={contextValue}>
      {children}
    </ThemeContext.Provider>
  );
};

// Temayı kullanmak için hook
export const useTheme = () => {
  const context = useContext(ThemeContext);
  
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  
  return context;
};