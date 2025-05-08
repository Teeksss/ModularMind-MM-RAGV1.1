import React, { createContext, useState, useEffect, useContext, ReactNode } from 'react';
import { apiClient } from '../api/apiClient';

// User type definition
export type User = {
  id: string;
  name: string;
  email: string;
  role: 'admin' | 'user' | 'editor';
  status: 'active' | 'inactive';
  organization?: string;
  avatarUrl?: string;
  createdAt: string;
  updatedAt: string;
};

// Auth context type
type AuthContextType = {
  user: User | null;
  loading: boolean;
  error: Error | null;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  register: (userData: RegisterData) => Promise<boolean>;
  updateProfile: (profileData: Partial<User>) => Promise<boolean>;
  isAuthenticated: boolean;
};

// Register data type
type RegisterData = {
  name: string;
  email: string;
  password: string;
  organization?: string;
};

// Create context with default values
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Provider props type
type AuthProviderProps = {
  children: ReactNode;
};

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

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
          const response = await apiClient.get<{ user: User }>('/api/auth/me');
          
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
        setError(err instanceof Error ? err : new Error('An unknown error occurred'));
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
  const login = async (email: string, password: string): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.post<{ token: string; user: User }>('/api/auth/login', {
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
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError(new Error(errorMessage));
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Logout function
  const logout = async (): Promise<void> => {
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
  const register = async (userData: RegisterData): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.post<{ token: string; user: User }>('/api/auth/register', userData);
      
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
      const errorMessage = err instanceof Error ? err.message : 'Registration failed';
      setError(new Error(errorMessage));
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Update user profile
  const updateProfile = async (profileData: Partial<User>): Promise<boolean> => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await apiClient.put<{ user: User }>('/api/auth/profile', profileData);
      
      if (response.data && response.data.user) {
        // Update user data
        setUser(response.data.user);
        return true;
      } else {
        throw new Error('Invalid response from server');
      }
    } catch (err) {
      console.error('Profile update failed:', err);
      const errorMessage = err instanceof Error ? err.message : 'Profile update failed';
      setError(new Error(errorMessage));
      return false;
    } finally {
      setLoading(false);
    }
  };

  // Context value
  const value: AuthContextType = {
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
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};