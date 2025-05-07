import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  FaChartLine, FaSearch, FaDatabase, FaServer, 
  FaSpinner, FaMemory, FaExclamationTriangle
} from 'react-icons/fa';
import { apiService } from '../../services/api';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import ErrorBoundary from '../common/ErrorBoundary';

interface MetricData {
  timestamp: string;
  value: number;
}

interface LatencyData {
  avg: number;
  p50: number;
  p95: number;
  p99: number;
}

interface RetrievalStats {
  total_requests: number;
  cached_ratio: number;
  avg_latency: LatencyData;
  by_method: Record<string, number>;
}

interface ModelStats {
  name: string;
  usage_count: number;
  avg_latency: number;
  memory_usage: string;
}

interface SystemStats {
  cpu_usage: number;
  memory_usage: number;
  gpu_usage?: number;
  uptime: string;
}

const MetricsDashboard: React.FC = () => {
  const { t } = useTranslation();
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<string>('day');
  
  // Metrics state
  const [retrievalStats, setRetrievalStats] = useState<RetrievalStats | null>(null);
  const [modelStats, setModelStats] = useState<ModelStats[]>([]);
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null);
  const [latencyData, setLatencyData] = useState<MetricData[]>([]);
  const [requestsData, setRequestsData] = useState<MetricData[]>([]);
  
  // Fetch metrics data
  useEffect(() => {
    const fetchMetrics = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        // Fetch retrieval metrics
        const retrievalResponse = await apiService.get('/retrieval/metrics', {
          params: { timeRange }
        });
        
        // Fetch model metrics
        const modelsResponse = await apiService.get('/models/metrics', {
          params: { timeRange }
        });
        
        // Fetch system stats
        const systemResponse = await apiService.get('/admin/system-stats');
        
        // Update state with fetched data
        setRetrievalStats(retrievalResponse.data);
        setModelStats(modelsResponse.data.models || []);
        setSystemStats(systemResponse.data);
        
        // Prepare time-series data for charts
        if (retrievalResponse.data.latency_timeseries) {
          setLatencyData(retrievalResponse.data.latency_timeseries);
        }
        
        if (retrievalResponse.data.requests_timeseries) {
          setRequestsData(retrievalResponse.data.requests_timeseries);
        }
      } catch (error) {
        console.error('Error fetching metrics:', error);
        setError('Failed to load metrics data. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };
    
    fetchMetrics();
    
    // Set up polling interval
    const intervalId = setInterval(fetchMetrics, 30000); // every 30 seconds
    
    return () => clearInterval(intervalId);
  }, [timeRange]);
  
  // Format large numbers
  const formatNumber = (num: number): string => {
    return new Intl.NumberFormat().format(num);
  };
  
  // Format milliseconds as seconds
  const formatLatency = (ms: number): string => {
    return `${(ms / 1000).toFixed(3)}s`;
  };
  
  if (isLoading && !retrievalStats) {
    return (
      <div className="flex justify-center items-center h-64">
        <FaSpinner className="animate-spin text-blue-500 h-8 w-8" />
        <span className="ml-2 text-gray-600 dark:text-gray-400">Loading metrics...</span>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900 dark:bg-opacity-20 p-4 rounded-md">
        <div className="flex">
          <FaExclamationTriangle className="h-5 w-5 text-red-500" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-400">
              {error}
            </h3>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <ErrorBoundary>
      <div className="space-y-6">
        {/* Header and Controls */}
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('admin.systemMetrics')}
          </h1>
          
          <div className="flex items-center space-x-2">
            <label htmlFor="timeRange" className="text-sm text-gray-700 dark:text-gray-300">
              {t('admin.timeRange')}:
            </label>
            <select
              id="timeRange"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="rounded-md border-gray-300 dark:border-gray-700 text-sm py-1 px-2 bg-white dark:bg-gray-800 dark:text-gray-200"
            >
              <option value="hour">{t('admin.lastHour')}</option>
              <option value="day">{t('admin.lastDay')}</option>
              <option value="week">{t('admin.lastWeek')}</option>
              <option value="month">{t('admin.lastMonth')}</option>
            </select>
          </div>
        </div>
        
        {/* System Stats */}
        {systemStats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center">
                <div className="rounded-md bg-blue-500 p-2">
                  <FaServer className="h-5 w-5 text-white" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('admin.cpuUsage')}
                  </p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {systemStats.cpu_usage.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
            
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center">
                <div className="rounded-md bg-green-500 p-2">
                  <FaMemory className="h-5 w-5 text-white" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('admin.memoryUsage')}
                  </p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {systemStats.memory_usage.toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
            
            {systemStats.gpu_usage !== undefined && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
                <div className="flex items-center">
                  <div className="rounded-md bg-purple-500 p-2">
                    <FaMemory className="h-5 w-5 text-white" />
                  </div>
                  <div className="ml-3">
                    <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {t('admin.gpuUsage')}
                    </p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {systemStats.gpu_usage.toFixed(1)}%
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <div className="flex items-center">
                <div className="rounded-md bg-yellow-500 p-2">
                  <FaChartLine className="h-5 w-5 text-white" />
                </div>
                <div className="ml-3">
                  <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                    {t('admin.uptime')}
                  </p>
                  <p className="text-lg font-semibold text-gray-900 dark:text-white">
                    {systemStats.uptime}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Retrieval Stats */}
        {retrievalStats && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium leading-6 text-gray-900 dark:text-white flex items-center">
                <FaSearch className="mr-2" />
                {t('admin.retrievalMetrics')}
              </h3>
              
              <div className="mt-5 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                <div className="bg-gray-50 dark:bg-gray-700 overflow-hidden rounded-lg shadow">
                  <div className="px-4 py-5 sm:p-6">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                        {t('admin.totalRequests')}
                      </dt>
                      <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                        {formatNumber(retrievalStats.total_requests)}
                      </dd>
                    </dl>
                  </div>
                </div>
                
                <div className="bg-gray-50 dark:bg-gray-700 overflow-hidden rounded-lg shadow">
                  <div className="px-4 py-5 sm:p-6">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                        {t('admin.cacheHitRatio')}
                      </dt>
                      <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                        {(retrievalStats.cached_ratio * 100).toFixed(1)}%
                      </dd>
                    </dl>
                  </div>
                </div>
                
                <div className="bg-gray-50 dark:bg-gray-700 overflow-hidden rounded-lg shadow">
                  <div className="px-4 py-5 sm:p-6">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                        {t('admin.avgLatency')}
                      </dt>
                      <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                        {formatLatency(retrievalStats.avg_latency.avg)}
                      </dd>
                    </dl>
                  </div>
                </div>
                
                <div className="bg-gray-50 dark:bg-gray-700 overflow-hidden rounded-lg shadow">
                  <div className="px-4 py-5 sm:p-6">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 dark:text-gray-400 truncate">
                        {t('admin.p95Latency')}
                      </dt>
                      <dd className="mt-1 text-3xl font-semibold text-gray-900 dark:text-white">
                        {formatLatency(retrievalStats.avg_latency.p95)}
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
              
              {/* Retrieval Method Distribution Chart */}
              <div className="mt-8">
                <h4 className="text-md font-medium text-gray-900 dark:text-white mb-3">
                  {t('admin.retrievalMethodDistribution')}
                </h4>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(retrievalStats.by_method).map(([key, value]) => ({ name: key, value }))}
                      margin={{ top: 10, right: 30, left: 0, bottom: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip 
                        formatter={(value) => [formatNumber(Number(value)), t('admin.requests')]}
                      />
                      <Legend />
                      <Bar dataKey="value" fill="#3B82F6" name={t('admin.requestCount')} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}
        
        {/* Latency and Requests Over Time Charts */}
        {latencyData.length > 0 && requestsData.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-md font-medium text-gray-900 dark:text-white mb-4">
                {t('admin.latencyOverTime')}
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={latencyData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()}
                    />
                    <YAxis tickFormatter={(value) => `${(value / 1000).toFixed(2)}s`} />
                    <Tooltip 
                      formatter={(value) => [`${(Number(value) / 1000).toFixed(3)}s`, t('admin.latency')]}
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="value" stroke="#8884d8" name={t('admin.avgLatency')} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
            
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4">
              <h3 className="text-md font-medium text-gray-900 dark:text-white mb-4">
                {t('admin.requestsOverTime')}
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={requestsData}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis 
                      dataKey="timestamp" 
                      tickFormatter={(timestamp) => new Date(timestamp).toLocaleTimeString()}
                    />
                    <YAxis />
                    <Tooltip 
                      formatter={(value) => [formatNumber(Number(value)), t('admin.requests')]}
                      labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                    />
                    <Legend />
                    <Line type="monotone" dataKey="value" stroke="#82ca9d" name={t('admin.requestCount')} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
        
        {/* Model Usage Stats */}
        {modelStats.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-4 py-5 sm:p-6">
              <h3 className="text-lg font-medium leading-6 text-gray-900 dark:text-white flex items-center">
                <FaDatabase className="mr-2" />
                {t('admin.modelMetrics')}
              </h3>
              
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead>
                    <tr>
                      <th className="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t('admin.modelName')}
                      </th>
                      <th className="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t('admin.usageCount')}
                      </th>
                      <th className="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t('admin.avgLatency')}
                      </th>
                      <th className="px-6 py-3 bg-gray-50 dark:bg-gray-700 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        {t('admin.memoryUsage')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {modelStats.map((model) => (
                      <tr key={model.name}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                          {model.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatNumber(model.usage_count)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {formatLatency(model.avg_latency)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {model.memory_usage}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
};

export default MetricsDashboard;