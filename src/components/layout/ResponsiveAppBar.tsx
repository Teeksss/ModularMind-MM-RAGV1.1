import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiMenu, FiChevronDown, FiLogOut, FiUser } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';
import { useResponsive } from '../../utils/responsive';
import MobileMenu from './MobileMenu';
import Logo from '../../assets/logo.svg';

const ResponsiveAppBar: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const { isMobile } = useResponsive();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  
  const handleLogout = async () => {
    await logout();
    setUserMenuOpen(false);
  };
  
  return (
    <>
      <header className="bg-white border-b border-gray-200">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="flex-shrink-0 flex items-center">
                <img
                  className="block h-8 w-auto"
                  src={Logo}
                  alt="ModularMind Logo"
                />
                <span className="ml-2 text-lg font-semibold text-gray-900 hidden sm:block">
                  ModularMind
                </span>
              </Link>
            </div>
            
            <div className="flex items-center">
              {user && (
                <div className="relative">
                  <button
                    className="flex items-center text-sm focus:outline-none"
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                  >
                    <div className="relative">
                      {user.avatarUrl ? (
                        <img
                          src={user.avatarUrl}
                          alt={user.name}
                          className="h-8 w-8 rounded-full object-cover"
                        />
                      ) : (
                        <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
                          {user.name.charAt(0).toUpperCase()}
                        </div>
                      )}
                    </div>
                    {!isMobile && (
                      <>
                        <span className="ml-2 font-medium text-gray-700 hidden md:block max-w-[120px] truncate">
                          {user.name}
                        </span>
                        <FiChevronDown className="ml-1 h-4 w-4 text-gray-500" />
                      </>
                    )}
                  </button>
                  
                  {userMenuOpen && (
                    <div className="absolute right-0 mt-2 w-48 py-2 bg-white rounded-md shadow-lg z-50 border border-gray-200">
                      <div className="px-4 py-2 border-b">
                        <p className="text-sm font-medium text-gray-700 truncate">{user.name}</p>
                        <p className="text-xs text-gray-500 truncate">{user.email}</p>
                      </div>
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        <FiUser className="mr-2 h-4 w-4" />
                        Your Profile
                      </Link>
                      <button
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 flex items-center"
                        onClick={handleLogout}
                      >
                        <FiLogOut className="mr-2 h-4 w-4" />
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
              )}
              
              {isMobile && (
                <button
                  className="ml-4 p-2 text-gray-500 hover:text-gray-700 focus:outline-none"
                  onClick={() => setMobileMenuOpen(true)}
                >
                  <FiMenu className="h-6 w-6" />
                </button>
              )}
            </div>
          </div>
        </div>
      </header>
      
      <MobileMenu 
        isOpen={mobileMenuOpen} 
        onClose={() => setMobileMenuOpen(false)} 
      />
    </>
  );
};

export default ResponsiveAppBar;