import { useState, useEffect, useRef } from 'react';

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

/**
 * Gerçek zamanlı veri alma hook'u
 * WebSocket ile veri alır, bağlantı koptuğunda HTTP polling'e geçer
 */
export function useRealTimeData<T>(
  wsUrl: string, 
  pollingInterval: number = 30000,
  fetchFallback?: () => Promise<T>
) {
  const [data, setData] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const pollingIntervalRef = useRef<NodeJS.Timeout>();
  
  // Yeniden bağlanma denemesi sayısı
  const reconnectAttemptsRef = useRef<number>(0);
  const MAX_RECONNECT_ATTEMPTS = 5;
  const RECONNECT_DELAY = 3000;
  
  // WebSocket bağlantısını oluştur
  const setupWebSocket = () => {
    // Önceki bağlantıyı temizle
    if (wsRef.current) {
      wsRef.current.close();
    }
    
    // Yeni bağlantı oluştur
    wsRef.current = new WebSocket(wsUrl);
    setConnectionStatus('connecting');
    
    // Bağlantı açıldığında
    wsRef.current.onopen = () => {
      setIsConnected(true);
      setConnectionStatus('connected');
      reconnectAttemptsRef.current = 0;
      
      // Polling'i durdur
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = undefined;
      }
    };
    
    // Mesaj alındığında
    wsRef.current.onmessage = (event) => {
      try {
        const receivedData = JSON.parse(event.data);
        setData(receivedData);
      } catch (error) {
        console.error('WebSocket veri ayrıştırma hatası:', error);
      }
    };
    
    // Bağlantı kapandığında
    wsRef.current.onclose = () => {
      setIsConnected(false);
      handleDisconnect();
    };
    
    // Hata durumunda
    wsRef.current.onerror = (error) => {
      console.error('WebSocket bağlantı hatası:', error);
      setIsConnected(false);
      handleDisconnect();
    };
  };
  
  // Bağlantı koptuğunda
  const handleDisconnect = () => {
    setConnectionStatus('disconnected');
    
    // Yeniden bağlanma denemesi
    if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
      setConnectionStatus('reconnecting');
      reconnectAttemptsRef.current += 1;
      
      reconnectTimeoutRef.current = setTimeout(() => {
        setupWebSocket();
      }, RECONNECT_DELAY);
      
      // Polling'i başlat
      startPolling();
    } else {
      // Maksimum yeniden bağlanma denemesi aşıldı, sadece polling'e geç
      startPolling();
    }
  };
  
  // HTTP polling'i başlat
  const startPolling = () => {
    if (fetchFallback && !pollingIntervalRef.current) {
      // İlk veriyi hemen al
      fetchFallback().then(setData).catch(console.error);
      
      // Düzenli polling başlat
      pollingIntervalRef.current = setInterval(() => {
        fetchFallback().then(setData).catch(console.error);
      }, pollingInterval);
    }
  };
  
  // Manuel yeniden bağlanma
  const reconnect = () => {
    reconnectAttemptsRef.current = 0;
    setupWebSocket();
  };
  
  // Hook başlatma
  useEffect(() => {
    setupWebSocket();
    
    // Temizleme
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, [wsUrl]);
  
  return {
    data,
    isConnected,
    connectionStatus,
    reconnect
  };
}