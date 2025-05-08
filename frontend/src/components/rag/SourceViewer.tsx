import React, { useState } from 'react';
import { FiExternalLink, FiFile, FiUser, FiCalendar, FiTag, FiChevronDown, FiChevronUp } from 'react-icons/fi';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import Markdown from '@/components/common/Markdown';

interface SourceMetadata {
  source?: string;
  doc_id?: string;
  title?: string;
  url?: string;
  author?: string;
  date?: string;
  tags?: string[];
  filename?: string;
  page_number?: number;
  [key: string]: any;
}

interface SourceProps {
  source: {
    text: string;
    metadata: SourceMetadata;
  };
}

const SourceViewer: React.FC<SourceProps> = ({ source }) => {
  const [showAllMetadata, setShowAllMetadata] = useState(false);
  
  // Format date if exists
  const formattedDate = source.metadata.date 
    ? new Date(source.metadata.date).toLocaleDateString()
    : null;
  
  // Get additional metadata fields excluding standard ones
  const standardFields = ['source', 'doc_id', 'title', 'url', 'author', 'date', 'tags', 'filename', 'page_number'];
  const additionalMetadata = Object.entries(source.metadata)
    .filter(([key]) => !standardFields.includes(key));
  
  // Detect if text appears to be markdown
  const isMarkdown = /^#|`{3}|!\[|^-\s|^[0-9]+\.\s|^>\s|\[.+\]\(.+\)/m.test(source.text);
  
  return (
    <div className="space-y-4">
      <div className="space-y-3">
        <h3 className="text-lg font-semibold">
          {source.metadata.title || 'Kaynak İçeriği'}
        </h3>
        
        <div className="flex flex-wrap gap-2">
          {source.metadata.source && (
            <Badge variant="outline" className="flex items-center gap-1">
              <FiFile size={12} />
              {source.metadata.source}
            </Badge>
          )}
          
          {source.metadata.author && (
            <Badge variant="outline" className="flex items-center gap-1">
              <FiUser size={12} />
              {source.metadata.author}
            </Badge>
          )}
          
          {formattedDate && (
            <Badge variant="outline" className="flex items-center gap-1">
              <FiCalendar size={12} />
              {formattedDate}
            </Badge>
          )}
          
          {source.metadata.tags && source.metadata.tags.length > 0 && (
            <Badge variant="outline" className="flex items-center gap-1">
              <FiTag size={12} />
              {Array.isArray(source.metadata.tags) 
                ? source.metadata.tags.join(', ') 
                : source.metadata.tags}
            </Badge>
          )}
        </div>
        
        {source.metadata.url && (
          <div>
            <a 
              href={source.metadata.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 text-sm"
            >
              <FiExternalLink size={14} />
              Kaynağa Git
            </a>
          </div>
        )}
      </div>
      
      <Card>
        <CardContent className="py-4 max-h-[500px] overflow-auto">
          {isMarkdown ? (
            <Markdown>{source.text}</Markdown>
          ) : (
            <pre className="whitespace-pre-wrap font-sans">{source.text}</pre>
          )}
        </CardContent>
      </Card>
      
      {/* Additional metadata */}
      {additionalMetadata.length > 0 && (
        <div className="space-y-2">
          <Button 
            variant="ghost" 
            size="sm"
            className="flex items-center gap-1 px-0"
            onClick={() => setShowAllMetadata(prev => !prev)}
          >
            {showAllMetadata ? <FiChevronUp /> : <FiChevronDown />}
            {showAllMetadata ? 'Detayları Gizle' : 'Tüm Metadata Detaylarını Göster'}
          </Button>
          
          {showAllMetadata && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
              {additionalMetadata.map(([key, value]) => (
                <div key={key} className="bg-gray-50 dark:bg-gray-800 p-2 rounded">
                  <span className="font-medium text-gray-600 dark:text-gray-400">{key}: </span>
                  <span>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default SourceViewer;