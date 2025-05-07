import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Document as DocumentType } from '../../store/documentStore';
import { FaFilePdf, FaFileWord, FaFileAlt, FaFileCode, FaImage, FaExpand, FaCompress, FaDownload, FaExternalLinkAlt } from 'react-icons/fa';
import { Tab } from '@headlessui/react';

// PDF Viewer
const PDFViewer = React.lazy(() => import('./viewers/PDFViewer'));
// Text Viewer
const TextViewer = React.lazy(() => import('./viewers/TextViewer'));
// Image Viewer
const ImageViewer = React.lazy(() => import('./viewers/ImageViewer'));
// Code Viewer
const CodeViewer = React.lazy(() => import('./viewers/CodeViewer'));

interface DocumentViewerProps {
  document: DocumentType;
  onClose?: () => void;
}

const DocumentViewer: React.FC<DocumentViewerProps> = ({ document, onClose }) => {
  const { t } = useTranslation();
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Content type mappings
  const contentTypeMappings = {
    'application/pdf': 'pdf',
    'application/msword': 'word',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'word',
    'text/plain': 'text',
    'text/markdown': 'markdown',
    'text/html': 'html',
    'application/json': 'json',
    'application/xml': 'xml',
    'image/png': 'image',
    'image/jpeg': 'image',
    'image/gif': 'image',
    'image/svg+xml': 'image',
  };
  
  // Determine the document type
  const docType = contentTypeMappings[document.content_type as keyof typeof contentTypeMappings] || 'text';
  
  // Toggle fullscreen
  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };
  
  // Download document
  const handleDownload = () => {
    if (document.source) {
      window.open(document.source, '_blank');
    }
  };
  
  // Render the appropriate viewer based on document type
  const renderViewer = () => {
    switch (docType) {
      case 'pdf':
        return (
          <React.Suspense fallback={<div className="loading">Loading PDF...</div>}>
            <PDFViewer documentUrl={document.source || ''} />
          </React.Suspense>
        );
        
      case 'image':
        return (
          <React.Suspense fallback={<div className="loading">Loading image...</div>}>
            <ImageViewer src={document.source || ''} alt={document.title} />
          </React.Suspense>
        );
        
      case 'json':
      case 'xml':
      case 'html':
        return (
          <React.Suspense fallback={<div className="loading">Loading code...</div>}>
            <CodeViewer code={document.content || ''} language={docType} />
          </React.Suspense>
        );
        
      case 'markdown':
        return (
          <React.Suspense fallback={<div className="loading">Loading markdown...</div>}>
            <TextViewer text={document.content || ''} format="markdown" />
          </React.Suspense>
        );
        
      default:
        return (
          <React.Suspense fallback={<div className="loading">Loading text...</div>}>
            <TextViewer text={document.content || ''} format="text" />
          </React.Suspense>
        );
    }
  };
  
  // Icon for document type
  const renderIcon = () => {
    switch (docType) {
      case 'pdf':
        return <FaFilePdf className="mr-2" />;
      case 'word':
        return <FaFileWord className="mr-2" />;
      case 'image':
        return <FaImage className="mr-2" />;
      case 'json':
      case 'xml':
      case 'html':
        return <FaFileCode className="mr-2" />;
      default:
        return <FaFileAlt className="mr-2" />;
    }
  };
  
  // View classes based on fullscreen state
  const viewerClasses = isFullscreen
    ? 'fixed inset-0 z-50 bg-white dark:bg-gray-900 p-4 overflow-auto'
    : 'relative w-full h-full min-h-[300px] bg-white dark:bg-gray-900 rounded-lg shadow-lg overflow-auto';
  
  return (
    <div className={viewerClasses}>
      {/* Header */}
      <div className="flex justify-between items-center mb-4 p-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center">
          {renderIcon()}
          <h2 className="text-lg font-semibold truncate max-w-lg">{document.title}</h2>
        </div>
        
        <div className="flex space-x-2">
          {document.source && (
            <>
              <button
                onClick={handleDownload}
                className="p-2 text-gray-600 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400"
                title={t('document.download')}
              >
                <FaDownload />
              </button>
              
              <a
                href={document.source}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-gray-600 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400"
                title={t('document.openInNewTab')}
              >
                <FaExternalLinkAlt />
              </a>
            </>
          )}
          
          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-600 hover:text-blue-600 dark:text-gray-300 dark:hover:text-blue-400"
            title={isFullscreen ? t('document.exitFullscreen') : t('document.fullscreen')}
          >
            {isFullscreen ? <FaCompress /> : <FaExpand />}
          </button>
          
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 text-gray-600 hover:text-red-600 dark:text-gray-300 dark:hover:text-red-400"
              title={t('common.close')}
            >
              &times;
            </button>
          )}
        </div>
      </div>
      
      {/* Content Tabs */}
      <Tab.Group>
        <Tab.List className="flex space-x-2 border-b border-gray-200 dark:border-gray-700">
          <Tab className={({ selected }) =>
            `py-2 px-4 text-sm leading-5 font-medium border-b-2 ${
              selected
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`
          }>
            {t('document.content')}
          </Tab>
          <Tab className={({ selected }) =>
            `py-2 px-4 text-sm leading-5 font-medium border-b-2 ${
              selected
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`
          }>
            {t('document.metadata')}
          </Tab>
          <Tab className={({ selected }) =>
            `py-2 px-4 text-sm leading-5 font-medium border-b-2 ${
              selected
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300'
            }`
          }>
            {t('document.chunks')}
          </Tab>
        </Tab.List>
        
        <Tab.Panels className="mt-4">
          {/* Content panel */}
          <Tab.Panel className="p-2">
            <div className="h-full min-h-[500px]">
              {renderViewer()}
            </div>
          </Tab.Panel>
          
          {/* Metadata panel */}
          <Tab.Panel className="p-2">
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
              <h3 className="text-md font-medium mb-2">{t('document.documentInfo')}</h3>
              <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-2">
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.id')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.id}</dd>
                </div>
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.contentType')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.content_type}</dd>
                </div>
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.language')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">{document.language || 'Unknown'}</dd>
                </div>
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.createdAt')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {new Date(document.created_at).toLocaleString()}
                  </dd>
                </div>
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.status')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {document.is_processed ? t('document.processed') : t('document.processing')}
                  </dd>
                </div>
                <div className="col-span-1">
                  <dt className="text-sm font-medium text-gray-500 dark:text-gray-400">{t('document.indexed')}</dt>
                  <dd className="mt-1 text-sm text-gray-900 dark:text-gray-100">
                    {document.is_indexed ? t('document.indexed') : t('document.notIndexed')}
                  </dd>
                </div>
              </dl>
              
              {/* Metadata section */}
              {document.metadata && Object.keys(document.metadata).length > 0 && (
                <div className="mt-6">
                  <h3 className="text-md font-medium mb-2">{t('document.customMetadata')}</h3>
                  <div className="bg-white dark:bg-gray-700 p-4 rounded-md shadow-sm overflow-auto max-h-[300px]">
                    <pre className="text-xs text-gray-800 dark:text-gray-200">
                      {JSON.stringify(document.metadata, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </Tab.Panel>
          
          {/* Chunks panel */}
          <Tab.Panel className="p-2">
            <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-md">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-md font-medium">{t('document.documentChunks')}</h3>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {t('document.totalChunks', { count: document.chunks_count || 0 })}
                </span>
              </div>
              
              <div className="border rounded-md border-gray-200 dark:border-gray-700 overflow-hidden divide-y divide-gray-200 dark:divide-gray-700">
                {/* Placeholder for chunks list, would be populated from document store */}
                <div className="p-4 text-center text-gray-500 dark:text-gray-400">
                  {t('document.loadingChunks')}
                </div>
              </div>
            </div>
          </Tab.Panel>
        </Tab.Panels>
      </Tab.Group>
    </div>
  );
};

export default DocumentViewer;