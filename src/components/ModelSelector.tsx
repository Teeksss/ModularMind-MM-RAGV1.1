import React, { useEffect, useState } from 'react'
import { FiChevronDown, FiCheck, FiSearch, FiX, FiInfo } from 'react-icons/fi'
import { cn } from '@/lib/utils'

export interface ModelOption {
  id: string
  name?: string
  provider?: string
  dimensions?: number
  description?: string
  isDefault?: boolean
  embedding_count?: number
}

interface ModelSelectorProps {
  models: ModelOption[]
  selectedModelId: string | string[]
  onChange: (modelId: string | string[]) => void
  label?: string
  description?: string
  multiple?: boolean
  placeholder?: string
  className?: string
  size?: 'sm' | 'md' | 'lg'
  disabled?: boolean
}

const ModelSelector: React.FC<ModelSelectorProps> = ({
  models,
  selectedModelId,
  onChange,
  label = 'Select Model',
  description,
  multiple = false,
  placeholder = 'Select a model...',
  className,
  size = 'md',
  disabled = false
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>(
    Array.isArray(selectedModelId) ? selectedModelId : selectedModelId ? [selectedModelId] : []
  )
  
  // Update internal state when prop changes
  useEffect(() => {
    setSelectedIds(Array.isArray(selectedModelId) ? selectedModelId : selectedModelId ? [selectedModelId] : [])
  }, [selectedModelId])
  
  // Filter models based on search query
  const filteredModels = models.filter(model => {
    const searchText = `${model.id} ${model.name || ''} ${model.provider || ''}`.toLowerCase()
    return searchText.includes(searchQuery.toLowerCase())
  })
  
  // Handle model selection
  const handleSelectModel = (modelId: string) => {
    if (disabled) return
    
    if (multiple) {
      // For multiple selection
      const newSelectedIds = selectedIds.includes(modelId)
        ? selectedIds.filter(id => id !== modelId)
        : [...selectedIds, modelId]
      
      setSelectedIds(newSelectedIds)
      onChange(newSelectedIds)
    } else {
      // For single selection
      setSelectedIds([modelId])
      onChange(modelId)
      setIsOpen(false)
    }
  }
  
  // Clear all selections
  const handleClearAll = () => {
    if (disabled) return
    setSelectedIds([])
    onChange(multiple ? [] : '')
  }
  
  // Get display text for selected models
  const getDisplayText = () => {
    if (selectedIds.length === 0) return placeholder
    
    if (selectedIds.length === 1) {
      const selectedModel = models.find(m => m.id === selectedIds[0])
      return selectedModel?.name || selectedModel?.id || placeholder
    }
    
    return `${selectedIds.length} models selected`
  }
  
  // Size classes
  const sizeClasses = {
    sm: 'text-xs py-1 px-2',
    md: 'text-sm py-2 px-3',
    lg: 'text-base py-2.5 px-4'
  }
  
  return (
    <div className={cn("relative", className)}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
          {description && (
            <div className="ml-1 inline-block relative group">
              <FiInfo className="inline-block text-gray-400 h-4 w-4" />
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 invisible group-hover:visible bg-gray-900 text-white text-xs rounded py-1 px-2 whitespace-nowrap mb-1 max-w-xs">
                {description}
              </div>
            </div>
          )}
        </label>
      )}
      
      <div className="relative">
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={cn(
            "w-full flex justify-between items-center rounded-md border shadow-sm focus:outline-none",
            sizeClasses[size],
            disabled 
              ? "bg-gray-100 text-gray-500 cursor-not-allowed border-gray-200"
              : "bg-white border-gray-300 hover:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:border-primary-500",
            selectedIds.length > 0 && "text-gray-900",
            selectedIds.length === 0 && !disabled && "text-gray-500"
          )}
        >
          <span className="truncate">{getDisplayText()}</span>
          <FiChevronDown className={cn(
            "ml-2 h-5 w-5 text-gray-400 transition-transform",
            isOpen && "transform rotate-180"
          )} />
        </button>
        
        {selectedIds.length > 0 && !disabled && (
          <button
            type="button"
            onClick={handleClearAll}
            className="absolute inset-y-0 right-8 flex items-center pr-2"
          >
            <FiX className="h-4 w-4 text-gray-400 hover:text-gray-600" />
          </button>
        )}
        
        {isOpen && !disabled && (
          <div className="absolute z-10 mt-1 w-full rounded-md bg-white shadow-lg">
            <div className="p-2 border border-gray-200 rounded-md max-h-60 overflow-auto">
              <div className="relative mb-2">
                <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-500 focus:border-primary-500"
                  placeholder="Search models..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onClick={(e) => e.stopPropagation()}
                />
              </div>
              
              <ul className="space-y-1">
                {filteredModels.length === 0 ? (
                  <li className="px-3 py-2 text-sm text-gray-500">No models found</li>
                ) : (
                  filteredModels.map((model) => (
                    <li 
                      key={model.id}
                      onClick={() => handleSelectModel(model.id)}
                      className={cn(
                        "px-3 py-2 rounded-md cursor-pointer flex items-start text-sm",
                        selectedIds.includes(model.id) 
                          ? "bg-primary-50 text-primary-900" 
                          : "hover:bg-gray-100"
                      )}
                    >
                      <div className="flex-shrink-0 mr-2 mt-0.5">
                        {selectedIds.includes(model.id) ? (
                          <FiCheck className="h-4 w-4 text-primary-600" />
                        ) : (
                          <div className="h-4 w-4" />
                        )}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center">
                          <span className="font-medium">{model.name || model.id}</span>
                          {model.isDefault && (
                            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800">
                              Default
                            </span>
                          )}
                        </div>
                        
                        <div className="mt-1 text-xs text-gray-500">
                          {model.provider && <span className="mr-1.5">{model.provider}</span>}
                          {model.dimensions && <span className="mr-1.5">{model.dimensions} dims</span>}
                          {model.embedding_count !== undefined && (
                            <span>{model.embedding_count} vectors</span>
                          )}
                        </div>
                        
                        {model.description && (
                          <p className="mt-1 text-xs text-gray-600">{model.description}</p>
                        )}
                      </div>
                    </li>
                  ))
                )}
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default ModelSelector