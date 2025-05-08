import React, { useState, useEffect } from 'react'
import { FiUpload, FiDownload, FiPlus, FiTrash2, FiSave, FiAlertTriangle, FiInfo } from 'react-icons/fi'

import Layout from '@/layouts/DashboardLayout'
import ModelSelector from '@/components/ModelSelector'
import ModelAnalyzer from '@/components/ModelAnalyzer'
import { Button } from '@/components/ui/Button'
import { ragApi, embeddingApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'

const EmbeddingSettings: React.FC = () => {
  const [embedModels, setEmbedModels] = useState<any[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [defaultModel, setDefaultModel] = useState('')
  const [documentCoverage, setDocumentCoverage] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [savingSettings, setSavingSettings] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [rebuildingIndex, setRebuildingIndex] = useState(false)
  
  const { showToast } = useToast()
  
  // Load data
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true)
        // Load embedding models
        const embeddingModels = await embeddingApi.getModels()
        
        // Load configured models
        const response = await ragApi.getStats()
        const models = response.stats.models || []
        
        // Set default model
        const defaultModelId = models.find((m: any) => m.is_default)?.id || ''
        setDefaultModel(defaultModelId)
        setSelectedModel(defaultModelId)
        
        // Merge model data
        const mergedModels = models.map((model: any) => {
          const embModel = embeddingModels.find((m: any) => m.id === model.id)
          return {
            id: model.id,
            name: embModel?.name || model.id,
            dimensions: model.dimensions,
            embedding_count: model.embedding_count,
            is_default: model.is_default,
            provider: embModel?.provider
          }
        })
        
        setEmbedModels(mergedModels)
        
        // Load document coverage
        const coverageData = await ragApi.getEmbeddingCoverage()
        setDocumentCoverage(coverageData.coverage)
      } catch (error) {
        console.error('Error loading data:', error)
        showToast({
          title: 'Error',
          message: 'Failed to load embedding models',
          type: 'error'
        })
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [])
  
  // Format document coverage for the analyzer component
  const formatDocCoverage = () => {
    return Object.entries(documentCoverage).map(([docId, data]: [string, any]) => ({
      id: docId,
      title: data.title || docId,
      coverage: Object.fromEntries(
        Object.entries(data).filter(([key]) => key !== 'title' && key !== 'total_chunks')
      ),
      totalChunks: data.total_chunks || 0
    }))
  }
  
  // Set model as default
  const handleSetDefaultModel = async () => {
    try {
      setSavingSettings(true)
      
      // API call to set default model
      await ragApi.setDefaultEmbeddingModel(selectedModel)
      
      // Update local state
      setDefaultModel(selectedModel)
      
      // Update models list
      const updatedModels = embedModels.map(model => ({
        ...model,
        is_default: model.id === selectedModel
      }))
      
      setEmbedModels(updatedModels)
      
      showToast({
        title: 'Success',
        message: 'Default embedding model updated',
        type: 'success'
      })
    } catch (error) {
      console.error('Error setting default model:', error)
      showToast({
        title: 'Error',
        message: 'Failed to update default model',
        type: 'error'
      })
    } finally {
      setSavingSettings(false)
    }
  }
  
  // Rebuild index for selected model
  const handleRebuildIndex = async () => {
    try {
      setRebuildingIndex(true)
      
      // API call to rebuild index
      await ragApi.rebuildModelIndex(selectedModel)
      
      showToast({
        title: 'Success',
        message: 'Index rebuilt successfully',
        type: 'success'
      })
      
      // Refresh stats
      const response = await ragApi.getStats()
      const models = response.stats.models || []
      
      // Update models with new stats
      const updatedModels = embedModels.map(model => {
        const updatedModel = models.find((m: any) => m.id === model.id)
        return {
          ...model,
          embedding_count: updatedModel?.embedding_count || model.embedding_count
        }
      })
      
      setEmbedModels(updatedModels)
    } catch (error) {
      console.error('Error rebuilding index:', error)
      showToast({
        title: 'Error',
        message: 'Failed to rebuild index',
        type: 'error'
      })
    } finally {
      setRebuildingIndex(false)
    }
  }
  
  // Analyze embeddings across all documents
  const handleAnalyzeEmbeddings = async () => {
    try {
      setAnalyzing(true)
      
      // API call to analyze embeddings
      const coverageData = await ragApi.getEmbeddingCoverage()
      setDocumentCoverage(coverageData.coverage)
      
      showToast({
        title: 'Success',
        message: 'Embedding analysis completed',
        type: 'success'
      })
    } catch (error) {
      console.error('Error analyzing embeddings:', error)
      showToast({
        title: 'Error',
        message: 'Failed to analyze embeddings',
        type: 'error'
      })
    } finally {
      setAnalyzing(false)
    }
  }
  
  return (
    <Layout title="Embedding Settings">
      <div className="space-y-6">
        <div className="bg-white rounded-lg border shadow-sm p-6">
          <h2 className="text-xl font-bold mb-4">Embedding Model Settings</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2">
              <ModelSelector
                models={embedModels}
                selectedModelId={selectedModel}
                onChange={(modelId) => setSelectedModel(modelId as string)}
                label="Select Embedding Model"
                description="Choose the model to manage or set as default"
              />
              
              <div className="flex flex-wrap gap-3 mt-6">
                <Button
                  onClick={handleSetDefaultModel}
                  loading={savingSettings}
                  disabled={selectedModel === defaultModel || !selectedModel}
                  icon={<FiSave />}
                >
                  Set as Default
                </Button>
                
                <Button
                  onClick={handleRebuildIndex}
                  loading={rebuildingIndex}
                  disabled={!selectedModel}
                  variant="outline"
                  icon={<FiUpload />}
                >
                  Rebuild Index
                </Button>
                
                <Button
                  onClick={handleAnalyzeEmbeddings}
                  loading={analyzing}
                  variant="outline"
                  icon={<FiInfo />}
                >
                  Analyze Coverage
                </Button>
              </div>
              
              {selectedModel && (
                <div className="mt-6 p-4 border rounded-lg bg-gray-50">
                  <h3 className="font-medium mb-2">Selected Model: {embedModels.find(m => m.id === selectedModel)?.name || selectedModel}</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Dimensions:</span>{' '}
                      <span className="font-medium">{embedModels.find(m => m.id === selectedModel)?.dimensions || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Provider:</span>{' '}
                      <span className="font-medium">{embedModels.find(m => m.id === selectedModel)?.provider || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Indexed Vectors:</span>{' '}
                      <span className="font-medium">{embedModels.find(m => m.id === selectedModel)?.embedding_count || 0}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Status:</span>{' '}
                      <span className={`font-medium ${defaultModel === selectedModel ? 'text-green-600' : 'text-blue-600'}`}>
                        {defaultModel === selectedModel ? 'Default Model' : 'Available'}
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg border">
              <h3 className="font-medium mb-3">Info</h3>
              <div className="text-sm space-y-3">
                <p className="flex items-start">
                  <FiInfo className="mr-2 mt-1 flex-shrink-0 text-blue-600" />
                  <span>
                    The default embedding model is used when no specific model is requested in queries.
                  </span>
                </p>
                <p className="flex items-start">
                  <FiInfo className="mr-2 mt-1 flex-shrink-0 text-blue-600" />
                  <span>
                    When adding documents, you can specify which embedding models to use.
                  </span>
                </p>
                <p className="flex items-start">
                  <FiAlertTriangle className="mr-2 mt-1 flex-shrink-0 text-yellow-600" />
                  <span>
                    Rebuilding indices may take time for large document collections.
                  </span>
                </p>
              </div>
            </div>
          </div>
        </div>
        
        <ModelAnalyzer 
          models={embedModels}
          documentCoverage={formatDocCoverage()}
          onModelSelect={(modelId) => setSelectedModel(modelId)}
        />
      </div>
    </Layout>
  )
}

export default EmbeddingSettings