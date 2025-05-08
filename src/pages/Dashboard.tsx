import { useState, useEffect } from 'react'
import { FiDatabase, FiFile, FiUsers, FiMessageSquare, FiArchive } from 'react-icons/fi'

import ChatBox from '@/components/ChatBox'
import DocumentExplorer from '@/components/DocumentExplorer'
import { adminApi, embeddingApi, llmApi } from '@/lib/api'
import { cn } from '@/lib/utils'

const Dashboard = () => {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stats, setStats] = useState<any>(null)
  const [activeTab, setActiveTab] = useState(0)
  const [models, setModels] = useState({
    embedding: [] as any[],
    llm: [] as any[]
  })
  
  // Sistem istatistiklerini ve modelleri yükle
  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true)
        
        // Paralel istekler
        const [statsResponse, embeddingModels, llmModels] = await Promise.all([
          adminApi.getSystemStats(),
          embeddingApi.getModels(),
          llmApi.getModels()
        ])
        
        setStats(statsResponse)
        setModels({
          embedding: embeddingModels,
          llm: llmModels
        })
        
        setLoading(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Veri yükleme hatası')
        setLoading(false)
      }
    }
    
    void loadData()
  }, [])
  
  // Tab değişikliği
  const handleTabChange = (index: number) => {
    setActiveTab(index)
  }
  
  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {loading ? (
        <div className="flex justify-center items-center min-h-[300px]">
          <div className="w-12 h-12 border-4 border-primary-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
          <p>{error}</p>
        </div>
      ) : (
        <div>
          {/* İstatistik Kartları */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Veri Deposu</h2>
                  <p className="text-sm text-gray-500">Doküman ve vektör bilgileri</p>
                </div>
                <div className="bg-primary-100 p-3 rounded-full">
                  <FiDatabase className="text-primary-700" size={20} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-2">
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.vector_store?.total_documents || 0}
                  </p>
                  <p className="text-xs text-gray-500">Belge</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.vector_store?.total_chunks || 0}
                  </p>
                  <p className="text-xs text-gray-500">Parça</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.vector_store?.dimensions || 0}
                  </p>
                  <p className="text-xs text-gray-500">Boyut</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Veri Ajanları</h2>
                  <p className="text-sm text-gray-500">Otomatik veri toplama</p>
                </div>
                <div className="bg-green-100 p-3 rounded-full">
                  <FiUsers className="text-green-700" size={20} />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 mt-2">
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.agents?.total_agents || 0}
                  </p>
                  <p className="text-xs text-gray-500">Toplam</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.agents?.enabled_agents || 0}
                  </p>
                  <p className="text-xs text-gray-500">Aktif</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-700">
                    {stats?.agents?.successful_runs || 0}
                  </p>
                  <p className="text-xs text-gray-500">Başarılı</p>
                </div>
              </div>
            </div>
            
            <div className="bg-white rounded-lg border shadow-sm p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Konnektörler</h2>
                  <p className="text-sm text-gray-500">Veri kaynağı bağlantıları</p>
                </div>
                <div className="bg-purple-100 p-3 rounded-full">
                  <FiArchive className="text-purple-700" size={20} />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.connectors?.total_connectors || 0}
                  </p>
                  <p className="text-xs text-gray-500">Toplam</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-gray-900">
                    {stats?.connectors?.active_connectors || 0}
                  </p>
                  <p className="text-xs text-gray-500">Aktif</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* Sekmeler */}
          <div className="bg-white rounded-lg border shadow-sm overflow-hidden mb-8">
            <div className="flex border-b">
              <button
                className={cn(
                  "px-4 py-3 text-sm font-medium", 
                  activeTab === 0 
                    ? "border-b-2 border-primary-600 text-primary-600" 
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                )}
                onClick={() => handleTabChange(0)}
              >
                <div className="flex items-center">
                  <FiFile className="mr-2" />
                  <span>Doküman Yönetimi</span>
                </div>
              </button>
              <button
                className={cn(
                  "px-4 py-3 text-sm font-medium", 
                  activeTab === 1 
                    ? "border-b-2 border-primary-600 text-primary-600" 
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                )}
                onClick={() => handleTabChange(1)}
              >
                <div className="flex items-center">
                  <FiMessageSquare className="mr-2" />
                  <span>RAG Chat</span>
                </div>
              </button>
              <button
                className={cn(
                  "px-4 py-3 text-sm font-medium", 
                  activeTab === 2 
                    ? "border-b-2 border-primary-600 text-primary-600" 
                    : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                )}
                onClick={() => handleTabChange(2)}
              >
                <div className="flex items-center">
                  <FiMessageSquare className="mr-2" />
                  <span>LLM Chat</span>
                </div>
              </button>
            </div>
            
            <div className="p-6">
              {activeTab === 0 && (
                <DocumentExplorer />
              )}
              
              {activeTab === 1 && (
                <div>
                  <div className="mb-4">
                    <h2 className="text-lg font-medium text-gray-900 mb-2">RAG Chat</h2>
                    <p className="text-sm text-gray-600 mb-4">
                      Veri tabanınızdan bilgi alarak sorularınızı cevaplayan AI asistanı
                    </p>
                  </div>
                  <ChatBox 
                    modelId="gpt-4o"
                    systemMessage="Verilen dokümanlardan bilgi çekerek detaylı cevaplar veren yardımcı bir asistansın."
                    ragEnabled={true}
                  />
                </div>
              )}
              
              {activeTab === 2 && (
                <div>
                  <div className="mb-4">
                    <h2 className="text-lg font-medium text-gray-900 mb-2">LLM Chat</h2>
                    <p className="text-sm text-gray-600 mb-4">
                      Doğrudan LLM ile konuşun (veri tabanı kullanılmıyor)
                    </p>
                  </div>
                  <ChatBox 
                    modelId="gpt-4o"
                    systemMessage="Yardımcı bir AI asistanısın."
                    ragEnabled={false}
                  />
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard