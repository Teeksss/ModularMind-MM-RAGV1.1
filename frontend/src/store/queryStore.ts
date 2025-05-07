import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import { apiClient } from '../services/api';
import { showToast } from '../utils/notifications';

export interface Source {
  id: string;
  title: string;
  url?: string;
  content_type: string;
  score: number;
  metadata: Record<string, any>;
}

export interface QueryResult {
  answer: string;
  sources: Source[];
  processing_time: number;
  token_usage?: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

export interface QueryEntry {
  id: string;
  query: string;
  timestamp: string;
  result?: QueryResult;
  session_id: string;
}

export interface QueryRequest {
  query: string;
  sessionId: string;
  language?: string;
  maxResults?: number;
  includeSourceContent?: boolean;
}

interface QueryState {
  queries: QueryEntry[];
  currentQuery: string;
  isLoading: boolean;
  currentResult: QueryResult | null;
  error: string | null;
  
  setCurrentQuery: (query: string) => void;
  sendQuery: (request: QueryRequest) => Promise<void>;
  clearCurrentResult: () => void;
  clearHistory: () => void;
  clearError: () => void;
}

export const useQueryStore = create<QueryState>()(
  persist(
    (set, get) => ({
      queries: [],
      currentQuery: '',
      isLoading: false,
      currentResult: null,
      error: null,
      
      setCurrentQuery: (query: string) => set({ currentQuery: query }),
      
      sendQuery: async (request: QueryRequest) => {
        const { query, sessionId, language, maxResults, includeSourceContent } = request;
        
        // Create a new query entry
        const queryEntry: QueryEntry = {
          id: uuidv4(),
          query,
          timestamp: new Date().toISOString(),
          session_id: sessionId,
        };
        
        try {
          set({ isLoading: true, error: null });
          
          // Add to history immediately
          set(state => ({
            queries: [queryEntry, ...state.queries],
            currentQuery: ''
          }));
          
          // Make API call
          const response = await apiClient.post<QueryResult>('/queries', {
            query,
            session_id: sessionId,
            language: language || 'tr',
            max_results: maxResults || 5,
            include_source_content: includeSourceContent ?? true,
          });
          
          // Update entry with result
          set(state => ({
            queries: state.queries.map(q => 
              q.id === queryEntry.id ? { ...q, result: response.data } : q
            ),
            currentResult: response.data,
            isLoading: false
          }));
          
        } catch (error) {
          console.error('Error sending query:', error);
          const errorMessage = error instanceof Error ? error.message : 'An error occurred';
          
          // Mark as failed in history
          set(state => ({
            queries: state.queries.map(q => 
              q.id === queryEntry.id ? { ...q, error: errorMessage } : q
            ),
            error: errorMessage,
            isLoading: false
          }));
          
          showToast('error', 'Sorgu işlenirken bir hata oluştu');
          throw error;
        }
      },
      
      clearCurrentResult: () => set({ currentResult: null }),
      
      clearHistory: () => set({ queries: [] }),
      
      clearError: () => set({ error: null })
    }),
    {
      name: 'modularmind-query-storage',
      partialize: (state) => ({ 
        queries: state.queries.slice(0, 20) // Only store last 20 queries
      }),
    }
  )
);