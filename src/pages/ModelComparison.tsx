import React, { useState, useEffect } from 'react'
import { FiSearch, FiBarChart2, FiLoader, FiFileText, FiTag, FiCalendar } from 'react-icons/fi'

import Layout from '@/layouts/DashboardLayout'
import { Button } from '@/components/ui/Button'
import ModelSelector from '@/components/ModelSelector'
import { ragApi } from '@/lib/api'
import { useEmbeddingStore } from '@/lib/embeddingStore'
import { useToast } from '@/hooks/useToast'
import { formatDate, truncateText } from '@/lib/utils'

const ModelComparison: React.FC = () => {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [resultsGrouped, setResultsGrouped] = useState<Record<string, any[]>>({})
  const [uniqueDocuments, setUniqueDocuments] = useState<Set<string>>(new Set())
  const [activeTabId, setActiveTabId] = useState<string>('')
  
  const { models, selectedModelIds, fetchModels, selectMultipleModels } = useEmbeddingStore()
  const { showToast } = useToast()
  
  // Modelleri yükle
  useEffect(() => {
    fetchModels()
  }, [fetchModels])
  
  // Search sonuçlarını modele göre grupla
  useEffect(() => {
    if (searchResults.length > 0) {
      const grouped: Record<string, any[]> = {}
      const docs = new Set<string>()
      
      searchResults.forEach(result => {
        const modelId = result.model_id || 'unknown'
        
        if (!grouped[modelId]) {
          grouped[modelId] = []
        }
        
        grouped[modelId].push(result)
        docs.add(result.document_id)
      })
      
      setResultsGrouped(grouped)
      setUniqueDocuments(docs)
      
      // İlk sekmeyi aktif et
      if (docs.size > 0) {
        const firstDoc = Array.from(docs)[0]
        setActiveTabId(getTabId(firstDoc))
      }
    } else {
      setResultsGrouped({})
      setUniqueDocuments(new Set())
      setActiveTabId('')
    }
  }, [searchResults])
  
  // Karşılaştırmalı arama
  const handleComparisonSearch = async () => {
    if (!query.trim() || selectedModelIds.length === 0) {
      showToast({
        title: 'Hata',
        message: 'Lütfen bir sorgu girin ve en az bir model seçin',
        type: 'error'
      })
      return
    }
    
    try {
      setIsSearching(true)
      
      // Her model için ayrı arama yap
      const allResults: any[] = []
      
      for (const modelId of selectedModelIds) {
        const response = await ragApi.search(query, {
          embedding_model: modelId,
          limit: 5,
          search_type: 'vector'
        })
        
        // Sonuçları grupla
        response.results.forEach((result: any) => {
          // Model bilgisini ekle
          result.model_id = modelId
          allResults.push(result)
        })
      }
      
      setSearchResults(allResults)
      
      if (allResults.length === 0) {
        showToast({
          title: 'Bilgi',
          message: 'Hiçbir sonuç bulunamadı',
          type: 'info'
        })
      }
    } catch (error) {
      console.error('Arama hatası:', error)
      showToast({
        title: 'Hata',
        message: 'Arama sırasında bir hata oluştu',
        type: 'error'
      })
    } finally {
      setIsSearching(false)
    }
  }
  
  // Model adını format
  const formatModelName = (modelId: string) => {
    const model = models.find(m => m.id === modelId)
    return model?.name || modelId
  }
  
  // Score format
  const formatScore = (score: number) => {
    return (score * 100).toFixed(2) + '%'
  }
  
  // Benzerlik skoru rengi
  const getScoreClass = (score: number) => {
    if (score >= 0.9) return 'text-green-600'
    if (score >= 0.7) return 'text-yellow-600'
    return 'text-red-600'
  }
  
  // Tab ID hesapla
  const getTabId = (docId: string) => {
    return `doc-${docId.replace(/[^a-zA-Z0-9]/g, '')}`
  }
  
  // Sekme değiştir
  const handleTabChange = (tabId: string) => {
    setActiveTabId(tabId)
  }
  
  return (
    <Layout title="Model Karşılaştırması">
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold mb-4">Embedding Modellerini Karşılaştır</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Karşılaştırmak için bir sorgu girin..."
                  className="w-full border border-gray-300 rounded-lg px-4 py-2 pr-10 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  onKeyDown={(e) => e.key === 'Enter' && handleComparisonSearch()}
                />
                <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                  <FiSearch />
                </span>
              </div>
            </div>
            
            <div>
              <Button
                onClick={handleComparisonSearch}
                loading={isSearching}
                disabled={!query.trim() || selectedModelIds.length === 0}
                className="w-full"
                icon={<FiBarChart2 />}
              >
                Modelleri Karşılaştır
              </Button>
            </div>
          </div>
          
          <div className="mt-6">
            <ModelSelector
              models={models}
              selectedModelId={selectedModelIds}
              onChange={(modelIds) => selectMultipleModels(modelIds as string[])}
              label="Karşılaştırılacak Modeller"
              description="Karşılaştırmak istediğiniz embedding modellerini seçin"
              multiple={true}
              placeholder="Karşılaştırma için modeller seçin..."
            />
          </div>
        </div>
        
        {isSearching ? (
          <div className="p-8 flex flex-col items-center justify-center">
            <FiLoader className="h-10 w-10 text-primary-600 animate-spin mb-4" />
            <p className="text-gray-500">Modeller karşılaştırılıyor...</p>
          </div>
        ) : searchResults.length > 0 ? (
          <div className="p-6">
            <h3 className="text-lg font-medium mb-4">
              {uniqueDocuments.size} belge içinde toplam {searchResults.length} sonuç bulundu
            </h3>
            
            {/* Belge bazlı sonuçlar */}
            <div className="border rounded-lg mt-4">
              <div className="bg-gray-50 p-4 border-b">
                <ul className="flex overflow-x-auto space-x-4 pb-2" role="tablist">
                  {Array.from(uniqueDocuments).map((docId, index) => {
                    const tabId = getTabId(docId)
                    const isActive = tabId === activeTabId
                    
                    return (
                      <li key={tabId} role="presentation">
                        <button
                          id={`tab-${tabId}`}
                          className={`px-4 py-2 text-sm font-medium rounded-md whitespace-nowrap
                            ${isActive 
                              ? 'bg-primary-600 text-white' 
                              : 'bg-white text-gray-600 hover:bg-gray-100'}`}
                          onClick={() => handleTabChange(tabId)}
                          role="tab"
                          aria-selected={isActive}
                          aria-controls={`panel-${tabId}`}
                        >
                          Belge {index + 1}: {truncateText(docId, 20)}
                        </button>
                      </li>
                    )
                  })}
                </ul>
              </div>
              
              <div className="p-4">
                {Array.from(uniqueDocuments).map(docId => {
                  const tabId = getTabId(docId)
                  const isActive = tabId === activeTabId
                  
                  // Her model için bu belge ile ilgili sonuçları grupla
                  const documentResults: Record<string, any[]> = {}
                  
                  Object.entries(resultsGrouped).forEach(([modelId, results]) => {
                    const filteredResults = results.filter(r => r.document_id === docId)
                    if (filteredResults.length > 0) {
                      documentResults[modelId] = filteredResults
                    }
                  })
                  
                  if (!isActive) return null
                  
                  return (
                    <div
                      key={tabId}
                      id={`panel-${tabId}`}
                      role="tabpanel"
                      aria-labelledby={`tab-${tabId}`}
                    >
                      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
                        <h4 className="font-medium text-yellow-800 flex items-center mb-2">
                          <FiFileText className="mr-2" /> Belge Bilgisi
                        </h4>
                        <p className="text-sm text-yellow-700">ID: {docId}</p>
                        
                        {/* Belgenin ilk chunk'ının metadata bilgileri */}
                        {Object.values(documentResults)[0]?.[0]?.metadata && (
                          <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 text-sm text-yellow-700">
                            {Object.values(documentResults)[0][0].metadata.title && (
                              <div className="flex items-center">
                                <span className="font-medium mr-2">Başlık:</span>
                                <span>{Object.values(documentResults)[0][0].metadata.title}</span>
                              </div>
                            )}
                            
                            {Object.values(documentResults)[0][0].metadata.source && (
                              <div className="flex items-center">
                                <span className="font-medium mr-2">Kaynak:</span>
                                <span>{Object.values(documentResults)[0][0].metadata.source}</span>
                              </div>
                            )}
                            
                            {Object.values(documentResults)[0][0].metadata.created_at && (
                              <div className="flex items-center">
                                <span className="font-medium mr-2">Oluşturulma:</span>
                                <span>{formatDate(Object.values(documentResults)[0][0].metadata.created_at)}</span>
                              </div>
                            )}
                            
                            {Object.values(documentResults)[0][0].metadata.tags && Object.values(documentResults)[0][0].metadata.tags.length > 0 && (
                              <div className="flex items-center col-span-2">
                                <span className="font-medium mr-2">Etiketler:</span>
                                <div className="flex flex-wrap gap-1">
                                  {Object.values(documentResults)[0][0].metadata.tags.map((tag: string, i: number) => (
                                    <span key={i} className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                                      <FiTag className="mr-1" size={10} /> {tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      
                      {/* Her model için sonuçlar */}
                      <div className="space-y-6">
                        {Object.entries(documentResults).map(([modelId, results]) => (
                          <div key={modelId} className="border rounded-lg">
                            <div className="p-3 bg-gray-50 border-b font-medium flex justify-between items-center">
                              <div className="flex items-center">
                                <span className="text-primary-600 mr-2">{formatModelName(modelId)}</span>
                                <span className="text-xs text-gray-500">{modelId}</span>
                              </div>
                              <span className="text-sm text-gray-600">{results.length} sonuç</span>
                            </div>
                            
                            <div className="divide-y">
                              {results.map((result, resultIndex) => (
                                <div key={`${result.chunk_id}-${resultIndex}`} className="p-4">
                                  <div className="flex justify-between items-start mb-2">
                                    <div className="text-xs text-gray-500">
                                      Parça ID: {result.chunk_id}
                                    </div>
                                    <div className={`text-lg font-bold ${getScoreClass(result.score)}`}>
                                      {formatScore(result.score)}
                                    </div>
                                  </div>
                                  
                                  <div className="bg-gray-50 p-3 rounded border text-sm">
                                    {result.text}
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
            
            {/* Model Performans Özeti */}
            <div className="mt-6 p-4 border rounded-lg">
              <h3 className="text-lg font-medium mb-4">Model Performans Özeti</h3>
              
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Model
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Sonuç Sayısı
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Ortalama Benzerlik
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        En Yüksek Benzerlik
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Benzersiz Belgeler
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(resultsGrouped).map(([modelId, results]) => {
                      // Model istatistiklerini hesapla
                      const resultCount = results.length
                      const avgSimilarity = results.reduce((sum, r) => sum + r.score, 0) / resultCount
                      const maxSimilarity = Math.max(...results.map(r => r.score))
                      const uniqueDocs = new Set(results.map(r => r.document_id)).size
                      
                      return (
                        <tr key={modelId}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="flex items-center">
                              <div className="text-sm font-medium text-gray-900">
                                {formatModelName(modelId)}
                              </div>
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm text-gray-900">{resultCount}</div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className={`text-sm font-medium ${getScoreClass(avgSimilarity)}`}>
                              {formatScore(avgSimilarity)}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className={`text-sm font-medium ${getScoreClass(maxSimilarity)}`}>
                              {formatScore(maxSimilarity)}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {uniqueDocs}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 flex flex-col items-center justify-center text-gray-500">
            <FiSearch className="h-12 w-12 mb-4 opacity-50" />
            <p className="mb-2">Henüz sonuç yok</p>
            <p className="text-sm">Modellerinizi karşılaştırmak için bir sorgu girin ve arama yapın</p>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default ModelComparison