import { create } from 'zustand';
import { apiService } from '../services/api';
import { websocketService } from '../services/websocket';
import { useNotificationStore } from './notificationStore';

interface ChatMessage {
  id: string;
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  sources?: Array<{
    id: string;
    title: string;
    url?: string;
  }>;
  citations?: Array<{
    text: string;
    source_id: string;
  }>;
}

interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  last_activity: string;
  message_count?: number;
}

interface StreamingState {
  isStreaming: boolean;
  sessionId: string | null;
  responseId: string | null;
  streamedContent: string;
}

interface ChatStore {
  // State
  sessions: ChatSession[];
  currentSession: ChatSession | null;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  streaming: StreamingState;
  
  // Actions
  fetchSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string>;
  fetchMessages: (sessionId: string) => Promise<void>;
  sendMessage: (content: string, sessionId?: string) => Promise<void>;
  regenerateResponse: (messageId: string) => Promise<void>;
  fetchSource: (sourceId: string) => Promise<any>;
  setCurrentSession: (sessionId: string) => Promise<void>;
  clearMessages: () => void;
  deleteSession: (sessionId: string) => Promise<void>;
  renameSession: (sessionId: string, title: string) => Promise<void>;
  
  // Streaming actions
  setupStreamListeners: () => void;
  cleanupStreamListeners: () => void;
  startStreaming: (sessionId: string, responseId: string) => void;
  endStreaming: (finalContent?: string) => void;
  updateStreamContent: (content: string) => void;
}

export const useChatStore = create<ChatStore>((set, get) => ({
  // Initial state
  sessions: [],
  currentSession: null,
  messages: [],
  isLoading: false,
  error: null,
  streaming: {
    isStreaming: false,
    sessionId: null,
    responseId: null,
    streamedContent: ''
  },
  
  // Actions
  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.get('/chat/sessions');
      set({ 
        sessions: response.data.sessions,
        isLoading: false
      });
    } catch (error) {
      console.error('Failed to fetch chat sessions:', error);
      set({ 
        error: 'Failed to fetch chat sessions', 
        isLoading: false 
      });
    }
  },
  
  createSession: async (title?: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.post('/chat/sessions', { title });
      const newSession = response.data;
      
      set(state => ({ 
        sessions: [newSession, ...state.sessions],
        currentSession: newSession,
        isLoading: false
      }));
      
      return newSession.id;
    } catch (error) {
      console.error('Failed to create chat session:', error);
      set({ 
        error: 'Failed to create chat session', 
        isLoading: false 
      });
      throw error;
    }
  },
  
  fetchMessages: async (sessionId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.get(`/chat/sessions/${sessionId}/messages`);
      set({ 
        messages: response.data.messages,
        isLoading: false
      });
    } catch (error) {
      console.error(`Failed to fetch messages for session ${sessionId}:`, error);
      set({ 
        error: `Failed to fetch messages for this chat`, 
        isLoading: false 
      });
    }
  },
  
  sendMessage: async (content: string, sessionId?: string) => {
    const currentSessionId = sessionId || get().currentSession?.id;
    
    // Create a new session if needed
    if (!currentSessionId) {
      try {
        const newSessionId = await get().createSession();
        return get().sendMessage(content, newSessionId);
      } catch (error) {
        throw error;
      }
    }
    
    set({ isLoading: true, error: null });
    
    try {
      // Optimistically add user message
      const tempUserMessage: ChatMessage = {
        id: `temp-${Date.now()}`,
        session_id: currentSessionId,
        role: 'user',
        content: content,
        created_at: new Date().toISOString()
      };
      
      set(state => ({
        messages: [...state.messages, tempUserMessage]
      }));
      
      // Send message to API
      const response = await apiService.post(`/chat/sessions/${currentSessionId}/messages`, {
        content,
        role: 'user'
      });
      
      // Replace temp message with real one
      const userMessage = response.data;
      
      set(state => ({
        messages: state.messages.map(msg => 
          msg.id === tempUserMessage.id ? userMessage : msg
        ),
      }));
      
      // Websocket is used for assistant response streaming
      // Set initial state for response
      const tempResponseId = `response-${Date.now()}`;
      
      // Start streaming state
      get().startStreaming(currentSessionId, tempResponseId);
      
      // Update last activity for session
      set(state => ({
        sessions: state.sessions.map(session => 
          session.id === currentSessionId 
            ? { ...session, last_activity: new Date().toISOString() }
            : session
        )
      }));
      
    } catch (error) {
      console.error('Failed to send message:', error);
      set({ 
        error: 'Failed to send message', 
        isLoading: false 
      });
      
      // End streaming if there was an error
      get().endStreaming();
    }
  },
  
  regenerateResponse: async (messageId: string) => {
    const currentSession = get().currentSession;
    
    if (!currentSession) {
      set({ error: 'No active chat session' });
      return;
    }
    
    set({ isLoading: true, error: null });
    
    try {
      // Get the message to regenerate and find the preceding user message
      const messages = get().messages;
      const messageIndex = messages.findIndex(m => m.id === messageId);
      
      if (messageIndex === -1) {
        throw new Error('Message not found');
      }
      
      // Find the most recent user message before this one
      let userMessageIndex = messageIndex - 1;
      while (userMessageIndex >= 0 && messages[userMessageIndex].role !== 'user') {
        userMessageIndex--;
      }
      
      if (userMessageIndex < 0) {
        throw new Error('No user message found before this response');
      }
      
      const userMessage = messages[userMessageIndex];
      
      // Remove the old assistant message
      set(state => ({
        messages: state.messages.filter(msg => msg.id !== messageId)
      }));
      
      // Start streaming for new response
      const tempResponseId = `regenerate-${Date.now()}`;
      get().startStreaming(currentSession.id, tempResponseId);
      
      // API call to regenerate response
      await apiService.post(`/chat/sessions/${currentSession.id}/regenerate`, {
        message_id: messageId
      });
      
    } catch (error) {
      console.error('Failed to regenerate response:', error);
      set({ 
        error: 'Failed to regenerate response', 
        isLoading: false 
      });
      
      // End streaming if there was an error
      get().endStreaming();
    }
  },
  
  fetchSource: async (sourceId: string) => {
    try {
      const response = await apiService.get(`/documents/${sourceId}`);
      return response.data;
    } catch (error) {
      console.error(`Failed to fetch source ${sourceId}:`, error);
      return null;
    }
  },
  
  setCurrentSession: async (sessionId: string) => {
    try {
      // Find session in current state
      const session = get().sessions.find(s => s.id === sessionId);
      
      if (session) {
        set({ currentSession: session });
      } else {
        // Fetch session details if not in state
        const response = await apiService.get(`/chat/sessions/${sessionId}`);
        set({ currentSession: response.data });
      }
      
      // Fetch messages for this session
      await get().fetchMessages(sessionId);
    } catch (error) {
      console.error(`Failed to set current session ${sessionId}:`, error);
      set({ error: 'Failed to load chat session' });
    }
  },
  
  clearMessages: () => {
    set({ messages: [] });
  },
  
  deleteSession: async (sessionId: string) => {
    set({ isLoading: true, error: null });
    
    try {
      await apiService.delete(`/chat/sessions/${sessionId}`);
      
      set(state => ({ 
        sessions: state.sessions.filter(session => session.id !== sessionId),
        currentSession: state.currentSession?.id === sessionId ? null : state.currentSession,
        isLoading: false
      }));
      
      // Clear messages if the deleted session was the current one
      if (get().currentSession === null) {
        get().clearMessages();
      }
    } catch (error) {
      console.error(`Failed to delete session ${sessionId}:`, error);
      set({ 
        error: 'Failed to delete chat session', 
        isLoading: false 
      });
    }
  },
  
  renameSession: async (sessionId: string, title: string) => {
    set({ isLoading: true, error: null });
    
    try {
      const response = await apiService.patch(`/chat/sessions/${sessionId}`, { title });
      const updatedSession = response.data;
      
      set(state => ({ 
        sessions: state.sessions.map(session => 
          session.id === sessionId ? updatedSession : session
        ),
        currentSession: state.currentSession?.id === sessionId ? updatedSession : state.currentSession,
        isLoading: false
      }));
    } catch (error) {
      console.error(`Failed to rename session ${sessionId}:`, error);
      set({ 
        error: 'Failed to rename chat session', 
        isLoading: false 
      });
    }
  },
  
  // Streaming related actions
  setupStreamListeners: () => {
    // Connect to websocket if not already connected
    if (!websocketService.isConnected()) {
      websocketService.connect();
    }
    
    // Message stream handler
    const handleMessageStream = (data: any) => {
      if (data.type === 'start') {
        // Update streaming state with real message ID
        const { message_id, session_id } = data;
        get().startStreaming(session_id, message_id);
      } 
      else if (data.type === 'content') {
        // Update streaming content
        get().updateStreamContent(data.content);
      }
      else if (data.type === 'end') {
        // End streaming and set final response
        get().endStreaming(data.content);
        
        // Add the completed message with sources
        set(state => ({
          messages: [...state.messages, {
            id: data.message_id,
            session_id: data.session_id,
            role: 'assistant',
            content: data.content,
            created_at: new Date().toISOString(),
            sources: data.sources,
            citations: data.citations
          }],
          isLoading: false
        }));
      }
      else if (data.type === 'error') {
        // Handle error
        const notificationStore = useNotificationStore.getState();
        notificationStore.addNotification({
          type: 'error',
          title: 'Chat Error',
          message: data.error || 'An error occurred while generating a response'
        });
        
        get().endStreaming();
        set({ error: data.error, isLoading: false });
      }
    };
    
    // Subscribe to message stream
    websocketService.onMessage('chat_message', handleMessageStream);
  },
  
  cleanupStreamListeners: () => {
    // This will be implemented when we have proper unsubscribe functionality
    // For now, it's a placeholder
  },
  
  startStreaming: (sessionId: string, responseId: string) => {
    // Set streaming state
    set({ 
      streaming: {
        isStreaming: true,
        sessionId,
        responseId,
        streamedContent: ''
      }
    });
    
    // Add placeholder message for UI
    set(state => ({
      messages: [...state.messages, {
        id: responseId,
        session_id: sessionId,
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      }]
    }));
  },
  
  endStreaming: (finalContent?: string) => {
    const { streaming, messages } = get();
    
    if (!streaming.isStreaming) return;
    
    // If final content is provided, update the message
    if (finalContent && streaming.responseId) {
      set({
        messages: messages.map(msg => 
          msg.id === streaming.responseId
            ? { ...msg, content: finalContent }
            : msg
        )
      });
    }
    
    // Reset streaming state
    set({ 
      streaming: {
        isStreaming: false,
        sessionId: null,
        responseId: null,
        streamedContent: ''
      },
      isLoading: false
    });
  },
  
  updateStreamContent: (content: string) => {
    const { streaming, messages } = get();
    
    if (!streaming.isStreaming) return;
    
    // Update streaming content
    set({ 
      streaming: {
        ...streaming,
        streamedContent: content
      }
    });
    
    // Update message content
    if (streaming.responseId) {
      set({
        messages: messages.map(msg => 
          msg.id === streaming.responseId
            ? { ...msg, content }
            : msg
        )
      });
    }
  }
}));

// Initialize WebSocket listeners when store is first loaded
if (typeof window !== 'undefined') {
  setTimeout(() => {
    useChatStore.getState().setupStreamListeners();
  }, 1000);
}