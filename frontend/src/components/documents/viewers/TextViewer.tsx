import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FaSearchPlus, FaSearchMinus, FaCopy } from 'react-icons/fa';
import ReactMarkdown from 'react-markdown';
import { PrismLight as SyntaxHighlighter } from 'react-syntax-highlighter';
import { materialDark, materialLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { useTheme } from '../../../hooks/useTheme';

interface TextViewerProps {
  text: string;
  format?: 'text' | 'markdown' | 'html';
}

const TextViewer: React.FC<TextViewerProps> = ({ text, format = 'text' }) => {
  const { t } = useTranslation();
  const { isDarkMode } = useTheme();
  const [fontSize, setFontSize] = useState<number>(14);
  const [copied, setCopied] = useState<boolean>(false);
  
  // Increase font size
  const increaseFontSize = () => {
    setFontSize(prev => Math.min(prev + 2, 24));
  };
  
  // Decrease font size
  const decreaseFontSize = () => {
    setFontSize(prev => Math.max(prev - 2, 10));
  };
  
  // Copy text to clipboard
  const copyToClipboard = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    
    // Reset copied state after 2 seconds
    setTimeout(() => {
      setCopied(false);
    }, 2000);
  };
  
  // Render different text formats
  const renderContent = () => {
    switch (format) {
      case 'markdown':
        return (
          <ReactMarkdown
            className="prose dark:prose-invert max-w-none"
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={isDarkMode ? materialDark : materialLight}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              }
            }}
          >
            {text}
          </ReactMarkdown>
        );
        
      case 'html':
        return (
          <div
            className="sanitized-html"
            dangerouslySetInnerHTML={{ __html: text }}
          />
        );
        
      default:
        return (
          <pre
            className="whitespace-pre-wrap font-mono"
            style={{ fontSize: `${fontSize}px` }}
          >
            {text}
          </pre>
        );
    }
  };
  
  return (
    <div className="text-viewer flex flex-col h-full">
      {/* Controls */}
      <div className="flex items-center justify-between p-2 bg-gray-100 dark:bg-gray-800 rounded-t-md mb-2">
        <div className="text-sm text-gray-500 dark:text-gray-400">
          {format === 'markdown' ? 'Markdown' : format === 'html' ? 'HTML' : 'Text'}
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={decreaseFontSize}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={t('text.decreaseFontSize')}
          >
            <FaSearchMinus size={14} />
          </button>
          
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {fontSize}px
          </span>
          
          <button
            onClick={increaseFontSize}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={t('text.increaseFontSize')}
          >
            <FaSearchPlus size={14} />
          </button>
          
          <button
            onClick={copyToClipboard}
            className="p-2 rounded text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700"
            title={copied ? t('text.copied') : t('text.copy')}
          >
            <FaCopy size={14} />
            {copied && (
              <span className="absolute top-0 right-0 transform translate-x-1/4 -translate-y-1/4 bg-green-600 text-white text-xs px-1 py-0.5 rounded-full">
                ✓
              </span>
            )}
          </button>
        </div>
      </div>
      
      {/* Content */}
      <div 
        className="flex-1 overflow-auto p-4 bg-white dark:bg-gray-900 rounded-md border border-gray-200 dark:border-gray-700"
        style={{ fontSize: format === 'text' ? `${fontSize}px` : 'inherit' }}
      >
        {renderContent()}
      </div>
    </div>
  );
};

export default TextViewer;