import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import { FaCopy, FaCheck, FaSyncAlt } from 'react-icons/fa';
import SourceCitation from './SourceCitation';
import ResponseFeedback from '../feedback/ResponseFeedback';
import { useNotificationStore } from '../../store/notificationStore';

interface Source {
  id: string;
  title: string;
  url?: string;
}

interface ChatMessageProps {
  id: string;
  message: string;
  sender: 'user' | 'assistant' | 'system';
  timestamp: string;
  sources?: Source[];
  isLoading?: boolean;
  queryId?: string;  // Added for feedback
  onRegenerate?: () => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({
  id,
  message,
  sender,
  timestamp,
  sources,
  isLoading,
  queryId,
  onRegenerate
}) => {
  const { t } = useTranslation();
  const { addNotification } = useNotificationStore();
  const [isCopied, setIsCopied] = useState(false);

  // Handle copy message to clipboard
  const handleCopy = () => {
    navigator.clipboard.writeText(message).then(
      () => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
        
        addNotification({
          type: 'success',
          title: t('chat.messageCopied'),
          message: t('chat.messageCopiedToClipboard')
        });
      },
      () => {
        addNotification({
          type: 'error',
          title: t('common.error'),
          message: t('chat.copyFailed')
        });
      }
    );
  };

  return (
    <div 
      className={`chat-message flex ${
        sender === 'user' ? 'justify-end' : 'justify-start'
      } mb-4`}
    >
      <div 
        className={`relative max-w-3xl rounded-lg px-4 py-3 shadow ${
          sender === 'user' 
            ? 'bg-blue-100 text-blue-900 dark:bg-blue-900 dark:text-blue-100' 
            : sender === 'system'
              ? 'bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-200'
              : 'bg-white text-gray-800 dark:bg-gray-700 dark:text-gray-100'
        }`}
        style={{ minWidth: '250px' }}
      >
        {/* Message content */}
        <div className="mb-1">
          {isLoading ? (
            <>
              <div className="flex items-center mb-2">
                <div className="animate-pulse h-2 w-2 rounded-full bg-blue-500 mr-1"></div>
                <div className="animate-pulse h-2 w-2 rounded-full bg-blue-500 mr-1"></div>
                <div className="animate-pulse h-2 w-2 rounded-full bg-blue-500"></div>
              </div>
              <ReactMarkdown>{message || t('chat.generating')}</ReactMarkdown>
            </>
          ) : (
            <ReactMarkdown>{message}</ReactMarkdown>
          )}
        </div>
        
        {/* Sources */}
        {sources && sources.length > 0 && (
          <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
              {t('chat.sources')}:
            </p>
            <div className="space-y-1">
              {sources.map(source => (
                <SourceCitation 
                  key={source.id} 
                  id={source.id}
                  title={source.title}
                  url={source.url}
                />
              ))}
            </div>
          </div>
        )}
        
        {/* Message footer */}
        <div className="flex justify-between items-center mt-2 text-xs text-gray-500 dark:text-gray-400">
          <span>{new Date(timestamp).toLocaleTimeString()}</span>
          
          <div className="flex items-center space-x-2">
            {sender === 'assistant' && onRegenerate && (
              <button
                onClick={onRegenerate}
                className="p-1 hover:text-blue-600 dark:hover:text-blue-400"
                title={t('chat.regenerateResponse')}
              >
                <FaSyncAlt />
              </button>
            )}
            
            <button
              onClick={handleCopy}
              className="p-1 hover:text-blue-600 dark:hover:text-blue-400"
              title={t('common.copy')}
            >
              {isCopied ? <FaCheck /> : <FaCopy />}
            </button>
          </div>
        </div>
        
        {/* Feedback component for assistant messages */}
        {sender === 'assistant' && !isLoading && queryId && (
          <ResponseFeedback
            responseId={id}
            queryId={queryId}
            sources={sources}
          />
        )}
      </div>
    </div>
  );
};

export default ChatMessage;