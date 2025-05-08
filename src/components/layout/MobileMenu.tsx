import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiX, FiMenu, FiHome, FiSearch, FiUpload, FiSettings, FiUsers, FiBarChart2 } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
}

const MobileMenu: React.FC<MobileMenuProps> = ({ isOpen, onClose }) => {
  const location = useLocation();
  const { user } = useAuth();
  
  const isActive = (path: string): boolean => {
    return location.pathname.startsWith(path);
  };
  
  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: <FiHome /> },
    { name: 'Search', path: '/search', icon: <FiSearch /> },
    { name: 'Upload', path: '/upload', icon: <FiUpload /> },
    { name: 'Analytics', path: '/analytics', icon: <FiBarChart2 /> },
    { name: 'Settings', path: '/settings', icon: <FiSettings /> }
  ];
  
  const adminItems = [
    { name: 'User Management', path: '/admin/users', icon: <FiUsers /> }
  ];
  
  if (!isOpen) return null;
  
  return (
    <div className="fixed inset-0 z-50 bg-gray-900 bg-opacity-50 overflow-y-auto h-full w-full" onClick={onClose}>
      <div 
        className="fixed right-0 top-0 w-5/6 max-w-sm h-full bg-white shadow-xl overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-medium text-gray-800">Menu</h2>
          <button 
            className="p-2 rounded-md text-gray-500 hover:text-gray-700 focus:outline-none"
            onClick={onClose}
          >
            <FiX className="h-6 w-6" />
          </button>
        </div>
        
        <nav className="px-4 py-6">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.name}>
                <Link
                  to={item.path}
                  className={`flex items-center px-4 py-3 text-sm font-medium rounded-md ${
                    isActive(item.path) 
                      ? 'bg-blue-50 text-blue-700' 
                      : 'text-gray-700 hover:bg-gray-100'
                  }`}
                  onClick={onClose}
                >
                  <span className="mr-3">{item.icon}</span>
                  {item.name}
                </Link>
              </li>
            ))}
          </ul>
          
          {user?.role === 'admin' && (
            <>
              <div className="pt-6 mt-6 border-t border-gray-200">
                <p className="px-4 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Admin
                </p>
              </div>
              
              <ul className="mt-2 space-y-2">
                {adminItems.map((item) => (
                  <li key={item.name}>
                    <Link
                      to={item.path}
                      className={`flex items-center px-4 py-3 text-sm font-medium rounded-md ${
                        isActive(item.path) 
                          ? 'bg-blue-50 text-blue-700' 
                          : 'text-gray-700 hover:bg-gray-100'
                      }`}
                      onClick={onClose}
                    >
                      <span className="mr-3">{item.icon}</span>
                      {item.name}
                    </Link>
                  </li>
                ))}
              </ul>
            </>
          )}
        </nav>
        
        <div className="p-4 border-t border-gray-200 mt-auto">
          <Link
            to="/profile"
            className="flex items-center p-3 text-sm font-medium text-gray-700 rounded-md hover:bg-gray-100"
            onClick={onClose}
          >
            <div className="mr-3 flex-shrink-0">
              {user?.avatarUrl ? (
                <img src={user.avatarUrl} alt={user.name} className="h-8 w-8 rounded-full" />
              ) : (
                <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white">
                  {user?.name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
            <div>
              <p className="font-medium">{user?.name}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default MobileMenu;