import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { FiSend, FiPaperclip, FiInfo, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';

import Button from '@/components/common/Button';
import ChatMessage from '@/components/chat/ChatMessage';
import SourceCitation from '@/components/chat/SourceCitation';
import { useChatStore } from '@/store/chatStore';
import { useDocumentStore } from '@/store/documentStore';
import { useNotificationStore } from '@/store/notificationStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { chatService } from '@/services/chatService';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  sources?: {
    document_id: string;
    document_name: string;
    chunk_content: string;
    relevance_score: number;
  }[];
}

const ChatPage: React.FC = () => {
  const { chatId } = useParams<{ chatId: string }>();
  const navigate = useNavigate();
  const { addNotification } = useNotificationStore();
  
  // State
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showSources, setShowSources] = useState<Record<string, boolean>>({});
  
  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  // Stores
  const { messages, addMessage, setChatHistory, clearMessages } = useChatStore();
  const { documents } = useDocumentStore();
  
  // WebSocket for real-time updates
  const { lastMessage } = useWebSocket(`/api/v1/chat/ws/${chatId}`);
  
  // Load chat history when component mounts
  useEffect(() => {
    const loadChatHistory = async () => {
      if (chatId) {
        try {
          const history = await chatService.getChatHistory(chatId);
          setChatHistory(history.messages);
        } catch (error) {
          console.error('Error loading chat history:', error);
          addNotification({
            id: Date.now().toString(),
            title: 'Hata',
            message: 'Sohbet geçmişi yüklenirken bir hata oluştu.',
            type: 'error',
          });
        }
      } else {
        clearMessages();
      }
    };
    
    loadChatHistory();
  }, [chatId, setChatHistory, clearMessages, addNotification]);
  
  // Process real-time updates from WebSocket
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data);
        if (data.type === 'message') {
          addMessage(data.message);
        }
      } catch (error) {
        console.error('Error processing WebSocket message:', error);
      }
    }
  }, [lastMessage, addMessage]);
  
  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSendMessage = async () => {
    if (!input.trim() && messages.length === 0) return;
    
    const messageText = input.trim();
    setInput('');
    
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };
    
    addMessage(userMessage);
    setIsLoading(true);
    
    try {
      if (!chatId) {
        // Create new chat
        const newChat = await chatService.createChat(messageText);
        navigate(`/chat/${newChat.id}`);
      } else {
        // Send message to existing chat
        await chatService.sendMessage(chatId, messageText);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Mesaj gönderilemedi',
        message: 'Mesajınız gönderilirken bir hata oluştu.',
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleFileUpload = () => {
    fileInputRef.current?.click();
  };
  
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const formData = new FormData();
    formData.append('file', files[0]);
    
    try {
      setIsLoading(true);
      const result = await chatService.uploadAttachment(chatId || 'new', formData);
      
      addMessage({
        id: Date.now().toString(),
        role: 'user',
        content: `[Dosya yüklendi: ${files[0].name}]`,
        timestamp: new Date(),
      });
      
      addNotification({
        id: Date.now().toString(),
        title: 'Dosya yüklendi',
        message: result.message,
        type: 'success',
      });
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (error) {
      console.error('Error uploading file:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Yükleme hatası',
        message: 'Dosya yüklenirken bir hata oluştu.',
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  const toggleSources = (messageId: string) => {
    setShowSources(prev => ({
      ...prev,
      [messageId]: !prev[messageId]
    }));
  };
  
  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center text-gray-500 dark:text-gray-400">
              <FiInfo className="mx-auto h-12 w-12 mb-4" />
              <h3 className="text-lg font-medium">RAG Destekli Sohbet</h3>
              <p className="mt-2 max-w-sm">
                Sorularınızı sorun, belge yükleyin ve yapay zeka ile etkileşime geçin.
                Yanıtlar yüklediğiniz belgelerden alınan bilgilerle desteklenir.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((message) => (
              <div key={message.id} className="space-y-2">
                <ChatMessage
                  message={message}
                  hasSources={!!message.sources?.length}
                  onToggleSources={() => toggleSources(message.id)}
                  showSources={!!showSources[message.id]}
                />
                
                <AnimatePresence>
                  {showSources[message.id] && message.sources && message.sources.length > 0 && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.2 }}
                      className="ml-12 space-y-2"
                    >
                      <div className="flex items-center text-xs text-gray-500 dark:text-gray-400 mb-1">
                        <span>Kaynaklar ({message.sources.length})</span>
                        <Button 
                          size="xs"
                          variant="ghost"
                          className="ml-2"
                          onClick={() => toggleSources(message.id)}
                        >
                          <FiChevronUp size={14} />
                        </Button>
                      </div>
                      
                      {message.sources.map((source, index) => (
                        <SourceCitation
                          key={`${message.id}-source-${index}`}
                          source={source}
                          documentName={source.document_name}
                          relevanceScore={source.relevance_score}
                        />
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex items-center space-x-2 text-gray-500 dark:text-gray-400">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-600 animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-sm">Düşünüyor...</span>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </>
        )}
      </div>
      
      <div className="border-t border-gray-200 dark:border-gray-800 p-4">
        <div className="flex items-end space-x-2">
          <button
            onClick={handleFileUpload}
            className="p-2 text-gray-500 dark:text-gray-400 hover:text-blue-500 dark:hover:text-blue-400"
          >
            <FiPaperclip size={20} />
          </button>
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="Mesajınızı yazın..."
              className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:border-gray-700 dark:text-white resize-none"
              rows={1}
              disabled={isLoading}
            />
          </div>
          
          <Button
            onClick={handleSendMessage}
            disabled={isLoading || (!input.trim() && messages.length === 0)}
            variant="primary"
            size="md"
            rounded
            rightIcon={<FiSend />}
          >
            Gönder
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;