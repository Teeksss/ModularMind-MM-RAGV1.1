import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User } from '../types/user';
import { apiClient } from '../api/apiClient';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  
  // Actions
  login: (email: string, password: string) => Promise<boolean>;
  register: (data: { name: string; email: string; password: string; organization?: string }) => Promise<boolean>;
  logout: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<boolean>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: localStorage.getItem('authToken'),
      isAuthenticated: !!localStorage.getItem('authToken'),
      loading: false,
      error: null,
      
      login: async (email, password) => {
        try {
          set({ loading: true, error: null });
          
          const response = await apiClient.post('/api/auth/login', { email, password });
          
          if (response.data.token && response.data.user) {
            // Store token
            localStorage.setItem('authToken', response.data.token);
            apiClient.setAuthToken(response.data.token);
            
            set({ 
              user: response.data.user,
              token: response.data.token,
              isAuthenticated: true,
              loading: false 
            });
            
            return true;
          }
          
          set({ loading: false, error: 'Invalid response from server' });
          return false;
        } catch (error: any) {
          const errorMessage = error.response?.data?.error?.message || 'Login failed';
          set({ loading: false, error: errorMessage });
          return false;
        }
      },
      
      register: async (data) => {
        try {
          set({ loading: true, error: null });
          
          const response = await apiClient.post('/api/auth/register', data);
          
          if (response.data.token && response.data.user) {
            // Store token
            localStorage.setItem('authToken', response.data.token);
            apiClient.setAuthToken(response.data.token);
            
            set({ 
              user: response.data.user,
              token: response.data.token,
              isAuthenticated: true,
              loading: false 
            });
            
            return true;
          }
          
          set({ loading: false, error: 'Invalid response from server' });
          return false;
        } catch (error: any) {
          const errorMessage = error.response?.data?.error?.message || 'Registration failed';
          set({ loading: false, error: errorMessage });
          return false;
        }
      },
      
      logout: async () => {
        try {
          set({ loading: true });
          
          // Call logout endpoint (even if it fails, we'll log out locally)
          await apiClient.post('/api/auth/logout');
        } catch (error) {
          console.error('Logout API call failed:', error);
        } finally {
          // Clear local state
          localStorage.removeItem('authToken');
          apiClient.clearAuthToken();
          
          set({ 
            user: null, 
            token: null, 
            isAuthenticated: false, 
            loading: false, 
            error: null 
          });
        }
      },
      
      updateProfile: async (data) => {
        try {
          set({ loading: true, error: null });
          
          const response = await apiClient.put('/api/auth/profile', data);
          
          if (response.data.user) {
            set({ 
              user: response.data.user,
              loading: false 
            });
            
            return true;
          }
          
          set({ loading: false, error: 'Invalid response from server' });
          return false;
        } catch (error: any) {
          const errorMessage = error.response?.data?.error?.message || 'Profile update failed';
          set({ loading: false, error: errorMessage });
          return false;
        }
      },
      
      clearError: () => set({ error: null })
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ token: state.token })
    }
  )
);