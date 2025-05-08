import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './contexts/AuthContext';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AdminRoute from './components/auth/AdminRoute';

// Pages
import Login from './pages/auth/Login';
import Register from './pages/auth/Register';
import Dashboard from './pages/Dashboard';
import SearchPage from './pages/search/SearchPage';
import UploadPage from './pages/upload/UploadPage';
import UserManagement from './pages/admin/UserManagement';
import SettingsPage from './pages/settings/SettingsPage';
import ProfilePage from './pages/profile/ProfilePage';
import ImageSearchPage from './pages/search/ImageSearchPage';
import AudioSearchPage from './pages/search/AudioSearchPage';
import NotFoundPage from './pages/NotFoundPage';

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
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/search/image" element={<ImageSearchPage />} />
          <Route path="/search/audio" element={<AudioSearchPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          
          {/* Admin routes */}
          <Route element={<AdminRoute />}>
            <Route path="/admin/users" element={<UserManagement />} />
          </Route>
        </Route>
      </Route>
      
      {/* Default route redirect */}
      <Route path="/" element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} />
      
      {/* 404 page */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
};

export default App;