import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { config } from '@/config/config';

// API response interfaces
interface ApiResponse<T = any> {
    data: T;
    status: number;
    message?: string;
}

interface ErrorResponse {
    error: string;
    message: string;
    status: number;
}

// Base API class
class BaseApi {
    protected api: AxiosInstance;
    protected baseURL: string;

    constructor() {
        this.baseURL = config.api.baseUrl;
        this.api = axios.create({
            baseURL: this.baseURL,
            timeout: config.api.timeout,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        this._initializeInterceptors();
    }

    private _initializeInterceptors(): void {
        // Request interceptor
        this.api.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem(config.auth.tokenStorageKey);
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor
        this.api.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    // Token yenileme işlemi
                    const refreshToken = localStorage.getItem(config.auth.refreshTokenStorageKey);
                    if (refreshToken) {
                        try {
                            const newToken = await this._refreshToken(refreshToken);
                            localStorage.setItem(config.auth.tokenStorageKey, newToken);
                            error.config.headers.Authorization = `Bearer ${newToken}`;
                            return this.api.request(error.config);
                        } catch (refreshError) {
                            localStorage.removeItem(config.auth.tokenStorageKey);
                            localStorage.removeItem(config.auth.refreshTokenStorageKey);
                            window.location.href = '/auth/login';
                            return Promise.reject(refreshError);
                        }
                    }
                }
                return Promise.reject(error);
            }
        );
    }

    private async _refreshToken(refreshToken: string): Promise<string> {
        const response = await this.api.post('/auth/refresh', { refreshToken });
        return response.data.token;
    }

    protected async request<T>(config: AxiosRequestConfig): Promise<ApiResponse<T>> {
        try {
            const response: AxiosResponse<T> = await this.api.request(config);
            return {
                data: response.data,
                status: response.status,
            };
        } catch (error) {
            throw this._handleError(error);
        }
    }

    private _handleError(error: any): ErrorResponse {
        if (error.response) {
            return {
                error: error.response.data.error || 'API Error',
                message: error.response.data.message || 'An error occurred',
                status: error.response.status,
            };
        }
        return {
            error: 'Network Error',
            message: error.message || 'Network error occurred',
            status: 500,
        };
    }
}

// RAG API Service
class RagApi extends BaseApi {
    async query(input: string, options?: Record<string, any>): Promise<ApiResponse> {
        return this.request({
            method: 'POST',
            url: '/rag/query',
            data: { input, ...options },
        });
    }

    async getHistory(limit?: number): Promise<ApiResponse> {
        return this.request({
            method: 'GET',
            url: '/rag/history',
            params: { limit },
        });
    }

    async getFeedback(queryId: string): Promise<ApiResponse> {
        return this.request({
            method: 'GET',
            url: `/rag/feedback/${queryId}`,
        });
    }

    async submitFeedback(queryId: string, feedback: Record<string, any>): Promise<ApiResponse> {
        return this.request({
            method: 'POST',
            url: `/rag/feedback/${queryId}`,
            data: feedback,
        });
    }
}

// Agent API Service
class AgentApi extends BaseApi {
    async createAgent(agentConfig: Record<string, any>): Promise<ApiResponse> {
        return this.request({
            method: 'POST',
            url: '/agents',
            data: agentConfig,
        });
    }

    async getAgents(): Promise<ApiResponse> {
        return this.request({
            method: 'GET',
            url: '/agents',
        });
    }

    async getAgent(agentId: string): Promise<ApiResponse> {
        return this.request({
            method: 'GET',
            url: `/agents/${agentId}`,
        });
    }

    async updateAgent(agentId: string, updates: Record<string, any>): Promise<ApiResponse> {
        return this.request({
            method: 'PUT',
            url: `/agents/${agentId}`,
            data: updates,
        });
    }

    async deleteAgent(agentId: string): Promise<ApiResponse> {
        return this.request({
            method: 'DELETE',
            url: `/agents/${agentId}`,
        });
    }

    async executeTask(agentId: string, task: Record<string, any>): Promise<ApiResponse> {
        return this.request({
            method: 'POST',
            url: `/agents/${agentId}/execute`,
            data: task,
        });
    }
}

// API instance exports
export const ragApi = new RagApi();
export const agentApi = new AgentApi();