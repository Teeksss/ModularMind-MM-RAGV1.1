import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import { llmApi, embeddingApi } from './api'

interface AppState {
  // Tema
  isDarkMode: boolean
  toggleDarkMode: () => void
  
  // LLM Modeller
  llmModels: any[]
  currentLLMModel: string
  embeddingModels: any[]
  currentEmbeddingModel: string
  
  // Ayarlar
  settings: {
    ragEnabled: boolean
    chunkSize: number
    chunkOverlap: number
    systemMessage: string
    apiEndpoint: string
  }
  
  // Yükleme ve hata
  isLoading: boolean
  setLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
  
  // İşlevler
  fetchModels: () => Promise<void>
  updateSettings: (settings: Partial<AppState['settings']>) => void
  setCurrentLLMModel: (modelId: string) => void
  setCurrentEmbeddingModel: (modelId: string) => void
}

// Mağaza oluştur
export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Varsayılan değerler
      isDarkMode: false,
      toggleDarkMode: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
      
      llmModels: [],
      currentLLMModel: 'gpt-4o',
      embeddingModels: [],
      currentEmbeddingModel: 'openai',
      
      settings: {
        ragEnabled: false,
        chunkSize: 500,
        chunkOverlap: 50,
        systemMessage: 'Yardımcı bir AI asistanısın.',
        apiEndpoint: '/api'
      },
      
      isLoading: false,
      setLoading: (loading) => set({ isLoading: loading }),
      error: null,
      setError: (error) => set({ error }),
      
      fetchModels: async () => {
        try {
          set({ isLoading: true, error: null })
          
          // Modelleri paralel olarak getir
          const [llmModelsResult, embeddingModelsResult] = await Promise.all([
            llmApi.getModels(),
            embeddingApi.getModels()
          ])
          
          set({ 
            llmModels: llmModelsResult, 
            embeddingModels: embeddingModelsResult,
            isLoading: false 
          })
        } catch (err) {
          set({ 
            isLoading: false, 
            error: err instanceof Error ? err.message : 'Modeller yüklenemedi' 
          })
        }
      },
      
      updateSettings: (newSettings) => set((state) => ({
        settings: { ...state.settings, ...newSettings }
      })),
      
      setCurrentLLMModel: (modelId) => set({ currentLLMModel: modelId }),
      setCurrentEmbeddingModel: (modelId) => set({ currentEmbeddingModel: modelId })
    }),
    {
      name: 'modularmind-storage',
      partialize: (state) => ({
        isDarkMode: state.isDarkMode,
        currentLLMModel: state.currentLLMModel,
        currentEmbeddingModel: state.currentEmbeddingModel,
        settings: state.settings
      })
    }
  )
)