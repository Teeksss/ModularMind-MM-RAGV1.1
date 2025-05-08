import React, { useState, useCallback } from 'react';
import { useMultimodalSearch } from '../../hooks/useMultimodalSearch';
import { SearchResult } from '../../types/search';
import SearchResultsList from '../search/SearchResultsList';
import Dropzone from 'react-dropzone';
import { FiUpload, FiSearch, FiX } from 'react-icons/fi';

const ImageSearchPanel: React.FC = () => {
  const [image, setImage] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { search, results, loading, error } = useMultimodalSearch();

  const handleImageUpload = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles[0]) {
      setImage(acceptedFiles[0]);
      // Create preview URL
      const previewUrl = URL.createObjectURL(acceptedFiles[0]);
      setImagePreview(previewUrl);
    }
  }, []);

  const handleImageSearch = async () => {
    if (!image && !searchQuery) return;
    
    await search({
      image,
      text: searchQuery,
      options: {
        limit: 10,
        filter: showAdvanced ? {} : null
      }
    });
  };

  const handleClearImage = () => {
    if (imagePreview) {
      URL.revokeObjectURL(imagePreview);
    }
    setImage(null);
    setImagePreview(null);
  };

  return (
    <div className="p-4 w-full max-w-6xl mx-auto">
      <h1 className="text-2xl font-semibold mb-4">
        Multimodal Image Search
      </h1>
      <div className="h-px w-full bg-gray-200 mb-6"></div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Image Upload Section */}
        <div className="border border-gray-200 rounded-lg p-4 h-full min-h-[300px]">
          <h2 className="text-lg font-medium mb-4">
            Upload or Drag an Image
          </h2>
          
          {imagePreview ? (
            <div className="relative mt-4">
              <div className="relative">
                <img 
                  src={imagePreview} 
                  alt="Uploaded image" 
                  className="w-full max-h-[300px] object-contain rounded-lg border border-gray-200"
                />
                <button
                  onClick={handleClearImage}
                  className="absolute top-2 right-2 bg-red-500 text-white p-1 rounded-full"
                >
                  <FiX className="w-5 h-5" />
                </button>
              </div>
            </div>
          ) : (
            <Dropzone onDrop={handleImageUpload}>
              {({getRootProps, getInputProps}) => (
                <div 
                  {...getRootProps()} 
                  className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:bg-gray-50 transition-colors flex flex-col items-center justify-center h-[260px]"
                >
                  <input {...getInputProps()} />
                  <FiUpload className="w-12 h-12 text-gray-400 mb-4" />
                  <p className="text-gray-500">Drag & drop an image here, or click to select</p>
                  <p className="text-gray-400 text-sm mt-2">Supports JPG, PNG and WEBP</p>
                </div>
              )}
            </Dropzone>
          )}
          
          <div className="flex justify-center mt-4">
            <button
              className="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center gap-2 hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              onClick={() => document.getElementById('image-upload-input')?.click()}
              disabled={loading}
            >
              <FiUpload />
              Select Image
            </button>
            <input
              id="image-upload-input"
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => e.target.files && handleImageUpload([e.target.files[0]])}
            />
          </div>
        </div>
        
        {/* Search Options Section */}
        <div className="border border-gray-200 rounded-lg p-4 h-full">
          <h2 className="text-lg font-medium mb-4">
            Search Options
          </h2>
          
          <div className="mb-4">
            <label htmlFor="search-query" className="block text-sm font-medium text-gray-700 mb-1">
              Optional Text Query
            </label>
            <input
              id="search-query"
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              disabled={loading}
              placeholder="Enter text to refine your search..."
            />
          </div>
          
          <div className="flex justify-between mt-4">
            <button
              className="px-4 py-2 border border-gray-300 rounded-md flex items-center gap-2 hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 disabled:opacity-50"
              onClick={() => setShowAdvanced(!showAdvanced)}
              disabled={loading}
            >
              {showAdvanced ? 'Hide Advanced' : 'Show Advanced'}
            </button>
            
            <button
              className="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center gap-2 hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
              onClick={handleImageSearch}
              disabled={loading || (!image && !searchQuery)}
            >
              {loading ? (
                <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <>
                  <FiSearch />
                  Search
                </>
              )}
            </button>
          </div>
          
          {showAdvanced && (
            <div className="mt-4 p-3 bg-gray-50 rounded-md">
              <p className="text-sm text-gray-500">
                Advanced search options coming soon...
              </p>
            </div>
          )}
        </div>
      </div>
      
      {/* Search Results */}
      <div className="mt-8">
        {error && (
          <div className="mb-4 p-3 bg-red-100 border border-red-200 text-red-700 rounded-md">
            Error: {error.message}
          </div>
        )}
        
        <SearchResultsList 
          results={results} 
          loading={loading}
          showImagePreview={true}
        />
      </div>
    </div>
  );
};

export default ImageSearchPanel;