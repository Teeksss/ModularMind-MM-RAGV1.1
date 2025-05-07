import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { FaCamera, FaSearch, FaList, FaSlidersH, FaTags } from 'react-icons/fa';
import ImageUploader from '../components/multimodal/ImageUploader';
import SearchResults from '../components/search/SearchResults';
import { Tab } from '@headlessui/react';
import { apiService } from '../services/api';
import { useNotificationStore } from '../store/notificationStore';
import ErrorBoundary from '../components/common/ErrorBoundary';

// Result type
interface SearchResult {
  id: string;
  text: string;
  score: number;
  metadata: Record<string, any>;
}

// Similarity result
interface SimilarityResult {
  text: string;
  score: number;
}

const MultimodalSearchPage: React.FC = () => {
  const { t } = useTranslation();
  const { addNotification } = useNotificationStore();
  
  // State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [similarityResults, setSimilarityResults] = useState<SimilarityResult[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [imageEmbedding, setImageEmbedding] = useState<number[] | null>(null);
  const [modelName, setModelName] = useState<string>('');
  const [availableModels, setAvailableModels] = useState<{name: string, description: string}[]>([]);
  const [selectedModel, setSelectedModel] = useState<string>('');
  
  // Fetch available multimodal models
  useEffect(() => {
    const fetchModels = async () => {
      try {
        const response = await apiService.get('/multimodal/models');
        const models = response.data.models.map((model: any) => ({
          name: model.name,
          description: model.metadata?.description || model.name
        }));
        setAvailableModels(models);
        
        // Set default model
        if (response.data.default_model && !selectedModel) {
          setSelectedModel(response.data.default_model);
        }
      } catch (error) {
        console.error('Error fetching multimodal models:', error);
      }
    };
    
    fetchModels();
  }, []);
  
  // Handle embedding generation callback
  const handleEmbeddingGenerated = (embedding: number[], model: string) => {
    setImageEmbedding(embedding);
    setModelName(model);
    
    addNotification({
      type: 'success',
      title: t('multimodal.embeddingGenerated'),
      message: t('multimodal.embeddingGeneratedDesc', { model })
    });
  };
  
  // Handle similarity generation callback
  const handleSimilarityGenerated = (scores: number[]) => {
    // Get similarity texts from somewhere (example: predefined options)
    const texts = searchQuery.split(',').map(t => t.trim());
    
    if (texts.length !== scores.length) {
      addNotification({
        type: 'error',
        title: t('multimodal.similarityError'),
        message: t('multimodal.textCountMismatch')
      });
      return;
    }
    
    // Create similarity results
    const similarityData = texts.map((text, index) => ({
      text,
      score: scores[index]
    }));
    
    // Sort by score
    similarityData.sort((a, b) => b.score - a.score);
    
    setSimilarityResults(similarityData);
  };
  
  // Handle search error
  const handleError = (error: string) => {
    addNotification({
      type: 'error',
      title: t('multimodal.error'),
      message: error
    });
  };
  
  // Handle search with image embedding
  const handleSearch = async () => {
    if (!imageEmbedding) {
      addNotification({
        type: 'warning',
        title: t('multimodal.noEmbedding'),
        message: t('multimodal.generateEmbeddingFirst')
      });
      return;
    }
    
    if (!searchQuery.trim()) {
      addNotification({
        type: 'warning',
        title: t('multimodal.noQuery'),
        message: t('multimodal.enterSearchQuery')
      });
      return;
    }
    
    setIsLoading(true);
    
    try {
      // Search using the image embedding
      const response = await apiService.post('/retrieval/search', {
        query: searchQuery,
        vector: imageEmbedding,
        model_name: modelName,
        k: 10
      });
      
      setResults(response.data.results);
      
    } catch (error) {
      console.error('Search error:', error);
      handleError(error.message || t('multimodal.searchError'));
    } finally {
      setIsLoading(false);
    }
  };
  
  return (
    <ErrorBoundary>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          {t('multimodal.title')}
        </h1>
        
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 mb-8">
          <Tab.Group>
            <Tab.List className="flex p-1 space-x-1 bg-gray-100 dark:bg-gray-700 rounded-xl mb-6">
              <Tab className={({ selected }) =>
                `w-full py-2.5 text-sm leading-5 font-medium rounded-lg
                 ${selected
                  ? 'bg-white dark:bg-gray-800 shadow text-blue-700 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-300'
                }`
              }>
                <div className="flex items-center justify-center">
                  <FaCamera className="mr-2" />
                  {t('multimodal.imageSearch')}
                </div>
              </Tab>
              
              <Tab className={({ selected }) =>
                `w-full py-2.5 text-sm leading-5 font-medium rounded-lg
                 ${selected
                  ? 'bg-white dark:bg-gray-800 shadow text-blue-700 dark:text-blue-400'
                  : 'text-gray-700 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-300'
                }`
              }>
                <div className="flex items-center justify-center">
                  <FaTags className="mr-2" />
                  {t('multimodal.similarityAnalysis')}
                </div>
              </Tab>
            </Tab.List>
            
            <Tab.Panels>
              {/* Image Search Panel */}
              <Tab.Panel>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Column - Image Upload */}
                  <div>
                    <h2 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">
                      {t('multimodal.uploadImage')}
                    </h2>
                    
                    {/* Model Selection */}
                    <div className="mb-4">
                      <label htmlFor="model-select" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {t('multimodal.selectModel')}
                      </label>
                      <select
                        id="model-select"
                        value={selectedModel}
                        onChange={(e) => setSelectedModel(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                      >
                        <option value="">{t('multimodal.selectModelOption')}</option>
                        {availableModels.map((model) => (
                          <option key={model.name} value={model.name}>
                            {model.name} - {model.description}
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    {/* Image Uploader Component */}
                    <ImageUploader
                      onEmbeddingGenerated={handleEmbeddingGenerated}
                      onError={handleError}
                      multimodalModel={selectedModel}
                    />
                    
                    {/* Status Info */}
                    {imageEmbedding && (
                      <div className="mt-4 p-3 bg-green-50 dark:bg-green-900 dark:bg-opacity-20 rounded-md">
                        <p className="text-sm text-green-800 dark:text-green-300">
                          {t('multimodal.embeddingReady')} ({modelName})
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {t('multimodal.dimensions')}: {imageEmbedding.length}
                        </p>
                      </div>
                    )}
                  </div>
                  
                  {/* Right Column - Search */}
                  <div>
                    <h2 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">
                      {t('multimodal.searchWithImage')}
                    </h2>
                    
                    {/* Search Input */}
                    <div className="mb-4">
                      <label htmlFor="search-query" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {t('multimodal.searchQueryLabel')}
                      </label>
                      <div className="relative">
                        <input
                          id="search-query"
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                          placeholder={t('multimodal.searchPlaceholder')}
                          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                        />
                        <FaSearch className="absolute right-3 top-3 text-gray-400" />
                      </div>
                    </div>
                    
                    {/* Search Button */}
                    <button
                      onClick={handleSearch}
                      disabled={isLoading || !imageEmbedding}
                      className={`w-full flex justify-center items-center px-4 py-2 rounded-md text-white font-medium 
                        ${isLoading || !imageEmbedding
                          ? 'bg-gray-400 cursor-not-allowed'
                          : 'bg-blue-600 hover:bg-blue-700'
                        }`}
                    >
                      {isLoading ? (
                        <>
                          <div className="animate-spin mr-2 h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                          {t('common.loading')}
                        </>
                      ) : (
                        <>
                          <FaSearch className="mr-2" />
                          {t('multimodal.search')}
                        </>
                      )}
                    </button>
                    
                    {/* Search Requirements */}
                    <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
                      <p>{t('multimodal.searchRequirements')}</p>
                      <ul className="list-disc list-inside mt-2 ml-2 space-y-1">
                        <li>{t('multimodal.requireImage')}</li>
                        <li>{t('multimodal.requireQuery')}</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                {/* Search Results */}
                {results.length > 0 && (
                  <div className="mt-8">
                    <h3 className="text-lg font-medium mb-4 text-gray-900 dark:text-white flex items-center">
                      <FaList className="mr-2" />
                      {t('search.results')} ({results.length})
                    </h3>
                    
                    <SearchResults results={results} />
                  </div>
                )}
              </Tab.Panel>
              
              {/* Similarity Analysis Panel */}
              <Tab.Panel>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Left Column - Image Upload */}
                  <div>
                    <h2 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">
                      {t('multimodal.uploadImageForSimilarity')}
                    </h2>
                    
                    {/* Image Uploader for Similarity */}
                    <ImageUploader
                      onSimilarityGenerated={handleSimilarityGenerated}
                      onError={handleError}
                      multimodalModel={selectedModel}
                    />
                    
                    {/* Text Input Instructions */}
                    <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900 dark:bg-opacity-20 rounded-md">
                      <p className="text-sm text-blue-800 dark:text-blue-300">
                        {t('multimodal.similarityInstructions')}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                        {t('multimodal.enterMultipleTexts')}
                      </p>
                    </div>
                  </div>
                  
                  {/* Right Column - Similarity Results */}
                  <div>
                    <h2 className="text-lg font-medium mb-4 text-gray-900 dark:text-white">
                      {t('multimodal.similarityResults')}
                    </h2>
                    
                    {/* Text Input for Similarity Comparison */}
                    <div className="mb-4">
                      <label htmlFor="similarity-texts" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                        {t('multimodal.textToCompare')}
                      </label>
                      <textarea
                        id="similarity-texts"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
                        rows={4}
                        placeholder={t('multimodal.textComparisonPlaceholder')}
                      />
                      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        {t('multimodal.separateWithCommas')}
                      </p>
                    </div>
                    
                    {/* Similarity Results Display */}
                    {similarityResults.length > 0 ? (
                      <div className="bg-white dark:bg-gray-700 rounded-md shadow p-4">
                        <h3 className="text-md font-medium mb-2 text-gray-900 dark:text-white">
                          {t('multimodal.matchResults')}
                        </h3>
                        
                        <ul className="space-y-2">
                          {similarityResults.map((result, index) => (
                            <li key={index} className="flex justify-between border-b border-gray-200 dark:border-gray-600 pb-2">
                              <span className="text-gray-800 dark:text-gray-200">{result.text}</span>
                              <span className={`font-medium ${
                                result.score > 0.7 
                                  ? 'text-green-600 dark:text-green-400' 
                                  : result.score > 0.4 
                                    ? 'text-yellow-600 dark:text-yellow-400'
                                    : 'text-red-600 dark:text-red-400'
                              }`}>
                                {(result.score * 100).toFixed(1)}%
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : (
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-md p-8 text-center">
                        <p className="text-gray-500 dark:text-gray-400">
                          {t('multimodal.noSimilarityResults')}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </Tab.Panel>
            </Tab.Panels>
          </Tab.Group>
        </div>
        
        {/* How It Works Section */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            {t('multimodal.howItWorks')}
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <div className="flex items-center mb-2">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mr-3">
                  <span className="text-blue-800 dark:text-blue-300 font-bold">1</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  {t('multimodal.step1Title')}
                </h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                {t('multimodal.step1Description')}
              </p>
            </div>
            
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <div className="flex items-center mb-2">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mr-3">
                  <span className="text-blue-800 dark:text-blue-300 font-bold">2</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  {t('multimodal.step2Title')}
                </h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                {t('multimodal.step2Description')}
              </p>
            </div>
            
            <div className="p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
              <div className="flex items-center mb-2">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mr-3">
                  <span className="text-blue-800 dark:text-blue-300 font-bold">3</span>
                </div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  {t('multimodal.step3Title')}
                </h3>
              </div>
              <p className="text-gray-600 dark:text-gray-300">
                {t('multimodal.step3Description')}
              </p>
            </div>
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
};

export default MultimodalSearchPage;