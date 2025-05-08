import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { SearchResult } from '../../types/search';
import { apiClient } from '../../api/apiClient';

interface SearchState {
  query: string;
  results: SearchResult[];
  loading: boolean;
  error: string | null;
  searchType: 'text' | 'image' | 'audio' | 'hybrid';
  currentFile: File | null;
  searchHistory: string[];
  additionalData: Record<string, any> | null;
}

const initialState: SearchState = {
  query: '',
  results: [],
  loading: false,
  error: null,
  searchType: 'text',
  currentFile: null,
  searchHistory: [],
  additionalData: null,
};

// Async thunks
export const performSearch = createAsyncThunk(
  'search/performSearch',
  async (
    { 
      query, 
      searchType,
      file,
      options 
    }: { 
      query?: string; 
      searchType: 'text' | 'image' | 'audio' | 'hybrid';
      file?: File | null;
      options?: Record<string, any>;
    }, 
    { rejectWithValue }
  ) => {
    try {
      let response;
      
      if (searchType === 'text' || (searchType === 'hybrid' && !file)) {
        // Text-only search
        response = await apiClient.post('/api/rag/search', {
          query,
          search_type: searchType,
          ...options
        });
      } else {
        // Multimodal search with file
        const formData = new FormData();
        
        if (query) {
          formData.append('text', query);
        }
        
        if (file) {
          if (searchType === 'image') {
            formData.append('image', file);
          } else if (searchType === 'audio') {
            formData.append('audio', file);
          }
        }
        
        if (options) {
          formData.append('options', JSON.stringify(options));
        }
        
        response = await apiClient.post('/api/multimodal/process', formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        });
      }
      
      return response.data;
    } catch (error: any) {
      return rejectWithValue(
        error.response?.data?.error?.message || 'Search failed'
      );
    }
  }
);

// Create the slice
const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload;
    },
    setSearchType: (state, action: PayloadAction<'text' | 'image' | 'audio' | 'hybrid'>) => {
      state.searchType = action.payload;
      // Reset file when switching search type
      if (action.payload === 'text') {
        state.currentFile = null;
      }
    },
    setSearchFile: (state, action: PayloadAction<File | null>) => {
      state.currentFile = action.payload;
    },
    clearSearch: (state) => {
      state.query = '';
      state.results = [];
      state.currentFile = null;
      state.error = null;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder.addCase(performSearch.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(performSearch.fulfilled, (state, action) => {
      state.loading = false;
      
      // Add to search history if it's a text query
      if (state.query && !state.searchHistory.includes(state.query)) {
        state.searchHistory = [...state.searchHistory, state.query].slice(-10);
      }
      
      // Handle response data based on search type
      if (action.payload.results) {
        state.results = action.payload.results;
      } else {
        state.results = [];
      }
      
      // Extract and store additional data
      const { results, ...additionalData } = action.payload;
      state.additionalData = Object.keys(additionalData).length > 0 ? additionalData : null;
    });
    builder.addCase(performSearch.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload as string;
    });
  },
});

export const { 
  setQuery, 
  setSearchType, 
  setSearchFile, 
  clearSearch,
  clearError
} = searchSlice.actions;

export default searchSlice.reducer;