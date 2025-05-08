import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { embeddingApi, ragApi } from './api'

export interface EmbeddingModel {
  id: string
  name?: string
  provider?: string
  dimensions: number
  embedding_count: number
  is_default: boolean
}

export interface DocumentCoverage {
  id: string
  title: string
  coverage: Record<string, number>
  totalChunks: number
}

interface EmbeddingState {
  models: EmbeddingModel[]
  defaultModelId: string
  isLoading: boolean
  error: string | null
  documentCoverage: DocumentCoverage[]
  selectedModelIds: string[]
  
  // Actions
  fetchModels: () => Promise<void>
  setDefaultModel: (modelId: string) => Promise<void>
  fetchCoverage: () => Promise<void>
  rebuildIndex: (modelId: string) => Promise<void>
  selectModel: (modelId: string) => void
  unselectModel: (modelId: string) => void
  toggleModelSelection: (modelId: string) => void
  selectMultipleModels: (modelIds: string[]) => void
  clearModelSelection: () => void
}

export const useEmbeddingStore = create<EmbeddingState>()(
  persist(
    (set, get) => ({
      models: [],
      defaultModelId: '',
      isLoading: false,
      error: null,
      documentCoverage: [],
      selectedModelIds: [],
      
      fetchModels: async () => {
        try {
          set({ isLoading: true, error: null })
          
          // Modelleri al
          const response = await ragApi.getModels()
          set({ 
            models: response.models,
            defaultModelId: response.models.find(m => m.is_default)?.id || ''
          })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Model listesi alınamadı' })
        } finally {
          set({ isLoading: false })
        }
      },
      
      setDefaultModel: async (modelId: string) => {
        try {
          set({ isLoading: true, error: null })
          
          // Varsayılan modeli ayarla
          await embeddingApi.setDefaultModel(modelId)
          
          // Modelleri güncelle
          const updatedModels = get().models.map(model => ({
            ...model,
            is_default: model.id === modelId
          }))
          
          set({ 
            models: updatedModels,
            defaultModelId: modelId
          })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Varsayılan model değiştirilemedi' })
        } finally {
          set({ isLoading: false })
        }
      },
      
      fetchCoverage: async () => {
        try {
          set({ isLoading: true, error: null })
          
          // Kapsam verilerini al
          const response = await ragApi.getEmbeddingCoverage()
          
          // Verileri DocumentCoverage formatına dönüştür
          const coverage: DocumentCoverage[] = []
          
          Object.entries(response.coverage).forEach(([docId, data]: [string, any]) => {
            coverage.push({
              id: docId,
              title: data.title || docId,
              coverage: Object.fromEntries(
                Object.entries(data).filter(([key]) => key !== 'title' && key !== 'total_chunks')
              ),
              totalChunks: data.total_chunks || 0
            })
          })
          
          set({ documentCoverage: coverage })
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Kapsam bilgisi alınamadı' })
        } finally {
          set({ isLoading: false })
        }
      },
      
      rebuildIndex: async (modelId: string) => {
        try {
          set({ isLoading: true, error: null })
          
          // İndeksi yeniden oluştur
          await ragApi.rebuildModelIndex(modelId)
          
          // İstatistikleri güncelle
          await get().fetchModels()
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'İndeks yeniden oluşturulamadı' })
        } finally {
          set({ isLoading: false })
        }
      },
      
      selectModel: (modelId: string) => {
        const { selectedModelIds } = get()
        if (!selectedModelIds.includes(modelId)) {
          set({ selectedModelIds: [...selectedModelIds, modelId] })
        }
      },
      
      unselectModel: (modelId: string) => {
        const { selectedModelIds } = get()
        set({ selectedModelIds: selectedModelIds.filter(id => id !== modelId) })
      },
      
      toggleModelSelection: (modelId: string) => {
        const { selectedModelIds } = get()
        if (selectedModelIds.includes(modelId)) {
          set({ selectedModelIds: selectedModelIds.filter(id => id !== modelId) })
        } else {
          set({ selectedModelIds: [...selectedModelIds, modelId] })
        }
      },
      
      selectMultipleModels: (modelIds: string[]) => {
        set({ selectedModelIds: modelIds })
      },
      
      clearModelSelection: () => {
        set({ selectedModelIds: [] })
      }
    }),
    {
      name: 'modularmind-embedding-store',
      partialize: (state) => ({ 
        selectedModelIds: state.selectedModelIds,
        defaultModelId: state.defaultModelId
      })
    }
  )
)