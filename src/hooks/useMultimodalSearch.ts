import { useState } from 'react';
import { apiClient } from '../api/apiClient';
import { SearchResult } from '../types/search';

type SearchParams = {
  text?: string;
  image?: File | null;
  audio?: File | null;
  options?: {
    limit?: number;
    filter?: Record<string, any> | null;
    transcribe?: boolean;
  };
};

type SearchResponse = {
  results: SearchResult[];
  text_result?: any;
  image_result?: any;
  audio_result?: any;
  image_caption?: string;
  audio_transcript?: string;
  embedding?: number[];
  embedding_dimensions?: number;
};

export const useMultimodalSearch = () => {
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [additionalData, setAdditionalData] = useState<Omit<SearchResponse, 'results'> | null>(null);

  const search = async (params: SearchParams): Promise<SearchResponse | null> => {
    try {
      setLoading(true);
      setError(null);
      
      // Create form data for file upload
      const formData = new FormData();
      
      if (params.text) {
        formData.append('text', params.text);
      }
      
      if (params.image) {
        formData.append('image', params.image);
      }
      
      if (params.audio) {
        formData.append('audio', params.audio);
      }
      
      // Add options as JSON string
      if (params.options) {
        formData.append('options', JSON.stringify(params.options));
      }
      
      // Make the API request
      const response = await apiClient.post<SearchResponse>('/api/multimodal/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Handle the response
      if (response.data) {
        // Set search results
        if (response.data.results) {
          setResults(response.data.results);
        } else {
          setResults([]);
        }
        
        // Extract additional data
        const { results, ...rest } = response.data;
        setAdditionalData(rest);
        
        return response.data;
      }
      
      return null;
    } catch (err) {
      const error = err instanceof Error ? err : new Error('An unknown error occurred');
      setError(error);
      console.error('Error performing multimodal search:', error);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { 
    search, 
    results, 
    loading, 
    error,
    additionalData
  };
};