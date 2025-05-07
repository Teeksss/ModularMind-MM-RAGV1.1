import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FaSearch, FaImage, FaTimes, FaExclamationCircle } from 'react-icons/fa';
import { useSearchStore } from '../../store/searchStore';
import { useNotificationStore } from '../../store/notificationStore';
import SearchResults from './SearchResults';
import ImageUploader from '../multimodal/ImageUploader';
import LoadingOverlay from '../common/LoadingOverlay';

interface SearchInterfaceProps {
  initialQuery?: string;
}

const SearchInterface: React.FC<SearchInterfaceProps> = ({ initialQuery = '' }) => {
  const { t } = useTranslation();
  const { 
    results, 
    isLoading, 
    error, 
    search, 
    setSearchMode,
    searchMode
  } = useSearchStore();
  const { addNotification } = useNotificationStore();
  
  const [query, setQuery] = useState(initialQuery);
  const [showImageUpload, setShowImageUpload] = useState(false);
  const [uploadedImage, setUploadedImage] = useState<string | null>(null);
  
  useEffect(() => {
    // If initialQuery is provided, auto-search
    if (initialQuery) {
      setQuery(initialQuery);
      handleSearch();
    }
  }, [initialQuery]);
  
  // Handle search form submission
  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    
    if (!query.trim() && !uploadedImage) {
      addNotification({
        type: 'warning',
        title: t('search.emptyQuery'),
        message: t('search.enterQueryOrUploadImage')
      });
      return;
    }
    
    try {
      await search(query, uploadedImage);
    } catch (err) {
      console.error('Search error:', err);
    }
  };
  
  // Handle image upload
  const handleImageUpload = (imageData: string) => {
    setUploadedImage(imageData);
    setShowImageUpload(false);
    setSearchMode('multimodal');
    
    // Auto-search if we have a query already
    if (query.trim()) {
      handleSearch();
    }
  };
  
  // Clear uploaded image
  const clearUploadedImage = () => {
    setUploadedImage(null);
    setSearchMode('text');
  };
  
  return (
    <div className="p-4">
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative">
          <div className="flex items-center">
            {/* Search input */}
            <div className="relative flex-grow">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={t('search.placeholder')}
                className="w-full p-3 pl-10 pr-12 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
                disabled={isLoading}
              />
              <FaSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500" />
              
              {/* Clear button */}
              {query && (
                <button
                  type="button"
                  onClick={() => setQuery('')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
                  aria-label={t('common.clear')}
                >
                  <FaTimes />
                </button>
              )}
            </div>
            
            {/* Image upload button */}
            <button
              type="button"
              onClick={() => setShowImageUpload(true)}
              className={`ml-3 p-3 rounded-md ${
                uploadedImage 
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
              title={t('search.uploadImage')}
            >
              <FaImage />
            </button>
            
            {/* Search button */}
            <button
              type="submit"
              className={`ml-3 px-4 py-3 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 ${
                isLoading ? 'opacity-70 cursor-not-allowed' : ''
              }`}
              disabled={isLoading}
            >
              {t('search.search')}
            </button>
          </div>
          
          {/* Show uploaded image preview */}
          {uploadedImage && (
            <div className="mt-2 flex items-center">
              <div className="relative w-12 h-12 rounded-md overflow-hidden border border-gray-300 dark:border-gray-600">
                <img
                  src={uploadedImage}
                  alt={t('search.uploadedImage')}
                  className="w-full h-full object-cover"
                />
                <button
                  type="button"
                  onClick={clearUploadedImage}
                  className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full p-1 shadow-md hover:bg-red-600"
                  aria-label={t('common.remove')}
                >
                  <FaTimes size={10} />
                </button>
              </div>
              <span className="ml-2 text-sm text-gray-500 dark:text-gray-400">
                {t('search.imageUploaded')}
              </span>
            </div>
          )}
        </div>
      </form>
      
      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded-md flex items-center">
          <FaExclamationCircle className="mr-2" />
          <span>{error}</span>
        </div>
      )}
      
      {/* Search results */}
      <LoadingOverlay isLoading={isLoading} message={t('search.searching')}>
        <SearchResults results={results} />
      </LoadingOverlay>
      
      {/* Image upload modal */}
      {showImageUpload && (
        <div className="fixed inset-0 z-40 bg-black/50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4 text-gray-900 dark:text-white">
              {t('search.uploadImage')}
            </h2>
            
            <ImageUploader 
              onImageSelected={handleImageUpload} 
              onCancel={() => setShowImageUpload(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchInterface;