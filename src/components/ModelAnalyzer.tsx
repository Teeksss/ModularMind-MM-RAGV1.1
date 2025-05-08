import React, { useState, useEffect } from 'react'
import { FiBarChart2, FiPieChart, FiCheckCircle, FiAlertCircle, FiChevronDown, FiChevronUp } from 'react-icons/fi'
import { cn } from '@/lib/utils'

interface ModelStats {
  id: string
  name?: string
  coverage: number
  documentsCount: number
  vectorsCount: number
  dimensions: number
  isDefault?: boolean
}

interface DocumentCoverage {
  id: string
  title: string
  coverage: Record<string, number>
  totalChunks: number
}

interface ModelAnalyzerProps {
  models: ModelStats[]
  documentCoverage: DocumentCoverage[]
  className?: string
  onModelSelect?: (modelId: string) => void
}

const ModelAnalyzer: React.FC<ModelAnalyzerProps> = ({
  models,
  documentCoverage,
  className,
  onModelSelect
}) => {
  const [activeTab, setActiveTab] = useState<'models' | 'documents'>('models')
  const [expandedDocId, setExpandedDocId] = useState<string | null>(null)
  
  // Calculate overall coverage for each model
  const getOverallCoverage = (modelId: string): number => {
    if (documentCoverage.length === 0) return 0
    
    let totalChunks = 0
    let coveredChunks = 0
    
    documentCoverage.forEach(doc => {
      totalChunks += doc.totalChunks
      coveredChunks += (doc.coverage[modelId] || 0) * doc.totalChunks / 100
    })
    
    return totalChunks > 0 ? (coveredChunks / totalChunks) * 100 : 0
  }
  
  // Update model stats with calculated coverage
  const modelStats = models.map(model => ({
    ...model,
    coverage: getOverallCoverage(model.id)
  }))
  
  // Toggle document expansion
  const toggleDocument = (docId: string) => {
    setExpandedDocId(expandedDocId === docId ? null : docId)
  }
  
  // Model selection handler
  const handleModelSelect = (modelId: string) => {
    if (onModelSelect) {
      onModelSelect(modelId)
    }
  }
  
  // Get status color based on coverage percent
  const getCoverageColor = (percent: number): string => {
    if (percent >= 90) return 'text-green-600'
    if (percent >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }
  
  // Get coverage bar color based on percent
  const getCoverageBarColor = (percent: number): string => {
    if (percent >= 90) return 'bg-green-500'
    if (percent >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }
  
  return (
    <div className={cn("bg-white rounded-lg border border-gray-200 shadow-sm", className)}>
      <div className="border-b border-gray-200">
        <div className="flex">
          <button
            onClick={() => setActiveTab('models')}
            className={cn(
              "px-4 py-3 text-sm font-medium flex items-center",
              activeTab === 'models' 
                ? "border-b-2 border-primary-600 text-primary-600"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <FiBarChart2 className="mr-2" />
            Model Coverage
          </button>
          <button
            onClick={() => setActiveTab('documents')}
            className={cn(
              "px-4 py-3 text-sm font-medium flex items-center",
              activeTab === 'documents' 
                ? "border-b-2 border-primary-600 text-primary-600"
                : "text-gray-600 hover:text-gray-900"
            )}
          >
            <FiPieChart className="mr-2" />
            Document Analysis
          </button>
        </div>
      </div>
      
      <div className="p-4">
        {activeTab === 'models' ? (
          <div className="space-y-3">
            <h3 className="text-base font-medium text-gray-900 mb-3">Model Coverage Analysis</h3>
            
            {modelStats.map(model => (
              <div 
                key={model.id} 
                className="border rounded-lg p-3 hover:border-primary-300 cursor-pointer transition-colors"
                onClick={() => handleModelSelect(model.id)}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h4 className="font-medium flex items-center text-gray-900">
                      {model.name || model.id}
                      {model.isDefault && (
                        <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-700">
                          Default
                        </span>
                      )}
                    </h4>
                    <div className="flex items-center mt-1 text-sm text-gray-600">
                      <span>{model.dimensions} dimensions</span>
                      <span className="mx-2">•</span>
                      <span>{model.vectorsCount} vectors</span>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className={cn(
                      "font-medium text-lg",
                      getCoverageColor(model.coverage)
                    )}>
                      {Math.round(model.coverage)}%
                    </div>
                    <div className="text-xs text-gray-500">coverage</div>
                  </div>
                </div>
                
                <div className="mt-2 bg-gray-200 rounded-full h-2.5 w-full">
                  <div 
                    className={cn(
                      "h-2.5 rounded-full",
                      getCoverageBarColor(model.coverage)
                    )}
                    style={{ width: `${model.coverage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div>
            <h3 className="text-base font-medium text-gray-900 mb-3">Document Coverage Analysis</h3>
            
            {documentCoverage.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No document coverage data available
              </div>
            ) : (
              <div className="space-y-3">
                {documentCoverage.map(doc => (
                  <div 
                    key={doc.id}
                    className="border rounded-lg overflow-hidden"
                  >
                    <div 
                      className="p-3 bg-gray-50 flex justify-between items-center cursor-pointer"
                      onClick={() => toggleDocument(doc.id)}
                    >
                      <div>
                        <h4 className="font-medium text-gray-900">{doc.title || doc.id}</h4>
                        <div className="text-xs text-gray-500 mt-1">
                          {doc.totalChunks} chunks total
                        </div>
                      </div>
                      
                      {expandedDocId === doc.id ? (
                        <FiChevronUp className="text-gray-500" />
                      ) : (
                        <FiChevronDown className="text-gray-500" />
                      )}
                    </div>
                    
                    {expandedDocId === doc.id && (
                      <div className="p-3 border-t">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b">
                              <th className="text-left pb-2 font-medium text-gray-600">Model</th>
                              <th className="text-right pb-2 font-medium text-gray-600">Coverage</th>
                              <th className="text-right pb-2 font-medium text-gray-600">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y">
                            {Object.entries(doc.coverage).map(([modelId, coverage]) => (
                              <tr key={modelId}>
                                <td className="py-2 text-gray-900">{
                                  models.find(m => m.id === modelId)?.name || modelId
                                }</td>
                                <td className="py-2 text-right">
                                  <span className={getCoverageColor(coverage)}>
                                    {Math.round(coverage)}%
                                  </span>
                                </td>
                                <td className="py-2 text-right">
                                  {coverage >= 95 ? (
                                    <FiCheckCircle className="inline ml-2 text-green-600" />
                                  ) : coverage >= 50 ? (
                                    <FiCheckCircle className="inline ml-2 text-yellow-600" />
                                  ) : (
                                    <FiAlertCircle className="inline ml-2 text-red-600" />
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ModelAnalyzer