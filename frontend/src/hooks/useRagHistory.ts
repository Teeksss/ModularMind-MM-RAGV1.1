import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

interface HistoryItem {
  query_id: string;
  timestamp: string;
  query: string;
  response: string;
  latency_ms: number;
  metrics?: {
    precision?: number;
    recall?: number;
    faithfulness?: number;
  };
  feedback?: {
    rating: number;
    comment?: string;
  };
}

export function useRagHistory() {
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  
  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/api/v1/rag/history');
      
      if (response.data && response.data.queries) {
        setHistory(response.data.queries);
      } else {
        setHistory([]);
      }
    } catch (err) {
      console.error('History fetch error:', err);
      setError(err instanceof Error ? err : new Error('RAG history fetch error'));
      setHistory([]);
    } finally {
      setIsLoading(false);
    }
  }, []);
  
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);
  
  return {
    history,
    isLoading,
    error,
    refresh: fetchHistory
  };
}