import api from './api';

export interface MultimodalContent {
  id: string;
  content_type: 'image' | 'video' | 'audio';
  filename: string;
  caption?: string;
  preview?: string;
  metadata: Record<string, any>;
  created_at: string;
}

export interface MultimodalSearchQuery {
  query_text?: string;
  query_image?: string;
  filter?: Record<string, any>;
  limit?: number;
}

export interface MultimodalSearchResult {
  id: string;
  content_type: 'image' | 'video' | 'audio';
  filename: string;
  caption: string;
  preview: string | null;
  metadata: Record<string, any>;
  created_at: string;
}

class MultimodalService {
  /**
   * Multimodal içerik yükler.
   */
  async uploadContent(file: File, metadata?: { title?: string; description?: string; tags?: string }): Promise<{ content_id: string; content_type: string; filename: string; caption?: string; metadata: Record<string, any>; message: string }> {
    const formData = new FormData();
    formData.append('file', file);
    
    if (metadata?.title) {
      formData.append('title', metadata.title);
    }
    
    if (metadata?.description) {
      formData.append('description', metadata.description);
    }
    
    if (metadata?.tags) {
      formData.append('tags', metadata.tags);
    }
    
    const response = await api.post('/api/v1/multimodal/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    return response.data;
  }
  
  /**
   * Görüntüleri listeler.
   */
  async listImages(page: number = 1, pageSize: number = 10): Promise<{ contents: MultimodalContent[]; total_count: number; page: number; page_size: number }> {
    const response = await api.get('/api/v1/multimodal/images', {
      params: { page, page_size: pageSize },
    });
    
    return response.data;
  }
  
  /**
   * Videoları listeler.
   */
  async listVideos(page: number = 1, pageSize: number = 10): Promise<{ contents: MultimodalContent[]; total_count: number; page: number; page_size: number }> {
    const response = await api.get('/api/v1/multimodal/videos', {
      params: { page, page_size: pageSize },
    });
    
    return response.data;
  }
  
  /**
   * Ses dosyalarını listeler.
   */
  async listAudios(page: number = 1, pageSize: number = 10): Promise<{ contents: MultimodalContent[]; total_count: number; page: number; page_size: number }> {
    const response = await api.get('/api/v1/multimodal/audios', {
      params: { page, page_size: pageSize },
    });
    
    return response.data;
  }
  
  /**
   * Multimodal içerik arar.
   */
  async search(query: MultimodalSearchQuery): Promise<{ results: MultimodalSearchResult[]; count: number }> {
    const response = await api.post('/api/v1/multimodal/search', query);
    return response.data;
  }
}

export const multimodalService = new MultimodalService();