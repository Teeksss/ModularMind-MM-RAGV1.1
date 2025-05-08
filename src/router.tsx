import { createBrowserRouter, Navigate } from 'react-router-dom';
import App from './App';
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import Dashboard from './pages/Dashboard';
import SearchPage from './pages/search/SearchPage';
import ImageSearchPage from './pages/search/ImageSearchPage';
import AudioSearchPage from './pages/search/AudioSearchPage';
import UploadPage from './pages/upload/UploadPage';
import AnalyticsDashboard from './pages/analytics/Dashboard';
import UserManagement from './pages/admin/UserManagement';
import SettingsPage from './pages/settings/SettingsPage';
import ProfilePage from './pages/profile/ProfilePage';
import NotFoundPage from './pages/NotFoundPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import AdminRoute from './components/auth/AdminRoute';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />
      },
      {
        path: 'login',
        element: <LoginPage />
      },
      {
        path: 'register',
        element: <RegisterPage />
      },
      {
        path: 'dashboard',
        element: <ProtectedRoute element={<Dashboard />} />
      },
      {
        path: 'search',
        element: <ProtectedRoute element={<SearchPage />} />
      },
      {
        path: 'search/image',
        element: <ProtectedRoute element={<ImageSearchPage />} />
      },
      {
        path: 'search/audio',
        element: <ProtectedRoute element={<AudioSearchPage />} />
      },
      {
        path: 'upload',
        element: <ProtectedRoute element={<UploadPage />} />
      },
      {
        path: 'analytics',
        element: <ProtectedRoute element={<AnalyticsDashboard />} />
      },
      {
        path: 'settings',
        element: <ProtectedRoute element={<SettingsPage />} />
      },
      {
        path: 'profile',
        element: <ProtectedRoute element={<ProfilePage />} />
      },
      {
        path: 'admin/users',
        element: <AdminRoute element={<UserManagement />} />
      },
      {
        path: '*',
        element: <NotFoundPage />
      }
    ]
  }
]);