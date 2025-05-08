import React, { useState, ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import Logo from '../../assets/logo.svg';
import { 
  FiMenu, FiX, FiSearch, FiUpload, FiSettings, 
  FiBarChart2, FiUsers, FiLogOut, FiChevronDown 
} from 'react-icons/fi';

type AppLayoutProps = {
  children: ReactNode;
};

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout } = useAuth();
  const location = useLocation();

  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };

  const toggleUserMenu = () => {
    setUserMenuOpen(!userMenuOpen);
  };

  const handleLogout = async () => {
    await logout();
  };

  const isActive = (path: string): boolean => {
    return location.pathname.startsWith(path);
  };

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <FiBarChart2 /> },
    { name: 'Search', path: '/search', icon: <FiSearch /> },
    { name: 'Upload', path: '/upload', icon: <FiUpload /> },
    { name: 'Settings', path: '/settings', icon: <FiSettings /> }
  ];

  const adminItems = [
    { name: 'User Management', path: '/admin/users', icon: <FiUsers /> }
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 z-20 bg-black bg-opacity-50 transition-opacity lg:hidden"
          onClick={toggleSidebar}
        ></div>
      )}

      {/* Sidebar */}
      <div 
        className={`fixed inset-y-0 left-0 z-30 w-64 transform bg-white shadow-lg transition-transform duration-300 lg:translate-x-0 lg:static lg:inset-auto ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <Link to="/" className="flex items-center space-x-2">
            <img src={Logo} alt="ModularMind Logo" className="h-8 w-auto" />
            <span className="text-lg font-semibold text-gray-900">ModularMind</span>
          </Link>
          <button
            className="p-2 rounded-md text-gray-500 hover:text-gray-900 focus:outline-none lg:hidden"
            onClick={toggleSidebar}
          >
            <FiX className="h-6 w-6" />
          </button>
        </div>
        
        <nav className="flex flex-col p-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.name}
              to={item.path}
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-md ${
                isActive(item.path)
                  ? 'bg-blue-50 text-blue-700'
                  : 'text-gray-700 hover:bg-gray-100'
              }`}
              onClick={() => setSidebarOpen(false)}
            >
              <span className="mr-3">{item.icon}</span>
              {item.name}
            </Link>
          ))}
          
          {user?.role === 'admin' && (
            <>
              <div className="pt-4 mt-4 border-t border-gray-200">
                <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Admin
                </p>
              </div>
              
              {adminItems.map((item) => (
                <Link
                  key={item.name}
                  to={item.path}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-md ${
                    isActive(item.path)
                      ? 'bg-blue-50 text-blue-700'
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  onClick={() => setSidebarOpen(false)}
                >
                  <span className="mr-3">{item.icon}</span>
                  {item.name}
                </Link>
              ))}
            </>
          )}
        </nav>
      </div>

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        {/* Top navbar */}
        <div className="flex-shrink-0 border-b bg-white">
          <div className="flex justify-between h-16">
            <div className="flex px-4 lg:px-8">
              <button
                className="text-gray-500 focus:outline-none focus:text-gray-900 lg:hidden"
                onClick={toggleSidebar}
              >
                <FiMenu className="h-6 w-6" />
              </button>
            </div>
            
            <div className="flex items-center px-4 lg:px-8">
              {user && (
                <div className="relative">
                  <button
                    className="flex items-center space-x-2 text-sm focus:outline-none"
                    onClick={toggleUserMenu}
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
                    <span className="font-medium text-gray-700 hidden md:block">
                      {user.name}
                    </span>
                    <FiChevronDown className="h-4 w-4 text-gray-500" />
                  </button>
                  
                  {userMenuOpen && (
                    <div className="absolute right-0 mt-2 w-48 py-2 bg-white rounded-md shadow-lg z-50">
                      <div className="px-4 py-2 border-b">
                        <p className="text-sm font-medium text-gray-700">{user.name}</p>
                        <p className="text-xs text-gray-500 truncate">{user.email}</p>
                      </div>
                      <Link
                        to="/profile"
                        className="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        Your Profile
                      </Link>
                      <button
                        className="flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                        onClick={handleLogout}
                      >
                        <FiLogOut className="mr-2 h-4 w-4" />
                        Sign out
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  );
};

export default AppLayout;