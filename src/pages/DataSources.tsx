import { useState, useEffect } from 'react'
import { FiPlus, FiClock, FiDatabase, FiCloud, FiServer, FiGlobe, FiAlertCircle, FiCheck, FiEdit, FiTrash2 } from 'react-icons/fi'

import { agentApi } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Agent {
  agent_id: string
  name: string
  agent_type: string
  description: string
  enabled: boolean
  status: string
  schedule?: string
  last_run?: number
}

interface Connector {
  connector_id: string
  name: string
  connector_type: string
  description: string
  enabled: boolean
  is_connected: boolean
}

const DataSources = () => {
  const [activeTab, setActiveTab] = useState('agents') // agents, connectors
  const [agents, setAgents] = useState<Agent[]>([])
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  // Ajanları yükle
  useEffect(() => {
    const loadData = async () => {
      if (activeTab === 'agents') {
        try {
          setLoading(true)
          const data = await agentApi.listAgents()
          setAgents(data)
          setLoading(false)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Veri yükleme hatası')
          setLoading(false)
        }
      } else if (activeTab === 'connectors') {
        // Burada konnektörleri yükle
        try {
          setLoading(true)
          // Gerçek uygulama için konnektör API çağrısı eklenecek
          // Örnek veri:
          const mockConnectors: Connector[] = [
            {
              connector_id: "conn-1",
              name: "PostgreSQL Database",
              connector_type: "database",
              description: "Main database connection",
              enabled: true,
              is_connected: true
            },
            {
              connector_id: "conn-2",
              name: "Company API",
              connector_type: "web_api",
              description: "REST API connection",
              enabled: true,
              is_connected: false
            }
          ]
          setConnectors(mockConnectors)
          setLoading(false)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Veri yükleme hatası')
          setLoading(false)
        }
      }
    }
    
    void loadData()
  }, [activeTab])
  
  // Ajan tipine göre ikon
  const getAgentIcon = (type: string) => {
    switch (type) {
      case 'web_crawler':
        return <FiGlobe className="text-blue-500" />
      case 'database':
        return <FiDatabase className="text-indigo-500" />
      case 'file_system':
        return <FiServer className="text-orange-500" />
      case 'rss_reader':
        return <FiClock className="text-green-500" />
      default:
        return <FiClock className="text-gray-500" />
    }
  }
  
  // Konnektör tipine göre ikon
  const getConnectorIcon = (type: string) => {
    switch (type) {
      case 'database':
        return <FiDatabase className="text-indigo-500" />
      case 'web_api':
        return <FiGlobe className="text-blue-500" />
      case 'cloud_storage':
        return <FiCloud className="text-purple-500" />
      default:
        return <FiServer className="text-gray-500" />
    }
  }
  
  return (
    <div className="max-w-7xl mx-auto">
      <div className="bg-white rounded-lg border shadow-sm mb-6">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold">Veri Kaynakları</h1>
            <button className="px-3 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium flex items-center hover:bg-primary-700">
              <FiPlus size={16} className="mr-1" />
              <span>Yeni Ekle</span>
            </button>
          </div>
        </div>
        
        <div className="px-4 border-b">
          <div className="flex">
            <button
              className={`px-4 py-3 text-sm font-medium ${
                activeTab === 'agents' 
                  ? 'border-b-2 border-primary-600 text-primary-600' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('agents')}
            >
              Veri Ajanları
            </button>
            <button
              className={`px-4 py-3 text-sm font-medium ${
                activeTab === 'connectors' 
                  ? 'border-b-2 border-primary-600 text-primary-600' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('connectors')}
            >
              Konnektörler
            </button>
          </div>
        </div>
        
        <div className="p-4">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="w-10 h-10 border-2 border-primary-600 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : error ? (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4">
              <div className="flex items-center">
                <FiAlertCircle className="mr-2" size={18} />
                <span>{error}</span>
              </div>
            </div>
          ) : activeTab === 'agents' ? (
            <div>
              {agents.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <FiClock size={48} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">
                    Henüz hiç veri ajanı eklenmemiş
                  </h3>
                  <p className="text-gray-500 mb-4">
                    Veri ajanları, farklı kaynaklardan otomatik olarak veri toplar
                  </p>
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-primary-700">
                    <FiPlus size={16} className="mr-2" />
                    <span>Yeni Ajan Ekle</span>
                  </button>
                </div>
              ) : (
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {agents.map((agent) => (
                    <div key={agent.agent_id} className="border rounded-lg hover:shadow-md transition-shadow">
                      <div className="flex items-start p-4">
                        <div className="mr-3 bg-gray-100 p-2 rounded-lg">
                          {getAgentIcon(agent.agent_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-gray-900 truncate">{agent.name}</h3>
                          <p className="text-xs text-gray-500 truncate mt-1">{agent.description || 'Açıklama yok'}</p>
                        </div>
                        <div className="ml-2 flex flex-col items-end">
                          <span 
                            className={cn(
                              "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                              agent.status === 'running' && "bg-green-100 text-green-800",
                              agent.status === 'error' && "bg-red-100 text-red-800",
                              agent.status === 'idle' && "bg-gray-100 text-gray-800",
                              agent.status === 'disabled' && "bg-yellow-100 text-yellow-800"
                            )}
                          >
                            {agent.status === 'running' ? 'Çalışıyor' :
                             agent.status === 'error' ? 'Hata' :
                             agent.status === 'idle' ? 'Bekliyor' :
                             agent.status === 'disabled' ? 'Devre Dışı' : agent.status}
                          </span>
                        </div>
                      </div>
                      <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t flex justify-between items-center">
                        <div className="flex space-x-1">
                          <button className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded">
                            <FiEdit size={14} />
                          </button>
                          <button className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-100 rounded">
                            <FiTrash2 size={14} />
                          </button>
                        </div>
                        <button className="px-3 py-1 bg-primary-600 text-white rounded text-xs font-medium hover:bg-primary-700">
                          Çalıştır
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div>
              {connectors.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-lg">
                  <FiDatabase size={48} className="mx-auto text-gray-400 mb-4" />
                  <h3 className="text-lg font-medium text-gray-600 mb-2">
                    Henüz hiç konnektör eklenmemiş
                  </h3>
                  <p className="text-gray-500 mb-4">
                    Konnektörler, harici veri kaynaklarına bağlantı sağlar
                  </p>
                  <button className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm font-medium inline-flex items-center hover:bg-primary-700">
                    <FiPlus size={16} className="mr-2" />
                    <span>Yeni Konnektör Ekle</span>
                  </button>
                </div>
              ) : (
                <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
                  {connectors.map((connector) => (
                    <div key={connector.connector_id} className="border rounded-lg hover:shadow-md transition-shadow">
                      <div className="flex items-start p-4">
                        <div className="mr-3 bg-gray-100 p-2 rounded-lg">
                          {getConnectorIcon(connector.connector_type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-medium text-gray-900 truncate">{connector.name}</h3>
                          <p className="text-xs text-gray-500 truncate mt-1">{connector.description || 'Açıklama yok'}</p>
                        </div>
                        <div className="ml-2 flex flex-col items-end">
                          <span 
                            className={cn(
                              "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium",
                              connector.is_connected 
                                ? "bg-green-100 text-green-800" 
                                : "bg-red-100 text-red-800"
                            )}
                          >
                            {connector.is_connected ? 'Bağlı' : 'Bağlantı Kesildi'}
                          </span>
                        </div>
                      </div>
                      <div className="px-4 py-3 bg-gray-50 rounded-b-lg border-t flex justify-between items-center">
                        <div className="flex space-x-1">
                          <button className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded">
                            <FiEdit size={14} />
                          </button>
                          <button className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-100 rounded">
                            <FiTrash2 size={14} />
                          </button>
                        </div>
                        <button className="px-3 py-1 bg-primary-600 text-white rounded text-xs font-medium hover:bg-primary-700">
                          Test Et
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DataSources