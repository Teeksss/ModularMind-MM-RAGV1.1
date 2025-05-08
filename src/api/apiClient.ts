import axios, { AxiosInstance, AxiosRequestConfig, AxiosError, AxiosResponse } from 'axios';
import { store } from '../store/store';
import { logout } from '../store/slices/authSlice';

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';
const API_TIMEOUT = 30000;

// Create axios instance
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    // Get token from localStorage
    const token = localStorage.getItem('authToken');
    
    // Add token to request headers if available
    if (token && config.headers) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    return config;
  },
  (error) => {
    // Handle request errors
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    // Process successful responses
    return response;
  },
  (error: AxiosError) => {
    // Handle response errors
    if (error.response) {
      // Handle 401 Unauthorized
      if (error.response.status === 401) {
        // Check if we're not already on the login page to prevent infinite loop
        if (window.location.pathname !== '/login') {
          console.warn('Unauthorized request, logging out...');
          store.dispatch(logout());
        }
      }
      
      // Log detailed error information in development
      if (import.meta.env.DEV) {
        console.error('API Response Error:', {
          status: error.response.status,
          data: error.response.data,
          config: error.config,
        });
      }
    } else if (error.request) {
      // Request was made but no response received
      console.error('API No Response Error:', error.request);
    } else {
      // Error during request setup
      console.error('API Setup Error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

// API client interface
export const apiClient = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.get<T>(url, config);
  },
  
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.post<T>(url, data, config);
  },
  
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.put<T>(url, data, config);
  },
  
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.patch<T>(url, data, config);
  },
  
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse<T>> => {
    return axiosInstance.delete<T>(url, config);
  },
  
  // Helper methods for auth token management
  setAuthToken: (token: string): void => {
    axiosInstance.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  },
  
  clearAuthToken: (): void => {
    delete axiosInstance.defaults.headers.common['Authorization'];
  },
};