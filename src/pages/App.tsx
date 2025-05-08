import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import ResponsiveNavigation from '../components/layout/ResponsiveNavigation';
import ProtectedRoute from '../components/auth/ProtectedRoute';
import AdminRoute from '../components/auth/AdminRoute';

// Pages
import Login from './auth/Login';
import Register from './auth/Register';
import Dashboard from './Dashboard';
import SearchPage from './search/SearchPage';
import ImageSearchPage from './search/ImageSearchPage';
import AudioSearchPage from './search/AudioSearchPage';
import UploadPage from './upload/UploadPage';
import AnalyticsDashboard from './analytics/Dashboard';
import UserManagement from './admin/UserManagement';
import SettingsPage from './settings/SettingsPage';
import ProfilePage from './profile/ProfilePage';
import NotFoundPage from './NotFoundPage';

const App: React.FC = () => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {isAuthenticated && <ResponsiveNavigation />}
      
      <main className="flex-1">
        <Routes>
          {/* Auth routes accessible only when not authenticated */}
          <Route
            path="/login"
            element={isAuthenticated ? <Navigate to="/dashboard" /> : <Login />}
          />
          <Route
            path="/register"
            element={isAuthenticated ? <Navigate to="/dashboard" /> : <Register />}
          />
          
          {/* Protected routes requiring authentication */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/search/image" element={<ImageSearchPage />} />
            <Route path="/search/audio" element={<AudioSearchPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/analytics" element={<AnalyticsDashboard />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            
            {/* Admin routes */}
            <Route element={<AdminRoute />}>
              <Route path="/admin/users" element={<UserManagement />} />
            </Route>
          </Route>
          
          {/* Default route redirect */}
          <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
          
          {/* 404 page */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      
      {isAuthenticated && (
        <footer className="bg-white border-t border-gray-200 py-4">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <p className="text-center text-sm text-gray-500">
              &copy; {new Date().getFullYear()} ModularMind RAG Platform. All rights reserved.
            </p>
          </div>
        </footer>
      )}
    </div>
  );
};

export default App;