// Embedding API için ek metotlar
export const embeddingApi = {
  // ... mevcut metotlar ...
  
  // Varsayılan embedding modelini ayarla
  setDefaultModel: async (modelId: string): Promise<boolean> => {
    try {
      const response = await apiClient.post('/embed/set-default-model', {
        model_id: modelId
      })
      return response.data.success
    } catch (err) {
      if (axios.isAxiosError(err)) {
        throw new Error(`Varsayılan model ayarlama hatası: ${err.response?.data?.detail || err.message}`)
      }
      throw new Error('Varsayılan model ayarlama hatası')
    }
  },
  
  // Model ekle veya güncelle
  updateModel: async (modelConfig: any, setAsDefault: boolean = false): Promise<any> => {
    try {
      const response = await apiClient.post('/embed/update-model', {
        model_config: modelConfig,
        set_as_default: setAsDefault
      })
      return response.data
    } catch (err) {
      if (axios.isAxiosError(err)) {
        throw new Error(`Model güncelleme hatası: ${err.response?.data?.detail || err.message}`)
      }
      throw new Error('Model güncelleme hatası')
    }
  }
}

// RAG API için ek metotlar
export const ragApi = {
  // ... mevcut metotlar ...
  
  // Modelleri listele
  getModels: async (): Promise<any> => {
    try {
      const response = await apiClient.get('/rag/models')
      return response.data
    } catch (err) {
      if (axios.isAxiosError(err)) {
        throw new Error(`Model listesi hatası: ${err.response?.data?.detail || err.message}`)
      }
      throw new Error('Model listesi hatası')
    }
  },
  
  // Embedding kapsamını getir
  getEmbeddingCoverage: async (): Promise<any> => {
    try {
      const response = await apiClient.get('/rag/embedding-coverage')
      return response.data
    } catch (err) {
      if (axios.isAxiosError(err)) {
        throw new Error(`Embedding kapsamı hatası: ${err.response?.data?.detail || err.message}`)
      }
      throw new Error('Embedding kapsamı hatası')
    }
  },
  
  // Model indeksini yeniden oluştur
  rebuildModelIndex: async (modelId: string): Promise<boolean> => {
    try {
      const response = await apiClient.post('/admin/rebuild-model-index', {
        model_id: modelId
      })
      return response.data.success
    } catch (err) {
      if (axios.isAxiosError(err)) {
        throw new Error(`İndeks yenileme hatası: ${err.response?.data?.detail || err.message}`)
      }
      throw new Error('İndeks yenileme hatası')
    }
  }
}