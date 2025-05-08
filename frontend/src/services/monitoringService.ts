import api from './api';

interface SystemHealthResponse {
  status: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  resources: {
    cpu: {
      percent: number;
      count_logical: number;
      count_physical: number;
    };
    memory: {
      percent: number;
      total_gb: number;
      available_gb: number;
      used_gb: number;
    };
    disk: {
      percent: number;
      total_gb: number;
      free_gb: number;
      used_gb: number;
    };
    process: {
      cpu_percent: number;
      memory_percent: number;
      threads: number;
      open_files: number;
    };
  };
  cache: {
    strategy: string;
    memory_cache: {
      size: number;
      max_size: number;
      usage_percent: number;
    };
    redis_cache: {
      used_memory: string;
      connected_clients: number;
      uptime_days: number;
    };
  };
  system: {
    platform: string;
    python_version: string;
    high_load_mode: boolean;
  };
  timestamp: number;
}

interface MetricsResponse {
  http_requests: {
    labels: string[];
    success: number[];
    error: number[];
  };
  resources: {
    labels: string[];
    cpu: number[];
    memory: number[];
  };
  cache: {
    labels: string[];
    hit_ratio: number[];
  };
  endpoints: {
    labels: string[];
    response_times: number[];
  };
  models: {
    labels: string[];
    request_counts: number[];
  };
}

interface ErrorLog {
  timestamp: string;
  level: string;
  message: string;
  module: string;
  function: string;
  line: number;
  request_id?: string;
  user_id?: string;
  exception?: {
    type: string;
    message: string;
  };
}

class MonitoringService {
  /**
   * Sistem sağlık durumunu alır
   */
  async getSystemHealth(): Promise<SystemHealthResponse> {
    const response = await api.get('/api/v1/admin/monitoring/health');
    return response.data;
  }
  
  /**
   * Sistem metriklerini belirli bir zaman aralığı için alır
   */
  async getMetrics(timeRange: string = '1h'): Promise<MetricsResponse> {
    const response = await api.get('/api/v1/admin/monitoring/metrics', {
      params: { time_range: timeRange }
    });
    return response.data;
  }
  
  /**
   * Hata loglarını alır
   */
  async getErrorLogs(limit: number = 100): Promise<ErrorLog[]> {
    const response = await api.get('/api/v1/admin/monitoring/logs', {
      params: { level: 'ERROR', limit }
    });
    return response.data.logs;
  }
  
  /**
   * Gerçek zamanlı metrik güncellemeleri için websocket bağlantısı
   */
  getMetricsWebsocket(): WebSocket {
    // API URL'ini Web Socket URL'ine çevir
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBaseUrl = api.defaults.baseURL?.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}//${wsBaseUrl}/api/v1/admin/monitoring/ws`;
    
    return new WebSocket(wsUrl);
  }
  
  /**
   * Önbellek istatistiklerini alır
   */
  async getCacheStats(): Promise<any> {
    const response = await api.get('/api/v1/admin/monitoring/cache');
    return response.data;
  }
  
  /**
   * Önbelleği temizler
   */
  async clearCache(cacheType?: string): Promise<{success: boolean, message: string}> {
    const response = await api.post('/api/v1/admin/monitoring/cache/clear', {
      cache_type: cacheType
    });
    return response.data;
  }
}

export const monitoringService = new MonitoringService();