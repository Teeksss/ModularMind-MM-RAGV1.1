import React, { useState, useEffect } from 'react';
import { FiSearch, FiBarChart2, FiAlertTriangle, FiCheck, FiRefreshCw, FiFilter } from 'react-icons/fi';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Select, SelectContent, SelectGroup, SelectItem, SelectValue, SelectTrigger } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@/components/ui/tabs';
import { useRealTimeData } from '@/hooks/useRealTimeData';
import { api } from '@/lib/api';

// ChartJS bileşenlerini kaydet
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

interface MetricsData {
  timestamp: number;
  metrics: {
    rag_metrics: {
      latency: {
        avg_ms: number;
        p95_ms: number;
        p99_ms: number;
      };
      retrieval: {
        precision: number;
        recall: number;
        relevance: number;
      };
      generation: {
        faithfulness: number;
        coherence: number;
        relevance: number;
      };
      error_rate: number;
      queries_per_minute: number;
    };
    system_metrics: {
      cpu_usage: number;
      memory_usage: number;
      database_connections: number;
    };
  };
  historical: {
    timeframes: string[];
    values: {
      latency: number[];
      precision: number[];
      recall: number[];
      queries_per_minute: number[];
    };
  };
}

interface QueryLog {
  id: string;
  timestamp: string;
  query: string;
  response: string;
  latency_ms: number;
  context_chunks: string[];
  metrics: {
    precision: number;
    recall: number;
    faithfulness: number;
    relevance: number;
  };
  user_id: string;
  model_id: string;
  feedback?: {
    rating: number;
    comment?: string;
  };
}

const RAGMonitoring: React.FC = () => {
  const [timeframe, setTimeframe] = useState<string>('24h');
  const [filterText, setFilterText] = useState<string>('');
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>(['latency', 'precision', 'recall']);
  const [queryLogs, setQueryLogs] = useState<QueryLog[]>([]);
  const [filteredLogs, setFilteredLogs] = useState<QueryLog[]>([]);
  const [selectedLog, setSelectedLog] = useState<QueryLog | null>(null);
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);

  // WebSocket ile gerçek zamanlı veri alma
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/admin/rag-metrics/ws`;
  
  const {
    data: metricsData,
    isConnected,
    connectionStatus,
    reconnect
  } = useRealTimeData<MetricsData>(
    wsUrl,
    60000, // Backup HTTP polling 1 dakika
    async () => {
      // WebSocket bağlantısı olmadığında çağrılacak fallback fonksiyon
      const response = await api.get('/api/v1/admin/rag-metrics');
      return response.data;
    }
  );

  // Query loglarını getir
  useEffect(() => {
    const fetchQueryLogs = async () => {
      try {
        const response = await api.get('/api/v1/admin/rag-query-logs', {
          params: { timeframe }
        });
        setQueryLogs(response.data);
      } catch (error) {
        console.error('Query logları getirme hatası:', error);
      }
    };

    fetchQueryLogs();
  }, [timeframe, refreshTrigger]);

  // Filtreleme
  useEffect(() => {
    if (!queryLogs.length) {
      setFilteredLogs([]);
      return;
    }

    const lowercaseFilter = filterText.toLowerCase();
    const filtered = queryLogs.filter(log => 
      log.query.toLowerCase().includes(lowercaseFilter) ||
      log.response.toLowerCase().includes(lowercaseFilter) ||
      log.user_id.toLowerCase().includes(lowercaseFilter)
    );

    setFilteredLogs(filtered);
  }, [queryLogs, filterText]);

  // Grafik verileri
  const prepareChartData = () => {
    if (!metricsData?.historical) return null;

    const datasets = [];

    if (selectedMetrics.includes('latency')) {
      datasets.push({
        label: 'Ortalama Gecikme (ms)',
        data: metricsData.historical.values.latency,
        borderColor: 'rgb(99, 102, 241)',
        backgroundColor: 'rgba(99, 102, 241, 0.1)',
        yAxisID: 'y-latency',
      });
    }

    if (selectedMetrics.includes('precision')) {
      datasets.push({
        label: 'Precision',
        data: metricsData.historical.values.precision,
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        yAxisID: 'y-metrics',
      });
    }

    if (selectedMetrics.includes('recall')) {
      datasets.push({
        label: 'Recall',
        data: metricsData.historical.values.recall,
        borderColor: 'rgb(249, 115, 22)',
        backgroundColor: 'rgba(249, 115, 22, 0.1)',
        yAxisID: 'y-metrics',
      });
    }

    if (selectedMetrics.includes('queries')) {
      datasets.push({
        label: 'Dakika Başına Sorgu',
        data: metricsData.historical.values.queries_per_minute,
        borderColor: 'rgb(139, 92, 246)',
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        yAxisID: 'y-queries',
      });
    }

    return {
      labels: metricsData.historical.timeframes,
      datasets
    };
  };

  const chartOptions = {
    responsive: true,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    stacked: false,
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: timeframe === '24h' ? 'hour' as const : 
                timeframe === '7d' ? 'day' as const : 'week' as const
        }
      },
      'y-latency': {
        type: 'linear' as const,
        display: selectedMetrics.includes('latency'),
        position: 'left' as const,
        title: {
          display: true,
          text: 'Gecikme (ms)'
        },
        min: 0
      },
      'y-metrics': {
        type: 'linear' as const,
        display: selectedMetrics.includes('precision') || selectedMetrics.includes('recall'),
        position: 'right' as const,
        title: {
          display: true,
          text: 'Başarı Oranı'
        },
        min: 0,
        max: 1,
        grid: {
          drawOnChartArea: false,
        },
      },
      'y-queries': {
        type: 'linear' as const,
        display: selectedMetrics.includes('queries'),
        position: 'right' as const,
        title: {
          display: true,
          text: 'Sorgu/Dakika'
        },
        min: 0,
        grid: {
          drawOnChartArea: false,
        },
      },
    },
  };

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">RAG Sistem İzleme</h1>
        
        <div className="flex items-center space-x-2">
          <div className="flex items-center">
            <span className={`w-3 h-3 rounded-full mr-2 ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
            <span className="text-sm text-gray-500 dark:text-gray-400">
              {isConnected ? 'Canlı' : 'Bağlantı Kesildi'}
            </span>
          </div>
          
          {!isConnected && (
            <Button variant="outline" size="sm" onClick={reconnect}>
              <FiRefreshCw className="mr-1" /> Yeniden Bağlan
            </Button>
          )}
          
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectItem value="24h">Son 24 Saat</SelectItem>
                <SelectItem value="7d">Son 7 Gün</SelectItem>
                <SelectItem value="30d">Son 30 Gün</SelectItem>
                <SelectItem value="90d">Son 90 Gün</SelectItem>
              </SelectGroup>
            </SelectContent>
          </Select>
        </div>
      </div