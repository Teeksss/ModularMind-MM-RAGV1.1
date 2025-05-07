import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { FaUpload, FaImage, FaTrash, FaSpinner } from 'react-icons/fa';
import { apiService } from '../../services/api';

interface ImageUploaderProps {
  onEmbeddingGenerated?: (embedding: number[], modelName: string) => void;
  onSimilarityGenerated?: (similarityScores: number[]) => void;
  onError?: (error: string) => void;
  className?: string;
  multimodalModel?: string;
}

const ImageUploader: React.FC<ImageUploaderProps> = ({
  onEmbeddingGenerated,
  onSimilarityGenerated,
  onError,
  className = '',
  multimodalModel
}) => {
  const { t } = useTranslation();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [similarityText, setSimilarityText] = useState<string>('');
  const [similarityMode, setSimilarityMode] = useState<boolean>(false);

  // Handle file selection
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      
      // Validate file is an image
      if (!file.type.startsWith('image/')) {
        if (onError) onError(t('multimodal.invalidImageFile'));
        return;
      }
      
      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        if (onError) onError(t('multimodal.imageTooLarge'));
        return;
      }
      
      setSelectedImage(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  // Trigger file input click
  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Clear selected image
  const handleClearImage = () => {
    setSelectedImage(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
  };

  // Generate embedding from the image
  const handleGenerateEmbedding = async () => {
    if (!selectedImage) {
      if (onError) onError(t('multimodal.noImageSelected'));
      return;
    }

    setIsLoading(true);

    try {
      // Create form data
      const formData = new FormData();
      formData.append('file', selectedImage);
      
      if (multimodalModel) {
        formData.append('model', multimodalModel);
      }
      
      // Send request to generate embedding
      const response = await apiService.upload('/multimodal/image-upload', formData);
      
      // Call callback with embedding
      if (onEmbeddingGenerated) {
        onEmbeddingGenerated(response.data.embeddings[0], response.data.model);
      }
      
    } catch (error) {
      console.error('Error generating image embedding:', error);
      if (onError) onError(error.message || t('multimodal.embeddingError'));
    } finally {
      setIsLoading(false);
    }
  };

  // Compute similarity between image and text
  const handleComputeSimilarity = async () => {
    if (!selectedImage) {
      if (onError) onError(t('multimodal.noImageSelected'));
      return;
    }

    if (!similarityText.trim()) {
      if (onError) onError(t('multimodal.noTextEntered'));
      return;
    }

    setIsLoading(true);

    try {
      // Convert image to base64
      const base64Image = await fileToBase64(selectedImage);
      
      // Send request to compute similarity
      const response = await apiService.post('/multimodal/similarity', {
        image_data: base64Image,
        texts: similarityText.trim(),
        model: multimodalModel
      });
      
      // Call callback with similarity scores
      if (onSimilarityGenerated) {
        onSimilarityGenerated(response.data.similarities);
      }
      
    } catch (error) {
      console.error('Error computing similarity:', error);
      if (onError) onError(error.message || t('multimodal.similarityError'));
    } finally {
      setIsLoading(false);
    }
  };

  // Convert file to base64
  const fileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = error => reject(error);
    });
  };

  // Toggle between embedding and similarity modes
  const toggleSimilarityMode = () => {
    setSimilarityMode(!similarityMode);
  };

  return (
    <div className={`image-uploader ${className}`}>
      {/* Mode toggle */}
      <div className="flex justify-end mb-2">
        <button
          type="button"
          onClick={toggleSimilarityMode}
          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
        >
          {similarityMode ? t('multimodal.switchToEmbedding') : t('multimodal.switchToSimilarity')}
        </button>
      </div>

      {/* Image selection area */}
      <div className="mb-4">
        <div 
          className={`border-2 border-dashed rounded-lg p-4 text-center cursor-pointer
            ${previewUrl ? 'border-green-500' : 'border-gray-300 hover:border-blue-500'}
            dark:border-gray-600 dark:hover:border-blue-400 transition-colors
            flex flex-col items-center justify-center min-h-[200px]`}
          onClick={handleUploadClick}
        >
          {previewUrl ? (
            <div className="relative w-full h-full">
              <img
                src={previewUrl}
                alt="Preview"
                className="max-h-[200px] mx-auto object-contain"
              />
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearImage();
                }}
                className="absolute top-2 right-2 bg-red-500 text-white rounded-full p-1 hover:bg-red-600"
                title={t('multimodal.removeImage')}
              >
                <FaTrash size={12} />
              </button>
            </div>
          ) : (
            <>
              <FaImage className="text-gray-400 text-4xl mb-2" />
              <p className="text-gray-500 dark:text-gray-400 mb-2">{t('multimodal.dropImageHere')}</p>
              <button
                type="button"
                className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded inline-flex items-center"
              >
                <FaUpload className="mr-2" />
                {t('multimodal.uploadImage')}
              </button>
            </>
          )}
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileSelect}
          className="hidden"
        />
      </div>

      {/* Similarity text input (if in similarity mode) */}
      {similarityMode && (
        <div className="mb-4">
          <label htmlFor="similarity-text" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            {t('multimodal.enterTextForSimilarity')}
          </label>
          <textarea
            id="similarity-text"
            value={similarityText}
            onChange={(e) => setSimilarityText(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            rows={3}
            placeholder={t('multimodal.textPlaceholder')}
          />
        </div>
      )}

      {/* Action button */}
      <div className="flex justify-center">
        <button
          type="button"
          onClick={similarityMode ? handleComputeSimilarity : handleGenerateEmbedding}
          disabled={!selectedImage || isLoading}
          className={`font-medium py-2 px-6 rounded inline-flex items-center
            ${!selectedImage || isLoading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed dark:bg-gray-700 dark:text-gray-400'
              : 'bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-700 dark:hover:bg-blue-800'
            }`}
        >
          {isLoading ? (
            <>
              <FaSpinner className="animate-spin mr-2" />
              {t('common.loading')}
            </>
          ) : (
            <>
              {similarityMode ? t('multimodal.computeSimilarity') : t('multimodal.generateEmbedding')}
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default ImageUploader;