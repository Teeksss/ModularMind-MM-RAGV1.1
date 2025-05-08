import { useState, useCallback, useRef } from 'react'
import { QueryResponse, ragApi } from '@/lib/api'

export interface UseRagQueryOptions {
  llmModel?: string
  embeddingModel?: string
  systemMessage?: string
  contextLimit?: number
  includeSources?: boolean
  filterMetadata?: Record<string, any>
}

interface QueryState {
  isLoading: boolean
  error: string | null
  result: QueryResponse | null
}

export function useRagQuery(defaultOptions: UseRagQueryOptions = {}) {
  const [state, setState] = useState<QueryState>({
    isLoading: false,
    error: null,
    result: null
  })
  
  // Mevcut sorguyu takip et
  const currentQueryRef = useRef<string | null>(null)
  
  const executeQuery = useCallback(async (query: string, options: UseRagQueryOptions = {}) => {
    try {
      // Önceki sorguyu iptal et
      if (currentQueryRef.current === query) {
        return state.result
      }
      
      setState(prev => ({ ...prev, isLoading: true, error: null }))
      currentQueryRef.current = query
      
      const response = await ragApi.query(query, {
        llm_model: options.llmModel || defaultOptions.llmModel,
        embedding_model: options.embeddingModel || defaultOptions.embeddingModel,
        system_message: options.systemMessage || defaultOptions.systemMessage,
        context_limit: options.contextLimit || defaultOptions.contextLimit || 5,
        include_sources: options.includeSources ?? defaultOptions.includeSources ?? true,
        filter_metadata: options.filterMetadata || defaultOptions.filterMetadata
      })
      
      setState({ isLoading: false, error: null, result: response })
      return response
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'RAG sorgulama sırasında bir hata oluştu'
      setState({ isLoading: false, error: errorMessage, result: null })
      throw err
    } finally {
      currentQueryRef.current = null
    }
  }, [defaultOptions])
  
  const reset = useCallback(() => {
    setState({ isLoading: false, error: null, result: null })
    currentQueryRef.current = null
  }, [])
  
  return {
    executeQuery,
    isLoading: state.isLoading,
    error: state.error,
    result: state.result,
    reset
  }
}