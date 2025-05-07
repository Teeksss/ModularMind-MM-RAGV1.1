import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { api } from '../services/api';
import { User, AuthState, LoginRequest, RegisterRequest } from '../types';
import { showToast } from '../utils/notifications';
import { config } from '../config/config';

// Define the auth store state and actions
interface AuthStore extends AuthState {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<boolean>;
  updateUser: (user: User) => void;
  clearError: () => void;
}

// Create and export the auth store
export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isLoggedIn: false,
      isLoading: false,
      error: null,
      
      login: async (data: LoginRequest) => {
        try {
          set({ isLoading: true, error: null });
          
          const response = await api.post('/auth/login', data);
          
          const { access_token, refresh_token, user } = response.data;
          
          set({
            token: access_token,
            refreshToken: refresh_token,
            user,
            isLoggedIn: true,
            isLoading: false
          });
          
          // Store token in localStorage for API client
          localStorage.setItem(config.auth.tokenStorageKey, access_token);
          localStorage.setItem(config.auth.refreshTokenStorageKey, refresh_token);
          
          showToast('success', 'Başarıyla giriş yapıldı');
        } catch (error) {
          const errorMessage = error.message || 'Giriş yapılamadı';
          set({ error: errorMessage, isLoading: false });
          showToast('error', errorMessage);
          throw error;
        }
      },
      
      register: async (data: RegisterRequest) => {
        try {
          set({ isLoading: true, error: null });
          
          await api.post('/auth/register', data);
          
          set({ isLoading: false });
          
          showToast('success', 'Kayıt başarılı, lütfen giriş yapın');
        } catch (error) {
          const errorMessage = error.message || 'Kayıt işlemi başarısız';
          set({ error: errorMessage, isLoading: false });
          showToast('error', errorMessage);
          throw error;
        }
      },
      
      logout: () => {
        // Clear tokens from localStorage
        localStorage.removeItem(config.auth.tokenStorageKey);
        localStorage.removeItem(config.auth.refreshTokenStorageKey);
        
        // Reset state
        set({
          token: null,
          refreshToken: null,
          user: null,
          isLoggedIn: false,
          error: null
        });
        
        showToast('info', 'Çıkış yapıldı');
      },
      
      refreshToken: async () => {
        const currentRefreshToken = get().refreshToken;
        
        if (!currentRefreshToken) {
          return false;
        }
        
        try {
          set({ isLoading: true });
          
          const response = await api.post('/auth/refresh', {
            refresh_token: currentRefreshToken
          });
          
          const { access_token, refresh_token } = response.data;
          
          set({
            token: access_token,
            refreshToken: refresh_token,
            isLoading: false
          });
          
          // Store tokens
          localStorage.setItem(config.auth.tokenStorageKey, access_token);
          localStorage.setItem(config.auth.refreshTokenStorageKey, refresh_token);
          
          return true;
        } catch (error) {
          console.error('Token refresh failed:', error);
          set({ isLoading: false });
          return false;
        }
      },
      
      updateUser: (user: User) => {
        set({ user });
      },
      
      clearError: () => {
        set({ error: null });
      }
    }),
    {
      name: 'modularmind-auth-storage',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        isLoggedIn: state.isLoggedIn,
      }),
    }
  )
);