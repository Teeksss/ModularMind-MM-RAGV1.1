import { configureStore } from '@reduxjs/toolkit';
import { useDispatch, useSelector, TypedUseSelectorHook } from 'react-redux';
import authReducer from './slices/authSlice';
import searchReducer from './slices/searchSlice';
import documentsReducer from './slices/documentsSlice';
import uiReducer from './slices/uiSlice';
import analyticsReducer from './slices/analyticsSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    search: searchReducer,
    documents: documentsReducer,
    ui: uiReducer,
    analytics: analyticsReducer
  },
  middleware: (getDefaultMiddleware) => 
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['search/setSearchFile', 'documents/setUploadFiles'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.file', 'payload.files', 'meta.arg'],
        // Ignore these paths in the state
        ignoredPaths: [
          'search.currentFile',
          'documents.uploadFiles',
        ],
      },
    }),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

// Custom hooks for typed dispatch and selector
export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;