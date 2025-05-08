import React, { useState, useEffect } from 'react';
import { FiSearch, FiImage, FiVideo, FiMic, FiFilter, FiX, FiGrid, FiList, FiFile } from 'react-icons/fi';

import Button from '@/components/common/Button';
import ImageUploader from '@/components/multimodal/ImageUploader';
import { useNotificationStore } from '@/store/notificationStore';
import { multimodalService } from '@/services/multimodalService';

interface SearchResult {
  id: string;
  content_type: 'image' | 'video' | 'audio';
  filename: string;
  caption: string;
  preview: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

const MultimodalSearchPage: React.FC = () => {
  // State
  const [searchText, setSearchText] = useState('');
  const [searchImage, setSearchImage] = useState<{ file: File; preview: string } | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [contentTypeFilter, setContentTypeFilter] = useState<string[]>(['image', 'video', 'audio']);
  
  const { addNotification } = useNotificationStore();
  
  // Arama yapma fonksiyonu
  const handleSearch = async () => {
    if (!searchText && !searchImage) {
      addNotification({
        id: Date.now().toString(),
        title: 'Arama Hatası',
        message: 'Lütfen bir arama metni girin veya görüntü yükleyin.',
        type: 'warning',
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await multimodalService.search({
        query_text: searchText || undefined,
        query_image: searchImage?.preview || undefined,
        filter: {
          content_type: { $in: contentTypeFilter }
        },
        limit: 20
      });
      
      setResults(response.results);
      
      if (response.results.length === 0) {
        addNotification({
          id: Date.now().toString(),
          title: 'Sonuç Bulunamadı',
          message: 'Aramanızla eşleşen içerik bulunamadı.',
          type: 'info',
        });
      }
    } catch (error) {
      console.error('Search error:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Arama Hatası',
        message: 'İçerik aranırken bir hata oluştu.',
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // İçerik tipi filtresini değiştirme
  const toggleContentTypeFilter = (type: string) => {
    if (contentTypeFilter.includes(type)) {
      setContentTypeFilter(contentTypeFilter.filter(t => t !== type));
    } else {
      setContentTypeFilter([...contentTypeFilter, type]);
    }
  };
  
  // Önizleme render fonksiyonları
  const renderPreview = (result: SearchResult) => {
    if (result.content_type === 'image' && result.preview) {
      return (
        <img 
          src={result.preview} 
          alt={result.caption || result.filename}
          className="w-full h-full object-cover rounded"
        />
      );
    } else if (result.content_type === 'video' && result.preview) {
      return (
        <div className="relative w-full h-full">
          <img 
            src={result.preview} 
            alt={result.caption || result.filename}
            className="w-full h-full object-cover rounded"
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="bg-black bg-opacity-50 rounded-full p-2">
              <FiVideo className="text-white" size={24} />
            </div>
          </div>
        </div>
      );
    } else if (result.content_type === 'audio') {
      return (
        <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded">
          <FiMic className="text-gray-500" size={32} />
        </div>
      );
    }
    
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100 dark:bg-gray-800 rounded">
        <FiFile className="text-gray-500" size={32} />
      </div>
    );
  };
  
  // Grid view
  const renderGridView = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {results.map((result) => (
        <div 
          key={result.id}
          className="border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow bg-white dark:bg-gray-800 dark:border-gray-700"
        >
          <div className="h-48 bg-gray-100 dark:bg-gray-700">
            {renderPreview(result)}
          </div>
          <div className="p-3">
            <div className="flex items-center mb-1">
              {result.content_type === 'image' && <FiImage className="mr-1 text-blue-500" size={16} />}
              {result.content_type === 'video' && <FiVideo className="mr-1 text-green-500" size={16} />}
              {result.content_type === 'audio' && <FiMic className="mr-1 text-purple-500" size={16} />}
              <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {result.metadata.title || result.filename}
              </h3>
            </div>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {result.caption || result.metadata.description || 'Açıklama yok'}
            </p>
            
            <div className="flex mt-2 text-xs text-gray-500">
              <span>
                {new Date(result.created_at).toLocaleDateString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
  
  // List view
  const renderListView = () => (
    <div className="space-y-3">
      {results.map((result) => (
        <div 
          key={result.id}
          className="flex border rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow bg-white dark:bg-gray-800 dark:border-gray-700"
        >
          <div className="w-24 h-24 bg-gray-100 dark:bg-gray-700 flex-shrink-0">
            {renderPreview(result)}
          </div>
          <div className="p-3 flex-1">
            <div className="flex items-center mb-1">
              {result.content_type === 'image' && <FiImage className="mr-1 text-blue-500" size={16} />}
              {result.content_type === 'video' && <FiVideo className="mr-1 text-green-500" size={16} />}
              {result.content_type === 'audio' && <FiMic className="mr-1 text-purple-500" size={16} />}
              <h3 className="font-medium text-gray-900 dark:text-gray-100 truncate">
                {result.metadata.title || result.filename}
              </h3>
            </div>
            
            <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
              {result.caption || result.metadata.description || 'Açıklama yok'}
            </p>
            
            <div className="flex mt-2 text-xs text-gray-500">
              <span className="mr-3">
                {new Date(result.created_at).toLocaleDateString()}
              </span>
              
              {result.content_type === 'video' && result.metadata.duration && (
                <span className="mr-3">
                  {result.metadata.duration}
                </span>
              )}
              
              {result.content_type === 'audio' && result.metadata.duration && (
                <span>
                  {result.metadata.duration}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
  
  return (
    <div className="container mx-auto py-6 px-4">
      <h1 className="text-2xl font-bold mb-6 text-gray-900 dark:text-white">
        Multimodal Arama
      </h1>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-4 mb-8">
        <div className="mb-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <input
                  type="text"
                  value={searchText}
                  onChange={(e) => setSearchText(e.target.value)}
                  placeholder="Görüntü, video veya ses içeriği arayın..."
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white pr-10"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSearch();
                    }
                  }}
                />
                {searchText && (
                  <button
                    className="absolute right-10 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                    onClick={() => setSearchText('')}
                  >
                    <FiX size={18} />
                  </button>
                )}
                <button
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-blue-500 dark:text-gray-400 dark:hover:text-blue-400"
                  onClick={handleSearch}
                >
                  <FiSearch size={18} />
                </button>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Button
                variant={showFilters ? "primary" : "secondary"}
                onClick={() => setShowFilters(!showFilters)}
                leftIcon={<FiFilter size={16} />}
                size="sm"
              >
                Filtreler
              </Button>
              
              <div className="border rounded-lg overflow-hidden flex">
                <button
                  className={`p-2 ${viewMode === 'grid' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid View"
                >
                  <FiGrid size={18} />
                </button>
                <button
                  className={`p-2 ${viewMode === 'list' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                  onClick={() => setViewMode('list')}
                  title="List View"
                >
                  <FiList size={18} />
                </button>
              </div>
            </div>
          </div>
          
          {showFilters && (
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
              <h3 className="font-medium mb-2 text-gray-700 dark:text-gray-300">İçerik Türü</h3>
              <div className="flex flex-wrap gap-2">
                <button
                  className={`px-3 py-1 rounded-full text-sm flex items-center ${contentTypeFilter.includes('image') ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'}`}
                  onClick={() => toggleContentTypeFilter('image')}
                >
                  <FiImage size={14} className="mr-1" /> Görüntü
                </button>
                <button
                  className={`px-3 py-1 rounded-full text-sm flex items-center ${contentTypeFilter.includes('video') ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'}`}
                  onClick={() => toggleContentTypeFilter('video')}
                >
                  <FiVideo size={14} className="mr-1" /> Video
                </button>
                <button
                  className={`px-3 py-1 rounded-full text-sm flex items-center ${contentTypeFilter.includes('audio') ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400' : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'}`}
                  onClick={() => toggleContentTypeFilter('audio')}
                >
                  <FiMic size={14} className="mr-1" /> Ses
                </button>
              </div>
            </div>
          )}
        </div>
        
        <div className="border-t dark:border-gray-700 pt-4">
          <h3 className="font-medium mb-4 text-gray-700 dark:text-gray-300">Görüntü ile Ara</h3>
          <div className="max-w-md">
            <ImageUploader
              onImageSelect={(file, preview) => setSearchImage({ file, preview })}
              onImageClear={() => setSearchImage(null)}
              acceptedTypes="image/*"
              maxSizeMB={5}
              label="Görüntü Yükle"
              showPreview={true}
            />
          </div>
          
          <div className="mt-4">
            <Button
              onClick={handleSearch}
              disabled={isLoading}
              loading={isLoading}
              variant="primary"
              leftIcon={<FiSearch />}
            >
              {isLoading ? 'Aranıyor...' : 'Ara'}
            </Button>
          </div>
        </div>
      </div>
      
      {/* Sonuçlar */}
      {results.length > 0 && (
        <div className="mb-4">
          <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-white">
            Sonuçlar ({results.length})
          </h2>
          
          {viewMode === 'grid' ? renderGridView() : renderListView()}
        </div>
      )}
      
      {results.length === 0 && !isLoading && (
        <div className="text-center py-10">
          <p className="text-gray-500 dark:text-gray-400">Henüz sonuç yok.</p>
          <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
            Aramak için metin girin veya görüntü yükleyin.
          </p>
        </div>
      )}
    </div>
  );
};

export default MultimodalSearchPage;