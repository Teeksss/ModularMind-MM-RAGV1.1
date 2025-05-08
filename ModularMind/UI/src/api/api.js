/**
 * ModularMind API istemcisi.
 */

import axios from 'axios';

// API URL
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// API istemcisi
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// API anahtarını ayarla
export const setApiKey = (apiKey) => {
  if (apiKey) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${apiKey}`;
    localStorage.setItem('mm_api_key', apiKey);
    return true;
  }
  return false;
};

// Saklanan API anahtarını yükle
export const loadApiKey = () => {
  const apiKey = localStorage.getItem('mm_api_key');
  if (apiKey) {
    setApiKey(apiKey);
    return true;
  }
  return false;
};

// API anahtarını kaldır
export const clearApiKey = () => {
  delete apiClient.defaults.headers.common['Authorization'];
  localStorage.removeItem('mm_api_key');
};

// API durumunu kontrol et
export const checkApiStatus = async () => {
  try {
    const response = await apiClient.get('/health');
    return response.data;
  } catch (error) {
    throw new Error('API bağlantı hatası: ' + (error.response?.data?.detail || error.message));
  }
};

// Embedding API
export const embeddingApi = {
  // Metin için embedding
  getEmbedding: async (text, model = null) => {
    try {
      const response = await apiClient.post('/embed/embed', {
        text,
        model
      });
      return response.data;
    } catch (error) {
      throw new Error('Embedding hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Çoklu metin için embedding
  getBatchEmbeddings: async (texts, model = null) => {
    try {
      const response = await apiClient.post('/embed/embed_batch', {
        texts,
        model
      });
      return response.data;
    } catch (error) {
      throw new Error('Batch embedding hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Metin benzerliği hesaplama
  calculateSimilarity: async (text1, text2, model = null) => {
    try {
      const response = await apiClient.post('/embed/similarity', {
        text1,
        text2,
        model
      });
      return response.data;
    } catch (error) {
      throw new Error('Benzerlik hesaplama hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Embedding modelleri listesi
  getModels: async () => {
    try {
      const response = await apiClient.get('/embed/models');
      return response.data.models;
    } catch (error) {
      throw new Error('Embedding modelleri listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// LLM API
export const llmApi = {
  // Metin tamamlama
  completeText: async (prompt, model = null, options = {}) => {
    try {
      const response = await apiClient.post('/llm/complete', {
        prompt,
        model,
        max_tokens: options.max_tokens,
        temperature: options.temperature,
        top_p: options.top_p,
        stop_sequences: options.stop_sequences,
        system_message: options.system_message,
        stream: false
      });
      return response.data;
    } catch (error) {
      throw new Error('Metin tamamlama hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Streaming metin tamamlama
  streamingComplete: (prompt, callback, model = null, options = {}) => {
    const source = new EventSource(
      `${API_URL}/llm/complete?` + 
      new URLSearchParams({
        prompt,
        model: model || '',
        max_tokens: options.max_tokens || 500,
        temperature: options.temperature || 0.7,
        top_p: options.top_p || 1.0,
        system_message: options.system_message || '',
        stream: true
      })
    );
    
    source.onmessage = (event) => {
      if (event.data === '[DONE]') {
        source.close();
        callback(null, true);
      } else {
        callback(event.data, false);
      }
    };
    
    source.onerror = (error) => {
      source.close();
      callback(null, true, error);
    };
    
    return () => source.close();
  },
  
  // Sohbet tamamlama
  chatCompletion: async (messages, model = null, options = {}) => {
    try {
      const response = await apiClient.post('/llm/chat', {
        messages,
        model,
        max_tokens: options.max_tokens,
        temperature: options.temperature,
        top_p: options.top_p,
        stop_sequences: options.stop_sequences,
        stream: false
      });
      return response.data;
    } catch (error) {
      throw new Error('Sohbet tamamlama hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Streaming sohbet tamamlama
  streamingChat: (messages, callback, model = null, options = {}) => {
    const source = new EventSource(
      `${API_URL}/llm/chat?` + 
      new URLSearchParams({
        messages: JSON.stringify(messages),
        model: model || '',
        max_tokens: options.max_tokens || 500,
        temperature: options.temperature || 0.7,
        top_p: options.top_p || 1.0,
        stream: true
      })
    );
    
    source.onmessage = (event) => {
      if (event.data === '[DONE]') {
        source.close();
        callback(null, true);
      } else {
        callback(event.data, false);
      }
    };
    
    source.onerror = (error) => {
      source.close();
      callback(null, true, error);
    };
    
    return () => source.close();
  },
  
  // Şablon ile tamamlama
  templateCompletion: async (templateId, variables, model = null, options = {}) => {
    try {
      const response = await apiClient.post('/llm/template', {
        template_id: templateId,
        variables,
        model,
        max_tokens: options.max_tokens,
        temperature: options.temperature
      });
      return response.data;
    } catch (error) {
      throw new Error('Şablon tamamlama hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // LLM modelleri listesi
  getModels: async () => {
    try {
      const response = await apiClient.get('/llm/models');
      return response.data.models;
    } catch (error) {
      throw new Error('LLM modelleri listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Şablonlar listesi
  getTemplates: async () => {
    try {
      const response = await apiClient.get('/llm/templates');
      return response.data.templates;
    } catch (error) {
      throw new Error('Şablonlar listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// RAG API
export const ragApi = {
  // Belge ekleme
  addDocument: async (document, options = {}) => {
    try {
      const response = await apiClient.post('/rag/documents', {
        document,
        chunk_size: options.chunk_size,
        chunk_overlap: options.chunk_overlap,
        metadata: options.metadata,
        embedding_model: options.embedding_model
      });
      return response.data;
    } catch (error) {
      throw new Error('Belge ekleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Dosya yükleme
  uploadFile: async (file, options = {}) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (options.chunk_size) {
        formData.append('chunk_size', options.chunk_size);
      }
      
      if (options.chunk_overlap) {
        formData.append('chunk_overlap', options.chunk_overlap);
      }
      
      if (options.embedding_model) {
        formData.append('embedding_model', options.embedding_model);
      }
      
      const response = await apiClient.post('/rag/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      return response.data;
    } catch (error) {
      throw new Error('Dosya yükleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Arama
  search: async (query, options = {}) => {
    try {
      const response = await apiClient.post('/rag/search', {
        query,
        limit: options.limit,
        filter_metadata: options.filter_metadata,
        include_metadata: options.include_metadata,
        min_score_threshold: options.min_score_threshold,
        embedding_model: options.embedding_model,
        search_type: options.search_type || 'hybrid'
      });
      return response.data;
    } catch (error) {
      throw new Error('Arama hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // RAG sorgusu
  query: async (query, options = {}) => {
    try {
      const response = await apiClient.post('/rag/query', {
        query,
        context_limit: options.context_limit,
        filter_metadata: options.filter_metadata,
        include_sources: options.include_sources,
        llm_model: options.llm_model,
        embedding_model: options.embedding_model,
        system_message: options.system_message
      });
      return response.data;
    } catch (error) {
      throw new Error('RAG sorgu hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Belge bilgisi
  getDocument: async (documentId) => {
    try {
      const response = await apiClient.get(`/rag/documents/${documentId}`);
      return response.data;
    } catch (error) {
      throw new Error('Belge alma hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Belgeleri listele
  listDocuments: async (options = {}) => {
    try {
      const params = new URLSearchParams();
      
      if (options.limit) {
        params.append('limit', options.limit);
      }
      
      if (options.offset) {
        params.append('offset', options.offset);
      }
      
      if (options.filter_metadata) {
        params.append('filter_metadata', JSON.stringify(options.filter_metadata));
      }
      
      const response = await apiClient.get(`/rag/documents?${params}`);
      return response.data;
    } catch (error) {
      throw new Error('Belge listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Belge silme
  deleteDocument: async (documentId) => {
    try {
      const response = await apiClient.delete(`/rag/documents/${documentId}`);
      return response.data;
    } catch (error) {
      throw new Error('Belge silme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // İstatistikler
  getStats: async () => {
    try {
      const response = await apiClient.get('/rag/stats');
      return response.data.stats;
    } catch (error) {
      throw new Error('İstatistikler alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// Ajan API
export const agentApi = {
  // Ajan ekleme
  createAgent: async (agentConfig) => {
    try {
      const response = await apiClient.post('/agents', agentConfig);
      return response.data;
    } catch (error) {
      throw new Error('Ajan ekleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan listesi
  listAgents: async () => {
    try {
      const response = await apiClient.get('/agents');
      return response.data.agents;
    } catch (error) {
      throw new Error('Ajan listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan detayı
  getAgent: async (agentId) => {
    try {
      const response = await apiClient.get(`/agents/${agentId}`);
      return response.data;
    } catch (error) {
      throw new Error('Ajan detayı alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan güncelleme
  updateAgent: async (agentId, agentConfig) => {
    try {
      const response = await apiClient.put(`/agents/${agentId}`, agentConfig);
      return response.data;
    } catch (error) {
      throw new Error('Ajan güncelleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan silme
  deleteAgent: async (agentId) => {
    try {
      const response = await apiClient.delete(`/agents/${agentId}`);
      return response.data;
    } catch (error) {
      throw new Error('Ajan silme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan çalıştırma
  runAgent: async (agentId, sync = false) => {
    try {
      const response = await apiClient.post(`/agents/${agentId}/run?sync=${sync}`);
      return response.data;
    } catch (error) {
      throw new Error('Ajan çalıştırma hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan durumu
  getAgentStatus: async (agentId) => {
    try {
      const response = await apiClient.get(`/agents/${agentId}/status`);
      return response.data;
    } catch (error) {
      throw new Error('Ajan durumu alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Ajan sonucu
  getAgentResult: async (agentId) => {
    try {
      const response = await apiClient.get(`/agents/${agentId}/result`);
      return response.data;
    } catch (error) {
      throw new Error('Ajan sonucu alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// Konnektör API
export const connectorApi = {
  // Konnektör ekleme
  createConnector: async (connectorConfig) => {
    try {
      const response = await apiClient.post('/connectors', connectorConfig);
      return response.data;
    } catch (error) {
      throw new Error('Konnektör ekleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör listesi
  listConnectors: async () => {
    try {
      const response = await apiClient.get('/connectors');
      return response.data.connectors;
    } catch (error) {
      throw new Error('Konnektör listesi alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör detayı
  getConnector: async (connectorId) => {
    try {
      const response = await apiClient.get(`/connectors/${connectorId}`);
      return response.data;
    } catch (error) {
      throw new Error('Konnektör detayı alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör güncelleme
  updateConnector: async (connectorId, connectorConfig) => {
    try {
      const response = await apiClient.put(`/connectors/${connectorId}`, connectorConfig);
      return response.data;
    } catch (error) {
      throw new Error('Konnektör güncelleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör silme
  deleteConnector: async (connectorId) => {
    try {
      const response = await apiClient.delete(`/connectors/${connectorId}`);
      return response.data;
    } catch (error) {
      throw new Error('Konnektör silme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör sorgusu
  executeQuery: async (connectorId, query, params = null) => {
    try {
      const response = await apiClient.post(`/connectors/${connectorId}/query`, {
        query,
        params
      });
      return response.data;
    } catch (error) {
      throw new Error('Konnektör sorgu hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör bağlantı testi
  testConnection: async (connectorId) => {
    try {
      const response = await apiClient.get(`/connectors/${connectorId}/test`);
      return response.data;
    } catch (error) {
      throw new Error('Konnektör bağlantı testi hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Konnektör metadata
  getMetadata: async (connectorId) => {
    try {
      const response = await apiClient.get(`/connectors/${connectorId}/metadata`);
      return response.data.metadata;
    } catch (error) {
      throw new Error('Konnektör metadata alma hatası: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// Admin API
export const adminApi = {
  // Sistem istatistikleri
  getSystemStats: async () => {
    try {
      const response = await apiClient.get('/admin/stats');
      return response.data;
    } catch (error) {
      throw new Error('Sistem istatistikleri alınamadı: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Yedekleme
  createBackup: async (options = {}) => {
    try {
      const response = await apiClient.post('/admin/backup', options);
      return response.data;
    } catch (error) {
      throw new Error('Yedekleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Geri yükleme
  restoreBackup: async (backupPath, options = {}) => {
    try {
      const response = await apiClient.post('/admin/restore', {
        backup_path: backupPath,
        ...options
      });
      return response.data;
    } catch (error) {
      throw new Error('Geri yükleme hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // İndeksleri yeniden oluştur
  rebuildIndices: async () => {
    try {
      const response = await apiClient.post('/admin/rebuild_indices');
      return response.data;
    } catch (error) {
      throw new Error('İndeks yeniden oluşturma hatası: ' + (error.response?.data?.detail || error.message));
    }
  },
  
  // Sistemi sıfırla
  resetSystem: async (options = {}) => {
    try {
      const response = await apiClient.post('/admin/reset', null, {
        params: options
      });
      return response.data;
    } catch (error) {
      throw new Error('Sistem sıfırlama hatası: ' + (error.response?.data?.detail || error.message));
    }
  }
};

// Tüm API'leri dışa aktar
export default {
  setApiKey,
  loadApiKey,
  clearApiKey,
  checkApiStatus,
  embedding: embeddingApi,
  llm: llmApi,
  rag: ragApi,
  agent: agentApi,
  connector: connectorApi,
  admin: adminApi
};