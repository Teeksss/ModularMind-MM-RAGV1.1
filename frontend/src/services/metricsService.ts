import { apiService } from './api';

/**
 * Service for metrics operations
 */
export const metricsService = {
  /**
   * Get system metrics
   */
  getSystemMetrics: async (timeRange: string = 'day') => {
    return apiService.get('/admin/system-stats', {
      params: { timeRange }
    });
  },

  /**
   * Get retrieval metrics
   */
  getRetrievalMetrics: async (timeRange: string = 'day') => {
    return apiService.get('/retrieval/metrics', {
      params: { timeRange }
    });
  },

  /**
   * Get model metrics
   */
  getModelMetrics: async (timeRange: string = 'day') => {
    return apiService.get('/models/metrics', {
      params: { timeRange }
    });
  },

  /**
   * Get prometheus raw metrics (admin only)
   */
  getRawMetrics: async () => {
    return apiService.get('/metrics', {
      responseType: 'text'
    });
  }
};