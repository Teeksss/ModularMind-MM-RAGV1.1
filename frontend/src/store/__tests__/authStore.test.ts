import { act, renderHook } from '@testing-library/react-hooks';
import { useAuthStore } from '../authStore';
import { apiService } from '../../services/api';

// Mock apiService
jest.mock('../../services/api', () => ({
  apiService: {
    post: jest.fn(),
    get: jest.fn()
  }
}));

// Mock localStorage
const localStorageMock = (function() {
  let store: Record<string, string> = {};
  return {
    getItem: function(key: string) {
      return store[key] || null;
    },
    setItem: function(key: string, value: string) {
      store[key] = value.toString();
    },
    removeItem: function(key: string) {
      delete store[key];
    },
    clear: function() {
      store = {};
    }
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
});

describe('authStore', () => {
  beforeEach(() => {
    // Clear localStorage and reset store between tests
    window.localStorage.clear();
    act(() => {
      useAuthStore.getState().logout();
    });
    
    // Reset mocks
    jest.clearAllMocks();
  });
  
  test('initial state is not authenticated', () => {
    const { result } = renderHook(() => useAuthStore());
    
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.isInitialized).toBe(false);
  });
  
  test('login should update authentication state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    const testToken = 'test-token';
    const testRefreshToken = 'test-refresh-token';
    const testUser = { id: '123', name: 'Test User', email: 'test@example.com' };
    
    act(() => {
      result.current.login(testToken, testRefreshToken, testUser);
    });
    
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe(testToken);
    expect(result.current.refreshToken).toBe(testRefreshToken);
    expect(result.current.user).toEqual(testUser);
    expect(result.current.isInitialized).toBe(true);
    
    // Check localStorage
    expect(window.localStorage.getItem('auth_token')).toBe(testToken);
    expect(window.localStorage.getItem('refresh_token')).toBe(testRefreshToken);
    expect(window.localStorage.getItem('auth_user')).toBe(JSON.stringify(testUser));
  });
  
  test('logout should clear authentication state', () => {
    const { result } = renderHook(() => useAuthStore());
    
    // Set initial authenticated state
    act(() => {
      result.current.login('test-token', 'test-refresh', { id: '123', name: 'Test User' });
    });
    
    // Then logout
    act(() => {
      result.current.logout();
    });
    
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.isInitialized).toBe(true);
    
    // Check localStorage was cleared
    expect(window.localStorage.getItem('auth_token')).toBeNull();
    expect(window.localStorage.getItem('refresh_token')).toBeNull();
    expect(window.localStorage.getItem('auth_user')).toBeNull();
  });
  
  test('checkAuth should restore authentication from localStorage', () => {
    const { result } = renderHook(() => useAuthStore());
    
    // Setup localStorage with auth data
    const testToken = 'stored-token';
    const testRefreshToken = 'stored-refresh-token';
    const testUser = { id: '456', name: 'Stored User' };
    
    window.localStorage.setItem('auth_token', testToken);
    window.localStorage.setItem('refresh_token', testRefreshToken);
    window.localStorage.setItem('auth_user', JSON.stringify(testUser));
    
    // Call checkAuth
    act(() => {
      result.current.checkAuth();
    });
    
    expect(result.current.isAuthenticated).toBe(true);
    expect(result.current.token).toBe(testToken);
    expect(result.current.refreshToken).toBe(testRefreshToken);
    expect(result.current.user).toEqual(testUser);
    expect(result.current.isInitialized).toBe(true);
  });
  
  test('refreshAccessToken should update the token', async () => {
    const { result } = renderHook(() => useAuthStore());
    
    // Setup initial state with a refresh token
    act(() => {
      result.current.login('old-token', 'test-refresh', { id: '123', name: 'Test User' });
    });
    
    // Mock successful token refresh
    const newToken = 'new-token';
    const newRefreshToken = 'new-refresh';
    (apiService.post as jest.Mock).mockResolvedValueOnce({
      data: {
        access_token: newToken,
        refresh_token: newRefreshToken
      }
    });
    
    // Call refreshAccessToken
    await act(async () => {
      await result.current.refreshAccessToken();
    });
    
    // Verify API was called correctly
    expect(apiService.post).toHaveBeenCalledWith('/auth/refresh-token', {
      refresh_token: 'test-refresh'
    });
    
    // Verify state was updated
    expect(result.current.token).toBe(newToken);
    expect(result.current.refreshToken).toBe(newRefreshToken);
    expect(result.current.isAuthenticated).toBe(true);
    
    // Check localStorage
    expect(window.localStorage.getItem('auth_token')).toBe(newToken);
    expect(window.localStorage.getItem('refresh_token')).toBe(newRefreshToken);
  });
  
  test('refreshAccessToken should handle failure', async () => {
    const { result } = renderHook(() => useAuthStore());
    
    // Setup initial state
    act(() => {
      result.current.login('old-token', 'bad-refresh', { id: '123', name: 'Test User' });
    });
    
    // Mock failed token refresh
    (apiService.post as jest.Mock).mockRejectedValueOnce(new Error('Invalid refresh token'));
    
    // Call refreshAccessToken
    await act(async () => {
      await result.current.refreshAccessToken();
    });
    
    // Should have called logout
    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.user).toBeNull();
    
    // Check localStorage was cleared
    expect(window.localStorage.getItem('auth_token')).toBeNull();
    expect(window.localStorage.getItem('refresh_token')).toBeNull();
  });
});