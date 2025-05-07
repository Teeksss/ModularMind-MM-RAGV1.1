import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';

import { useAuthStore } from '../../store/authStore';
import { useSessionStore } from '../../store/sessionStore';
import Sidebar from '../layout/Sidebar';
import Header from '../layout/Header';
import Footer from '../layout/Footer';
import LoadingScreen from '../common/LoadingScreen';

const Dashboard: React.FC = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoggedIn, user, token, refreshToken } = useAuthStore();
  const { initializeSession } = useSessionStore();
  
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  
  // Check authentication status
  useEffect(() => {
    const checkAuth = async () => {
      if (!isLoggedIn || !token) {
        // Redirect to login if not authenticated
        navigate('/login', { state: { from: location.pathname }});
        return;
      }
      
      setIsLoading(false);
      
      // Initialize user session
      initializeSession();
    };
    
    checkAuth();
  }, [isLoggedIn, token, navigate, location.pathname, initializeSession]);
  
  // Toggle sidebar
  const toggleSidebar = () => {
    setIsSidebarOpen(prev => !prev);
  };
  
  // Show loading screen until auth check is complete
  if (isLoading) {
    return <LoadingScreen />;
  }
  
  return (
    <div className="flex flex-col min-h-screen bg-gray-50 dark:bg-gray-900">
      <Header 
        toggleSidebar={toggleSidebar} 
        isSidebarOpen={isSidebarOpen} 
      />
      
      <div className="flex flex-1 pt-16">
        <Sidebar 
          isOpen={isSidebarOpen} 
          onClose={() => setIsSidebarOpen(false)} 
        />
        
        <main className={`flex-1 transition-all duration-300 ${
          isSidebarOpen ? 'md:ml-64' : ''
        }`}>
          <div className="container mx-auto px-4 py-6">
            {/* Page content */}
            <Outlet />
          </div>
        </main>
      </div>
      
      <Footer />
    </div>
  );
};

export default Dashboard;