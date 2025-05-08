import React, { useState, useRef } from 'react';
import { FiImage, FiUpload, FiX, FiVideo, FiMic } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';
import Button from '@/components/common/Button';
import { useNotificationStore } from '@/store/notificationStore';

interface ImageUploaderProps {
  onImageSelect: (file: File, preview: string) => void;
  onImageClear?: () => void;
  acceptedTypes?: string;
  maxSizeMB?: number;
  previewURL?: string;
  className?: string;
  label?: string;
  showPreview?: boolean;
  multiple?: boolean;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({
  onImageSelect,
  onImageClear,
  acceptedTypes = 'image/*,video/*,audio/*',
  maxSizeMB = 10,
  previewURL,
  className = '',
  label = 'Dosya Yükle',
  showPreview = true,
  multiple = false,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [preview, setPreview] = useState<string | null>(previewURL || null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addNotification } = useNotificationStore();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    // Dosya boyutu kontrolü
    if (file.size > maxSizeMB * 1024 * 1024) {
      addNotification({
        id: Date.now().toString(),
        title: 'Dosya Çok Büyük',
        message: `Dosya boyutu ${maxSizeMB}MB'den küçük olmalıdır.`,
        type: 'error',
      });
      return;
    }
    
    // Dosya tipi kontrolü
    if (!file.type.match(acceptedTypes.replace(/\*/g, '.*'))) {
      addNotification({
        id: Date.now().toString(),
        title: 'Desteklenmeyen Dosya Tipi',
        message: `Lütfen geçerli bir dosya yükleyin (${acceptedTypes}).`,
        type: 'error',
      });
      return;
    }
    
    // Dosya için önizleme oluştur
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      setPreview(result);
      onImageSelect(file, result);
    };
    
    reader.readAsDataURL(file);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      // Dosya tipine göre işlem yap
      const file = e.dataTransfer.files[0];
      
      // Dosya boyutu kontrolü
      if (file.size > maxSizeMB * 1024 * 1024) {
        addNotification({
          id: Date.now().toString(),
          title: 'Dosya Çok Büyük',
          message: `Dosya boyutu ${maxSizeMB}MB'den küçük olmalıdır.`,
          type: 'error',
        });
        return;
      }
      
      // Dosya tipi kontrolü
      if (!file.type.match(acceptedTypes.replace(/\*/g, '.*'))) {
        addNotification({
          id: Date.now().toString(),
          title: 'Desteklenmeyen Dosya Tipi',
          message: `Lütfen geçerli bir dosya yükleyin (${acceptedTypes}).`,
          type: 'error',
        });
        return;
      }
      
      // Dosya için önizleme oluştur
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        setPreview(result);
        onImageSelect(file, result);
      };
      
      reader.readAsDataURL(file);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleClear = () => {
    setPreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (onImageClear) {
      onImageClear();
    }
  };

  // Dosya türüne göre icon belirleme
  const renderIcon = () => {
    if (!preview) return <FiUpload size={24} />;
    
    if (preview.startsWith('data:image')) {
      return <FiImage size={24} />;
    } else if (preview.startsWith('data:video')) {
      return <FiVideo size={24} />;
    } else if (preview.startsWith('data:audio')) {
      return <FiMic size={24} />;
    }
    
    return <FiUpload size={24} />;
  };

  return (
    <div className={`flex flex-col ${className}`}>
      <input
        type="file"
        onChange={handleFileChange}
        accept={acceptedTypes}
        ref={fileInputRef}
        className="hidden"
        multiple={multiple}
      />
      
      <div
        className={`border-2 border-dashed rounded-lg p-4 flex flex-col items-center justify-center transition-colors ${
          dragActive 
            ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
            : 'border-gray-300 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-600'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleButtonClick}
        style={{ minHeight: '200px', cursor: 'pointer' }}
      >
        <AnimatePresence mode="wait">
          {showPreview && preview ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="w-full flex flex-col items-center"
            >
              {preview.startsWith('data:image') ? (
                <img 
                  src={preview} 
                  alt="Preview" 
                  className="max-h-40 max-w-full object-contain rounded mb-2" 
                />
              ) : preview.startsWith('data:video') ? (
                <video 
                  src={preview} 
                  controls 
                  className="max-h-40 max-w-full object-contain rounded mb-2" 
                />
              ) : preview.startsWith('data:audio') ? (
                <audio 
                  src={preview} 
                  controls 
                  className="max-w-full mb-2" 
                />
              ) : (
                <div className="flex items-center justify-center h-32 w-32 bg-gray-100 dark:bg-gray-800 rounded mb-2">
                  {renderIcon()}
                </div>
              )}
              
              <Button
                size="sm"
                variant="danger"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClear();
                }}
                className="mt-2"
              >
                <FiX size={16} className="mr-1" /> Kaldır
              </Button>
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center text-center p-4"
            >
              <div className="mb-4 p-3 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-500">
                {renderIcon()}
              </div>
              <p className="text-gray-700 dark:text-gray-300 mb-2 font-medium">{label}</p>
              <p className="text-gray-500 dark:text-gray-400 text-sm">
                Dosyayı buraya sürükleyin veya tıklayarak seçin
              </p>
              <p className="text-gray-400 dark:text-gray-500 text-xs mt-2">
                Desteklenen formatlar: {acceptedTypes.replace(/\*/g, '')}
              </p>
              <p className="text-gray-400 dark:text-gray-500 text-xs">
                Maksimum dosya boyutu: {maxSizeMB}MB
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ImageUploader;