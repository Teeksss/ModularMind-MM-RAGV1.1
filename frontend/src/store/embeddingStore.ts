import { create } from 'zustand';
import { apiService } from '../services/api';
import { useNotificationStore } from './notificationStore';

interface EmbeddingModel {
  name: string;
  model_id: string;
  type: string;
  dimension: number;
  device: string;
  is_loaded: boolean;
  is_default: boolean;
  max_sequence_length: number;
  metadata: Record<string, any>;
}

interface EmbeddingCache {
  [key: string]: {
    text: string;
    model: string;
    embedding: number[];
    timestamp: number;
  };
}

interface EmbeddingStore {
  // State
  models: EmbeddingModel[];
  availableModels: string[];
  defaultModel: string | null;
  selectedModel: string | null;
  isLoading: boolean;
  isGenerating: boolean;
  cache: EmbeddingCache;
  cacheTTL: number; // In milliseconds
  
  // Actions
  fetchModels: () => Promise<void>;
  generateEmbedding: (text: string, model?: string) => Promise<number[]>;
  generateBatchEmbeddings: (texts: string[], model?: string) => Promise<number[][]>;
  computeSimilarity: (text1: string, text2: string, model?: string) => Promise<number>;
  computeBatchSimilarity: (texts1: string[], texts2: string[], model?: string) => Promise<number[]>;
  setSelectedModel: (model: string) => void;
  clearCache: () => void;
}

export const useEmbeddingStore = create<EmbeddingStore>((set, get) => ({
  // Initial state
  models: [],
  availableModels: [],
  defaultModel: null,
  selectedModel: null,
  isLoading: false,
  isGenerating: false,
  cache: {},
  cacheTTL: 30 * 60 * 1000, // 30 minutes
  
  // Actions
  fetchModels: async () => {
    set({ isLoading: true });
    
    try {
      const response = await apiService.get('/models');
      const { models, default_model } = response.data;
      
      set({
        models: models,
        availableModels: models.map((model: EmbeddingModel) => model.name),
        defaultModel: default_model,
        selectedModel: default_model,
        isLoading: false
      });
    } catch (error) {
      console.error('Failed to fetch embedding models:', error);
      useNotificationStore.getState().addNotification({
        type: 'error',
        title: 'Failed to load models',
        message: error.message || 'An error occurred while loading embedding models'
      });
      set({ isLoading: false });
    }
  },
  
  generateEmbedding: async (text: string, model?: string) => {
    const state = get();
    const modelToUse = model || state.selectedModel || state.defaultModel;
    
    if (!modelToUse) {
      throw new Error('No embedding model selected or available');
    }
    
    // Check cache first
    const cacheKey = `${text}:${modelToUse}`;
    const cachedItem = state.cache[cacheKey];
    
    if (cachedItem && (Date.now() - cachedItem.timestamp) < state.cacheTTL) {
      return cachedItem.embedding;
    }
    
    // Generate new embedding
    set({ isGenerating: true });
    
    try {
      const response = await apiService.post('/embeddings', {
        texts: text,
        model: modelToUse
      });
      
      const embedding = response.data.embeddings[0];
      
      // Update cache
      set(state => ({
        cache: {
          ...state.cache,
          [cacheKey]: {
            text,
            model: modelToUse,
            embedding,
            timestamp: Date.now()
          }
        },
        isGenerating: false
      }));
      
      return embedding;
    } catch (error) {
      console.error('Failed to generate embedding:', error);
      set({ isGenerating: false });
      throw error;
    }
  },
  
  generateBatchEmbeddings: async (texts: string[], model?: string) => {
    const state = get();
    const modelToUse = model || state.selectedModel || state.defaultModel;
    
    if (!modelToUse) {
      throw new Error('No embedding model selected or available');
    }
    
    // Check if all are in cache
    const allCached = texts.every(text => {
      const cacheKey = `${text}:${modelToUse}`;
      const cachedItem = state.cache[cacheKey];
      return cachedItem && (Date.now() - cachedItem.timestamp) < state.cacheTTL;
    });
    
    if (allCached) {
      return texts.map(text => {
        const cacheKey = `${text}:${modelToUse}`;
        return state.cache[cacheKey].embedding;
      });
    }
    
    // Generate new embeddings
    set({ isGenerating: true });
    
    try {
      const response = await apiService.post('/embeddings', {
        texts: texts,
        model: modelToUse
      });
      
      const embeddings = response.data.embeddings;
      
      // Update cache
      const newCache = { ...state.cache };
      for (let i = 0; i < texts.length; i++) {
        const cacheKey = `${texts[i]}:${modelToUse}`;
        newCache[cacheKey] = {
          text: texts[i],
          model: modelToUse,
          embedding: embeddings[i],
          timestamp: Date.now()
        };
      }
      
      set({ cache: newCache, isGenerating: false });
      
      return embeddings;
    } catch (error) {
      console.error('Failed to generate batch embeddings:', error);
      set({ isGenerating: false });
      throw error;
    }
  },
  
  computeSimilarity: async (text1: string, text2: string, model?: string) => {
    const state = get();
    const modelToUse = model || state.selectedModel || state.defaultModel;
    
    if (!modelToUse) {
      throw new Error('No embedding model selected or available');
    }
    
    try {
      const response = await apiService.post('/embeddings/similarity', {
        texts1: [text1],
        texts2: [text2],
        model: modelToUse
      });
      
      return response.data.similarities[0];
    } catch (error) {
      console.error('Failed to compute similarity:', error);
      throw error;
    }
  },
  
  computeBatchSimilarity: async (texts1: string[], texts2: string[], model?: string) => {
    if (texts1.length !== texts2.length) {
      throw new Error('texts1 and texts2 must have the same length');
    }
    
    const state = get();
    const modelToUse = model || state.selectedModel || state.defaultModel;
    
    if (!modelToUse) {
      throw new Error('No embedding model selected or available');
    }
    
    try {
      const response = await apiService.post('/embeddings/similarity', {
        texts1: texts1,
        texts2: texts2,
        model: modelToUse
      });
      
      return response.data.similarities;
    } catch (error) {
      console.error('Failed to compute batch similarity:', error);
      throw error;
    }
  },
  
  setSelectedModel: (model: string) => {
    set({ selectedModel: model });
  },
  
  clearCache: () => {
    set({ cache: {} });
  }
}));