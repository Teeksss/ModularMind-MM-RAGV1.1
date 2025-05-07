import React from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

const Footer: React.FC = () => {
  const { t } = useTranslation();
  const currentYear = new Date().getFullYear();
  
  return (
    <footer className="bg-white dark:bg-gray-800 border-t dark:border-gray-700">
      <div className="w-full mx-auto p-4 md:py-6">
        <div className="sm:flex sm:items-center sm:justify-between">
          <span className="text-sm text-gray-500 dark:text-gray-400">
            © {currentYear} <Link to="/" className="hover:underline">ModularMind</Link>. {t('footer.allRightsReserved')}
          </span>
          <div className="flex mt-4 space-x-5 sm:mt-0">
            <Link to="/privacy" className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
              {t('footer.privacy')}
            </Link>
            <Link to="/terms" className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
              {t('footer.terms')}
            </Link>
            <Link to="/help" className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300">
              {t('footer.help')}
            </Link>
            <a 
              href="https://modularmind.com" 
              target="_blank" 
              rel="noopener noreferrer" 
              className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
            >
              {t('footer.website')}
            </a>
          </div>
        </div>
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {t('footer.version')} 1.1.0
        </div>
      </div>
    </footer>
  );
};

export default Footer;