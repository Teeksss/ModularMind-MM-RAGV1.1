import axios, { AxiosRequestConfig, AxiosResponse, AxiosError, AxiosInstance } from 'axios';
import { useAuthStore } from '../store/authStore';
import { useNotificationStore } from '../store/notificationStore';
import i18n from '../i18n';

// Token refresh configuration
const RETRY_COUNT = 3;
const RETRY_DELAY = 1000; // ms
const TOKEN_REFRESH_THRESHOLD = 5 * 60 * 1000; // 5 minutes in ms

// Default timeout setting
const DEFAULT_TIMEOUT = 30000; // 30 seconds

/**
 * API service configuration
 */
class ApiService {
  private axiosInstance: AxiosInstance;
  private refreshPromise: Promise<string> | null = null;
  private tokenExpirationTime: number | null = null;
  private pendingRequests: {config: AxiosRequestConfig, resolve: Function, reject: Function}[] = [];
  private isRefreshing = false;

  constructor() {
    // Create axios instance with default config
    this.axiosInstance = axios.create({
      baseURL: '/api/v1',
      timeout: DEFAULT_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Set up request interceptor
    this.axiosInstance.interceptors.request.use(
      this.handleRequest.bind(this),
      this.handleRequestError.bind(this)
    );

    // Set up response interceptor
    this.axiosInstance.interceptors.response.use(
      this.handleResponse.bind(this),
      this.handleResponseError.bind(this)
    );
  }

  /**
   * Handle the request
   */
  private async handleRequest(config: AxiosRequestConfig): Promise<AxiosRequestConfig> {
    const store = useAuthStore.getState();
    const token = store.token;
    
    if (token) {
      // Check if token needs to be refreshed
      if (this.shouldRefreshToken()) {
        try {
          // Refresh token and update config
          const newToken = await this.refreshToken();
          config.headers = config.headers || {};
          config.headers.Authorization = `Bearer ${newToken}`;
        } catch (error) {
          console.error('Failed to refresh token:', error);
          // Continue with the original token if refresh fails
          config.headers = config.headers || {};
          config.headers.Authorization = `Bearer ${token}`;
        }
      } else {
        // Use the current token
        config.headers = config.headers || {};
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    return config;
  }

  /**
   * Handle request error
   */
  private handleRequestError(error: AxiosError): Promise<AxiosError> {
    console.error('Request error:', error);
    
    const notificationStore = useNotificationStore.getState();
    notificationStore.addNotification({
      type: 'error',
      title: i18n.t('errors.requestError'),
      message: i18n.t('errors.couldNotSendRequest')
    });
    
    return Promise.reject(error);
  }

  /**
   * Handle the response
   */
  private handleResponse(response: AxiosResponse): AxiosResponse {
    // You can add additional global response handling here if needed
    return response;
  }

  /**
   * Handle response error
   */
  private async handleResponseError(error: AxiosError): Promise<AxiosResponse | Promise<AxiosError>> {
    // Get notification store
    const notificationStore = useNotificationStore.getState();
    
    // Check if request can be retried
    if (this.canRetry(error) && error.config) {
      return this.retryRequest(error.config);
    }
    
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      
      // Check for 401 errors (Unauthorized)
      if (error.response.status === 401) {
        const authStore = useAuthStore.getState();
        
        // Only logout if not already on login page
        if (authStore.isAuthenticated) {
          authStore.logout();
          
          // Show notification
          notificationStore.addNotification({
            type: 'error',
            title: i18n.t('auth.unauthorized'),
            message: i18n.t('auth.sessionExpired')
          });
        }
      }
      
      // Check for backend translated messages
      if (error.response.data?.message) {
        // Check if message is a translation key
        const message = error.response.data.message;
        const translatedMessage = message.startsWith('errors.') 
          ? i18n.t(message) 
          : message;
        
        // Add translated message to error
        (error as any).translatedMessage = translatedMessage;
        
        // Show notification for errors (except 401 which we handle separately)
        if (error.response.status !== 401) {
          notificationStore.addNotification({
            type: 'error',
            title: i18n.t('common.error'),
            message: translatedMessage
          });
        }
      }
    } else if (error.request) {
      // The request was made but no response was received
      notificationStore.addNotification({
        type: 'error',
        title: i18n.t('errors.connectionError'),
        message: i18n.t('errors.noResponse')
      });
    } else {
      // Something happened in setting up the request that triggered an Error
      notificationStore.addNotification({
        type: 'error',
        title: i18n.t('errors.requestError'),
        message: error.message
      });
    }
    
    return Promise.reject(error);
  }

  /**
   * Check if a token refresh is needed
   */
  private shouldRefreshToken(): boolean {
    const store = useAuthStore.getState();
    if (!store.token || !this.tokenExpirationTime) return false;
    
    const now = Date.now();
    return (this.tokenExpirationTime - now) < TOKEN_REFRESH_THRESHOLD;
  }

  /**
   * Refresh the authentication token
   */
  private async refreshToken(): Promise<string> {
    const store = useAuthStore.getState();
    
    // If already refreshing, wait for that to complete
    if (this.isRefreshing) {
      return this.refreshPromise!;
    }
    
    // Start the refresh process
    this.isRefreshing = true;
    
    // Create a promise that will be resolved when token is refreshed
    this.refreshPromise = new Promise<string>(async (resolve, reject) => {
      try {
        // Call token refresh API
        const response = await this.axiosInstance.post('/auth/refresh', {}, {
          headers: {
            Authorization: `Bearer ${store.token}`
          }
        });
        
        // Update token in store
        const newToken = response.data.access_token;
        store.setToken(newToken);
        
        // Parse expiration date from token (assuming JWT)
        try {
          const payload = JSON.parse(atob(newToken.split('.')[1]));
          if (payload.exp) {
            this.tokenExpirationTime = payload.exp * 1000; // Convert to milliseconds
          }
        } catch (error) {
          console.warn('Failed to parse token expiration:', error);
        }
        
        // Process pending requests
        this.resolvePendingRequests(newToken);
        
        // Resolve the refresh promise
        resolve(newToken);
      } catch (error) {
        // Reject pending requests
        this.rejectPendingRequests(error);
        
        // Reject the refresh promise
        reject(error);
        
        // Handle critical error (like invalid refresh token)
        if (error.response?.status === 401) {
          store.logout();
        }
      } finally {
        // Reset refresh state
        this.isRefreshing = false;
        this.refreshPromise = null;
      }
    });
    
    return this.refreshPromise;
  }

  /**
   * Check if a request can be retried based on the error
   */
  private canRetry(error: AxiosError): boolean {
    // Don't retry if retry count is exceeded or no config is available
    if (!error.config || (error.config as any).__retryCount >= RETRY_COUNT) {
      return false;
    }
    
    // Don't retry for client errors (4xx) except for 429 (rate limit) and network errors
    if (error.response && error.response.status >= 400 && error.response.status < 500 && error.response.status !== 429) {
      return false;
    }
    
    return true;
  }

  /**
   * Retry a request
   */
  private async retryRequest(config: AxiosRequestConfig): Promise<AxiosResponse> {
    // Initialize retry count if not already set
    (config as any).__retryCount = (config as any).__retryCount || 0;
    (config as any).__retryCount++;
    
    // Wait for delay before retrying
    await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
    
    // Retry the request
    return this.axiosInstance(config);
  }

  /**
   * Add a request to the pending queue during token refresh
   */
  private addToPendingRequests(config: AxiosRequestConfig): Promise<AxiosResponse> {
    return new Promise((resolve, reject) => {
      this.pendingRequests.push({ config, resolve, reject });
    });
  }

  /**
   * Resolve all pending requests with the new token
   */
  private resolvePendingRequests(newToken: string): void {
    this.pendingRequests.forEach(({ config, resolve }) => {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${newToken}`;
      resolve(this.axiosInstance(config));
    });
    
    this.pendingRequests = [];
  }

  /**
   * Reject all pending requests
   */
  private rejectPendingRequests(error: any): void {
    this.pendingRequests.forEach(({ reject }) => {
      reject(error);
    });
    
    this.pendingRequests = [];
  }

  /**
   * GET request
   */
  public async get(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.axiosInstance.get(url, config);
  }

  /**
   * POST request
   */
  public async post(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.axiosInstance.post(url, data, config);
  }

  /**
   * PUT request
   */
  public async put(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.axiosInstance.put(url, data, config);
  }

  /**
   * PATCH request
   */
  public async patch(url: string, data?: any, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.axiosInstance.patch(url, data, config);
  }

  /**
   * DELETE request
   */
  public async delete(url: string, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    return this.axiosInstance.delete(url, config);
  }

  /**
   * Upload files
   */
  public async upload(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    const uploadConfig = {
      ...config,
      headers: {
        ...config?.headers,
        'Content-Type': 'multipart/form-data'
      }
    };
    return this.axiosInstance.post(url, formData, uploadConfig);
  }

  /**
   * Download files
   */
  public async download(url: string, filename?: string, config?: AxiosRequestConfig): Promise<AxiosResponse> {
    const downloadConfig = {
      ...config,
      responseType: 'blob' as 'blob'
    };
    
    return this.axiosInstance.get(url, downloadConfig)
      .then((response: AxiosResponse<Blob>) => {
        // Create blob URL
        const blob = new Blob([response.data]);
        const downloadUrl = window.URL.createObjectURL(blob);
        
        // Create temporary link and trigger download
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = filename || this.getFilenameFromResponse(response);
        document.body.appendChild(link);
        link.click();
        
        // Clean up
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
        
        return response;
      });
  }

  /**
   * Extract filename from content-disposition header
   */
  private getFilenameFromResponse(response: AxiosResponse): string {
    const contentDisposition = response.headers['content-disposition'];
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]*)"?/);
      if (filenameMatch && filenameMatch[1]) {
        return filenameMatch[1];
      }
    }
    return 'downloaded_file';
  }

  /**
   * Setup a cached request
   */
  public createCachedRequest<T>(url: string, ttl: number = 60000): () => Promise<T> {
    let cachedData: T | null = null;
    let lastFetch: number = 0;
    
    return async (): Promise<T> => {
      const now = Date.now();
      
      // If cache is valid, return it
      if (cachedData && (now - lastFetch) < ttl) {
        return cachedData;
      }
      
      // Fetch fresh data
      const response = await this.get(url);
      cachedData = response.data;
      lastFetch = now;
      
      return cachedData;
    };
  }
}

// Create singleton instance
export const apiService = new ApiService();