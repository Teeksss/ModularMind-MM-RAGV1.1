import { apiService } from './api';

/**
 * Service for multimodal operations
 */
export const multimodalService = {
  /**
   * Generate embeddings for an image
   */
  generateImageEmbedding: async (imageData: string, modelName?: string) => {
    return apiService.post('/multimodal/image-embedding', {
      image_data: imageData,
      model: modelName
    });
  },

  /**
   * Upload image file for embedding
   */
  uploadImageForEmbedding: async (file: File, modelName?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (modelName) formData.append('model', modelName);
    
    return apiService.upload('/multimodal/image-upload', formData);
  },

  /**
   * Compute similarity between image and text
   */
  computeSimilarity: async (imageData: string, texts: string | string[], modelName?: string) => {
    return apiService.post('/multimodal/similarity', {
      image_data: imageData,
      texts,
      model: modelName
    });
  },

  /**
   * Get available multimodal models
   */
  getModels: async () => {
    return apiService.get('/multimodal/models');
  }
};