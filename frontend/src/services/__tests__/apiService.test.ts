import { apiService } from '../api';
import axios from 'axios';
import { useAuthStore } from '../../store/authStore';
import { useNotificationStore } from '../../store/notificationStore';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

// Mock the stores
jest.mock('../../store/authStore');
jest.mock('../../store/notificationStore');

describe('API Service', () => {
  beforeEach(() => {
    // Reset all mocks
    jest.resetAllMocks();
    
    // Default store mocks
    (useAuthStore as jest.Mock).mockReturnValue({
      token: 'test-token',
      logout: jest.fn()
    });
    
    (useNotificationStore as jest.Mock).mockReturnValue({
      addNotification: jest.fn()
    });
    
    // Default axios mock
    mockedAxios.create.mockReturnValue({
      get: jest.fn().mockResolvedValue({ data: {} }),
      post: jest.fn().mockResolvedValue({ data: {} }),
      put: jest.fn().mockResolvedValue({ data: {} }),
      patch: jest.fn().mockResolvedValue({ data: {} }),
      delete: jest.fn().mockResolvedValue({ data: {} }),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() }
      }
    } as any);
  });

  it('should make a GET request correctly', async () => {
    const mockResponse = { data: { test: 'data' } };
    mockedAxios.create().get.mockResolvedValueOnce(mockResponse);
    
    const result = await apiService.get('/test');
    
    expect(mockedAxios.create().get).toHaveBeenCalledWith('/test', undefined);
    expect(result).toEqual(mockResponse);
  });

  it('should make a POST request correctly', async () => {
    const mockResponse = { data: { id: 1 } };
    const postData = { name: 'Test' };
    mockedAxios.create().post.mockResolvedValueOnce(mockResponse);
    
    const result = await apiService.post('/test', postData);
    
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/test', postData, undefined);
    expect(result).toEqual(mockResponse);
  });

  it('should handle errors correctly', async () => {
    const errorResponse = {
      response: {
        status: 400,
        data: { message: 'Bad request' }
      }
    };
    
    mockedAxios.create().get.mockRejectedValueOnce(errorResponse);
    const addNotificationMock = jest.fn();
    (useNotificationStore as jest.Mock).mockReturnValue({
      addNotification: addNotificationMock
    });
    
    try {
      await apiService.get('/test');
    } catch (error) {
      expect(error).toEqual(errorResponse);
      expect(addNotificationMock).toHaveBeenCalled();
    }
  });

  it('should handle 401 errors and logout the user', async () => {
    const errorResponse = {
      response: {
        status: 401,
        data: { message: 'Unauthorized' }
      }
    };
    
    mockedAxios.create().get.mockRejectedValueOnce(errorResponse);
    const logoutMock = jest.fn();
    (useAuthStore as jest.Mock).mockReturnValue({
      token: 'test-token',
      isAuthenticated: true,
      logout: logoutMock
    });
    
    try {
      await apiService.get('/test');
    } catch (error) {
      expect(error).toEqual(errorResponse);
      expect(logoutMock).toHaveBeenCalled();
    }
  });

  it('should add authorization header with token', () => {
    let requestConfig;
    
    // Mock the interceptor
    mockedAxios.create().interceptors.request.use.mockImplementation((fn) => {
      requestConfig = fn({ headers: {} });
    });
    
    // Re-initialize to trigger interceptors
    const apiInstance = mockedAxios.create();
    apiInstance.interceptors.request.use.mock.calls[0][0]({ headers: {} });
    
    expect(requestConfig).toHaveProperty('headers.Authorization', 'Bearer test-token');
  });

  it('should handle file upload correctly', async () => {
    const mockResponse = { data: { id: 1 } };
    mockedAxios.create().post.mockResolvedValueOnce(mockResponse);
    
    const formData = new FormData();
    formData.append('file', new File(['test'], 'test.txt'));
    
    const result = await apiService.upload('/upload', formData);
    
    expect(mockedAxios.create().post).toHaveBeenCalledWith('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    expect(result).toEqual(mockResponse);
  });
});