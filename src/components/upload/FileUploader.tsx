import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { FiUpload, FiFile, FiX, FiCheck, FiAlertCircle } from 'react-icons/fi';
import { formatBytes } from '../../utils/fileUtils';

// Izin verilen dosya türleri
const ACCEPTED_FILE_TYPES = {
  document: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'text/html'
  ],
  image: ['image/jpeg', 'image/png', 'image/webp', 'image/gif'],
  audio: ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/x-m4a']
};

interface FileUploaderProps {
  maxFiles?: number;
  maxSize?: number; // bytes
  accept?: 'document' | 'image' | 'audio' | 'all';
  onFilesChange: (files: File[]) => void;
  uploading?: boolean;
  uploadProgress?: number;
  uploadStatus?: 'idle' | 'uploading' | 'success' | 'error';
  uploadError?: string;
}

const FileUploader: React.FC<FileUploaderProps> = ({
  maxFiles = 10,
  maxSize = 50 * 1024 * 1024, // 50MB default
  accept = 'all',
  onFilesChange,
  uploading = false,
  uploadProgress = 0,
  uploadStatus = 'idle',
  uploadError
}) => {
  const [files, setFiles] = useState<File[]>([]);
  const [rejected, setRejected] = useState<{ file: File; errors: { code: string; message: string }[] }[]>([]);
  
  // Define accepted mime types
  const acceptedMimeTypes = accept === 'all'
    ? { 
        'application/pdf': ['.pdf'],
        'application/msword': ['.doc'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
        'text/plain': ['.txt'],
        'text/markdown': ['.md'],
        'text/html': ['.html'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/webp': ['.webp'],
        'image/gif': ['.gif'],
        'audio/mpeg': ['.mp3'],
        'audio/wav': ['.wav'],
        'audio/ogg': ['.ogg'],
        'audio/x-m4a': ['.m4a']
      }
    : accept === 'document'
      ? {
          'application/pdf': ['.pdf'],
          'application/msword': ['.doc'],
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
          'text/plain': ['.txt'],
          'text/markdown': ['.md'],
          'text/html': ['.html']
        }
      : accept === 'image'
        ? {
            'image/jpeg': ['.jpg', '.jpeg'],
            'image/png': ['.png'],
            'image/webp': ['.webp'],
            'image/gif': ['.gif']
          }
        : {
            'audio/mpeg': ['.mp3'],
            'audio/wav': ['.wav'],
            'audio/ogg': ['.ogg'],
            'audio/x-m4a': ['.m4a']
          };
  
  // Handle file drop
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    const newFiles = [...files, ...acceptedFiles].slice(0, maxFiles);
    setFiles(newFiles);
    setRejected(rejectedFiles);
    onFilesChange(newFiles);
  }, [files, maxFiles, onFilesChange]);
  
  // Configure dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    maxFiles,
    maxSize,
    accept: acceptedMimeTypes,
    disabled: uploading,
  });
  
  // Remove a file
  const removeFile = (index: number) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);
    onFilesChange(newFiles);
  };
  
  // Clear all files
  const clearFiles = () => {
    setFiles([]);
    setRejected([]);
    onFilesChange([]);
  };
  
  // Get accept type description
  const getAcceptTypeDescription = () => {
    switch (accept) {
      case 'document':
        return 'PDF, Word, Text, Markdown, HTML';
      case 'image':
        return 'JPEG, PNG, WebP, GIF';
      case 'audio':
        return 'MP3, WAV, OGG, M4A';
      case 'all':
        return 'Documents, Images, Audio files';
      default:
        return 'All files';
    }
  };
  
  return (
    <div className="w-full">
      {/* Dropzone area */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:bg-gray-50'
        } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} />
        
        <div className="flex flex-col items-center justify-center">
          <FiUpload className="w-12 h-12 text-gray-400 mb-4" />
          
          <p className="text-lg font-medium text-gray-700">
            {isDragActive
              ? 'Drop files here'
              : 'Drag & drop files here, or click to select'}
          </p>
          
          <p className="text-sm text-gray-500 mt-2">
            {getAcceptTypeDescription()} up to {formatBytes(maxSize)}
          </p>
        </div>
      </div>
      
      {/* Status indicator */}
      {uploadStatus === 'uploading' && (
        <div className="mt-4">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-blue-600 h-2.5 rounded-full"
              style={{ width: `${uploadProgress}%` }}
            ></div>
          </div>
          <p className="text-sm text-gray-600 mt-2">Uploading {uploadProgress}%</p>
        </div>
      )}
      
      {uploadStatus === 'success' && (
        <div className="mt-4 p-3 bg-green-50 text-green-800 rounded-md flex items-center">
          <FiCheck className="mr-2" />
          <span>Files uploaded successfully!</span>
        </div>
      )}
      
      {uploadStatus === 'error' && (
        <div className="mt-4 p-3 bg-red-50 text-red-800 rounded-md flex items-center">
          <FiAlertCircle className="mr-2" />
          <span>{uploadError || 'An error occurred during upload'}</span>
        </div>
      )}
      
      {/* File list */}
      {files.length > 0 && (
        <div className="mt-6">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-medium text-gray-900">Selected Files</h3>
            <button
              onClick={clearFiles}
              className="text-sm text-red-600 hover:text-red-800"
              disabled={uploading}
            >
              Clear all
            </button>
          </div>
          
          <ul className="divide-y divide-gray-200 border border-gray-200 rounded-md">
            {files.map((file, index) => (
              <li key={index} className="flex items-center justify-between py-3 px-4 hover:bg-gray-50">
                <div className="flex items-center">
                  <FiFile className="text-gray-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900 truncate max-w-md">{file.name}</p>
                    <p className="text-xs text-gray-500">{formatBytes(file.size)}</p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  disabled={uploading}
                  className="text-gray-400 hover:text-red-500"
                >
                  <FiX />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      
      {/* Rejected files */}
      {rejected.length > 0 && (
        <div className="mt-6">
          <h3 className="text-lg font-medium text-gray-900 mb-2">Rejected Files</h3>
          
          <ul className="divide-y divide-gray-200 border border-red-200 rounded-md bg-red-50">
            {rejected.map((rejection, index) => (
              <li key={index} className="py-3 px-4">
                <div className="flex items-center">
                  <FiAlertCircle className="text-red-500 mr-3" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{rejection.file.name}</p>
                    <ul className="list-disc pl-5 mt-1">
                      {rejection.errors.map((error, errorIndex) => (
                        <li key={errorIndex} className="text-xs text-red-600">
                          {error.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default FileUploader;