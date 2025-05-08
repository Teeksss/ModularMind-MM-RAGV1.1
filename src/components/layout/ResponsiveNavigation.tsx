import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import Logo from '../../assets/logo.svg';
import { 
  FiMenu, FiX, FiSearch, FiUpload, FiSettings, 
  FiBarChart2, FiUsers, FiLogOut, FiUser, FiMic, FiImage
} from 'react-icons/fi';

const ResponsiveNavigation: React.FC = () => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isSearchMenuOpen, setIsSearchMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  // Close menus when URL changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
    setIsUserMenuOpen(false);
    setIsSearchMenuOpen(false);
  }, [location.pathname]);

  // Close menus when clicking outside
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      
      if (isUserMenuOpen && !target.closest('[data-user-menu]')) {
        setIsUserMenuOpen(false);
      }
      
      if (isSearchMenuOpen && !target.closest('[data-search-menu]')) {
        setIsSearchMenuOpen(false);
      }
    };
    
    document.addEventListener('click', handleOutsideClick);
    
    return () => {
      document.removeEventListener('click', handleOutsideClick);
    };
  }, [isUserMenuOpen, isSearchMenuOpen]);

  const isActive = (path: string): boolean => {
    return location.pathname === path || location.pathname.startsWith(`${path}/`);
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const toggleUserMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsUserMenuOpen(!isUserMenuOpen);
  };

  const toggleSearchMenu = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsSearchMenuOpen(!isSearchMenuOpen);
  };

  const handleLogout = async () => {
    setIsUserMenuOpen(false);
    await logout();
  };

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Navigation */}
          <div className="flex">
            {/* Logo */}
            <div className="flex-shrink-0 flex items-center">
              <Link to="/dashboard" className="flex items-center">
                <img className="h-8 w-auto" src={Logo} alt="ModularMind" />
                <span className="ml-2 text-lg font-semibold text-gray-900 hidden sm:block">
                  ModularMind
                </span>
              </Link>
            </div>
            
            {/* Desktop Navigation */}
            <nav className="hidden sm:ml-6 sm:flex sm:space-x-4 sm:items-center">
              <Link
                to="/dashboard"
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  isActive('/dashboard')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                Dashboard
              </Link>
              
              {/* Search dropdown */}
              <div className="relative" data-search-menu>
                <button
                  onClick={toggleSearchMenu}
                  className={`px-3 py-2 rounded-md text-sm font-medium flex items-center ${
                    isActive('/search')
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <FiSearch className="mr-1" />
                  Search
                  <svg className={`ml-1 h-4 w-4 transition-transform ${isSearchMenuOpen ? 'transform rotate-180' : ''}`} xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
                
                {isSearchMenuOpen && (
                  <div className="absolute z-10 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5">
                    <Link
                      to="/search"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiSearch className="inline mr-2" />
                      Text Search
                    </Link>
                    <Link
                      to="/search/image"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiImage className="inline mr-2" />
                      Image Search
                    </Link>
                    <Link
                      to="/search/audio"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiMic className="inline mr-2" />
                      Audio Search
                    </Link>
                  </div>
                )}
              </div>
              
              <Link
                to="/upload"
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  isActive('/upload')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <FiUpload className="inline mr-1" />
                Upload
              </Link>
              
              <Link
                to="/analytics"
                className={`px-3 py-2 rounded-md text-sm font-medium ${
                  isActive('/analytics')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <FiBarChart2 className="inline mr-1" />
                Analytics
              </Link>
              
              {user?.role === 'admin' && (
                <Link
                  to="/admin/users"
                  className={`px-3 py-2 rounded-md text-sm font-medium ${
                    isActive('/admin/users')
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                  }`}
                >
                  <FiUsers className="inline mr-1" />
                  Users
                </Link>
              )}
            </nav>
          </div>
          
          {/* Mobile menu button and User Profile */}
          <div className="flex items-center">
            {/* User Profile Dropdown */}
            {user && (
              <div className="ml-3 relative" data-user-menu>
                <div>
                  <button
                    onClick={toggleUserMenu}
                    className="flex text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                  >
                    <span className="sr-only">Open user menu</span>
                    {user.avatarUrl ? (
                      <img
                        className="h-8 w-8 rounded-full"
                        src={user.avatarUrl}
                        alt={user.name}
                      />
                    ) : (
                      <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
                        {user.name.charAt(0).toUpperCase()}
                      </div>
                    )}
                  </button>
                </div>
                
                {isUserMenuOpen && (
                  <div className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white ring-1 ring-black ring-opacity-5 z-10">
                    <div className="px-4 py-2 text-sm text-gray-700 border-b border-gray-100">
                      Signed in as <span className="font-semibold">{user.email}</span>
                    </div>
                    <Link
                      to="/profile"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiUser className="inline mr-2" />
                      Your Profile
                    </Link>
                    <Link
                      to="/settings"
                      className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiSettings className="inline mr-2" />
                      Settings
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                    >
                      <FiLogOut className="inline mr-2" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            )}
            
            {/* Mobile menu button */}
            <div className="flex ml-4 sm:hidden">
              <button
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-md text-gray-700 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                aria-controls="mobile-menu"
                aria-expanded={isMobileMenuOpen}
                onClick={toggleMobileMenu}
              >
                <span className="sr-only">
                  {isMobileMenuOpen ? 'Close menu' : 'Open menu'}
                </span>
                {isMobileMenuOpen ? (
                  <FiX className="block h-6 w-6" />
                ) : (
                  <FiMenu className="block h-6 w-6" />
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <div className="sm:hidden" id="mobile-menu">
          <div className="pt-2 pb-3 space-y-1">
            <Link
              to="/dashboard"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/dashboard')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiBarChart2 className="inline mr-2" />
              Dashboard
            </Link>
            
            <Link
              to="/search"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/search') && !isActive('/search/image') && !isActive('/search/audio')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiSearch className="inline mr-2" />
              Text Search
            </Link>
            
            <Link
              to="/search/image"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/search/image')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiImage className="inline mr-2" />
              Image Search
            </Link>
            
            <Link
              to="/search/audio"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/search/audio')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiMic className="inline mr-2" />
              Audio Search
            </Link>
            
            <Link
              to="/upload"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/upload')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiUpload className="inline mr-2" />
              Upload
            </Link>
            
            <Link
              to="/analytics"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/analytics')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiBarChart2 className="inline mr-2" />
              Analytics
            </Link>
            
            {user?.role === 'admin' && (
              <Link
                to="/admin/users"
                className={`block px-3 py-2 rounded-md text-base font-medium ${
                  isActive('/admin/users')
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <FiUsers className="inline mr-2" />
                Users
              </Link>
            )}
            
            <Link
              to="/settings"
              className={`block px-3 py-2 rounded-md text-base font-medium ${
                isActive('/settings')
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
              }`}
            >
              <FiSettings className="inline mr-2" />
              Settings
            </Link>
          </div>
          
          {/* Mobile user menu */}
          {user && (
            <div className="pt-4 pb-3 border-t border-gray-200">
              <div className="flex items-center px-4">
                {user.avatarUrl ? (
                  <div className="flex-shrink-0">
                    <img
                      className="h-10 w-10 rounded-full"
                      src={user.avatarUrl}
                      alt={user.name}
                    />
                  </div>
                ) : (
                  <div className="flex-shrink-0 h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center text-white">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="ml-3">
                  <div className="text-base font-medium text-gray-800">{user.name}</div>
                  <div className="text-sm font-medium text-gray-500">{user.email}</div>
                </div>
              </div>
              <div className="mt-3 space-y-1">
                <Link
                  to="/profile"
                  className="block px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                >
                  <FiUser className="inline mr-2" />
                  Your Profile
                </Link>
                <button
                  onClick={handleLogout}
                  className="block w-full text-left px-4 py-2 text-base font-medium text-gray-700 hover:bg-gray-50 hover:text-gray-900"
                >
                  <FiLogOut className="inline mr-2" />
                  Sign out
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </header>
  );
};

export default ResponsiveNavigation;