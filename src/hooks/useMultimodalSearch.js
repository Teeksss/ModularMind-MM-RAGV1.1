import { useState } from 'react';
import { apiClient } from '../services/apiClient';

export const useMultimodalSearch = () => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const search = async ({ text, image, audio, options = {} }) => {
    try {
      setLoading(true);
      setError(null);
      
      // Create form data for file upload
      const formData = new FormData();
      
      if (text) {
        formData.append('text', text);
      }
      
      if (image) {
        formData.append('image', image);
      }
      
      if (audio) {
        formData.append('audio', audio);
      }
      
      // Add options as JSON string
      formData.append('options', JSON.stringify(options));
      
      // Make the API request
      const response = await apiClient.post('/api/multimodal/process', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      // Handle the response
      if (response.data && response.data.results) {
        setResults(response.data.results);
      } else {
        setResults([]);
      }
      
      setLoading(false);
      return response.data;
    } catch (err) {
      setError(err);
      setLoading(false);
      console.error('Error performing multimodal search:', err);
      return null;
    }
  };

  return { search, results, loading, error };
};