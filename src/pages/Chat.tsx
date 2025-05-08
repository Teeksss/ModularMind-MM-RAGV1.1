import { useState, useEffect } from 'react'
import { FiSettings, FiX, FiCheck } from 'react-icons/fi'

import ChatBox from '@/components/ChatBox'
import { llmApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useStore } from '@/lib/store'

const Chat = () => {
  const { 
    llmModels, 
    currentLLMModel, 
    setCurrentLLMModel,
    settings,
    updateSettings,
    fetchModels,
    isLoading
  } = useStore()
  
  // Yerel ayarlar
  const [localSettings, setLocalSettings] = useState({
    ragEnabled: settings.ragEnabled,
    systemMessage: settings.systemMessage
  })
  
  // Ayarlar modali
  const [showSettings, setShowSettings] = useState(false)
  
  // İlk yükleme
  useEffect(() => {
    if (llmModels.length === 0) {
      fetchModels()
    }
  }, [llmModels.length, fetchModels])
  
  // Ayarları kaydet
  const saveSettings = () => {
    setCurrentLLMModel(currentLLMModel)
    updateSettings({
      ragEnabled: localSettings.ragEnabled,
      systemMessage: localSettings.systemMessage
    })
    setShowSettings(false)
  }
  
  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg border shadow-sm mb-6">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold">Chat</h1>
            <button
              onClick={() => setShowSettings(true)}
              className="p-2 rounded-full text-gray-500 hover:bg-gray-100"
            >
              <FiSettings size={20} />
            </button>
          </div>
        </div>
        <div className="p-4">
          <ChatBox 
            modelId={currentLLMModel}
            systemMessage={settings.systemMessage}
            ragEnabled={settings.ragEnabled}
            onSettingsClick={() => setShowSettings(true)}
          />
        </div>
      </div>
      
      {/* Ayarlar Modali */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Chat Ayarları</h3>
              <button
                onClick={() => setShowSettings(false)}
                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded"
              >
                <FiX size={18} />
              </button>
            </div>
            
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  LLM Modeli
                </label>
                <select
                  value={currentLLMModel}
                  onChange={(e) => setCurrentLLMModel(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                >
                  {isLoading ? (
                    <option>Yükleniyor...</option>
                  ) : (
                    llmModels.map((model) => (
                      <option key={model.id} value={model.id}>
                        {model.id} {model.provider && `(${model.provider})`}
                      </option>
                    ))
                  )}
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sistem Mesajı
                </label>
                <textarea
                  value={localSettings.systemMessage}
                  onChange={(e) => setLocalSettings(prev => ({
                    ...prev,
                    systemMessage: e.target.value
                  }))}
                  rows={3}
                  className="w-full px-3 py-2 border rounded-lg text-sm"
                  placeholder="AI asistanın karakterini tanımlayan sistem mesajı"
                />
              </div>
              
              <div>
                <div className="flex items-center">
                  <button
                    type="button"
                    onClick={() => setLocalSettings(prev => ({
                      ...prev,
                      ragEnabled: !prev.ragEnabled
                    }))}
                    className={cn(
                      "relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                      localSettings.ragEnabled ? "bg-primary-600" : "bg-gray-200"
                    )}
                  >
                    <span
                      className={cn(
                        "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
                        localSettings.ragEnabled ? "translate-x-5" : "translate-x-0"
                      )}
                    />
                  </button>
                  <span className="ml-3 text-sm font-medium text-gray-700">
                    RAG Etkin (Vektör Veritabanını Kullan)
                  </span>
                </div>
                <p className="mt-1 text-xs text-gray-500">
                  Etkinleştirildiğinde, AI cevapları belge veritabanından alınan bilgilerle zenginleştirilir.
                </p>
              </div>
            </div>
            
            <div className="mt-6 flex justify-end">
              <button
                onClick={saveSettings}
                className="px-4 py-2 rounded-lg font-medium flex items-center text-white bg-primary-600 hover:bg-primary-700"
              >
                <FiCheck size={16} className="mr-2" />
                Ayarları Kaydet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Chat