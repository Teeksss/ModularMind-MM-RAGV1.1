import React, { useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { 
  BiHomeAlt, 
  BiChat, 
  BiFileBlank, 
  BiData, 
  BiCog, 
  BiHistory,
  BiX,
  BiBookOpen,
  BiGridAlt
} from 'react-icons/bi';

import { useAuthStore } from '../../store/authStore';
import logo from '../../assets/images/logo.svg';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { t } = useTranslation();
  const location = useLocation();
  const { user } = useAuthStore();
  
  // Close sidebar on location change on mobile
  useEffect(() => {
    if (window.innerWidth < 768) {
      onClose();
    }
  }, [location.pathname, onClose]);
  
  // Define navigation items
  const navItems = [
    {
      icon: <BiHomeAlt className="w-5 h-5" />,
      label: t('nav.dashboard'),
      path: '/dashboard',
    },
    {
      icon: <BiChat className="w-5 h-5" />,
      label: t('nav.chat'),
      path: '/dashboard/chat',
    },
    {
      icon: <BiFileBlank className="w-5 h-5" />,
      label: t('nav.documents'),
      path: '/dashboard/documents',
    },
    {
      icon: <BiData className="w-5 h-5" />,
      label: t('nav.dataSources'),
      path: '/dashboard/data-sources',
    },
    {
      icon: <BiHistory className="w-5 h-5" />,
      label: t('nav.history'),
      path: '/dashboard/history',
    },
    {
      icon: <BiBookOpen className="w-5 h-5" />,
      label: t('nav.knowledgeBase'),
      path: '/dashboard/knowledge',
    },
  ];
  
  // Admin-only items
  const adminItems = [
    {
      icon: <BiGridAlt className="w-5 h-5" />,
      label: t('nav.agentDashboard'),
      path: '/dashboard/agents',
    },
  ];
  
  // Bottom items
  const bottomItems = [
    {
      icon: <BiCog className="w-5 h-5" />,
      label: t('nav.settings'),
      path: '/dashboard/settings',
    },
  ];
  
  // Check if a route is active
  const isActive = (path: string) => {
    if (path === '/dashboard' && location.pathname === '/dashboard') {
      return true;
    }
    return location.pathname.startsWith(path) && path !== '/dashboard';
  };
  
  return (
    <>
      {/* Overlay for mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-20 md:hidden"
          onClick={onClose}
        ></div>
      )}
      
      {/* Sidebar */}
      <aside 
        className={`fixed top-0 left-0 z-30 w-64 h-screen pt-16 transition-transform duration-300 
          bg-white dark:bg-gray-800 border-r dark:border-gray-700 
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}
      >
        {/* Close button (mobile only) */}
        <button 
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white md:hidden"
          onClick={onClose}
        >
          <BiX className="w-6 h-6" />
        </button>
        
        <div className="flex flex-col h-full px-3 py-4 overflow-y-auto">
          {/* Logo and branding */}
          <div className="flex items-center mb-6 px-2">
            <img src={logo} alt="ModularMind" className="h-8 mr-3" />
            <span className="text-lg font-semibold dark:text-white">
              ModularMind
            </span>
          </div>
          
          {/* Primary navigation */}
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) => `
                    flex items-center p-2 text-base font-medium rounded-lg
                    ${isActive || isActive(item.path)
                      ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }
                  `}
                >
                  {item.icon}
                  <span className="ml-3">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
          
          {/* Admin section */}
          {user?.role === 'admin' && (
            <div className="pt-4 mt-4 border-t border-gray-200 dark:border-gray-700">
              <h3 className="px-2 mb-2 text-xs font-semibold text-gray-500 uppercase dark:text-gray-400">
                {t('nav.adminSection')}
              </h3>
              <ul className="space-y-2">
                {adminItems.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) => `
                        flex items-center p-2 text-base font-medium rounded-lg
                        ${isActive || isActive(item.path)
                          ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                        }
                      `}
                    >
                      {item.icon}
                      <span className="ml-3">{item.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          )}
          
          {/* Bottom items */}
          <div className="mt-auto">
            <ul className="space-y-2">
              {bottomItems.map((item) => (
                <li key={item.path}>
                  <NavLink
                    to={item.path}
                    className={({ isActive }) => `
                      flex items-center p-2 text-base font-medium rounded-lg
                      ${isActive || isActive(item.path)
                        ? 'bg-gray-100 dark:bg-gray-700 text-blue-600 dark:text-blue-400'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                      }
                    `}
                  >
                    {item.icon}
                    <span className="ml-3">{item.label}</span>
                  </NavLink>
                </li>
              ))}
            </ul>
            
            {/* User info */}
            <div className="flex items-center mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
              <div className="flex-shrink-0">
                <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
                  <span className="text-blue-600 dark:text-blue-300 font-medium">
                    {user?.full_name?.charAt(0) || user?.username?.charAt(0) || '?'}
                  </span>
                </div>
              </div>
              <div className="ml-3 overflow-hidden">
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                  {user?.full_name || user?.username}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                  {user?.email}
                </p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default Sidebar;