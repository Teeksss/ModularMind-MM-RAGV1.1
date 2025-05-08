import React, { useState, useEffect } from 'react';
import { FiActivity, FiCpu, FiDatabase, FiHardDrive, FiRefreshCw, FiAlertCircle, FiClock, FiZap } from 'react-icons/fi';
import { Line, Bar, Pie } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { motion } from 'framer-motion';

import { monitoringService } from '@/services/monitoringService';
import Button from '@/components/common/Button';
import Card from '@/components/common/Card';
import Badge from '@/components/common/Badge';
import LoadingScreen from '@/components/common/LoadingScreen';

// Chart.js kayıt
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Grafik stilleri
const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
    },
  },
  interaction: {
    mode: 'nearest' as const,
    axis: 'x' as const,
    intersect: false
  }
};

const MonitoringDashboard: React.FC = () => {
  // State
  const [systemHealth, setSystemHealth] = useState<any>(null);
  const [metrics, setMetrics] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorLogs, setErrorLogs] = useState<any[]>([]);
  const [refreshInterval, setRefreshInterval] = useState<number>(30);
  const [timeRange, setTimeRange] = useState<string>('1h');
  const [showAlerts, setShowAlerts] = useState(false);
  
  // Verileri yükle
  const loadData = async () => {
    setIsLoading(true);
    try {
      // Sistem sağlığı bilgisini al
      const healthData = await monitoringService.getSystemHealth();
      setSystemHealth(healthData);
      
      // Metrikleri al
      const metricsData = await monitoringService.getMetrics(timeRange);
      setMetrics(metricsData);
      
      // Hata loglarını al
      const logs = await monitoringService.getErrorLogs(50);
      setErrorLogs(logs);
      
      // Uyarıları göster/gizle
      const hasWarnings = healthData.resources.cpu.percent > 70 || 
                          healthData.resources.memory.percent > 75 ||
                          logs.length > 0;
      setShowAlerts(hasWarnings);
      
    } catch (error) {
      console.error("Monitoring data loading error:", error);
    } finally {
      setIsLoading(false);
    }
  };
  
  // İlk yükleme ve otomatik yenileme
  useEffect(() => {
    loadData();
    
    // Periyodik yenileme
    const intervalId = setInterval(() => {
      loadData();
    }, refreshInterval * 1000);
    
    return () => clearInterval(intervalId);
  }, [refreshInterval, timeRange]);
  
  // Yükleniyor durumu
  if (isLoading && !systemHealth) {
    return <LoadingScreen text="Sistem verileri yükleniyor..." />;
  }
  
  // HTTP istek grafiği verileri
  const requestChartData = {
    labels: metrics?.http_requests.labels || [],
    datasets: [
      {
        label: 'Başarılı İstekler',
        data: metrics?.http_requests.success || [],
        borderColor: 'rgba(75, 192, 192, 1)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Başarısız İstekler',
        data: metrics?.http_requests.error || [],
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        tension: 0.4,
        fill: true
      }
    ],
  };
  
  // Kaynak kullanım grafiği verileri
  const resourceChartData = {
    labels: metrics?.resources.labels || [],
    datasets: [
      {
        label: 'CPU (%)',
        data: metrics?.resources.cpu || [],
        borderColor: 'rgba(54, 162, 235, 1)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        tension: 0.4,
        fill: true
      },
      {
        label: 'Bellek (%)',
        data: metrics?.resources.memory || [],
        borderColor: 'rgba(255, 159, 64, 1)',
        backgroundColor: 'rgba(255, 159, 64, 0.2)',
        tension: 0.4,
        fill: true
      }
    ],
  };
  
  // Önbellek performans grafiği
  const cacheChartData = {
    labels: metrics?.cache.labels || [],
    datasets: [
      {
        label: 'Hit Ratio (%)',
        data: metrics?.cache.hit_ratio || [],
        borderColor: 'rgba(153, 102, 255, 1)',
        backgroundColor: 'rgba(153, 102, 255, 0.2)',
        tension: 0.4,
        fill: true
      }
    ],
  };
  
  // Endpoint performans grafiği
  const endpointPerformanceData = {
    labels: metrics?.endpoints.labels || [],
    datasets: [
      {
        label: 'Yanıt Süresi (ms)',
        data: metrics?.endpoints.response_times || [],
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
      }
    ],
  };
  
  // LLM model kullanım grafiği
  const modelUsageData = {
    labels: metrics?.models.labels || [],
    datasets: [
      {
        label: 'İstek Sayısı',
        data: metrics?.models.request_counts || [],
        backgroundColor: [
          'rgba(255, 99, 132, 0.5)',
          'rgba(54, 162, 235, 0.5)',
          'rgba(255, 206, 86, 0.5)',
          'rgba(75, 192, 192, 0.5)',
        ],
        borderWidth: 1,
      }
    ],
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Sistem İzleme Paneli
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Sunucu durumu, performans metrikleri ve hata izleme
          </p>
        </div>
        
        <div className="flex flex-wrap items-center space-x-2 mt-4 md:mt-0">
          <div className="flex items-center space-x-2 mr-4">
            <label className="text-sm text-gray-600 dark:text-gray-400">Zaman Aralığı:</label>
            <select 
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              className="border border-gray-300 dark:border-gray-700 rounded p-1 text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
            >
              <option value="1h">Son 1 saat</option>
              <option value="3h">Son 3 saat</option>
              <option value="12h">Son 12 saat</option>
              <option value="24h">Son 24 saat</option>
              <option value="7d">Son 7 gün</option>
            </select>
          </div>
          
          <div className="flex items-center space-x-2 mr-4">
            <label className="text-sm text-gray-600 dark:text-gray-400">Yenileme:</label>
            <select 
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              className="border border-gray-300 dark:border-gray-700 rounded p-1 text-sm bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
            >
              <option value="10">10 sn</option>
              <option value="30">30 sn</option>
              <option value="60">1 dk</option>
              <option value="300">5 dk</option>
            </select>
          </div>
          
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<FiRefreshCw />}
            onClick={loadData}
            loading={isLoading}
          >
            Yenile
          </Button>
        </div>
      </div>
      
      {showAlerts && (
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 p-3 rounded-lg mb-6 flex items-start"
        >
          <FiAlertCircle className="text-yellow-500 mt-0.5 mr-2 flex-shrink-0" size={20} />
          <div>
            <h3 className="font-medium text-yellow-800 dark:text-yellow-300">Sistem Uyarıları</h3>
            <ul className="mt-1 text-sm text-yellow-700 dark:text-yellow-400 space-y-1">
              {systemHealth?.resources.cpu.percent > 70 && (
                <li>Yüksek CPU kullanımı: {systemHealth.resources.cpu.percent.toFixed(1)}%</li>
              )}
              {systemHealth?.resources.memory.percent > 75 && (
                <li>Yüksek bellek kullanımı: {systemHealth.resources.memory.percent.toFixed(1)}%</li>
              )}
              {errorLogs.length > 0 && (
                <li>Son 24 saatte {errorLogs.length} hata tespit edildi</li>
              )}
            </ul>
          </div>
        </motion.div>
      )}
      
      {/* Sistem Durumu Kartları */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {/* CPU Kartı */}
        <Card className="flex flex-col">
          <div className="flex items-center space-x-2 mb-4">
            <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
              <FiCpu className="text-blue-500" size={20} />
            </div>
            <h3 className="font-medium">CPU Kullanımı</h3>
          </div>
          
          <div className="flex-1 flex items-center">
            <div className="w-16 h-16 relative mb-2">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e6e6e6"
                  strokeWidth="3"
                  strokeDasharray="100, 100"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke={systemHealth?.resources.cpu.percent > 70 ? "#ef4444" : "#3b82f6"}
                  strokeWidth="3"
                  strokeDasharray={`${systemHealth?.resources.cpu.percent || 0}, 100`}
                />
                <text x="18" y="20.5" textAnchor="middle" fontSize="10" fill="currentColor">
                  {systemHealth?.resources.cpu.percent.toFixed(1)}%
                </text>
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {systemHealth?.resources.cpu.count_logical} Çekirdek
              </div>
              {systemHealth?.resources.process.cpu_percent > 0 && (
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  API: {systemHealth.resources.process.cpu_percent.toFixed(1)}%
                </div>
              )}
            </div>
          </div>
        </Card>
        
        {/* Bellek Kartı */}
        <Card className="flex flex-col">
          <div className="flex items-center space-x-2 mb-4">
            <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30">
              <FiHardDrive className="text-purple-500" size={20} />
            </div>
            <h3 className="font-medium">Bellek Kullanımı</h3>
          </div>
          
          <div className="flex-1 flex items-center">
            <div className="w-16 h-16 relative mb-2">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e6e6e6"
                  strokeWidth="3"
                  strokeDasharray="100, 100"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke={systemHealth?.resources.memory.percent > 75 ? "#ef4444" : "#8b5cf6"}
                  strokeWidth="3"
                  strokeDasharray={`${systemHealth?.resources.memory.percent || 0}, 100`}
                />
                <text x="18" y="20.5" textAnchor="middle" fontSize="10" fill="currentColor">
                  {systemHealth?.resources.memory.percent.toFixed(1)}%
                </text>
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {systemHealth?.resources.memory.used_gb.toFixed(1)} / {systemHealth?.resources.memory.total_gb.toFixed(1)} GB
              </div>
              {systemHealth?.resources.process.memory_percent > 0 && (
                <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                  API: {systemHealth.resources.process.memory_percent.toFixed(1)}%
                </div>
              )}
            </div>
          </div>
        </Card>
        
        {/* Disk Kartı */}
        <Card className="flex flex-col">
          <div className="flex items-center space-x-2 mb-4">
            <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
              <FiDatabase className="text-green-500" size={20} />
            </div>
            <h3 className="font-medium">Disk Kullanımı</h3>
          </div>
          
          <div className="flex-1 flex items-center">
            <div className="w-16 h-16 relative mb-2">
              <svg className="w-full h-full" viewBox="0 0 36 36">
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e6e6e6"
                  strokeWidth="3"
                  strokeDasharray="100, 100"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke={systemHealth?.resources.disk.percent > 85 ? "#ef4444" : "#10b981"}
                  strokeWidth="3"
                  strokeDasharray={`${systemHealth?.resources.disk.percent || 0}, 100`}
                />
                <text x="18" y="20.5" textAnchor="middle" fontSize="10" fill="currentColor">
                  {systemHealth?.resources.disk.percent.toFixed(1)}%
                </text>
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {systemHealth?.resources.disk.used_gb.toFixed(1)} / {systemHealth?.resources.disk.total_gb.toFixed(1)} GB
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                Boş: {systemHealth?.resources.disk.free_gb.toFixed(1)} GB
              </div>
            </div>
          </div>
        </Card>
        
        {/* Önbellek Kartı */}
        <Card className="flex flex-col">
          <div className="flex items-center space-x-2 mb-4">
            <div className="p-3 rounded-full bg-yellow-100 dark:bg-yellow-900/30">
              <FiZap className="text-yellow-500" size={20} />
            </div>
            <h3 className="font-medium">Önbellek Durumu</h3>
          </div>
          
          <div className="flex-1">
            <div className="mb-2">
              <div className="flex items-center justify-between text-sm mb-1">
                <span className="text-gray-600 dark:text-gray-400">Strateji</span>
                <Badge color="blue">{systemHealth?.cache.strategy}</Badge>
              </div>
              
              {systemHealth?.cache.memory_cache && (
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-600 dark:text-gray-400">Bellek Önbellek</span>
                  <span className="text-gray-800 dark:text-gray-200">
                    {systemHealth.cache.memory_cache.size} / {systemHealth.cache.memory_cache.max_size}
                  </span>
                </div>
              )}
              
              {systemHealth?.cache.redis_cache && Object.keys(systemHealth.cache.redis_cache).length > 0 && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600 dark:text-gray-400">Redis</span>
                  <span className="text-gray-800 dark:text-gray-200">
                    {systemHealth.cache.redis_cache.used_memory || "N/A"}
                  </span>
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>
      
      {/* Grafik Satırı 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* HTTP İstek Grafiği */}
        <Card className="p-0 overflow-hidden">
          <div className="p-4 border-b dark:border-gray-700">
            <h3 className="font-medium flex items-center">
              <FiActivity className="mr-2 text-blue-500" />
              HTTP İstek Oranı
            </h3>
          </div>
          <div className="p-4 h-80">
            {metrics ? (
              <Line data={requestChartData} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-400 dark:text-gray-500">Veri yükleniyor...</div>
              </div>
            )}
          </div>
        </Card>
        
        {/* Kaynak Kullanımı Grafiği */}
        <Card className="p-0 overflow-hidden">
          <div className="p-4 border-b dark:border-gray-700">
            <h3 className="font-medium flex items-center">
              <FiCpu className="mr-2 text-purple-500" />
              Kaynak Kullanımı
            </h3>
          </div>
          <div className="p-4 h-80">
            {metrics ? (
              <Line data={resourceChartData} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-400 dark:text-gray-500">Veri yükleniyor...</div>
              </div>
            )}
          </div>
        </Card>
      </div>
      
      {/* Grafik Satırı 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Önbellek Performansı */}
        <Card className="p-0 overflow-hidden lg:col-span-2">
          <div className="p-4 border-b dark:border-gray-700">
            <h3 className="font-medium flex items-center">
              <FiZap className="mr-2 text-yellow-500" />
              Önbellek Hit Ratio
            </h3>
          </div>
          <div className="p-4 h-80">
            {metrics ? (
              <Line data={cacheChartData} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center">
                <div className="text-gray-400 dark:text-gray-500">Veri yükleniyor...</div>
              </div>
            )}
          </div>
        </Card>
        
        {/* Model Kullanımı */}
        <Card className="p-0 overflow-hidden">
          <div className="p-4 border-b dark:border-gray-700">
            <h3 className="font-medium flex items-center">
              <FiDatabase className="mr-2 text-green-500" />
              LLM Model Kullanımı
            </h3>
          </div>
          <div className="p-4 h-80 flex items-center justify-center">
            {metrics ? (
              <Pie data={modelUsageData} />
            ) : (
              <div className="text-gray-400 dark:text-gray-500">Veri yükleniyor...</div>
            )}
          </div>
        </Card>
      </div>
      
      {/* Endpoint Performansı */}
      <Card className="p-0 overflow-hidden mb-8">
        <div className="p-4 border-b dark:border-gray-700">
          <h3 className="font-medium flex items-center">
            <FiClock className="mr-2 text-indigo-500" />
            Endpoint Performans