import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  BiMenu, 
  BiX, 
  BiSun, 
  BiMoon, 
  BiLogOut, 
  BiUserCircle,
  BiNotification,
  BiGlobe
} from 'react-icons/bi';

import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import Dropdown from '../common/Dropdown';
import logo from '../../assets/images/logo.svg';

interface HeaderProps {
  toggleSidebar: () => void;
  isSidebarOpen: boolean;
}

const Header: React.FC<HeaderProps> = ({ toggleSidebar, isSidebarOpen }) => {
  const { t, i18n } = useTranslation();
  const { logout, user } = useAuthStore();
  const { theme, toggleTheme } = useThemeStore();
  const [isScrolled, setIsScrolled] = useState(false);
  
  // Languages supported
  const languages = [
    { code: 'en', name: 'English' },
    { code: 'tr', name: 'Türkçe' },
    { code: 'de', name: 'Deutsch' },
    { code: 'fr', name: 'Français' },
  ];
  
  // Handle scroll event to add shadow when scrolled
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 0);
    };
    
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);
  
  // Handle language change
  const changeLanguage = (langCode: string) => {
    i18n.changeLanguage(langCode);
    
    // Store language preference in localstorage
    localStorage.setItem('language', langCode);
    
    // If user is logged in, update preferences
    if (user) {
      // This would typically make an API call to update user preferences
      console.log('Language changed to:', langCode);
    }
  };
  
  // Handle logout
  const handleLogout = () => {
    logout();
  };
  
  return (
    <header className={`fixed top-0 left-0 right-0 z-30 bg-white dark:bg-gray-800 border-b dark:border-gray-700 transition-shadow ${
      isScrolled ? 'shadow-md' : ''
    }`}>
      <div className="flex items-center justify-between h-16 px-4">
        {/* Left section: Logo and mobile menu */}
        <div className="flex items-center">
          <button
            type="button"
            className="p-2 mr-2 text-gray-600 rounded-lg cursor-pointer md:hidden hover:text-gray-900 hover:bg-gray-100 focus:bg-gray-100 dark:focus:bg-gray-700 focus:ring-2 focus:ring-gray-100 dark:focus:ring-gray-700 dark:text-gray-400 dark:hover:bg-gray-700 dark:hover:text-white"
            onClick={toggleSidebar}
          >
            {isSidebarOpen ? <BiX className="w-6 h-6" /> : <BiMenu className="w-6 h-6" />}
            <span className="sr-only">
              {isSidebarOpen ? t('common.closeSidebar') : t('common.openSidebar')}
            </span>
          </button>
          
          <Link to="/dashboard" className="flex items-center">
            <img src={logo} className="h-8 mr-3" alt="ModularMind Logo" />
            <span className="hidden md:inline-block text-xl font-semibold dark:text-white">
              ModularMind
            </span>
          </Link>
        </div>
        
        {/* Right section: User menu, notifications, theme, etc. */}
        <div className="flex items-center space-x-3">
          {/* Language selector */}
          <Dropdown
            trigger={
              <button
                type="button"
                className="p-2 text-gray-500 rounded-lg hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-700"
              >
                <BiGlobe className="w-5 h-5" />
              </button>
            }
            align="right"
            width="w-40"
          >
            <div className="py-1">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => changeLanguage(lang.code)}
                  className={`block w-full text-left px-4 py-2 text-sm ${
                    i18n.language === lang.code
                      ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                  }`}
                >
                  {lang.name}
                </button>
              ))}
            </div>
          </Dropdown>
          
          {/* Theme toggler */}
          <button
            type="button"
            className="p-2 text-gray-500 rounded-lg hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-700"
            onClick={toggleTheme}
          >
            {theme === 'dark' ? (
              <BiSun className="w-5 h-5" />
            ) : (
              <BiMoon className="w-5 h-5" />
            )}
          </button>
          
          {/* Notifications */}
          <button
            type="button"
            className="p-2 text-gray-500 rounded-lg hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-700"
          >
            <BiNotification className="w-5 h-5" />
          </button>
          
          {/* User menu */}
          <Dropdown
            trigger={
              <button
                type="button"
                className="flex items-center space-x-2 p-2 text-gray-500 rounded-lg hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-white dark:hover:bg-gray-700"
              >
                <BiUserCircle className="w-5 h-5" />
                <span className="hidden md:inline-block text-sm font-medium">
                  {user?.username || t('common.account')}
                </span>
              </button>
            }
            align="right"
            width="w-48"
          >
            <div className="px-4 py-3 text-sm text-gray-900 dark:text-white">
              <div className="font-medium">{user?.full_name || user?.username}</div>
              <div className="truncate text-gray-500 dark:text-gray-400">{user?.email}</div>
            </div>
            <hr className="border-gray-200 dark:border-gray-700" />
            <div className="py-1">
              <Link
                to="/dashboard/profile"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
              >
                {t('nav.profile')}
              </Link>
              <Link
                to="/dashboard/settings"
                className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 dark:hover:text-white"
              >
                {t('nav.settings')}
              </Link>
              <button
                onClick={handleLogout}
                className="flex items-center w-full px-4 py-2 text-sm text-red-600 hover:bg-gray-100 dark:text-red-400 dark:hover:bg-gray-700"
              >
                <BiLogOut className="w-4 h-4 mr-2" />
                {t('auth.logout')}
              </button>
            </div>
          </Dropdown>
        </div>
      </div>
    </header>
  );
};

export default Header;