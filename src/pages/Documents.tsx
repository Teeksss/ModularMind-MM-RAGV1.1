import { useState } from 'react'
import { FiSearch, FiFilter, FiDownload, FiUpload } from 'react-icons/fi'

import DocumentExplorer from '@/components/DocumentExplorer'

const Documents = () => {
  const [activeTab, setActiveTab] = useState('all') // all, recent, favorites
  const [searchVisible, setSearchVisible] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  
  return (
    <div className="max-w-7xl mx-auto">
      <div className="bg-white rounded-lg border shadow-sm mb-6">
        <div className="p-4 border-b">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold">Doküman Yönetimi</h1>
            <div className="flex space-x-2">
              {searchVisible ? (
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <FiSearch className="text-gray-400" size={16} />
                  </div>
                  <input
                    type="text"
                    className="pl-10 pr-4 py-2 border rounded-lg text-sm w-64"
                    placeholder="Belgelerde ara..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    autoFocus
                    onBlur={() => {
                      if (!searchTerm) setSearchVisible(false)
                    }}
                  />
                </div>
              ) : (
                <button
                  onClick={() => setSearchVisible(true)}
                  className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
                >
                  <FiSearch size={18} />
                </button>
              )}
              <button
                className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
                title="Filtreleri Göster"
              >
                <FiFilter size={18} />
              </button>
              <button
                className="p-2 rounded-lg text-gray-500 hover:bg-gray-100"
                title="Dışa Aktar"
              >
                <FiDownload size={18} />
              </button>
            </div>
          </div>
        </div>
        
        <div className="px-4 border-b">
          <div className="flex">
            <button
              className={`px-4 py-3 text-sm font-medium ${
                activeTab === 'all' 
                  ? 'border-b-2 border-primary-600 text-primary-600' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('all')}
            >
              Tüm Belgeler
            </button>
            <button
              className={`px-4 py-3 text-sm font-medium ${
                activeTab === 'recent' 
                  ? 'border-b-2 border-primary-600 text-primary-600' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('recent')}
            >
              Son Eklenenler
            </button>
            <button
              className={`px-4 py-3 text-sm font-medium ${
                activeTab === 'favorites' 
                  ? 'border-b-2 border-primary-600 text-primary-600' 
                  : 'text-gray-500 hover:text-gray-700'
              }`}
              onClick={() => setActiveTab('favorites')}
            >
              Favoriler
            </button>
          </div>
        </div>
        
        <div className="p-4">
          <DocumentExplorer />
        </div>
      </div>
    </div>
  )
}

export default Documents