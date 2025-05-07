import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { BiLinkExternal, BiChevronDown, BiChevronUp, BiFile } from 'react-icons/bi';

import { Source } from '../../types';
import Badge from '../common/Badge';

interface SourceCitationsProps {
  sources: Source[];
  className?: string;
}

const SourceCitations: React.FC<SourceCitationsProps> = ({ sources, className = '' }) => {
  const { t } = useTranslation();
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null);
  
  // If no sources, don't render anything
  if (!sources || sources.length === 0) {
    return null;
  }
  
  const toggleSource = (sourceId: string) => {
    if (expandedSourceId === sourceId) {
      setExpandedSourceId(null);
    } else {
      setExpandedSourceId(sourceId);
    }
  };
  
  // Format score as percentage
  const formatScore = (score: number): string => {
    return `${Math.round(score * 100)}%`;
  };
  
  // Get icon for content type
  const getContentTypeIcon = (contentType: string) => {
    // This could be expanded with many more content type icons
    if (contentType.includes('pdf')) {
      return <BiFile className="text-red-500" />;
    }
    if (contentType.includes('html')) {
      return <BiFile className="text-blue-500" />;
    }
    return <BiFile className="text-gray-500" />;
  };
  
  return (
    <div className={`mt-4 ${className}`}>
      <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        {t('query.sources')} ({sources.length})
      </h3>
      
      <div className="space-y-2">
        {sources.map((source) => (
          <div 
            key={source.id}
            className="border rounded-lg overflow-hidden bg-white dark:bg-gray-800 dark:border-gray-700"
          >
            {/* Source header */}
            <div 
              className="flex items-center justify-between p-3 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700"
              onClick={() => toggleSource(source.id)}
            >
              <div className="flex items-center space-x-2">
                {getContentTypeIcon(source.content_type)}
                <div className="text-sm font-medium truncate max-w-xs">
                  {source.title || t('query.untitledSource')}
                </div>
                <Badge 
                  variant={source.score > 0.8 ? 'success' : source.score > 0.5 ? 'warning' : 'danger'}
                  size="sm"
                >
                  {formatScore(source.score)}
                </Badge>
              </div>
              <div className="flex items-center">
                {source.url && (
                  <a 
                    href={source.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-600 dark:text-blue-400 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/30"
                    onClick={(e) => e.stopPropagation()}
                    title={t('common.openInNewTab')}
                  >
                    <BiLinkExternal size={18} />
                  </a>
                )}
                <div className="ml-2">
                  {expandedSourceId === source.id ? (
                    <BiChevronUp size={20} />
                  ) : (
                    <BiChevronDown size={20} />
                  )}
                </div>
              </div>
            </div>
            
            {/* Source content */}
            {expandedSourceId === source.id && (
              <div className="p-3 border-t dark:border-gray-700">
                {source.content ? (
                  <div className="text-sm whitespace-pre-wrap">
                    {source.content}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500 dark:text-gray-400 italic">
                    {t('query.sourceContentNotAvailable')}
                  </div>
                )}
                
                {/* Source metadata */}
                {source.metadata && Object.keys(source.metadata).length > 0 && (
                  <div className="mt-3 pt-3 border-t dark:border-gray-700">
                    <h4 className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      {t('common.metadata')}
                    </h4>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      {Object.entries(source.metadata)
                        .filter(([key, value]) => key !== 'content' && value !== null && value !== undefined)
                        .map(([key, value]) => (
                          <div key={key} className="flex">
                            <span className="font-medium text-gray-600 dark:text-gray-400 mr-1">
                              {key}:
                            </span>
                            <span className="text-gray-900 dark:text-gray-200 truncate">
                              {typeof value === 'object' 
                                ? JSON.stringify(value) 
                                : String(value)
                              }
                            </span>
                          </div>
                        ))
                      }
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default SourceCitations;