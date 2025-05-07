import React, { useState, useRef, useEffect } from 'react';
import { useChatStore, ChatMessage } from '../../store/chatStore';
import { useTranslation } from 'react-i18next';
import { FaPaperPlane, FaRedo, FaThumbsUp, FaThumbsDown, FaCopy, FaEllipsisV } from 'react-icons/fa';
import { Menu, Transition } from '@headlessui/react';
import ReactMarkdown from 'react-markdown';
import SourceCitation from './SourceCitation';

interface ChatInterfaceProps {
  sessionId?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId }) => {
  const { t } = useTranslation();
  const messageInputRef = useRef<HTMLTextAreaElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');
  
  // Chat store state
  const {
    currentSession,
    messages,
    isTyping,
    sendMessage,
    regenerateResponse,
    fetchMessages
  } = useChatStore();
  
  // Get the active session ID
  const activeSessionId = sessionId || currentSession?.id;
  
  // Get messages for the current session
  const sessionMessages = activeSessionId ? (messages[activeSessionId] || []) : [];
  
  // Scroll to bottom when messages change or when isTyping changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [sessionMessages, isTyping]);
  
  // Load messages when session changes
  useEffect(() => {
    if (activeSessionId && !messages[activeSessionId]) {
      fetchMessages(activeSessionId);
    }
  }, [activeSessionId, messages, fetchMessages]);
  
  // Handle sending a message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() || isTyping) {
      return;
    }
    
    // Clear input
    const messageText = message;
    setMessage('');
    
    // Send message
    if (activeSessionId) {
      await sendMessage(messageText, activeSessionId);
    } else {
      await sendMessage(messageText);
    }
    
    // Focus input again
    messageInputRef.current?.focus();
  };
  
  // Handle regenerating the last response
  const handleRegenerateResponse = async () => {
    if (isTyping || sessionMessages.length === 0) {
      return;
    }
    
    // Find the last assistant message
    const lastAssistantMessage = [...sessionMessages]
      .reverse()
      .find(msg => msg.role === 'assistant');
    
    if (lastAssistantMessage && activeSessionId) {
      await regenerateResponse(lastAssistantMessage.id, activeSessionId);
    }
  };
  
  // Handle text area input (resize and submit on Enter)
  const handleTextAreaInput = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(e);
    }
  };
  
  // Copy message content to clipboard
  const copyToClipboard = (content: string) => {
    navigator.clipboard.writeText(content);
    
    // Show toast notification (you would implement this)
    // showToast(t('chat.messageCopied'));
  };
  
  // Render individual message
  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === 'user';
    
    return (
      <div
        key={message.id}
        className={`mb-4 ${isUser ? 'ml-auto' : 'mr-auto'} max-w-[90%]`}
      >
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
          <div
            className={`${
              isUser
                ? 'bg-blue-600 text-white rounded-tl-2xl rounded-tr-sm rounded-br-2xl rounded-bl-2xl'
                : 'bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl'
            } px-4 py-3 shadow-sm`}
          >
            {isUser ? (
              <p className="whitespace-pre-wrap">{message.content}</p>
            ) : (
              <div className="markdown-content">
                <ReactMarkdown>
                  {message.content}
                </ReactMarkdown>
                
                {/* Render citations if available */}
                {message.citations && message.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">{t('chat.sources')}:</p>
                    <div className="space-y-1">
                      {message.citations.map((citation, index) => (
                        <SourceCitation key={index} citation={citation} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* Message actions */}
        {!isUser && (
          <div className="flex justify-start mt-1 space-x-2">
            <button
              onClick={() => copyToClipboard(message.content)}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-xs flex items-center"
              title={t('chat.copy')}
            >
              <FaCopy className="mr-1" size={12} />
              {t('chat.copy')}
            </button>
            
            <button
              onClick={() => handleRegenerateResponse()}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-xs flex items-center"
              title={t('chat.regenerate')}
            >
              <FaRedo className="mr-1" size={12} />
              {t('chat.regenerate')}
            </button>
            
            <Menu as="div" className="relative inline-block text-left">
              <Menu.Button className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300 text-xs flex items-center">
                <FaEllipsisV size={12} />
              </Menu.Button>
              
              <Transition
                enter="transition ease-out duration-100"
                enterFrom="transform opacity-0 scale-95"
                enterTo="transform opacity-100 scale-100"
                leave="transition ease-in duration-75"
                leaveFrom="transform opacity-100 scale-100"
                leaveTo="transform opacity-0 scale-95"
              >
                <Menu.Items className="absolute left-0 mt-2 w-40 origin-top-left bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
                  <div className="py-1">
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={`${
                            active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'
                          } group flex items-center w-full px-4 py-2 text-sm`}
                        >
                          <FaThumbsUp className="mr-2 h-4 w-4" aria-hidden="true" />
                          {t('chat.helpful')}
                        </button>
                      )}
                    </Menu.Item>
                    
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={`${
                            active ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'
                          } group flex items-center w-full px-4 py-2 text-sm`}
                        >
                          <FaThumbsDown className="mr-2 h-4 w-4" aria-hidden="true" />
                          {t('chat.notHelpful')}
                        </button>
                      )}
                    </Menu.Item>
                  </div>
                </Menu.Items>
              </Transition>
            </Menu>
          </div>
        )}
      </div>
    );
  };
  
  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 rounded-lg overflow-hidden shadow-lg">
      {/* Messages container */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800">
        {sessionMessages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-center p-4">
            <div>
              <h3 className="text-xl font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('chat.welcomeTitle')}
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                {t('chat.welcomeMessage')}
              </p>
            </div>
          </div>
        ) : (
          <div>
            {sessionMessages.map(message => renderMessage(message))}
          </div>
        )}
        
        {/* Typing indicator */}
        {isTyping && (
          <div className="flex mb-4 mr-auto max-w-[90%]">
            <div className="bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-100 rounded-tl-sm rounded-tr-2xl rounded-br-2xl rounded-bl-2xl px-4 py-2 shadow-sm">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-500 dark:bg-gray-300 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-500 dark:bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-500 dark:bg-gray-300 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        {/* Empty div for scrolling to bottom */}
        <div ref={messagesEndRef} />
      </div>
      
      {/* Message input */}
      <div className="border-t border-gray-200 dark:border-gray-700 p-4 bg-white dark:bg-gray-900">
        <form onSubmit={handleSendMessage} className="flex items-end">
          <textarea
            ref={messageInputRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleTextAreaInput}
            className="flex-1 border border-gray-300 dark:border-gray-600 rounded-md p-3 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 resize-none min-h-[80px] max-h-[160px]"
            placeholder={t('chat.messagePlaceholder')}
            rows={2}
            disabled={isTyping}
          />
          
          <button
            type="submit"
            disabled={isTyping || !message.trim()}
            className={`ml-2 p-3 rounded-md ${
              isTyping || !message.trim()
                ? 'bg-gray-300 dark:bg-gray-700 text-gray-500 dark:text-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            }`}
          >
            <FaPaperPlane />
          </button>
        </form>
        
        {/* Additional controls */}
        {sessionMessages.length > 0 && (
          <div className="mt-2 flex justify-between">
            <button
              onClick={handleRegenerateResponse}
              disabled={isTyping}
              className={`text-sm flex items-center ${
                isTyping
                  ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                  : 'text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400'
              }`}
            >
              <FaRedo className="mr-1" size={12} />
              {t('chat.regenerateResponse')}
            </button>
            
            <div className="text-xs text-gray-500 dark:text-gray-400">
              {t('chat.disclaimer')}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatInterface;