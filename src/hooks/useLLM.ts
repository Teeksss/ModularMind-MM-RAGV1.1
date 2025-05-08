import { useState, useCallback } from 'react'
import { llmApi, ChatMessage } from '@/lib/api'

export interface UseLLMOptions {
  modelId?: string
  maxTokens?: number
  temperature?: number
  topP?: number
  systemMessage?: string
  streamingEnabled?: boolean
}

export function useLLM(defaultOptions: UseLLMOptions = {}) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  
  // Metin tamamlama (tek seferlik cevap)
  const completeText = useCallback(async (prompt: string, options: UseLLMOptions = {}) => {
    try {
      setIsLoading(true)
      setError(null)
      
      const modelId = options.modelId || defaultOptions.modelId
      const response = await llmApi.completeText(prompt, modelId, {
        max_tokens: options.maxTokens || defaultOptions.maxTokens,
        temperature: options.temperature || defaultOptions.temperature,
        top_p: options.topP || defaultOptions.topP,
        system_message: options.systemMessage || defaultOptions.systemMessage
      })
      
      setIsLoading(false)
      return response.text
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'LLM tamamlama sırasında bir hata oluştu'
      setError(errorMessage)
      setIsLoading(false)
      throw err
    }
  }, [defaultOptions])
  
  // Sohbet tamamlama
  const chatCompletion = useCallback(async (userMessage: string, options: UseLLMOptions = {}) => {
    try {
      setIsLoading(true)
      setError(null)
      
      // Kullanıcı mesajını ekle
      const userChatMessage: ChatMessage = { role: 'user', content: userMessage }
      const updatedMessages = [...messages, userChatMessage]
      setMessages(updatedMessages)
      
      // Sistem mesajını ekleme
      const systemMsg = options.systemMessage || defaultOptions.systemMessage
      const chatMessages: ChatMessage[] = systemMsg 
        ? [{ role: 'system', content: systemMsg }, ...updatedMessages]
        : updatedMessages
      
      // Streaming etkin mi kontrol et
      const streamingEnabled = options.streamingEnabled ?? defaultOptions.streamingEnabled ?? false
      const modelId = options.modelId || defaultOptions.modelId
      
      if (streamingEnabled) {
        // Asistan mesajı için yer tutucu ekle
        const assistantMessage: ChatMessage = { role: 'assistant', content: '' }
        setMessages([...updatedMessages, assistantMessage])
        
        // Streaming yanıtını başlat
        let responseText = ''
        
        const handleStream = (chunk: string | null, done: boolean, error?: Error) => {
          if (error) {
            setError(`Streaming hatası: ${error.message}`)
            setIsLoading(false)
            return
          }
          
          if (done) {
            setIsLoading(false)
            return
          }
          
          if (chunk) {
            responseText += chunk
            setMessages(prev => {
              const updated = [...prev]
              updated[updated.length - 1] = { role: 'assistant', content: responseText }
              return updated
            })
          }
        }
        
        // Streaming başlat
        const cancelStream = llmApi.streamingChat(chatMessages, handleStream, modelId, {
          max_tokens: options.maxTokens || defaultOptions.maxTokens,
          temperature: options.temperature || defaultOptions.temperature,
          top_p: options.topP || defaultOptions.topP
        })
        
        return () => cancelStream()
      } else {
        // Normal sohbet tamamlama
        const response = await llmApi.chatCompletion(chatMessages, modelId, {
          max_tokens: options.maxTokens || defaultOptions.maxTokens,
          temperature: options.temperature || defaultOptions.temperature,
          top_p: options.topP || defaultOptions.topP
        })
        
        // Asistan mesajını ekle
        setMessages([...updatedMessages, response.message])
        
        setIsLoading(false)
        return response.message.content
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Sohbet tamamlama sırasında bir hata oluştu'
      setError(errorMessage)
      setIsLoading(false)
      throw err
    }
  }, [messages, defaultOptions])
  
  // Mesajları temizle
  const clearMessages = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])
  
  return {
    completeText,
    chatCompletion,
    messages,
    isLoading,
    error,
    clearMessages,
    setMessages
  }
}