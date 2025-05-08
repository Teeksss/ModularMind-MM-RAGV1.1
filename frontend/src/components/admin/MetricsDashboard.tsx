import React, { useState, useEffect, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { 
    FaChartLine, FaSearch, FaDatabase, FaServer, 
    FaSpinner, FaMemory, FaExclamationTriangle
} from 'react-icons/fa';
import { apiService } from '../../services/api';
import { 
    BarChart, Bar, LineChart, Line, XAxis, YAxis, 
    CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import ErrorBoundary from '../common/ErrorBoundary';
import { useErrorHandler } from '@/hooks/useErrorHandler';
import { useMetricsData } from '@/hooks/useMetricsData';

interface LatencyData {
    avg: number | null;
    p50: number | null;
    p95: number | null;
    p99: number | null;
}

interface RetrievalStats {
    total_requests: number;
    cached_ratio: number;
    avg_latency: LatencyData | null;
    by_method: Record<string, number>;
}

interface ModelStats {
    name: string;
    usage_count: number;
    avg_latency: number | null;
    memory_usage: string;
    error_rate?: number;
}

interface SystemStats {
    cpu_usage: number;
    memory_usage: number;
    gpu_usage?: number | null;
    uptime: string;
    disk_usage: number;
}

const MetricsDashboard: React.FC = () => {
    const { t } = useTranslation();
    const { handleError } = useErrorHandler();
    const [timeRange, setTimeRange] = useState<string>('day');
    
    const {
        isLoading,
        error,
        data: {
            retrievalStats,
            systemStats,
            modelStats,
            latencyData,
            requestsData
        },
        refetch
    } = useMetricsData(timeRange);

    // Memoized calculations
    const averageLatency = useMemo(() => {
        if (!latencyData?.length) return null;
        const sum = latencyData.reduce((acc, curr) => acc + curr.value, 0);
        return (sum / latencyData.length).toFixed(2);
    }, [latencyData]);

    const totalRequests = useMemo(() => {
        return retrievalStats?.total_requests ?? 0;
    }, [retrievalStats]);

    // Error handling
    useEffect(() => {
        if (error) {
            handleError(error);
        }
    }, [error, handleError]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-full">
                <FaSpinner className="animate-spin h-8 w-8 text-blue-500" />
            </div>
        );
    }

    return (
        <ErrorBoundary>
            <div className="space-y-6">
                {/* Time Range Selection */}
                <div className="flex justify-end">
                    <select
                        value={timeRange}
                        onChange={(e) => setTimeRange(e.target.value)}
                        className="rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
                    >
                        <option value="hour">Last Hour</option>
                        <option value="day">Last 24 Hours</option>
                        <option value="week">Last Week</option>
                        <option value="month">Last Month</option>
                    </select>
                </div>

                {/* System Stats */}
                {systemStats && (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <SystemStatCard
                            icon={<FaServer />}
                            title={t('admin.cpuUsage')}
                            value={`${systemStats.cpu_usage.toFixed(1)}%`}
                        />
                        <SystemStatCard
                            icon={<FaMemory />}
                            title={t('admin.memoryUsage')}
                            value={`${systemStats.memory_usage.toFixed(1)}%`}
                        />
                        {systemStats.gpu_usage !== null && (
                            <SystemStatCard
                                icon={<FaDatabase />}
                                title={t('admin.gpuUsage')}
                                value={`${systemStats.gpu_usage.toFixed(1)}%`}
                            />
                        )}
                        <SystemStatCard
                            icon={<FaChartLine />}
                            title={t('admin.uptime')}
                            value={systemStats.uptime}
                        />
                    </div>
                )}

                {/* Charts and Tables */}
                {retrievalStats && latencyData && requestsData && (
                    <div className="space-y-6">
                        <MetricsChart
                            data={latencyData}
                            title={t('admin.latencyOverTime')}
                            dataKey="value"
                            yAxisLabel={t('admin.latencyMs')}
                        />
                        <MetricsChart
                            data={requestsData}
                            title={t('admin.requestsOverTime')}
                            dataKey="value"
                            yAxisLabel={t('admin.requestCount')}
                        />
                        <ModelStatsTable data={modelStats} />
                    </div>
                )}
            </div>
        </ErrorBoundary>
    );
};

export default MetricsDashboard;