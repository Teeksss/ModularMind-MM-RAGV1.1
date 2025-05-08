import React, { createContext, useState, useEffect, useContext } from 'react';
import { apiClient } from '../services/apiClient';

// Create context
const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Initialize - check if user is already logged in
  useEffect(() => {
    const checkAuthStatus = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Get token from local storage
        const token = localStorage.getItem('authToken');
        
        if (token) {
          // Set token in API client
          apiClient.setAuthToken(token);
          
          // Fetch current user
          const response = await apiClient.get('/api/auth/me');
          
          if (response.data && response.data.user) {
            setUser(response.data.user);
          } else {
            // Invalid token or user
            localStorage.removeItem('authToken');
            apiClient.clearAuthToken();
          }
        }
      } catch (err) {
        console.error('Auth status check failed:', err);
        setError(err);
        // Clear invalid token
        localStorage.removeItem('authToken');
        apiClient.clearAuthToken();
      } finally {
        setLoading(false);
      }
    };
    
    checkAuthStatus();
  }, []);

  // Login function
  const login = async (email, password) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.post('/api/auth/login', {
        email,
        password
      });
      
      if (response.data && response.data.token) {
        // Save token
        localStorage.setItem('authToken', response.data.token);
        apiClient.setAuthToken(response.data.token);
        
        // Set user data
        setUser(response.data.user);
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('Login failed:', err);
      setError(err.response?.data?.message || 'Login failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async () => {
    try {
      // Call logout endpoint
      await apiClient.post('/api/auth/logout');
    } catch (err) {
      console.error('Logout API call failed:', err);
    } finally {
      // Clear local data regardless of API success
      localStorage.removeItem('authToken');
      apiClient.clearAuthToken();
      setUser(null);
    }
  };

  // Register function
  const register = async (userData) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.post('/api/auth/register', userData);
      
      if (response.data && response.data.token) {
        // Save token
        localStorage.setItem('authToken', response.data.token);
        apiClient.setAuthToken(response.data.token);
        
        // Set user data
        setUser(response.data.user);
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('Registration failed:', err);
      setError(err.response?.data?.message || 'Registration failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Update user profile
  const updateProfile = async (profileData) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.put('/api/auth/profile', profileData);
      
      if (response.data && response.data.user) {
        // Update user data
        setUser(response.data.user);
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('Profile update failed:', err);
      setError(err.response?.data?.message || 'Profile update failed');
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Context value
  const value = {
    user,
    loading,
    error,
    login,
    logout,
    register,
    updateProfile,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

// Custom hook to use auth context
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};