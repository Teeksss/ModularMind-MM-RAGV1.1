import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Menu, Transition } from '@headlessui/react';
import { FaGlobe, FaCheck } from 'react-icons/fa';

interface LanguageOption {
  code: string;
  name: string;
  flag: string;
  native?: string;
}

interface LanguageSelectorProps {
  onChange?: (language: string) => void;
  showFlag?: boolean;
  showName?: boolean;
  className?: string;
  buttonClassName?: string;
  menuClassName?: string;
}

const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  onChange,
  showFlag = true,
  showName = true,
  className = '',
  buttonClassName = '',
  menuClassName = ''
}) => {
  const { i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState(i18n.language || 'en');
  
  // Define supported languages with their names and flags
  const languages: LanguageOption[] = [
    { code: 'en', name: 'English', flag: '🇬🇧', native: 'English' },
    { code: 'tr', name: 'Turkish', flag: '🇹🇷', native: 'Türkçe' },
    { code: 'de', name: 'German', flag: '🇩🇪', native: 'Deutsch' },
    { code: 'fr', name: 'French', flag: '🇫🇷', native: 'Français' },
    { code: 'es', name: 'Spanish', flag: '🇪🇸', native: 'Español' },
    { code: 'zh', name: 'Chinese', flag: '🇨🇳', native: '中文' },
    { code: 'ja', name: 'Japanese', flag: '🇯🇵', native: '日本語' },
    { code: 'ar', name: 'Arabic', flag: '🇸🇦', native: 'العربية' }
  ];
  
  // Find current language details
  const currentLanguageDetails = languages.find(lang => lang.code === currentLanguage) || languages[0];
  
  // Update when language changes externally
  useEffect(() => {
    setCurrentLanguage(i18n.language);
  }, [i18n.language]);
  
  // Handle language change
  const changeLanguage = (languageCode: string) => {
    i18n.changeLanguage(languageCode).then(() => {
      setCurrentLanguage(languageCode);
      document.documentElement.lang = languageCode;
      
      // Store preference in localStorage
      localStorage.setItem('language', languageCode);
      
      // Call onChange callback if provided
      if (onChange) {
        onChange(languageCode);
      }
    });
  };
  
  return (
    <div className={`language-selector ${className}`}>
      <Menu as="div" className="relative inline-block text-left">
        <Menu.Button
          className={`inline-flex items-center justify-center w-full px-4 py-2 text-sm font-medium rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 ${buttonClassName || 'text-gray-700 bg-white hover:bg-gray-50 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-700'}`}
        >
          <FaGlobe className={`${showName ? 'mr-2' : ''} h-4 w-4`} aria-hidden="true" />
          
          {showFlag && (
            <span className="mr-1" aria-hidden="true">
              {currentLanguageDetails.flag}
            </span>
          )}
          
          {showName && (
            <span>
              {currentLanguageDetails.native || currentLanguageDetails.name}
            </span>
          )}
        </Menu.Button>
        
        <Transition
          enter="transition ease-out duration-100"
          enterFrom="transform opacity-0 scale-95"
          enterTo="transform opacity-100 scale-100"
          leave="transition ease-in duration-75"
          leaveFrom="transform opacity-100 scale-100"
          leaveTo="transform opacity-0 scale-95"
        >
          <Menu.Items
            className={`absolute z-10 right-0 mt-2 w-48 origin-top-right divide-y divide-gray-100 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none ${menuClassName || 'bg-white dark:bg-gray-800 dark:divide-gray-700'}`}
          >
            <div className="py-1">
              {languages.map((language) => (
                <Menu.Item key={language.code}>
                  {({ active }) => (
                    <button
                      onClick={() => changeLanguage(language.code)}
                      className={`${
                        active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'
                      } group flex items-center w-full px-2 py-2 text-sm`}
                    >
                      <span className="mr-2 text-lg" aria-hidden="true">
                        {language.flag}
                      </span>
                      <span className="flex-grow text-left">
                        {language.native || language.name}
                      </span>
                      {currentLanguage === language.code && (
                        <FaCheck className="h-4 w-4 text-green-500" aria-hidden="true" />
                      )}
                    </button>
                  )}
                </Menu.Item>
              ))}
            </div>
          </Menu.Items>
        </Transition>
      </Menu>
    </div>
  );
};

export default LanguageSelector;