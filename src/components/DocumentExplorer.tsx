import { useState, useEffect } from 'react'
import { 
  FiTrash2, FiUpload, FiSearch, FiChevronDown, FiCopy, FiFile,
  FiAlertCircle, FiCheck, FiX, FiLoader
} from 'react-icons/fi'

import { Document, Chunk, DocumentMetadata, ragApi } from '@/lib/api'
import { cn, truncateText, formatDate } from '@/lib/utils'
import FileUploadButton from './FileUploadButton'

interface DocumentExplorerProps {
  className?: string
}

const DocumentExplorer = ({ className }: DocumentExplorerProps) => {
  const [documents, setDocuments] = useState<Document[]>([])
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(10)
  const [totalCount, setTotalCount] = useState(0)
  const [stats, setStats] = useState<any>(null)
  const [notification, setNotification] = useState({ 
    open: false, 
    message: '', 
    type: 'info' as 'info' | 'success' | 'error' | 'warning' 
  })
  
  // Belgeleri yükle
  const loadDocuments = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Belgeleri al
      const result = await ragApi.listDocuments({
        limit: pageSize,
        offset: (page - 1) * pageSize,
        filter_metadata: searchTerm ? { $text: searchTerm } : undefined
      })
      
      setDocuments(result.documents || [])
      setTotalCount(result.total || 0)
      
      // İstatistikleri al
      const statsData = await ragApi.getStats()
      setStats(statsData)
      
      setLoading(false)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Bilinmeyen hata')
      }
      setLoading(false)
    }
  }
  
  // İlk yükleme ve sayfa değişikliklerinde belgeleri yükle
  useEffect(() => {
    void loadDocuments()
  }, [page, pageSize, searchTerm])
  
  // Belge detaylarını yükle
  const loadDocumentDetails = async (documentId: string) => {
    try {
      setLoading(true)
      
      const document = await ragApi.getDocument(documentId)
      setSelectedDocument(document)
      
      setLoading(false)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Bilinmeyen hata')
      }
      setLoading(false)
    }
  }
  
  // Belge silme
  const handleDeleteDocument = async (documentId: string) => {
    try {
      setLoading(true)
      
      await ragApi.deleteDocument(documentId)
      
      // Belgeleri yeniden yükle
      await loadDocuments()
      
      setNotification({ 
        open: true, 
        message: 'Belge başarıyla silindi', 
        type: 'success' 
      })
      
      setLoading(false)
      setConfirmDelete(null)
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      } else {
        setError('Bilinmeyen hata')
      }
      setLoading(false)
      setConfirmDelete(null)
      
      setNotification({ 
        open: true, 
        message: err instanceof Error ? `Hata: ${err.message}` : 'Bilinmeyen hata',
        type: 'error' 
      })
    }
  }
  
  // Dosya yükleme tamamlandı
  const handleFileUploaded = async (result: any) => {
    setNotification({ 
      open: true, 
      message: `Dosya başarıyla yüklendi: ${result.document_id}`, 
      type: 'success' 
    })
    
    // Belgeleri yeniden yükle
    await loadDocuments()
  }
  
  // Sayfa değiştirme
  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }
  
  // Belge görüntüleme
  const handleViewDocument = (documentId: string) => {
    if (expandedDocId === documentId) {
      setExpandedDocId(null)
    } else {
      setExpandedDocId(documentId)
      void loadDocumentDetails(documentId)
    }
  }
  
  // Bildirimi kapat
  const closeNotification = () => {
    setNotification({ ...notification, open: false })
  }
  
  return (
    <div className={cn("bg-white rounded-lg border shadow-sm", className)}>
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Belgeler</h2>
          <FileUploadButton 
            onFileUploaded={handleFileUploaded}
            onError={(err) => setNotification({ open: true, message: err, type: 'error' })}
          />
        </div>
        
        {stats && (
          <div className="mb-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Toplam Belge</h3>
                  <p className="text-2xl font-semibold">{stats.total_documents}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Toplam Chunk</h3>
                  <p className="text-2xl font-semibold">{stats.total_chunks}</p>
                </div>
                <div>
                  <h3 className="text-sm font-medium text-gray-500">Vector Boyutu</h3>
                  <p className="text-2xl font-semibold">{stats.dimensions}</p>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div className="mb-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <FiSearch className="text-gray-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Belge ara..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </div>
        
        {loading && documents.length === 0 ? (
          <div className="flex justify-center items-center py-12">
            <div className="w-10 h-10 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
            <div className="flex items-center">
              <FiAlertCircle className="mr-2" size={18} />
              <span>{error}</span>
            </div>
          </div>
        ) : documents.length === 0 ? (
          <div className="text-center bg-gray-50 rounded-lg py-12">
            <FiFile size={48} className="mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-600 mb-2">
              Henüz hiç belge eklenmemiş
            </h3>
            <p className="text-gray-500 mb-4">
              Belgelerinizi yükleyerek başlayın
            </p>
            <FileUploadButton 
              onFileUploaded={handleFileUploaded}
              onError={(err) => setNotification({ open: true, message: err, type: 'error' })}
              variant="primary"
            />
          </div>
        ) : (
          <>
            <div className="overflow-x-auto border rounded-lg mb-4">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Belge ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Başlık
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Tür
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Parça Sayısı
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      İşlemler
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {documents.map((doc) => (
                    <tr 
                      key={doc.id} 
                      className={cn(
                        "hover:bg-gray-50 cursor-pointer", 
                        expandedDocId === doc.id && "bg-blue-50 hover:bg-blue-50"
                      )}
                    >
                      <td 
                        className="px-4 py-3 whitespace-nowrap"
                        onClick={() => handleViewDocument(doc.id)}
                      >
                        <span className="text-sm font-mono text-gray-600 bg-gray-100 px-2 py-1 rounded">
                          {truncateText(doc.id, 12)}
                        </span>
                      </td>
                      <td 
                        className="px-4 py-3 whitespace-nowrap text-sm"
                        onClick={() => handleViewDocument(doc.id)}
                      >
                        {doc.metadata?.title || 'İsimsiz'}
                      </td>
                      <td 
                        className="px-4 py-3 whitespace-nowrap"
                        onClick={() => handleViewDocument(doc.id)}
                      >
                        <span className="px-2 py-1 text-xs font-medium rounded-full bg-primary-100 text-primary-800">
                          {doc.metadata?.source_type || doc.metadata?.file_type || 'Bilinmiyor'}
                        </span>
                      </td>
                      <td 
                        className="px-4 py-3 whitespace-nowrap text-center text-sm"
                        onClick={() => handleViewDocument(doc.id)}
                      >
                        {doc.chunks?.length || 0}
                      </td>
                      <td className="px-4 py-3 whitespace-nowrap text-right text-sm">
                        <button 
                          className="p-1.5 text-red-600 hover:text-red-800 hover:bg-red-100 rounded"
                          onClick={(e) => {
                            e.stopPropagation()
                            setConfirmDelete(doc.id)
                          }}
                          title="Belgeyi Sil"
                        >
                          <FiTrash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            
            {/* Sayfalama */}
            {totalCount > pageSize && (
              <div className="flex justify-center mt-4">
                <div className="flex items-center space-x-2">
                  {Array.from({ length: Math.ceil(totalCount / pageSize) }).map((_, i) => (
                    <button
                      key={i}
                      className={cn(
                        "px-3 py-1 rounded text-sm",
                        page === i + 1
                          ? "bg-primary-600 text-white"
                          : "bg-white border hover:bg-gray-50"
                      )}
                      onClick={() => handlePageChange(i + 1)}
                    >
                      {i + 1}
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {/* Belge Detayları */}
            {expandedDocId && selectedDocument && (
              <div className="mt-4 bg-gray-50 p-4 rounded-lg border">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-medium">Belge Detayları</h3>
                  <button
                    onClick={() => setExpandedDocId(null)}
                    className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                  >
                    <FiX size={18} />
                  </button>
                </div>
                
                {loading ? (
                  <div className="flex justify-center py-4">
                    <div className="w-8 h-8 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
                  </div>
                ) : (
                  <>
                    <div className="mb-4">
                      <h4 className="text-sm font-medium text-gray-500 mb-2">Metadata</h4>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 bg-white p-3 rounded border">
                        {Object.entries(selectedDocument.metadata || {}).map(([key, value]) => (
                          <div key={key} className="overflow-hidden">
                            <span className="text-xs font-medium text-gray-500 block">{key}</span>
                            <span className="text-sm truncate block">
                              {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div>
                      <h4 className="text-sm font-medium text-gray-500 mb-2">
                        Metin Parçaları ({selectedDocument.chunks?.length || 0})
                      </h4>
                      
                      <div className="space-y-3">
                        {selectedDocument.chunks?.map((chunk, index) => (
                          <div key={chunk.id} className="border rounded-lg bg-white overflow-hidden">
                            <div 
                              className="flex justify-between items-center p-3 bg-gray-50 border-b cursor-pointer"
                              onClick={() => {
                                // Akordiyon işlevi için durum ekle
                                const elem = document.getElementById(`chunk-content-${chunk.id}`)
                                if (elem) {
                                  elem.classList.toggle('hidden')
                                }
                              }}
                            >
                              <div className="flex items-center">
                                <FiChevronDown className="mr-2 text-gray-500" />
                                <span className="font-medium text-sm">Parça {index + 1}</span>
                                <span className="ml-2 text-xs text-gray-500 font-mono">{chunk.id}</span>
                              </div>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  navigator.clipboard.writeText(chunk.text)
                                  setNotification({
                                    open: true,
                                    message: 'Metin panoya kopyalandı',
                                    type: 'success'
                                  })
                                }}
                                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                                title="Metni Kopyala"
                              >
                                <FiCopy size={14} />
                              </button>
                            </div>
                            <div id={`chunk-content-${chunk.id}`} className="p-3 text-sm whitespace-pre-wrap hidden">
                              {chunk.text}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
      
      {/* Silme Onay Modalı */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-medium mb-3">Belgeyi Sil</h3>
            <p className="text-gray-600 mb-4">
              Bu belgeyi silmek istediğinizden emin misiniz? Bu işlem geri alınamaz.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-gray-800"
                disabled={loading}
              >
                İptal
              </button>
              <button
                onClick={() => void handleDeleteDocument(confirmDelete)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white flex items-center"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    <span>İşleniyor...</span>
                  </>
                ) : (
                  <span>Sil</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Bildirim */}
      {notification.open && (
        <div className="fixed bottom-4 right-4 z-50">
          <div 
            className={cn(
              "rounded-lg shadow-lg p-4 max-w-md flex items-start",
              notification.type === 'success' && "bg-green-50 border border-green-200",
              notification.type === 'error' && "bg-red-50 border border-red-200",
              notification.type === 'warning' && "bg-yellow-50 border border-yellow-200",
              notification.type === 'info' && "bg-blue-50 border border-blue-200"
            )}
          >
            <div className="mr-3 mt-0.5">
              {notification.type === 'success' && <FiCheck className="text-green-500" size={18} />}
              {notification.type === 'error' && <FiAlertCircle className="text-red-500" size={18} />}
              {notification.type === 'warning' && <FiAlertCircle className="text-yellow-500" size={18} />}
              {notification.type === 'info' && <FiAlertCircle className="text-blue-500" size={18} />}
            </div>
            <div className="flex-1 mr-2">
              <p className={cn(
                "text-sm",
                notification.type === 'success' && "text-green-800",
                notification.type === 'error' && "text-red-800",
                notification.type === 'warning' && "text-yellow-800",
                notification.type === 'info' && "text-blue-800"
              )}>
                {notification.message}
              </p>
            </div>
            <button
              onClick={closeNotification}
              className="p-1 text-gray-500 hover:text-gray-700 rounded"
            >
              <FiX size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocumentExplorer