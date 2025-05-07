import { useState, useEffect, useRef, useCallback } from 'react';
import { websocketService } from '../services/websocket';
import { useAuthStore } from '../store/authStore';
import { useNotificationStore } from '../store/notificationStore';

type MessageHandler = (data: any) => void;

/**
 * Hook for using WebSocket connections with auto-reconnect
 */
export const useWebSocket = (
  autoConnect: boolean = true,
  reconnectOptions: {
    maxAttempts?: number;
    initialDelay?: number;
    maxDelay?: number;
    showNotifications?: boolean;
  } = {}
) => {
  const { token, isAuthenticated } = useAuthStore();
  const { addNotification } = useNotificationStore();
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState<number>(0);
  const messageHandlers = useRef<Map<string, () => void>>(new Map());
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Default reconnect options
  const {
    maxAttempts = 10,
    initialDelay = 1000,
    maxDelay = 30000,
    showNotifications = true
  } = reconnectOptions;
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated) return;
    
    try {
      websocketService.connect(token || undefined);
      setReconnectAttempt(0);
    } catch (err) {
      setError('Failed to connect to WebSocket server');
      console.error('WebSocket connection error:', err);
    }
  }, [isAuthenticated, token]);
  
  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    websocketService.disconnect();
    
    // Clear any active reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
  }, []);
  
  // Handle reconnection
  const handleReconnect = useCallback(() => {
    if (reconnectAttempt >= maxAttempts) {
      setError(`Failed to reconnect after ${maxAttempts} attempts`);
      if (showNotifications) {
        addNotification({
          type: 'error',
          title: 'Connection Lost',
          message: `Failed to reconnect to server after ${maxAttempts} attempts. Please refresh the page.`
        });
      }
      return;
    }
    
    // Calculate backoff delay with jitter
    const delay = Math.min(
      initialDelay * Math.pow(1.5, reconnectAttempt) + Math.random() * 1000,
      maxDelay
    );
    
    // Set reconnect timeout
    reconnectTimeoutRef.current = setTimeout(() => {
      if (showNotifications && reconnectAttempt > 0) {
        addNotification({
          type: 'info',
          title: 'Reconnecting',
          message: `Attempting to reconnect (${reconnectAttempt + 1}/${maxAttempts})...`
        });
      }
      
      connect();
      setReconnectAttempt(prev => prev + 1);
    }, delay);
  }, [reconnectAttempt, maxAttempts, initialDelay, maxDelay, connect, showNotifications, addNotification]);
  
  // Send message to WebSocket server
  const sendMessage = useCallback((type: string, data: any) => {
    if (!isConnected) {
      console.warn('Cannot send message: WebSocket is not connected');
      return;
    }
    
    websocketService.send(type, data);
  }, [isConnected]);
  
  // Subscribe to message type
  const subscribe = useCallback((type: string, handler: MessageHandler) => {
    // Register handler
    const unsubscribe = websocketService.onMessage(type, handler);
    
    // Store unsubscribe function
    const handlerId = type + handler.toString();
    messageHandlers.current.set(handlerId, unsubscribe);
    
    // Return unsubscribe function
    return () => {
      unsubscribe();
      messageHandlers.current.delete(handlerId);
    };
  }, []);
  
  // Handle connection changes
  useEffect(() => {
    if (!autoConnect || !isAuthenticated) return;
    
    // Set up connection handlers
    const handleConnect = () => {
      setIsConnected(true);
      setError(null);
      setReconnectAttempt(0);
      
      if (showNotifications && reconnectAttempt > 0) {
        addNotification({
          type: 'success',
          title: 'Reconnected',
          message: 'Connection to server has been restored.'
        });
      }
    };
    
    const handleError = (event: Event) => {
      setError('WebSocket error occurred');
      console.error('WebSocket error:', event);
    };
    
    const handleClose = () => {
      setIsConnected(false);
      
      // Attempt to reconnect
      handleReconnect();
    };
    
    // Register handlers
    const unsubscribeConnect = websocketService.onConnect(handleConnect);
    const unsubscribeError = websocketService.onError(handleError);
    const unsubscribeClose = websocketService.onClose(handleClose);
    
    // Connect if not already connected
    if (!websocketService.isConnected()) {
      connect();
    } else {
      setIsConnected(true);
    }
    
    // Cleanup
    return () => {
      unsubscribeConnect();
      unsubscribeError();
      unsubscribeClose();
      
      // Clear any active reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      // Clean up message handlers
      messageHandlers.current.forEach(unsubscribe => unsubscribe());
      messageHandlers.current.clear();
    };
  }, [autoConnect, isAuthenticated, connect, handleReconnect, reconnectAttempt, addNotification, showNotifications]);
  
  // Update connected status on token change
  useEffect(() => {
    setIsConnected(websocketService.isConnected());
  }, [token]);
  
  return {
    isConnected,
    error,
    reconnectAttempt,
    connect,
    disconnect,
    sendMessage,
    subscribe
  };
};

export default useWebSocket;