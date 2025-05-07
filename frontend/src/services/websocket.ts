import { useAuthStore } from '../store/authStore';

type MessageHandler = (data: any) => void;
type ErrorHandler = (error: Event) => void;
type ConnectionHandler = () => void;
type CloseHandler = (event: CloseEvent) => void;

/**
 * WebSocket service for real-time communication
 */
export class WebSocketService {
  private socket: WebSocket | null = null;
  private url: string;
  private messageHandlers: Map<string, MessageHandler[]> = new Map();
  private connectionHandlers: ConnectionHandler[] = [];
  private errorHandlers: ErrorHandler[] = [];
  private closeHandlers: CloseHandler[] = [];
  private heartbeatInterval: NodeJS.Timeout | null = null;
  private heartbeatTimeout: NodeJS.Timeout | null = null;
  private pingIntervalMs: number = 30000; // 30 seconds
  private pingTimeoutMs: number = 5000; // 5 seconds

  constructor(url: string) {
    this.url = url;
  }

  /**
   * Connect to the WebSocket server
   */
  connect(token?: string): void {
    // Get token from auth store if not provided
    if (!token) {
      const authStore = useAuthStore.getState();
      token = authStore.token;
    }
    
    // Close existing connection
    if (this.socket) {
      this.socket.close();
    }

    // Create WebSocket URL with token if provided
    const wsUrl = token ? `${this.url}?token=${token}` : this.url;
    
    // Create new WebSocket
    this.socket = new WebSocket(wsUrl);
    
    // Set event handlers
    this.socket.onopen = this.handleOpen.bind(this);
    this.socket.onmessage = this.handleMessage.bind(this);
    this.socket.onerror = this.handleError.bind(this);
    this.socket.onclose = this.handleClose.bind(this);
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    this.stopHeartbeat();
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  /**
   * Send a message to the WebSocket server
   */
  send(type: string, data: any): void {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      const message = JSON.stringify({ type, data });
      this.socket.send(message);
    } else {
      console.error('WebSocket is not connected');
    }
  }

  /**
   * Send a ping message to check connection
   */
  ping(): void {
    this.send('ping', { timestamp: Date.now() });
    
    // Set timeout for pong response
    this.heartbeatTimeout = setTimeout(() => {
      console.warn('Pong response not received, connection may be dead');
      this.reconnect();
    }, this.pingTimeoutMs);
  }

  /**
   * Handle pong response
   */
  pong(): void {
    // Clear the timeout since we got a response
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /**
   * Start heartbeat for connection
   */
  startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = setInterval(() => {
      this.ping();
    }, this.pingIntervalMs);
  }

  /**
   * Stop heartbeat
   */
  stopHeartbeat(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
    
    if (this.heartbeatTimeout) {
      clearTimeout(this.heartbeatTimeout);
      this.heartbeatTimeout = null;
    }
  }

  /**
   * Reconnect to the server
   */
  reconnect(): void {
    this.stopHeartbeat();
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.connect();
  }

  /**
   * Register a message handler
   */
  onMessage(type: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, []);
    }
    
    this.messageHandlers.get(type)!.push(handler);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index !== -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }

  /**
   * Register a connection handler
   */
  onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.push(handler);
    
    // Return unsubscribe function
    return () => {
      const index = this.connectionHandlers.indexOf(handler);
      if (index !== -1) {
        this.connectionHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Register an error handler
   */
  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.push(handler);
    
    // Return unsubscribe function
    return () => {
      const index = this.errorHandlers.indexOf(handler);
      if (index !== -1) {
        this.errorHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Register a close handler
   */
  onClose(handler: CloseHandler): () => void {
    this.closeHandlers.push(handler);
    
    // Return unsubscribe function
    return () => {
      const index = this.closeHandlers.indexOf(handler);
      if (index !== -1) {
        this.closeHandlers.splice(index, 1);
      }
    };
  }

  /**
   * Check if socket is connected
   */
  isConnected(): boolean {
    return !!this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  /**
   * Handle WebSocket open event
   */
  private handleOpen(event: Event): void {
    console.log('WebSocket connected');
    
    // Start heartbeat
    this.startHeartbeat();
    
    // Notify handlers
    this.connectionHandlers.forEach(handler => handler());
  }

  /**
   * Handle WebSocket message event
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message = JSON.parse(event.data);
      const { type, data } = message;
      
      // Handle pong messages
      if (type === 'pong') {
        this.pong();
        return;
      }
      
      // Dispatch to specific handlers
      const handlers = this.messageHandlers.get(type);
      if (handlers) {
        handlers.forEach(handler => handler(data));
      }
      
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Handle WebSocket error event
   */
  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
    
    // Notify handlers
    this.errorHandlers.forEach(handler => handler(event));
  }

  /**
   * Handle WebSocket close event
   */
  private handleClose(event: CloseEvent): void {
    console.log(`WebSocket closed: ${event.code} ${event.reason}`);
    
    // Stop heartbeat
    this.stopHeartbeat();
    
    // Notify handlers
    this.closeHandlers.forEach(handler => handler(event));
  }
}

// Create singleton instance
export const websocketService = new WebSocketService(
  `${window.location.protocol === 'https:' ? 'wss://' : 'ws://'}${window.location.host}/api/ws`
);