import { useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { api } from '../services/api';
import { useAuthStore } from '../store/authStore';

export interface MemorySession {
  id: string;
  user_id: string;
  created_at: string;
  last_used: string;
  metadata: Record<string, any>;
}

export interface MemoryItem {
  id: string;
  session_id: string;
  type: 'query' | 'response' | 'document' | 'system';
  content: string;
  created_at: string;
  metadata?: Record<string, any>;
}

interface UseSessionMemoryReturn {
  sessionId: string | null;
  isLoading: boolean;
  error: string | null;
  sessionItems: MemoryItem[];
  createSession: () => Promise<string>;
  addToSession: (type: 'query' | 'response' | 'document' | 'system', content: string, metadata?: Record<string, any>) => Promise<void>;
  clearSession: () => Promise<void>;
  loadSessionItems: () => Promise<void>;
}

export const useSessionMemory = (): UseSessionMemoryReturn => {
  const { isLoggedIn } = useAuthStore();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionItems, setSessionItems] = useState<MemoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Initialize or load session from storage
  useEffect(() => {
    if (isLoggedIn) {
      const storedSessionId = localStorage.getItem('current_session_id');
      if (storedSessionId) {
        setSessionId(storedSessionId);
        loadSessionItems(storedSessionId);
      }
    }
  }, [isLoggedIn]);

  // Create a new session
  const createSession = async (): Promise<string> => {
    if (!isLoggedIn) {
      throw new Error('User must be logged in to create a session');
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post<{ session_id: string }>('/memory/sessions');
      const newSessionId = response.data.session_id;
      
      // Store session ID
      setSessionId(newSessionId);
      localStorage.setItem('current_session_id', newSessionId);
      
      // Clear items for new session
      setSessionItems([]);
      
      return newSessionId;
    } catch (error) {
      const errorMessage = error.message || 'Failed to create session';
      setError(errorMessage);
      throw new Error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Load session items
  const loadSessionItems = async (targetSessionId?: string): Promise<void> => {
    const sessionToLoad = targetSessionId || sessionId;
    
    if (!sessionToLoad || !isLoggedIn) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get<MemoryItem[]>(`/memory/sessions/${sessionToLoad}/items`);
      // Sort by creation time (oldest first)
      const sortedItems = response.data.sort((a, b) => 
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      );
      setSessionItems(sortedItems);
    } catch (error) {
      const errorMessage = error.message || 'Failed to load session items';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Add item to session
  const addToSession = async (
    type: 'query' | 'response' | 'document' | 'system', 
    content: string, 
    metadata?: Record<string, any>
  ): Promise<void> => {
    if (!sessionId || !isLoggedIn) {
      // Create a session if none exists
      try {
        const newSessionId = await createSession();
        setSessionId(newSessionId);
      } catch (error) {
        return;
      }
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await api.post<{ item_id: string }>(`/memory/sessions/${sessionId}/items`, {
        type,
        content,
        metadata
      });

      // Add to local state with optimistic update
      const newItem: MemoryItem = {
        id: response.data.item_id,
        session_id: sessionId!,
        type,
        content,
        created_at: new Date().toISOString(),
        metadata
      };

      setSessionItems(prev => [...prev, newItem]);
    } catch (error) {
      const errorMessage = error.message || 'Failed to add item to session';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Clear session
  const clearSession = async (): Promise<void> => {
    if (!sessionId || !isLoggedIn) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await api.delete(`/memory/sessions/${sessionId}/items`);
      setSessionItems([]);
    } catch (error) {
      const errorMessage = error.message || 'Failed to clear session';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return {
    sessionId,
    isLoading,
    error,
    sessionItems,
    createSession,
    addToSession,
    clearSession,
    loadSessionItems: useCallback(() => loadSessionItems(), [sessionId, isLoggedIn])
  };
};