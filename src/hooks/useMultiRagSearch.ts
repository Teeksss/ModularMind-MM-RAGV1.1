import { useState, useCallback } from 'react'
import { useEmbeddingStore } from '@/lib/embeddingStore'
import { ragApi } from '@/lib/api'

export interface MultiRagOptions {
  contextLimit?: number
  filterMetadata?: Record<string, any>
  llmModel?: string
  systemMessage?: string
  includeSources?: boolean
}

interface MultiRagState {
  isLoading: boolean
  error: string | null
  answer: string | null
  sources: any[] | null
  usedModels: string[]
}

export function useMultiRagSearch(defaultOptions: MultiRagOptions = {}) {
  const { selectedModelIds } = useEmbeddingStore()
  const [state, setState] = useState<MultiRagState>({
    isLoading: false,
    error: null,
    answer: null,
    sources: null,
    usedModels: []
  })
  
  const query = useCallback(async (
    queryText: string, 
    options: MultiRagOptions = {}
  ) => {
    try {
      // En az bir model seçilmiş olmalı
      if (selectedModelIds.length === 0) {
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
      const queryOptions = {
        context_limit: options.contextLimit ?? defaultOptions.contextLimit ?? 5,
        filter_metadata: options.filterMetadata ?? defaultOptions.filterMetadata,
        llm_model: options.llmModel ?? defaultOptions.llmModel,
        system_message: options.systemMessage ?? defaultOptions.systemMessage,
        include_sources: options.includeSources ?? defaultOptions.includeSources ?? true,
        use_multi_model: true,
        models_to_use: selectedModelIds
      }
      
      // RAG sorgusu yap
      const response = await ragApi.query(queryText, queryOptions)
      
      setState({
        isLoading: false,
        error: null,
        answer: response.answer,
        sources: response.sources || [],
        usedModels: response.embedding_models || []
      })
      
      return {
        answer: response.answer,
        sources: response.sources || [],
        llmModel: response.llm_model,
        embeddingModels: response.embedding_models || []
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'RAG sorgusu sırasında bir hata oluştu'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false
      }))
      return null
    }
  }, [selectedModelIds, defaultOptions])
  
  const smartQuery = useCallback(async (
    queryText: string, 
    options: MultiRagOptions = {}
  ) => {
    try {
      // Yükleme durumunu başlat
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      
      // Seçenekleri birleştir
      const queryOptions = {
        context_limit: options.contextLimit ?? defaultOptions.contextLimit ?? 5,
        filter_metadata: options.filterMetadata ?? defaultOptions.filterMetadata,
        llm_model: options.llmModel ?? defaultOptions.llmModel,
        system_message: options.systemMessage ?? defaultOptions.systemMessage,
        include_sources: options.includeSources ?? defaultOptions.includeSources ?? true,
        use_auto_routing: true  // Akıllı yönlendirme
      }
      
      // RAG sorgusu yap
      const response = await ragApi.query(queryText, queryOptions)
      
      setState({
        isLoading: false,
        error: null,
        answer: response.answer,
        sources: response.sources || [],
        usedModels: response.embedding_models || []
      })
      
      return {
        answer: response.answer,
        sources: response.sources || [],
        llmModel: response.llm_model,
        embeddingModels: response.embedding_models || []
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'RAG sorgusu sırasında bir hata oluştu'
      setState(prev => ({
        ...prev,
        error: errorMessage,
        isLoading: false
      }))
      return null
    }
  }, [defaultOptions])
  
  const reset = useCallback(() => {
    setState({
      isLoading: false,
      error: null,
      answer: null,
      sources: null,
      usedModels: []
    })
  }, [])
  
  return {
    query,          // Seçili modellerle sorgu
    smartQuery,     // Akıllı model yönlendirme ile sorgu
    isLoading: state.isLoading,
    error: state.error,
    answer: state.answer,
    sources: state.sources,
    usedModels: state.usedModels,
    reset
  }
}