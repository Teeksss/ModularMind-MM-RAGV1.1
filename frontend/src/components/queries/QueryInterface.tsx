import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { BiSend, BiLoaderAlt, BiMicrophone, BiX } from 'react-icons/bi';

import { useQueryStore } from '../../store/queryStore';
import { useSessionStore } from '../../store/sessionStore';
import { useSpeechRecognition } from '../../hooks/useSpeechRecognition';
import { QueryResult } from '../../types/query';
import QueryResultView from './QueryResultView';
import SourceCitations from './SourceCitations';
import LoadingIndicator from '../common/LoadingIndicator';
import ErrorMessage from '../common/ErrorMessage';
import { config } from '../../config/config';

type QueryInterfaceProps = {
  className?: string;
};

const QueryInterface: React.FC<QueryInterfaceProps> = ({ className = '' }) => {
  const { t } = useTranslation();
  const [queryText, setQueryText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { sendQuery, queries, currentResult, clearCurrentResult } = useQueryStore();
  const { sessionId } = useSessionStore();
  
  const { 
    isListening, 
    transcript, 
    startListening, 
    stopListening, 
    hasRecognitionSupport 
  } = useSpeechRecognition();

  // Update textarea height to fit content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [queryText]);

  // Update textarea with speech recognition transcript
  useEffect(() => {
    if (transcript) {
      setQueryText(prev => prev + transcript);
    }
  }, [transcript]);

  const handleQueryChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQueryText(e.target.value);
  };

  const handleQuerySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!queryText.trim() || isSubmitting) return;
    
    try {
      setIsSubmitting(true);
      setError(null);
      
      await sendQuery({
        query: queryText.trim(),
        sessionId,
        language: config.ui.defaultLanguage,
      });
      
      setQueryText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred while processing your query');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter without Shift
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuerySubmit(e);
    }
  };

  const toggleSpeechRecognition = () => {
    if (isListening) {
      stopListening();
    } else {
      setError(null);
      startListening();
    }
  };

  const handleClearQuery = () => {
    setQueryText('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  return (
    <div className={`flex flex-col w-full ${className}`}>
      {/* Results area */}
      <div className="flex-1 overflow-y-auto mb-4 space-y-6">
        {queries.map((query) => (
          <div key={query.id} className="space-y-2">
            <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <p className="font-medium">{query.query}</p>
              <div className="text-xs text-gray-500">
                {new Date(query.timestamp).toLocaleString()}
              </div>
            </div>
            
            {query.result && (
              <QueryResultView result={query.result} />
            )}
          </div>
        ))}
        
        {isSubmitting && (
          <div className="py-4 flex justify-center">
            <LoadingIndicator text={t('common.processing')} />
          </div>
        )}
        
        {currentResult && (
          <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <QueryResultView result={currentResult} />
            <div className="mt-4">
              <SourceCitations sources={currentResult.sources || []} />
            </div>
            <button 
              onClick={clearCurrentResult}
              className="mt-2 text-xs text-blue-600 dark:text-blue-400 hover:underline"
            >
              {t('query.dismiss')}
            </button>
          </div>
        )}
        
        {error && (
          <ErrorMessage 
            message={error} 
            onDismiss={() => setError(null)} 
          />
        )}
      </div>
      
      {/* Query input */}
      <form onSubmit={handleQuerySubmit} className="relative">
        <div className="relative flex items-center border dark:border-gray-700 rounded-lg shadow-sm bg-white dark:bg-gray-800">
          <textarea
            ref={textareaRef}
            value={queryText}
            onChange={handleQueryChange}
            onKeyDown={handleKeyDown}
            placeholder={t('query.placeholder')}
            disabled={isSubmitting}
            rows={1}
            className="w-full py-3 px-4 pr-24 resize-none max-h-32 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg dark:bg-gray-800 dark:text-white"
          />
          
          <div className="absolute right-2 flex items-center space-x-1">
            {queryText && (
              <button
                type="button"
                onClick={handleClearQuery}
                className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                title={t('common.clear')}
              >
                <BiX size={20} />
              </button>
            )}
            
            {hasRecognitionSupport && (
              <button
                type="button"
                onClick={toggleSpeechRecognition}
                className={`p-2 rounded-full ${isListening 
                  ? 'text-red-500 bg-red-100 dark:bg-red-900/30' 
                  : 'text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'}`}
                title={isListening ? t('query.stopListening') : t('query.startListening')}
                disabled={isSubmitting}
              >
                <BiMicrophone size={20} />
              </button>
            )}
            
            <button
              type="submit"
              className="p-2 text-white bg-blue-600 rounded-full hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={!queryText.trim() || isSubmitting}
              title={t('query.send')}
            >
              {isSubmitting ? (
                <BiLoaderAlt size={20} className="animate-spin" />
              ) : (
                <BiSend size={20} />
              )}
            </button>
          </div>
        </div>
        
        <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          {t('query.hint')}
        </div>
      </form>
    </div>
  );
};

export default QueryInterface;