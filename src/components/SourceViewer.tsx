import React, { useState } from 'react'
import { FiExternalLink, FiCopy, FiChevronDown, FiChevronUp } from 'react-icons/fi'
import { QuerySource } from '@/lib/api'
import { cn, truncateText } from '@/lib/utils'

interface SourceViewerProps {
  sources: QuerySource[]
  className?: string
  maxInitialSources?: number
  onSourceClick?: (source: QuerySource) => void
}

const SourceViewer: React.FC<SourceViewerProps> = ({
  sources,
  className,
  maxInitialSources = 3,
  onSourceClick
}) => {
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null)
  const [showAllSources, setShowAllSources] = useState(false)
  
  if (!sources || sources.length === 0) {
    return null
  }
  
  const visibleSources = showAllSources ? sources : sources.slice(0, maxInitialSources)
  
  const handleCopySource = (text: string, event: React.MouseEvent) => {
    event.stopPropagation()
    navigator.clipboard.writeText(text)
      .then(() => {
        // Kopya bildirimini göstermek için burada bir state güncellemesi yapılabilir
      })
      .catch((err) => {
        console.error('Metin kopyalama hatası:', err)
      })
  }
  
  const handleSourceClick = (source: QuerySource) => {
    if (expandedSourceId === source.chunk_id) {
      setExpandedSourceId(null)
    } else {
      setExpandedSourceId(source.chunk_id)
    }
    
    if (onSourceClick) {
      onSourceClick(source)
    }
  }
  
  return (
    <div className={cn("mt-4", className)}>
      <h3 className="text-sm font-medium text-gray-700 mb-2">
        Kaynaklar ({sources.length})
      </h3>
      
      <div className="space-y-2">
        {visibleSources.map((source) => (
          <div 
            key={source.chunk_id}
            className="border rounded-lg overflow-hidden bg-white hover:border-primary-300 transition-colors cursor-pointer"
            onClick={() => handleSourceClick(source)}
          >
            <div className="flex justify-between items-start p-3">
              <div className="flex-1">
                <div className="flex items-center">
                  <h4 className="text-sm font-medium">
                    {source.metadata?.title || 'İsimsiz Kaynak'}
                  </h4>
                  {source.metadata?.url && (
                    <a 
                      href={source.metadata.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="ml-2 text-primary-600 hover:text-primary-800" 
                      onClick={(e) => e.stopPropagation()}
                    >
                      <FiExternalLink size={14} />
                    </a>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-1">
                  {source.metadata?.source_type || 'Belge'}
                  {source.metadata?.created_at && ` • ${new Date(source.metadata.created_at).toLocaleDateString()}`}
                </p>
              </div>
              
              <div className="flex items-center space-x-1">
                <button
                  onClick={(e) => handleCopySource(source.text_snippet, e)}
                  className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                  title="Metni Kopyala"
                >
                  <FiCopy size={14} />
                </button>
                {expandedSourceId === source.chunk_id ? (
                  <FiChevronUp size={16} className="text-gray-400" />
                ) : (
                  <FiChevronDown size={16} className="text-gray-400" />
                )}
              </div>
            </div>
            
            {expandedSourceId === source.chunk_id && (
              <div className="border-t p-3 bg-gray-50">
                <div className="text-sm text-gray-800 whitespace-pre-wrap">
                  {source.text_snippet}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      
      {sources.length > maxInitialSources && (
        <button
          onClick={() => setShowAllSources(!showAllSources)}
          className="mt-2 text-sm text-primary-600 hover:text-primary-800 flex items-center"
        >
          {showAllSources ? (
            <>
              <FiChevronUp size={16} className="mr-1" />
              Daha az göster
            </>
          ) : (
            <>
              <FiChevronDown size={16} className="mr-1" />
              {sources.length - maxInitialSources} kaynak daha göster
            </>
          )}
        </button>
      )}
    </div>
  )
}

export default SourceViewer