import { useState } from 'react'
import { FiUpload, FiX, FiAlertCircle } from 'react-icons/fi'

import { ragApi } from '@/lib/api'
import { cn, formatFileSize } from '@/lib/utils'

interface FileUploadButtonProps {
  onFileUploaded?: (result: any) => void
  onError?: (message: string) => void
  className?: string
  variant?: 'default' | 'primary' | 'outline'
  size?: 'sm' | 'md' | 'lg'
}

const FileUploadButton = ({ 
  onFileUploaded, 
  onError, 
  className,
  variant = 'default',
  size = 'md'
}: FileUploadButtonProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [options, setOptions] = useState({
    chunkSize: 500,
    chunkOverlap: 50,
    embeddingModel: ''
  })
  
  // Dialog aç
  const handleOpen = () => {
    setIsOpen(true)
    setSelectedFile(null)
    setUploading(false)
    setProgress(0)
    setError(null)
  }
  
  // Dialog kapat
  const handleClose = () => {
    setIsOpen(false)
  }
  
  // Dosya seçimi
  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setSelectedFile(event.target.files[0])
      setError(null)
    }
  }
  
  // Dosya yükleme
  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Lütfen bir dosya seçin')
      return
    }
    
    try {
      setUploading(true)
      setProgress(0)
      setError(null)
      
      // Dosya tipini kontrol et
      const validExtensions = ['.txt', '.pdf', '.docx', '.md', '.csv', '.html']
      const extension = selectedFile.name.substring(selectedFile.name.lastIndexOf('.')).toLowerCase()
      
      if (!validExtensions.includes(extension)) {
        throw new Error(`Desteklenmeyen dosya türü: ${extension}. Desteklenen türler: ${validExtensions.join(', ')}`)
      }
      
      // İlerleme simulasyonu
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 500)
      
      // Dosyayı yükle
      const result = await ragApi.uploadFile(selectedFile, {
        chunk_size: options.chunkSize,
        chunk_overlap: options.chunkOverlap,
        embedding_model: options.embeddingModel || undefined
      })
      
      clearInterval(progressInterval)
      setProgress(100)
      
      // Sonucu bildir
      if (onFileUploaded) {
        onFileUploaded(result)
      }
      
      // Dialog kapat
      setTimeout(() => {
        setIsOpen(false)
        setUploading(false)
      }, 1000)
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Dosya yükleme hatası'
      setError(errorMessage)
      setUploading(false)
      
      if (onError) {
        onError(errorMessage)
      }
    }
  }
  
  // Buton stilleri
  const buttonStyles = cn(
    "rounded-lg font-medium flex items-center",
    size === 'sm' && "text-sm px-2.5 py-1.5",
    size === 'md' && "px-4 py-2",
    size === 'lg' && "text-lg px-5 py-2.5",
    variant === 'default' && "bg-white border border-gray-300 text-gray-700 hover:bg-gray-50",
    variant === 'primary' && "bg-primary-600 text-white hover:bg-primary-700",
    variant === 'outline' && "bg-transparent border border-primary-600 text-primary-600 hover:bg-primary-50",
    className
  )
  
  return (
    <>
      <button
        onClick={handleOpen}
        className={buttonStyles}
      >
        <FiUpload className="mr-2" size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />
        <span>Dosya Yükle</span>
      </button>
      
      {/* Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Dosya Yükle</h3>
              <button
                onClick={handleClose}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
                disabled={uploading}
              >
                <FiX size={18} />
              </button>
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              Desteklenen dosya tipleri: TXT, PDF, DOCX, MD, CSV, HTML
            </p>
            
            {/* Dosya Seçimi */}
            <div className="mb-4">
              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".txt,.pdf,.docx,.md,.csv,.html"
                onChange={handleFileChange}
                disabled={uploading}
              />
              <label
                htmlFor="file-upload"
                className={cn(
                  "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer",
                  uploading ? "bg-gray-100 border-gray-300" : "hover:bg-gray-50 border-gray-300"
                )}
              >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                  <FiUpload className="w-8 h-8 mb-3 text-gray-400" />
                  <p className="mb-1 text-sm text-gray-500">
                    <span className="font-semibold">Dosya yüklemek için tıklayın</span> veya sürükleyip bırakın
                  </p>
                  <p className="text-xs text-gray-500">
                    (Maksimum 10MB)
                  </p>
                </div>
              </label>
            </div>
            
            {/* Seçilen Dosya Bilgisi */}
            {selectedFile && (
              <div className="flex items-center justify-between bg-gray-50 p-3 rounded-lg mb-4">
                <div className="truncate">
                  <p className="font-medium text-sm truncate">{selectedFile.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(selectedFile.size)}</p>
                </div>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="p-1 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded ml-2"
                  disabled={uploading}
                >
                  <FiX size={16} />
                </button>
              </div>
            )}
            
            {/* Hata Mesajı */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <FiAlertCircle className="h-5 w-5 text-red-500" />
                  </div>
                  <div className="ml-3">
                    <p className="text-sm">{error}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Gelişmiş Ayarlar */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-sm font-medium text-gray-700">Gelişmiş Ayarlar</h4>
              </div>
              
              <div className="grid grid-cols-2 gap-3 mb-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Chunk Boyutu
                  </label>
                  <input
                    type="number"
                    value={options.chunkSize}
                    onChange={(e) => setOptions({
                      ...options,
                      chunkSize: parseInt(e.target.value) || 0
                    })}
                    min={100}
                    max={2000}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                    disabled={uploading}
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">
                    Chunk Örtüşmesi
                  </label>
                  <input
                    type="number"
                    value={options.chunkOverlap}
                    onChange={(e) => setOptions({
                      ...options,
                      chunkOverlap: parseInt(e.target.value) || 0
                    })}
                    min={0}
                    max={200}
                    className="w-full px-3 py-2 border rounded-lg text-sm"
                    disabled={uploading}
                  />
                </div>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">
                  Embedding Modeli
                </label>
                <select
                  value={options.embeddingModel}
                  onChange={(e) => setOptions({
                    ...options,
                    embeddingModel: e.target.value
                  })}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  disabled={uploading}
                >
                  <option value="">Varsayılan</option>
                  <option value="openai">OpenAI Embeddings</option>
                  <option value="local">Yerel Model</option>
                  <option value="sentence-transformers">Sentence Transformers</option>
                </select>
                <p className="mt-1 text-xs text-gray-500">
                  Boş bırakırsanız, sistem varsayılan modeli kullanacak
                </p>
              </div>
            </div>
            
            {/* İlerleme Çubuğu */}
            {uploading && (
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2.5">
                  <div 
                    className="bg-primary-600 h-2.5 rounded-full" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-500 text-center mt-1">
                  Yükleniyor... {progress}%
                </p>
              </div>
            )}
            
            {/* Butonlar */}
            <div className="flex justify-end space-x-3">
              <button
                onClick={handleClose}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg text-gray-800"
                disabled={uploading}
              >
                İptal
              </button>
              <button
                onClick={handleUpload}
                className={cn(
                  "px-4 py-2 rounded-lg text-white",
                  !selectedFile || uploading
                    ? "bg-primary-400 cursor-not-allowed"
                    : "bg-primary-600 hover:bg-primary-700"
                )}
                disabled={!selectedFile || uploading}
              >
                {uploading ? 'Yükleniyor...' : 'Yükle'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default FileUploadButton