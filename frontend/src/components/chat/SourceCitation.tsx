import React, { useState } from 'react';
import { FaExternalLinkAlt, FaInfoCircle, FaBookOpen } from 'react-icons/fa';
import { useChatStore } from '../../store/chatStore';
import { useDocumentStore } from '../../store/documentStore';

interface CitationSource {
  id: string;
  text: string;
  source_id: string;
  source_title?: string;
  source_url?: string;
}

interface SourceCitationProps {
  citation: CitationSource;
}

const SourceCitation: React.FC<SourceCitationProps> = ({ citation }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [sourceDetails, setSourceDetails] = useState<Record<string, any> | null>(null);
  
  const { fetchSource } = useChatStore();
  const { fetchDocument } = useDocumentStore();
  
  // Toggle citation details visibility
  const toggleExpanded = async () => {
    if (!isExpanded && !sourceDetails) {
      setIsLoading(true);
      try {
        // Try to get source from chat store first
        const source = await fetchSource(citation.source_id);
        
        if (source) {
          setSourceDetails(source);
        } else {
          // Fall back to document store if available
          const document = await fetchDocument(citation.source_id);
          if (document) {
            setSourceDetails(document);
          }
        }
      } catch (error) {
        console.error("Error fetching source details:", error);
      } finally {
        setIsLoading(false);
      }
    }
    setIsExpanded(!isExpanded);
  };
  
  // Open source document in viewer
  const openDocument = () => {
    if (sourceDetails) {
      // This would typically navigate to document viewer
      // e.g., navigate(`/documents/${citation.source_id}`);
      window.open(`/documents/${citation.source_id}`, '_blank');
    }
  };
  
  // Truncate text to a certain length
  const truncateText = (text: string, maxLength: number = 150) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };
  
  return (
    <div className="source-citation text-sm">
      <div 
        className="flex items-start cursor-pointer text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400"
        onClick={toggleExpanded}
      >
        <FaInfoCircle className="mt-0.5 mr-1 flex-shrink-0" />
        <span className="font-medium">
          {citation.source_title || `Source ${citation.source_id.substring(0, 8)}`}
        </span>
      </div>
      
      {isExpanded && (
        <div className="mt-1 ml-5 p-2 bg-gray-100 dark:bg-gray-800 rounded text-xs">
          {isLoading ? (
            <div className="flex justify-center py-2">
              <div className="animate-spin h-4 w-4 border-2 border-blue-500 rounded-full border-t-transparent"></div>
            </div>
          ) : (
            <>
              <div className="text-gray-700 dark:text-gray-300">
                <div className="italic mb-1">{truncateText(citation.text)}</div>
                
                {sourceDetails && (
                  <div className="mt-2 flex flex-col space-y-1">
                    {sourceDetails.title && (
                      <div><span className="font-semibold">Title:</span> {sourceDetails.title}</div>
                    )}
                    {sourceDetails.content_type && (
                      <div><span className="font-semibold">Type:</span> {sourceDetails.content_type}</div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="mt-2 flex space-x-2">
                <button
                  onClick={openDocument}
                  className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center"
                >
                  <FaBookOpen className="mr-1" size={12} />
                  <span>Open Document</span>
                </button>
                
                {(sourceDetails?.url || citation.source_url) && (
                  <a
                    href={sourceDetails?.url || citation.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <FaExternalLinkAlt className="mr-1" size={12} />
                    <span>External Link</span>
                  </a>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default SourceCitation;