import React, { useState, useEffect } from 'react';
import { FiActivity, FiAlertCircle, FiCpu, FiRefreshCw } from 'react-icons/fi';
import { useWebSocket } from '@/hooks/useWebSocket';
import { motion, AnimatePresence } from 'framer-motion';
import Badge from '@/components/common/Badge';
import Card from '@/components/common/Card';

interface RealtimeMetrics {
  timestamp: number;
  resources: {
    cpu: number;
    memory: number;
    disk: number;
  };
  requests: {
    active: number;
    per_second: number;
  };
  cache: {
    memory_size: number;
    hit_ratio: number;
  };
}

const RealtimeMonitoring: React.FC = () => {
  // WebSocket hook kullanımı
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/admin/monitoring/ws`;
  
  const {
    lastMessage,
    status,
    reconnect,
    isConnected,
    reconnectAttempt
  } = useWebSocket(wsUrl, {
    reconnectBackoffFactor: 1.5,
    maxReconnectAttempts: Infinity, // Sonsuz yeniden bağlanma denemesi
    onOpen: () => console.log('WebSocket bağlantısı açıldı'),
    onClose: () => console.log('WebSocket bağlantısı kapandı'),
    onError: () => console.error('WebSocket bağlantı hatası')
  });
  
  // Metrikler state'i
  const [metrics, setMetrics] = useState<RealtimeMetrics | null>(null);
  
  // Son mesaj geldiğinde metrikleri güncelle
  useEffect(() => {
    if (lastMessage) {
      setMetrics(lastMessage as RealtimeMetrics);
    }
  }, [lastMessage]);
  
  return (
    <div className="space-y-4">
      {/* Bağlantı durumu */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Gerçek Zamanlı Metrikler
          </h2>
          {status === 'connected' ? (
            <Badge color="green">Bağlı</Badge>
          ) : status === 'connecting' || status === 'reconnecting' ? (
            <Badge color="yellow">
              <span className="flex items-center">
                <motion.span
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                  className="mr-1"
                >
                  <FiRefreshCw size={12} />
                </motion.span>
                {status === 'connecting' ? 'Bağlanıyor' : `Yeniden Bağlanıyor (${reconnectAttempt})`}
              </span>
            </Badge>
          ) : (
            <Badge color="red">Bağlantı Kesildi</Badge>
          )}
        </div>
        
        {!isConnected && (
          <button
            onClick={reconnect}
            className="text-sm px-2 py-1 bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 rounded flex items-center"
          >
            <FiRefreshCw className="mr-1" /> Yeniden Bağlan
          </button>
        )}
      </div>
      
      <AnimatePresence>
        {status === 'connected' && metrics ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {/* CPU Kullanımı */}
            <Card className="p-4">
              <div className="flex items-center space-x-2 mb-2">
                <FiCpu className="text-blue-500" />
                <h3 className="font-medium">CPU Kullanımı</h3>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-semibold">{metrics.resources.cpu.toFixed(1)}%</div>
                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${metrics.resources.cpu > 80 ? 'bg-red-500' : metrics.resources.cpu > 50 ? 'bg-yellow-500' : 'bg-green-500'}`}
                    style={{ width: `${metrics.resources.cpu}%` }}
                  ></div>
                </div>
              </div>
            </Card>
            
            {/* Aktif İstekler */}
            <Card className="p-4">
              <div className="flex items-center space-x-2 mb-2">
                <FiActivity className="text-purple-500" />
                <h3 className="font-medium">Aktif İstekler</h3>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-semibold">{metrics.requests.active}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {metrics.requests.per_second.toFixed(1)}/sn
                </div>
              </div>
            </Card>
            
            {/* Önbellek Hit Ratio */}
            <Card className="p-4">
              <div className="flex items-center space-x-2 mb-2">
                <FiAlertCircle className="text-green-500" />
                <h3 className="font-medium">Önbellek Hit Ratio</h3>
              </div>
              <div className="flex items-center justify-between">
                <div className="text-2xl font-semibold">{metrics.cache.hit_ratio.toFixed(1)}%</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  {(metrics.cache.memory_size / 1024).toFixed(1)}K öğe
                </div>
              </div>
            </Card>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="p-8 text-center text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-800 rounded-lg"
          >
            {status === 'connecting' || status === 'reconnecting' ? (
              <div className="flex flex-col items-center">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="mb-4"
                >
                  <FiRefreshCw size={32} />
                </motion.div>
                <p>Gerçek zamanlı metrikler yükleniyor...</p>
              </div>
            ) : (
              <div className="flex flex-col items-center">
                <FiAlertCircle size={32} className="mb-4" />
                <p>WebSocket bağlantısı kurulamadı.</p>
                <button
                  onClick={reconnect}
                  className="mt-4 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
                >
                  Yeniden Bağlan
                </button>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* Son güncelleme zamanı */}
      {metrics && (
        <div className="text-xs text-gray-500 dark:text-gray-400 text-right">
          Son Güncelleme: {new Date(metrics.timestamp * 1000).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};

export default RealtimeMonitoring;