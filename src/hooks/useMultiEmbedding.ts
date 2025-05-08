import { useState, useCallback } from 'react'
import { useEmbeddingStore } from '@/lib/embeddingStore'
import { ragApi } from '@/lib/api'

export interface MultiEmbeddingOptions {
  limit?: number
  minScoreThreshold?: number
  filterMetadata?: Record<string, any>
  searchType?: 'vector' | 'text' | 'hybrid'
}

interface MultiEmbeddingState {
  isLoading: boolean
  error: string | null
  results: any[] | null
  modelResults: Record<string, any[]>
}

export function useMultiEmbedding(defaultOptions: MultiEmbeddingOptions = {}) {
  const { models, selectedModelIds } = useEmbeddingStore()
  const [state, setState] = useState<MultiEmbeddingState>({
    isLoading: false,
    error: null,
    results: null,
    modelResults: {}
  })
  
  const search = useCallback(async (
    query: string, 
    modelsToUse: string[] | null = null,
    options: MultiEmbeddingOptions = {}
  ) => {
    try {
      // Hangi modelleri kullanacağımızı belirle
      const modelIds = modelsToUse || selectedModelIds
      
      // En az bir model seçili olmalı
      if (!modelIds.length) {
        setState(prev => ({
          ...prev,
          error: 'En az bir embedding modeli seçmelisiniz',
          isLoading: false
        }))
        return null
      }
      
      // Yükleme durumunu başlat
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      
      // Tüm seçili modeller için arama sonuçları
      const allResults: any[] = []
      const modelResults: Record<string, any[]> = {}
      
      // Seçenekleri birleştir
      const searchOptions = {
        limit: options.limit ?? defaultOptions.limit ?? 5,
        min_score_threshold: options.minScoreThreshold ?? defaultOptions.minScoreThreshold,
        filter_metadata: options.filterMetadata ?? defaultOptions.filterMetadata,
        search_type: options.searchType ?? defaultOptions.searchType ?? 'hybrid'
      }
      
      // Her model için ayrı ayrı arama yap
      for (const modelId of modelIds) {
        try {
          const response = await ragApi.search(query, {
            ...searchOptions,
            embedding_model: modelId
          })
          
          // Her modelden dönen sonuçları modelin kendisiyle işaretle
          const results = response.results.map((r: any) => ({
            ...r,
            model_id: modelId
          }))
          
          // Modele özel sonuçları kaydet
          modelResults[modelId] = results
          
          // Tüm sonuçlara ekle
          allResults.push(...results)
        } catch (modelErr) {
          console.error(`${modelId} ile arama hatası:`, modelErr)
        }
      }
      
      // Sonuçları skora göre sırala
      allResults.sort((a, b) => b.score - a.score)
      
      // Limit uygula
      const limitedResults = allResults.slice(0, searchOptions.limit)
      
      setState({
        isLoading: false,
        error: null,
        results: limitedResults,
        modelResults
      })
      
      return {
        results: limitedResults,
        modelResults
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Çoklu model araması sırasında bir hata oluştu'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false
      }))
      return null
    }
  }, [selectedModelIds, defaultOptions])
  
  // Tek API çağrısı ile çoklu model arama
  const unifiedSearch = useCallback(async (
    query: string,
    modelsToUse: string[] | null = null,
    options: MultiEmbeddingOptions = {}
  ) => {
    try {
      // Hangi modelleri kullanacağımızı belirle
      const modelIds = modelsToUse || selectedModelIds
      
      // En az bir model seçili olmalı
      if (!modelIds.length) {
        setState(prev => ({
          ...prev,
          error: 'En az bir embedding modeli seçmelisiniz',
          isLoading: false
        }))
        return null
      }
      
      // Yükleme durumunu başlat
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      
      // Seçenekleri birleştir
      const searchOptions = {
        limit: options.limit ?? defaultOptions.limit ?? 5,
        min_score_threshold: options.minScoreThreshold ?? defaultOptions.minScoreThreshold,
        filter_metadata: options.filterMetadata ?? defaultOptions.filterMetadata,
        search_type: options.searchType ?? defaultOptions.searchType ?? 'hybrid',
        use_multi_model: true,
        models_to_use: modelIds
      }
      
      // Tek API çağrısı ile çoklu model arama
      const response = await ragApi.search(query, searchOptions)
      
      // Sonuçları modellere göre grupla
      const modelResults: Record<string, any[]> = {}
      
      for (const result of response.results) {
        const modelId = result.model_id || 'unknown'
        
        if (!modelResults[modelId]) {
          modelResults[modelId] = []
        }
        
        modelResults[modelId].push(result)
      }
      
      setState({
        isLoading: false,
        error: null,
        results: response.results,
        modelResults
      })
      
      return {
        results: response.results,
        modelResults
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Çoklu model araması sırasında bir hata oluştu'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false
      }))
      return null
    }
  }, [selectedModelIds, defaultOptions])
  
  const reset = useCallback(() => {
    setState({
      isLoading: false,
      error: null,
      results: null,
      modelResults: {}
    })
  }, [])
  
  return {
    search,           // Her model için ayrı API çağrısı yapar
    unifiedSearch,    // Tek API çağrısı ile çoklu model arama
    isLoading: state.isLoading,
    error: state.error,
    results: state.results,
    modelResults: state.modelResults,
    reset
  }
}