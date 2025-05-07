import React, { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { useTranslation } from 'react-i18next';
import { FaArrowLeft, FaArrowRight, FaSearch, FaSearchMinus, FaSearchPlus } from 'react-icons/fa';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

interface PDFViewerProps {
  documentUrl: string;
}

const PDFViewer: React.FC<PDFViewerProps> = ({ documentUrl }) => {
  const { t } = useTranslation();
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [error, setError] = useState<string | null>(null);
  
  // Handle document load success
  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPageNumber(1);
    setError(null);
  };
  
  // Handle document load error
  const onDocumentLoadError = (error: Error) => {
    console.error('Error loading PDF:', error);
    setError(error.message || 'Failed to load PDF document');
  };
  
  // Navigate to previous page
  const goToPrevPage = () => {
    if (pageNumber > 1) {
      setPageNumber(pageNumber - 1);
    }
  };
  
  // Navigate to next page
  const goToNextPage = () => {
    if (pageNumber < (numPages || 1)) {
      setPageNumber(pageNumber + 1);
    }
  };
  
  // Zoom in
  const zoomIn = () => {
    setScale(prevScale => Math.min(prevScale + 0.2, 3.0));
  };
  
  // Zoom out
  const zoomOut = () => {
    setScale(prevScale => Math.max(prevScale - 0.2, 0.5));
  };
  
  // Reset zoom
  const resetZoom = () => {
    setScale(1.0);
  };
  
  return (
    <div className="pdf-viewer flex flex-col h-full">
      {/* PDF controls */}
      <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-800 rounded-t-md mb-2">
        <div className="flex items-center space-x-2">
          <button
            onClick={goToPrevPage}
            disabled={pageNumber <= 1}
            className={`p-2 rounded ${
              pageNumber <= 1
                ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
            title={t('pdf.previousPage')}
          >
            <FaArrowLeft />
          </button>
          
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {t('pdf.pageCounter', { current: pageNumber, total: numPages || '?' })}
          </span>
          
          <button
            onClick={goToNextPage}
            disabled={!numPages || pageNumber >= numPages}
            className={`p-2 rounded ${
              !numPages || pageNumber >= numPages
                ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
            }`}
            title={t('pdf.nextPage')}
          >
            <FaArrowRight />
          </button>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={zoomOut}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={t('pdf.zoomOut')}
          >
            <FaSearchMinus />
          </button>
          
          <span 
            className="text-sm text-gray-700 dark:text-gray-300 cursor-pointer" 
            onClick={resetZoom} 
            title={t('pdf.resetZoom')}
          >
            {Math.round(scale * 100)}%
          </span>
          
          <button
            onClick={zoomIn}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={t('pdf.zoomIn')}
          >
            <FaSearchPlus />
          </button>
        </div>
      </div>
      
      {/* PDF document */}
      <div className="flex-1 overflow-auto flex justify-center bg-gray-200 dark:bg-gray-800 rounded-md">
        {error ? (
          <div className="flex items-center justify-center h-full text-red-500 dark:text-red-400 p-4 text-center">
            <div>
              <p className="font-medium mb-2">{t('pdf.loadError')}</p>
              <p className="text-sm">{error}</p>
            </div>
          </div>
        ) : (
          <Document
            file={documentUrl}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
            loading={
              <div className="flex items-center justify-center h-full">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
              </div>
            }
            error={
              <div className="flex items-center justify-center h-full text-red-500 dark:text-red-400 p-4 text-center">
                <div>
                  <p className="font-medium mb-2">{t('pdf.loadError')}</p>
                  <p className="text-sm">{t('pdf.checkPermissions')}</p>
                </div>
              </div>
            }
          >
            <Page
              pageNumber={pageNumber}
              scale={scale}
              renderTextLayer={true}
              renderAnnotationLayer={true}
              className="shadow-md"
            />
          </Document>
        )}
      </div>
    </div>
  );
};

export default PDFViewer;