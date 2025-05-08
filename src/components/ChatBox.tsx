import { useState, useRef, useEffect } from 'react'
import { FiSend, FiUser, FiCpu, FiChevronDown, FiChevronUp, FiAlertCircle, FiLoader } from 'react-icons/fi'
import { ChatMessage, llmApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import MarkdownRenderer from './MarkdownRenderer'
import SourceViewer from './SourceViewer'
import { useRagQuery } from '@/hooks/useRagQuery'

interface ChatBoxProps {
  modelId?: string
  systemMessage?: string
  ragEnabled?: boolean
  className?: string
  onSettingsClick?: () => void
}

const ChatBox = ({ 
  modelId = 'gpt-4o', 
  systemMessage = 'Sen yardımcı bir asistansın.', 
  ragEnabled = false,
  className,
  onSettingsClick
}: ChatBoxProps) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [streamingText, setStreamingText] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // RAG Sorgu Hook
  const {
    executeQuery: ragQuery,
    isLoading: ragLoading,
    error: ragError,
    result: ragResult
  } = useRagQuery({
    llmModel: modelId,
    systemMessage,
    includeSources: true
  })
  
  // Otomatik odaklanma
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus()
    }
  }, [])
  
  // Mesajları sona kaydır
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingText])
  
  // Mesaj gönderme
  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return
    
    const userMessage: ChatMessage = { role: 'user', content: inputMessage }
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setError(null)
    setIsLoading(true)
    setIsSending(true)
    
    try {
      if (ragEnabled) {
        // RAG modunda sorgulama
        const result = await ragQuery(inputMessage)
        
        // RAG yanıtını ekle
        if (result) {
          const assistantMessage: ChatMessage = { role: 'assistant', content: result.answer }
          setMessages(prev => [...prev, assistantMessage])
        }
      } else {
        // Normal chatbot (streaming)
        setStreamingText('')
        
        // Sistem mesajıyla birlikte tüm mesajları hazırla
        const allMessages = [
          { role: 'system', content: systemMessage } as ChatMessage,
          ...messages,
          userMessage
        ]
        
        // Streaming yanıtını başlat
        const cancelStream = llmApi.streamingChat(
          allMessages,
          (chunk, done, error) => {
            if (error) {
              setError(`Stream hatası: ${error.message}`)
              setIsLoading(false)
              return
            }
            
            if (done) {
              // Streaming tamamlandığında yanıtı kaydet
              if (streamingText) {
                const assistantMessage: ChatMessage = { role: 'assistant', content: streamingText }
                setMessages(prev => [...prev, assistantMessage])
                setStreamingText('')
              }
              setIsLoading(false)
              return
            }
            
            if (chunk) {
              setStreamingText(prev => prev + chunk)
            }
          },
          modelId
        )
        
        // Temizlik işlevi
        return () => {
          cancelStream()
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Mesaj gönderirken bir hata oluştu')
    } finally {
      setIsLoading(false)
      setIsSending(false)
    }
  }
  
  // Yükseklik otomatik ayarlama
  const adjustHeight = (el: HTMLTextAreaElement) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`
  }
  
  // Enter tuşu işleme
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }
  
  return (
    <div className={cn("flex flex-col h-[600px] border rounded-lg bg-gray-50", className)}>
      {/* Mesaj Alanı */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <FiCpu size={48} className="mb-4" />
            <p className="text-center text-sm max-w-md">
              {ragEnabled 
                ? 'Belgelerim üzerinde soru sorabilirsiniz. Belgelerden bilgi çekerek yanıt vereceğim.'
                : 'Nasıl yardımcı olabilirim? Herhangi bir konuda soru sorabilirsiniz.'}
            </p>
          </div>
        ) : (
          <>
            {messages.map((message, index) => (
              <div key={index} className={cn(
                "flex",
                message.role === 'user' ? "justify-end" : "justify-start"
              )}>
                <div className={cn(
                  "max-w-[80%] px-4 py-3 rounded-lg",
                  message.role === 'user' 
                    ? "bg-primary-600 text-white rounded-br-none" 
                    : "bg-white border border-gray-200 rounded-bl-none"
                )}>
                  <div className="flex items-center mb-1">
                    {message.role === 'user' ? (
                      <>
                        <span className="font-medium">Sen</span>
                        <FiUser className="ml-2" size={14} />
                      </>
                    ) : (
                      <>
                        <FiCpu className="mr-2" size={14} /> 
                        <span className="font-medium">AI Asistan</span>
                      </>
                    )}
                  </div>
                  
                  <div className={cn(
                    message.role === 'user' ? "text-white" : "text-gray-800"
                  )}>
                    {message.role === 'assistant' ? (
                      <MarkdownRenderer content={message.content} />
                    ) : (
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
            
            {/* Streaming metni */}
            {streamingText && (
              <div className="flex justify-start">
                <div className="max-w-[80%] px-4 py-3 rounded-lg bg-white border border-gray-200 rounded-bl-none">
                  <div className="flex items-center mb-1">
                    <FiCpu className="mr-2" size={14} /> 
                    <span className="font-medium">AI Asistan</span>
                  </div>
                  
                  <div className="text-gray-800">
                    <MarkdownRenderer content={streamingText} />
                  </div>
                </div>
              </div>
            )}
            
            {/* RAG Kaynakları */}
            {ragEnabled && ragResult?.sources && ragResult.sources.length > 0 && (
              <SourceViewer sources={ragResult.sources} />
            )}
            
            {/* Hata Mesajı */}
            {error && (
              <div className="flex justify-center my-2">
                <div className="max-w-[80%] px-4 py-2 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm flex items-center">
                  <FiAlertCircle className="mr-2" />
                  <span>{error}</span>
                </div>
              </div>
            )}
            
            {/* Yükleniyor Göstergesi */}
            {isLoading && !streamingText && (
              <div className="flex justify-center my-2">
                <div className="flex items-center space-x-2 text-gray-500 bg-white px-4 py-2 rounded-lg shadow-sm">
                  <FiLoader className="animate-spin" />
                  <span className="text-sm">Düşünüyor...</span>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      {/* Giriş Alanı */}
      <div className="px-4 py-3 border-t bg-white rounded-b-lg">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => {
              setInputMessage(e.target.value)
              adjustHeight(e.target)
            }}
            onKeyDown={handleKeyDown}
            placeholder={ragEnabled ? "Belgelere bir soru sorun..." : "Mesajınızı yazın..."}
            className="w-full px-4 py-2 pr-10 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none overflow-hidden"
            rows={1}
            style={{ minHeight: '42px', maxHeight: '150px' }}
            disabled={isLoading}
          />
          
          <button
            onClick={handleSendMessage}
            className={cn(
              "absolute right-2 bottom-2 p-2 rounded-full",
              isLoading || !inputMessage.trim()
                ? "text-gray-400 cursor-not-allowed"
                : "text-primary-600 hover:bg-primary-50"
            )}
            disabled={isLoading || !inputMessage.trim()}
          >
            {isLoading ? <FiLoader className="animate-spin" /> : <FiSend />}
          </button>
        </div>
        
        <div className="flex justify-between items-center mt-2 text-xs text-gray-500">
          <div>
            <span>
              {ragEnabled ? 'RAG Modu: Etkin' : 'RAG Modu: Devre Dışı'}
            </span>
          </div>
          
          {onSettingsClick && (
            <button
              onClick={onSettingsClick}
              className="text-gray-500 hover:text-gray-700 underline text-xs"
            >
              Ayarları Değiştir
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default ChatBox