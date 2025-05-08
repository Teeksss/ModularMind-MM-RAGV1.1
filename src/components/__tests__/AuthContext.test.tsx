import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';
import { apiClient } from '../../api/apiClient';

// Mock the apiClient
jest.mock('../../api/apiClient');

describe('AuthContext', () => {
  const mockLocalStorage = (function() {
    let store: Record<string, string> = {};
  
    return {
      getItem: jest.fn(key => store[key] || null),
      setItem: jest.fn((key, value) => {
        store[key] = value.toString();
      }),
      removeItem: jest.fn(key => {
        delete store[key];
      }),
      clear: jest.fn(() => {
        store = {};
      })
    };
  })();
  
  // Setup localStorage mock
  Object.defineProperty(window, 'localStorage', {
    value: mockLocalStorage
  });
  
  beforeEach(() => {
    jest.clearAllMocks();
    window.localStorage.clear();
  });
  
  it('should initialize with correct default state', async () => {
    // No token in localStorage
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    // Should start in loading state
    expect(result.current.loading).toBe(true);
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.error).toBeNull();
    
    await waitForNextUpdate();
    
    // Should end loading with no user
    expect(result.current.loading).toBe(false);
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });
  
  it('should initialize and load user with valid token', async () => {
    // Mock token and user data
    const mockToken = 'valid-token';
    const mockUser = {
      id: 'user123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      status: 'active',
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z'
    };
    
    // Set token in localStorage
    window.localStorage.setItem('authToken', mockToken);
    
    // Mock API response
    (apiClient.setAuthToken as jest.Mock).mockImplementation(() => {});
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: { user: mockUser }
    });
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    // Should start in loading state
    expect(result.current.loading).toBe(true);
    
    await waitForNextUpdate();
    
    // Should end loading with user data
    expect(result.current.loading).toBe(false);
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    
    // API calls should have happened
    expect(apiClient.setAuthToken).toHaveBeenCalledWith(mockToken);
    expect(apiClient.get).toHaveBeenCalledWith('/api/auth/me');
  });
  
  it('should handle login success', async () => {
    // Mock credentials
    const email = 'test@example.com';
    const password = 'password123';
    
    // Mock successful login response
    const mockToken = 'new-token';
    const mockUser = {
      id: 'user123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      status: 'active',
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z'
    };
    
    (apiClient.post as jest.Mock).mockResolvedValue({
      data: { token: mockToken, user: mockUser }
    });
    (apiClient.setAuthToken as jest.Mock).mockImplementation(() => {});
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    await waitForNextUpdate();
    
    // Perform login
    let loginSuccess: boolean = false;
    
    await act(async () => {
      loginSuccess = await result.current.login(email, password);
    });
    
    // Should return success
    expect(loginSuccess).toBe(true);
    
    // Should update context state
    expect(result.current.user).toEqual(mockUser);
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.error).toBeNull();
    
    // Should store token in localStorage
    expect(window.localStorage.setItem).toHaveBeenCalledWith('authToken', mockToken);
    
    // API calls should have happened
    expect(apiClient.post).toHaveBeenCalledWith('/api/auth/login', {
      email,
      password
    });
    expect(apiClient.setAuthToken).toHaveBeenCalledWith(mockToken);
  });
  
  it('should handle login failure', async () => {
    // Mock credentials
    const email = 'test@example.com';
    const password = 'wrong-password';
    
    // Mock failed login response
    const mockError = new Error('Invalid credentials');
    (apiClient.post as jest.Mock).mockRejectedValue(mockError);
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    await waitForNextUpdate();
    
    // Perform login
    let loginSuccess: boolean = false;
    
    await act(async () => {
      loginSuccess = await result.current.login(email, password);
    });
    
    // Should return failure
    expect(loginSuccess).toBe(false);
    
    // Should update context error state
    expect(result.current.error).toBeTruthy();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
    
    // Token should NOT be stored in localStorage
    expect(window.localStorage.setItem).not.toHaveBeenCalledWith('authToken', expect.any(String));
  });
  
  it('should handle logout', async () => {
    // Setup a logged in state first
    const mockUser = {
      id: 'user123',
      name: 'Test User',
      email: 'test@example.com',
      role: 'user',
      status: 'active',
      createdAt: '2025-01-01T00:00:00Z',
      updatedAt: '2025-01-01T00:00:00Z'
    };
    
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: { user: mockUser }
    });
    
    window.localStorage.setItem('authToken', 'existing-token');
    
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <AuthProvider>{children}</AuthProvider>
    );
    
    const { result, waitForNextUpdate } = renderHook(() => useAuth(), { wrapper });
    
    await waitForNextUpdate();
    
    // Should be in authenticated state
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.user).toEqual(mockUser);
    
    // Mock successful logout
    (apiClient.post as jest.Mock).mockResolvedValue({});
    (apiClient.clearAuthToken as jest.Mock).mockImplementation(() => {});
    
    // Perform logout
    await act(async () => {
      await result.current.logout();
    });
    
    // Should be logged out
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.user).toBeNull();
    
    // Should remove token from localStorage
    expect(window.localStorage.removeItem).toHaveBeenCalledWith('authToken');
    
    // API calls should have happened
    expect(apiClient.post).toHaveBeenCalledWith('/api/auth/logout');
    expect(apiClient.clearAuthToken).toHaveBeenCalled();
  });
});