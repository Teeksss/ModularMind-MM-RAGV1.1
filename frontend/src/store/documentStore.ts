import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { apiService } from '../services/api';
import { useNotificationStore } from './notificationStore';

// Document interface
export interface Document {
  id: string;
  title: string;
  content_type: string;
  source?: string;
  language?: string;
  summary?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
  is_processed: boolean;
  is_indexed: boolean;
  is_public: boolean;
  enrichment_status: string;
  chunks_count?: number;
}

// Document chunk interface
export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  metadata?: Record<string, any>;
  embedding_model?: string;
  created_at: string;
  updated_at?: string;
}

// Document upload progress
export interface UploadProgress {
  id: string;
  filename: string;
  progress: number;
  status: 'uploading' | 'processing' | 'completed' | 'failed';
  error?: string;
}

// Document store interface
interface DocumentStore {
  // Document state
  documents: Document[];
  selectedDocument: Document | null;
  documentChunks: Record<string, DocumentChunk[]>;
  isLoading: boolean;
  uploadProgress: Record<string, UploadProgress>;
  
  // Document filters
  searchQuery: string;
  filters: Record<string, any>;
  
  // Pagination
  page: number;
  pageSize: number;
  total: number;
  
  // Actions
  fetchDocuments: (page?: number, pageSize?: number, filters?: Record<string, any>) => Promise<void>;
  fetchDocument: (id: string) => Promise<Document | null>;
  fetchDocumentChunks: (documentId: string) => Promise<DocumentChunk[]>;
  uploadDocument: (file: File, metadata?: Record<string, any>) => Promise<string>;
  updateDocument: (id: string, data: Partial<Document>) => Promise<Document>;
  deleteDocument: (id: string) => Promise<boolean>;
  setSelectedDocument: (document: Document | null) => void;
  setFilters: (filters: Record<string, any>) => void;
  setSearchQuery: (query: string) => void;
  clearUploadProgress: (id: string) => void;
  resetStore: () => void;
}

// Create store
export const useDocumentStore = create<DocumentStore>()(
  persist(
    (set, get) => ({
      // Initial state
      documents: [],
      selectedDocument: null,
      documentChunks: {},
      isLoading: false,
      uploadProgress: {},
      searchQuery: '',
      filters: {},
      page: 1,
      pageSize: 10,
      total: 0,
      
      // Actions
      fetchDocuments: async (page = 1, pageSize = 10, filters = {}) => {
        set({ isLoading: true });
        
        try {
          const response = await apiService.get('/documents', {
            params: {
              page,
              per_page: pageSize,
              ...get().filters,
              ...filters,
              search: get().searchQuery || undefined,
            },
          });
          
          set({
            documents: response.data.items || [],
            page: response.data.page || 1,
            pageSize: response.data.per_page || 10,
            total: response.data.total || 0,
            isLoading: false,
          });
        } catch (error) {
          console.error('Failed to fetch documents:', error);
          set({ isLoading: false });
        }
      },
      
      fetchDocument: async (id: string) => {
        set({ isLoading: true });
        
        try {
          const response = await apiService.get(`/documents/${id}`);
          const document = response.data;
          
          // Update selected document
          set({ selectedDocument: document, isLoading: false });
          
          return document;
        } catch (error) {
          console.error(`Failed to fetch document ${id}:`, error);
          set({ isLoading: false });
          return null;
        }
      },
      
      fetchDocumentChunks: async (documentId: string) => {
        set({ isLoading: true });
        
        try {
          const response = await apiService.get(`/documents/${documentId}/chunks`);
          const chunks = response.data.items || [];
          
          // Update document chunks
          set((state) => ({
            documentChunks: {
              ...state.documentChunks,
              [documentId]: chunks,
            },
            isLoading: false,
          }));
          
          return chunks;
        } catch (error) {
          console.error(`Failed to fetch chunks for document ${documentId}:`, error);
          set({ isLoading: false });
          return [];
        }
      },
      
      uploadDocument: async (file: File, metadata = {}) => {
        // Create a unique ID for tracking upload progress
        const uploadId = `upload-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        
        // Initialize upload progress
        set((state) => ({
          uploadProgress: {
            ...state.uploadProgress,
            [uploadId]: {
              id: uploadId,
              filename: file.name,
              progress: 0,
              status: 'uploading',
            },
          },
        }));
        
        try {
          // Create form data
          const formData = new FormData();
          formData.append('file', file);
          
          // Add metadata if provided
          if (Object.keys(metadata).length > 0) {
            formData.append('metadata', JSON.stringify(metadata));
          }
          
          // Upload the document with progress tracking
          const response = await apiService.upload('/documents/upload', formData, {
            onUploadProgress: (progressEvent) => {
              const progress = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
              
              set((state) => ({
                uploadProgress: {
                  ...state.uploadProgress,
                  [uploadId]: {
                    ...state.uploadProgress[uploadId],
                    progress: progress,
                  },
                },
              }));
            },
          });
          
          // Update upload progress after upload is complete
          set((state) => ({
            uploadProgress: {
              ...state.uploadProgress,
              [uploadId]: {
                ...state.uploadProgress[uploadId],
                status: 'processing',
                progress: 100,
              },
            },
          }));
          
          // Refresh document list
          await get().fetchDocuments();
          
          // Show success notification
          useNotificationStore.getState().addNotification({
            type: 'success',
            title: 'Document Uploaded',
            message: `${file.name} has been uploaded successfully`,
          });
          
          // Update upload progress after processing
          set((state) => ({
            uploadProgress: {
              ...state.uploadProgress,
              [uploadId]: {
                ...state.uploadProgress[uploadId],
                status: 'completed',
              },
            },
          }));
          
          return response.data.id;
        } catch (error) {
          console.error(`Failed to upload document ${file.name}:`, error);
          
          // Update upload progress with error
          set((state) => ({
            uploadProgress: {
              ...state.uploadProgress,
              [uploadId]: {
                ...state.uploadProgress[uploadId],
                status: 'failed',
                error: error.message || 'Upload failed',
              },
            },
          }));
          
          // Show error notification
          useNotificationStore.getState().addNotification({
            type: 'error',
            title: 'Upload Failed',
            message: `Failed to upload ${file.name}: ${error.message || 'Unknown error'}`,
          });
          
          throw error;
        }
      },
      
      updateDocument: async (id: string, data: Partial<Document>) => {
        try {
          const response = await apiService.put(`/documents/${id}`, data);
          const updatedDocument = response.data;
          
          // Update documents list and selected document
          set((state) => ({
            documents: state.documents.map((doc) => 
              doc.id === id ? updatedDocument : doc
            ),
            selectedDocument: state.selectedDocument?.id === id 
              ? updatedDocument 
              : state.selectedDocument,
          }));
          
          return updatedDocument;
        } catch (error) {
          console.error(`Failed to update document ${id}:`, error);
          throw error;
        }
      },
      
      deleteDocument: async (id: string) => {
        try {
          await apiService.delete(`/documents/${id}`);
          
          // Remove document from state
          set((state) => ({
            documents: state.documents.filter((doc) => doc.id !== id),
            selectedDocument: state.selectedDocument?.id === id 
              ? null 
              : state.selectedDocument,
            documentChunks: {
              ...state.documentChunks,
              [id]: undefined,
            },
          }));
          
          return true;
        } catch (error) {
          console.error(`Failed to delete document ${id}:`, error);
          return false;
        }
      },
      
      setSelectedDocument: (document: Document | null) => {
        set({ selectedDocument: document });
      },
      
      setFilters: (filters: Record<string, any>) => {
        set({ filters });
      },
      
      setSearchQuery: (query: string) => {
        set({ searchQuery: query });
      },
      
      clearUploadProgress: (id: string) => {
        set((state) => {
          const newUploadProgress = { ...state.uploadProgress };
          delete newUploadProgress[id];
          return { uploadProgress: newUploadProgress };
        });
      },
      
      resetStore: () => {
        set({
          documents: [],
          selectedDocument: null,
          documentChunks: {},
          isLoading: false,
          uploadProgress: {},
          searchQuery: '',
          filters: {},
          page: 1,
          pageSize: 10,
          total: 0,
        });
      },
    }),
    {
      name: 'document-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        filters: state.filters,
        page: state.page,
        pageSize: state.pageSize,
      }),
    }
  )
);