import { useState, useEffect, useRef, useCallback } from 'react';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'reconnecting' | 'error';

interface UseWebSocketOptions {
  /** WebSocket yeniden bağlanırken kullanılacak maksimum gecikme (ms) */
  maxReconnectDelay?: number;
  /** Yeniden bağlanma denemesi başına artma faktörü */
  reconnectBackoffFactor?: number;
  /** Maksimum yeniden bağlanma denemesi sayısı */
  maxReconnectAttempts?: number;
  /** Yeniden bağlanma denemesi öncesi ilk gecikme (ms) */
  initialReconnectDelay?: number;
  /** Otomatik yeniden bağlanma etkinleştirme */
  autoReconnect?: boolean;
  /** Otomatik olarak bağlantıya başla */
  autoConnect?: boolean;
  /** Bağlantı başarılı olduğunda çağrılacak fonksiyon */
  onOpen?: (event: WebSocketEventMap['open']) => void;
  /** Mesaj alındığında çağrılacak fonksiyon */
  onMessage?: (event: WebSocketEventMap['message']) => void;
  /** Bağlantı kapandığında çağrılacak fonksiyon */
  onClose?: (event: WebSocketEventMap['close']) => void;
  /** Hata oluştuğunda çağrılacak fonksiyon */
  onError?: (event: WebSocketEventMap['error']) => void;
}

/**
 * WebSocket bağlantılarını yönetmek ve otomatik yeniden bağlanma
 * mantığı eklemek için React hook.
 */
export function useWebSocket(url: string, options: UseWebSocketOptions = {}) {
  // Varsayılan değerler
  const {
    autoReconnect = true,
    autoConnect = true,
    maxReconnectDelay = 30000, // 30 saniye
    reconnectBackoffFactor = 1.5,
    maxReconnectAttempts = 20,
    initialReconnectDelay = 1000, // 1 saniye
    onOpen,
    onMessage,
    onClose,
    onError,
  } = options;

  // WebSocket durumu
  const [status, setStatus] = useState<WebSocketStatus>(
    autoConnect ? 'connecting' : 'disconnected'
  );
  
  // WebSocket referansı
  const socketRef = useRef<WebSocket | null>(null);
  
  // Yeniden bağlanma denemesi sayısı
  const reconnectAttemptsRef = useRef(0);
  
  // Yeniden bağlanma zamanlayıcısı
  const reconnectTimerRef = useRef<number | null>(null);
  
  // Son mesajı tutacak state
  const [lastMessage, setLastMessage] = useState<any>(null);
  
  // WebSocket bağlantı işlevi
  const connect = useCallback(() => {
    // Mevcut bir bağlantı varsa, önce kapat
    if (socketRef.current) {
      socketRef.current.close();
    }
    
    try {
      // WebSocket bağlantısını oluştur
      const socket = new WebSocket(url);
      socketRef.current = socket;
      setStatus('connecting');
      
      // Açılış olay dinleyicisi
      socket.addEventListener('open', (event) => {
        setStatus('connected');
        reconnectAttemptsRef.current = 0; // Başarılı bağlantıda sayacı sıfırla
        
        if (onOpen) {
          onOpen(event);
        }
      });
      
      // Mesaj olay dinleyicisi
      socket.addEventListener('message', (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (e) {
          setLastMessage(event.data);
        }
        
        if (onMessage) {
          onMessage(event);
        }
      });
      
      // Hata olay dinleyicisi
      socket.addEventListener('error', (event) => {
        setStatus('error');
        
        if (onError) {
          onError(event);
        }
      });
      
      // Kapatma olay dinleyicisi
      socket.addEventListener('close', (event) => {
        setStatus('disconnected');
        
        if (onClose) {
          onClose(event);
        }
        
        // Otomatik yeniden bağlanma
        if (autoReconnect && reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(
            initialReconnectDelay * Math.pow(reconnectBackoffFactor, reconnectAttemptsRef.current),
            maxReconnectDelay
          );
          
          setStatus('reconnecting');
          
          // Zamanlayıcıyı temizle ve yeni zamanlayıcı oluştur
          if (reconnectTimerRef.current !== null) {
            window.clearTimeout(reconnectTimerRef.current);
          }
          
          reconnectTimerRef.current = window.setTimeout(() => {
            reconnectAttemptsRef.current += 1;
            connect();
          }, delay);
        }
      });
    } catch (error) {
      console.error('WebSocket bağlantı hatası:', error);
      setStatus('error');
    }
  }, [url, autoReconnect, initialReconnectDelay, reconnectBackoffFactor, maxReconnectDelay, maxReconnectAttempts, onOpen, onMessage, onClose, onError]);
  
  // Manuel olarak yeniden bağlanma işlevi
  const reconnect = useCallback(() => {
    if (status !== 'connecting') {
      reconnectAttemptsRef.current = 0; // Yeniden bağlanma sayacını sıfırla
      connect();
    }
  }, [connect, status]);
  
  // Manuel olarak bağlantıyı kapatma işlevi
  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      setStatus('disconnected');
    }
    
    // Zamanlayıcıyı temizle
    if (reconnectTimerRef.current !== null) {
      window.clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);
  
  // Mesaj gönderme işlevi
  const sendMessage = useCallback((data: string | ArrayBufferLike | Blob | ArrayBufferView) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(data);
      return true;
    }
    return false;
  }, []);
  
  // JSON mesajı gönderme işlevi
  const sendJsonMessage = useCallback((data: any) => {
    try {
      return sendMessage(JSON.stringify(data));
    } catch (e) {
      console.error('JSON mesajı gönderme hatası:', e);
      return false;
    }
  }, [sendMessage]);
  
  // Otomatik bağlantı
  useEffect(() => {
    if (autoConnect) {
      connect();
    }
    
    // Temizleme işlevi
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
      
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
      }
    };
  }, [connect, autoConnect]);
  
  // Sayfa görünürlüğünü izleyerek bağlantıyı yönet
  useEffect(() => {
    const handleVisibilityChange = () => {
      // Sayfa ön plana geldiğinde ve bağlantı kopmuşsa yeniden bağlan
      if (document.visibilityState === 'visible' && 
          socketRef.current && 
          socketRef.current.readyState !== WebSocket.OPEN && 
          status === 'disconnected') {
        reconnect();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [reconnect, status]);
  
  // Ağ bağlantısını izleyerek bağlantıyı yönet
  useEffect(() => {
    const handleOnline = () => {
      // Ağ bağlantısı yeniden sağlandığında ve WebSocket bağlantısı yoksa
      if (socketRef.current && 
          socketRef.current.readyState !== WebSocket.OPEN && 
          status === 'disconnected') {
        reconnect();
      }
    };
    
    window.addEventListener('online', handleOnline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
    };
  }, [reconnect, status]);
  
  return {
    // WebSocket referansı (ileri düzey kullanım için)
    socket: socketRef.current,
    
    // Bağlantı durumu
    status,
    
    // Son alınan mesaj
    lastMessage,
    
    // Bağlantı yönetimi
    connect,
    disconnect,
    reconnect,
    
    // Mesaj gönderme
    sendMessage,
    sendJsonMessage,
    
    // Bağlantı bilgileri
    isConnected: status === 'connected',
    isConnecting: status === 'connecting',
    isReconnecting: status === 'reconnecting',
    isDisconnected: status === 'disconnected',
    hasError: status === 'error',
    
    // Yeniden bağlanma bilgileri
    reconnectAttempt: reconnectAttemptsRef.current
  };
}