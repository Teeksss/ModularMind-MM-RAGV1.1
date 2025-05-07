import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { BiUpload, BiFile, BiX, BiLoader } from 'react-icons/bi';
import { useDropzone } from 'react-dropzone';

import { api } from '../../services/api';
import { Document, EnrichmentStatus } from '../../types';
import { useDocumentStore } from '../../store/documentStore';
import { showToast } from '../../utils/notifications';
import { config } from '../../config/config';

interface UploadingFile {
  id: string;
  file: File;
  progress: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

const DocumentUpload: React.FC = () => {
  const { t } = useTranslation();
  const [uploadingFiles, setUploadingFiles] = useState<UploadingFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const { addDocument } = useDocumentStore();
  const abortControllerRef = useRef<Record<string, AbortController>>({});

  const onDrop = (acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map((file) => ({
      id: crypto.randomUUID(),
      file,
      progress: 0,
      status: 'pending' as const,
    }));
    
    setUploadingFiles((prev) => [...prev, ...newFiles]);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/html': ['.html'],
      'application/json': ['.json'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
    multiple: true,
  });

  const uploadFile = async (fileItem: UploadingFile) => {
    // Create FormData
    const formData = new FormData();
    formData.append('file', fileItem.file);
    formData.append('title', fileItem.file.name);
    formData.append('source', 'file_upload');
    formData.append('language', config.ui.defaultLanguage);
    
    try {
      // Create AbortController for this upload
      const controller = new AbortController();
      abortControllerRef.current[fileItem.id] = controller;
      
      // Update status to uploading
      setUploadingFiles((prev) =>
        prev.map((item) =>
          item.id === fileItem.id ? { ...item, status: 'uploading' } : item
        )
      );
      
      // Upload file with progress tracking
      const document = await api.upload<Document>(
        '/documents/upload', 
        formData, 
        (progress) => {
          setUploadingFiles((prev) =>
            prev.map((item) =>
              item.id === fileItem.id ? { ...item, progress } : item
            )
          );
        },
        { signal: controller.signal }
      );
      
      // Update status to success
      setUploadingFiles((prev) =>
        prev.map((item) =>
          item.id === fileItem.id ? { ...item, status: 'success', progress: 100 } : item
        )
      );
      
      // Add document to store
      addDocument(document);
      
      // Clean up AbortController
      delete abortControllerRef.current[fileItem.id];
      
      // Show success toast
      showToast('success', t('documents.uploadSuccess', { name: fileItem.file.name }));
      
      return document;
      
    } catch (error) {
      // Check if the request was aborted
      if (error.name === 'AbortError') {
        return null;
      }
      
      // Update status to error
      setUploadingFiles((prev) =>
        prev.map((item) =>
          item.id === fileItem.id
            ? { 
                ...item, 
                status: 'error', 
                error: error.message || t('common.unknownError')
              }
            : item
        )
      );
      
      // Clean up AbortController
      delete abortControllerRef.current[fileItem.id];
      
      // Show error toast
      showToast('error', t('documents.uploadFailed', { name: fileItem.file.name }));
      
      return null;
    }
  };

  const uploadAllFiles = async () => {
    if (isUploading) return;
    
    const pendingFiles = uploadingFiles.filter((file) => file.status === 'pending');
    if (pendingFiles.length === 0) return;
    
    setIsUploading(true);
    
    try {
      // Upload files sequentially
      for (const file of pendingFiles) {
        await uploadFile(file);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const cancelUpload = (fileId: string) => {
    // If the file is uploading, abort the request
    if (abortControllerRef.current[fileId]) {
      abortControllerRef.current[fileId].abort();
      delete abortControllerRef.current[fileId];
    }
    
    // Remove file from the list
    setUploadingFiles((prev) => prev.filter((file) => file.id !== fileId));
  };

  const removeFile = (fileId: string) => {
    cancelUpload(fileId);
  };

  const clearCompleted = () => {
    setUploadingFiles((prev) => 
      prev.filter((file) => file.status !== 'success')
    );
  };

  const retryUpload = async (fileId: string) => {
    const fileItem = uploadingFiles.find((file) => file.id === fileId);
    if (!fileItem) return;
    
    // Reset file status
    setUploadingFiles((prev) =>
      prev.map((item) =>
        item.id === fileId ? { ...item, status: 'pending', progress: 0, error: undefined } : item
      )
    );
    
    // Upload the file
    await uploadFile(fileItem);
  };

  return (
    <div className="w-full">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
            : 'border-gray-300 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center justify-center space-y-2">
          <BiUpload className="text-4xl text-gray-400" />
          <p className="text-gray-600 dark:text-gray-300">
            {isDragActive
              ? t('documents.dropFilesHere')
              : t('documents.dragOrClick')}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {t('documents.supportedFormats')}
          </p>
        </div>
      </div>

      {uploadingFiles.length > 0 && (
        <div className="mt-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="font-medium">{t('documents.files')}</h3>
            <div className="space-x-2">
              {uploadingFiles.some((file) => file.status === 'success') && (
                <button
                  onClick={clearCompleted}
                  className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {t('documents.clearCompleted')}
                </button>
              )}
              {uploadingFiles.some((file) => file.status === 'pending') && (
                <button
                  onClick={uploadAllFiles}
                  disabled={isUploading}
                  className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {isUploading ? t('common.uploading') : t('common.uploadAll')}
                </button>
              )}
            </div>
          </div>
          
          <ul className="space-y-2">
            {uploadingFiles.map((file) => (
              <li
                key={file.id}
                className="border rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center space-x-3 overflow-hidden">
                  <BiFile className="flex-shrink-0 text-xl text-gray-500" />
                  <div className="overflow-hidden">
                    <p className="font-medium truncate" title={file.file.name}>
                      {file.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(file.file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  {file.status === 'uploading' && (
                    <div className="flex items-center space-x-2">
                      <div className="w-32 bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                        <div
                          className="bg-blue-600 h-2.5 rounded-full"
                          style={{ width: `${file.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-500">{file.progress}%</span>
                    </div>
                  )}
                  
                  {file.status === 'success' && (
                    <span className="text-xs text-green-600 dark:text-green-400">
                      {t('common.completed')}
                    </span>
                  )}
                  
                  {file.status === 'error' && (
                    <div className="flex items-center space-x-2">
                      <span className="text-xs text-red-600 dark:text-red-400" title={file.error}>
                        {t('common.failed')}
                      </span>
                      <button
                        onClick={() => retryUpload(file.id)}
                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        {t('common.retry')}
                      </button>
                    </div>
                  )}
                  
                  {file.status === 'pending' && (
                    <span className="text-xs text-gray-500">{t('common.pending')}</span>
                  )}
                  
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-1 text-gray-500 hover:text-red-600 dark:hover:text-red-400"
                    title={t('common.remove')}
                  >
                    <BiX />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default DocumentUpload;