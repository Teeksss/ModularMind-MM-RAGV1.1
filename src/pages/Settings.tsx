import { useState } from 'react'
import { FiSave, FiAlertCircle, FiRefreshCw, FiUpload, FiDownload, FiDatabase, FiTrash2 } from 'react-icons/fi'

import { adminApi } from '@/lib/api'
import { cn } from '@/lib/utils'

const Settings = () => {
  const [activeTab, setActiveTab] = useState('general') // general, vectors, security, backup
  const [loading, setLoading] = useState(false)
  const [notification, setNotification] = useState<{
    show: boolean;
    message: string;
    type: 'success' | 'error' | 'info';
  }>({
    show: false,
    message: '',
    type: 'info'
  })
  
  // Ayarlar formları
  const [generalSettings, setGeneralSettings] = useState({
    apiUrl: 'http://localhost:8000/api',
    defaultEmbeddingModel: 'openai',
    defaultLLMModel: 'gpt-4o',
    chunkSize: 500,
    chunkOverlap: 50,
    systemMessage: 'Yardımcı bir AI asistanısın.'
  })
  
  // Bildirim göster
  const showNotification = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setNotification({
      show: true,
      message,
      type
    })
    
    // 5 saniye sonra kapat
    setTimeout(() => {
      setNotification(prev => ({ ...prev, show: false }))
    }, 5000)
  }
  
  // İndeksleri yeniden oluştur
  const handleRebuildIndices = async () => {
    try {
      setLoading(true)
      const result = await adminApi.rebuildIndices()
      showNotification('İndeksler yeniden oluşturuluyor. Bu işlem birkaç dakika sürebilir.', 'success')
      setLoading(false)
    } catch (err) {
      showNotification(
        err instanceof Error ? `Hata: ${err.message}` : 'İndeksler yeniden oluşturulurken bir hata oluştu',
        'error'
      )
      setLoading(false)
    }
  }
  
  // Ayarları kaydet
  const handleSaveGeneralSettings = () => {
    // Ayarları kaydetme simülasyonu
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      showNotification('Ayarlar başarıyla kaydedildi', 'success')
    }, 1000)
  }
  
  return (
    <div className="max-w-7xl mx-auto">
      <div className="bg-white rounded-lg border shadow-sm mb-6">
        <div className="p-4 border-b">
          <h1 className="text-xl font-bold">Ayarlar</h1>
        </div>
        
        <div className="flex flex-col sm:flex-row">
          {/* Sidebar */}
          <div className="w-full sm:w-64 border-b sm:border-b-0 sm:border-r">
            <nav className="p-2">
              <button
                onClick={() => setActiveTab('general')}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-sm font-medium",
                  activeTab === 'general' 
                    ? "bg-primary-50 text-primary-700" 
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                Genel Ayarlar
              </button>
              <button
                onClick={() => setActiveTab('vectors')}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-sm font-medium",
                  activeTab === 'vectors' 
                    ? "bg-primary-50 text-primary-700" 
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                Vektör Veritabanı
              </button>
              <button
                onClick={() => setActiveTab('security')}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-sm font-medium",
                  activeTab === 'security' 
                    ? "bg-primary-50 text-primary-700" 
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                Güvenlik & API Anahtarları
              </button>
              <button
                onClick={() => setActiveTab('backup')}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg text-sm font-medium",
                  activeTab === 'backup' 
                    ? "bg-primary-50 text-primary-700" 
                    : "text-gray-700 hover:bg-gray-100"
                )}
              >
                Yedekleme & Geri Yükleme
              </button>
            </nav>
          </div>
          
          {/* İçerik */}
          <div className="flex-1 p-6">
            {/* Bildirim */}
            {notification.show && (
              <div className={cn(
                "mb-6 px-4 py-3 rounded-lg",
                notification.type === 'success' && "bg-green-50 border border-green-200 text-green-700",
                notification.type === 'error' && "bg-red-50 border border-red-200 text-red-700",
                notification.type === 'info' && "bg-blue-50 border border-blue-200 text-blue-700"
              )}>
                <div className="flex">
                  <div className="flex-shrink-0">
                    <FiAlertCircle className={cn(
                      "h-5 w-5",
                      notification.type === 'success' && "text-green-500",
                      notification.type === 'error' && "text-red-500",
                      notification.type === 'info' && "text-blue-500"
                    )} />
                  </div>
                  <div className="ml-3">
                    <p className="text-sm">{notification.message}</p>
                  </div>
                </div>
              </div>
            )}
            
            {/* Genel Ayarlar */}
            {activeTab === 'general' && (
              <div>
                <h2 className="text-lg font-medium mb-4">Genel Ayarlar</h2>
                
                <div className="space-y-6">
                  <div>
                    <label htmlFor="apiUrl" className="block text-sm font-medium text-gray-700 mb-1">
                      API URL
                    </label>
                    <input
                      type="text"
                      id="apiUrl"
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                      value={generalSettings.apiUrl}
                      onChange={(e) => setGeneralSettings(prev => ({
                        ...prev,
                        apiUrl: e.target.value
                      }))}
                    />
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="defaultEmbeddingModel" className="block text-sm font-medium text-gray-700 mb-1">
                        Varsayılan Embedding Modeli
                      </label>
                      <select
                        id="defaultEmbeddingModel"
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                        value={generalSettings.defaultEmbeddingModel}
                        onChange={(e) => setGeneralSettings(prev => ({
                          ...prev,
                          defaultEmbeddingModel: e.target.value
                        }))}
                      >
                        <option value="openai">OpenAI Embeddings</option>
                        <option value="local">Yerel Model</option>
                        <option value="sentence-transformers">Sentence Transformers</option>
                      </select>
                    </div>
                    
                    <div>
                      <label htmlFor="defaultLLMModel" className="block text-sm font-medium text-gray-700 mb-1">
                        Varsayılan LLM Modeli
                      </label>
                      <select
                        id="defaultLLMModel"
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                        value={generalSettings.defaultLLMModel}
                        onChange={(e) => setGeneralSettings(prev => ({
                          ...prev,
                          defaultLLMModel: e.target.value
                        }))}
                      >
                        <option value="gpt-4o">GPT-4o</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                        <option value="claude-3-opus">Claude 3 Opus</option>
                        <option value="llama-3-70b">Llama 3 70B</option>
                      </select>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label htmlFor="chunkSize" className="block text-sm font-medium text-gray-700 mb-1">
                        Varsayılan Chunk Boyutu
                      </label>
                      <input
                        type="number"
                        id="chunkSize"
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                        value={generalSettings.chunkSize}
                        onChange={(e) => setGeneralSettings(prev => ({
                          ...prev,
                          chunkSize: parseInt(e.target.value) || 0
                        }))}
                      />
                    </div>
                    
                    <div>
                      <label htmlFor="chunkOverlap" className="block text-sm font-medium text-gray-700 mb-1">
                        Varsayılan Chunk Örtüşmesi
                      </label>
                      <input
                        type="number"
                        id="chunkOverlap"
                        className="w-full px-3 py-2 border rounded-lg text-sm"
                        value={generalSettings.chunkOverlap}
                        onChange={(e) => setGeneralSettings(prev => ({
                          ...prev,
                          chunkOverlap: parseInt(e.target.value) || 0
                        }))}
                      />
                    </div>
                  </div>
                  
                  <div>
                    <label htmlFor="systemMessage" className="block text-sm font-medium text-gray-700 mb-1">
                      Varsayılan Sistem Mesajı
                    </label>
                    <textarea
                      id="systemMessage"
                      rows={3}
                      className="w-full px-3 py-2 border rounded-lg text-sm"
                      value={generalSettings.systemMessage}
                      onChange={(e) => setGeneralSettings(prev => ({
                        ...prev,
                        systemMessage: e.target.value
                      }))}
                    />
                  </div>
                  
                  <div className="flex justify-end">
                    <button
                      onClick={handleSaveGeneralSettings}
                      disabled={loading}
                      className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-primary-700 disabled:bg-primary-400"
                    >
                      {loading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                          <span>Kaydediliyor...</span>
                        </>
                      ) : (
                        <>
                          <FiSave size={16} className="mr-2" />
                          <span>Kaydet</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Vektör Veritabanı */}
            {activeTab === 'vectors' && (
              <div>
                <h2 className="text-lg font-medium mb-4">Vektör Veritabanı</h2>
                
                <div className="mb-6 bg-gray-50 p-4 rounded-lg border">
                  <h3 className="text-sm font-medium mb-2">İndeks Bilgileri</h3>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <p className="text-xs text-gray-500">İndeks Tipi</p>
                      <p className="text-sm font-medium">HNSW</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Vektör Boyutu</p>
                      <p className="text-sm font-medium">1536</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Benzerlik Metriği</p>
                      <p className="text-sm font-medium">Kosinüs Benzerliği</p>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <button
                    onClick={handleRebuildIndices}
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-blue-700 disabled:bg-blue-400"
                  >
                    {loading ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                        <span>İşleniyor...</span>
                      </>
                    ) : (
                      <>
                        <FiRefreshCw size={16} className="mr-2" />
                        <span>İndeksleri Yeniden Oluştur</span>
                      </>
                    )}
                  </button>
                  
                  <button className="px-4 py-2 border border-red-600 text-red-600 rounded-lg text-sm font-medium inline-flex items-center hover:bg-red-50">
                    <FiTrash2 size={16} className="mr-2" />
                    <span>Tüm Vektörleri Temizle</span>
                  </button>
                </div>
              </div>
            )}
            
            {/* Güvenlik & API Anahtarları */}
            {activeTab === 'security' && (
              <div>
                <h2 className="text-lg font-medium mb-4">Güvenlik & API Anahtarları</h2>
                
                <div className="mb-6 bg-gray-50 p-4 rounded-lg border">
                  <h3 className="text-sm font-medium mb-2">API Anahtarı</h3>
                  <div className="flex items-center">
                    <input
                      type="password"
                      value="••••••••••••••••••••••••••••••"
                      readOnly
                      className="flex-1 px-3 py-2 border rounded-lg text-sm bg-gray-100"
                    />
                    <button className="ml-2 px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium hover:bg-primary-700">
                      Göster
                    </button>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-primary-700">
                    <FiRefreshCw size={16} className="mr-2" />
                    <span>Yeni API Anahtarı Oluştur</span>
                  </button>
                </div>
              </div>
            )}
            
            {/* Yedekleme & Geri Yükleme */}
            {activeTab === 'backup' && (
              <div>
                <h2 className="text-lg font-medium mb-4">Yedekleme & Geri Yükleme</h2>
                
                <div className="space-y-6">
                  <div className="p-4 bg-gray-50 rounded-lg border">
                    <h3 className="text-sm font-medium mb-2">Manuel Yedekleme</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      Tüm veri tabanını, konnektör ve ajan yapılandırmalarını içeren bir yedek oluşturun.
                    </p>
                    <button className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-primary-700">
                      <FiDownload size={16} className="mr-2" />
                      <span>Yedek Oluştur</span>
                    </button>
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg border">
                    <h3 className="text-sm font-medium mb-2">Yedekten Geri Yükleme</h3>
                    <p className="text-sm text-gray-600 mb-4">
                      Önceden oluşturulmuş bir yedekten sistemi geri yükleyin.
                    </p>
                    <div className="flex items-center">
                      <input
                        type="file"
                        className="hidden"
                        id="backup-file"
                      />
                      <label
                        htmlFor="backup-file"
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-blue-700 cursor-pointer"
                      >
                        <FiUpload size={16} className="mr-2" />
                        <span>Yedek Seç</span>
                      </label>
                    </div>
                  </div>
                  
                  <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                    <h3 className="text-sm font-medium text-red-700 mb-2">Tehlikeli İşlemler</h3>
                    <p className="text-sm text-red-600 mb-4">
                      Bu işlemler geri alınamaz ve veri kaybına neden olabilir. Dikkatli kullanın.
                    </p>
                    <button className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-red-700">
                      <FiDatabase size={16} className="mr-2" />
                      <span>Sistemi Sıfırla</span>
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings