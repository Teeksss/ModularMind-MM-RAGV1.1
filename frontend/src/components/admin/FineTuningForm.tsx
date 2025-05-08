import React, { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { FiSave, FiUpload, FiInfo } from 'react-icons/fi';

import Button from '@/components/common/Button';
import { useNotificationStore } from '@/store/notificationStore';
import { fineTuningService, CreateJobRequest } from '@/services/fineTuningService';

interface Model {
  id: string;
  name: string;
  type: string;
}

interface FineTuningFormProps {
  onSubmitSuccess?: (jobId: string) => void;
}

const FineTuningForm: React.FC<FineTuningFormProps> = ({ onSubmitSuccess }) => {
  // Form durumu
  const { register, handleSubmit, control, formState: { errors, isSubmitting } } = useForm<CreateJobRequest>();
  
  // Diğer durumlar
  const [availableModels, setAvailableModels] = useState<Model[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [validationFile, setValidationFile] = useState<File | null>(null);
  
  const { addNotification } = useNotificationStore();
  
  // Kullanılabilir modelleri yükle
  useEffect(() => {
    // Normalde API'den alınır, burada örnek veriler
    setAvailableModels([
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', type: 'chat' },
      { id: 'gpt-4', name: 'GPT-4', type: 'chat' },
      { id: 'text-davinci-003', name: 'Text Davinci 003', type: 'completion' },
      { id: 'text-embedding-3-large', name: 'Text Embedding Large', type: 'embeddings' },
      { id: 'text-multilingual-1', name: 'Multilingual Model', type: 'multilingual' },
    ]);
  }, []);
  
  // Form gönderme
  const onSubmit = async (data: CreateJobRequest) => {
    try {
      // Dosya yükleme işlemi (normalde ayrı bir endpoint'e yüklenir)
      // Burada simüle ediyoruz
      const fileIds = Array.from({ length: selectedFiles.length }, () => 
        Math.random().toString(36).substring(2, 15)
      );
      
      // Doğrulama dosyası varsa
      let validationFileId = null;
      if (validationFile) {
        validationFileId = Math.random().toString(36).substring(2, 15);
      }
      
      // Fine-tuning işi oluştur
      const response = await fineTuningService.createJob({
        ...data,
        training_file_ids: fileIds,
        validation_file_id: validationFileId || undefined,
      });
      
      addNotification({
        id: Date.now().toString(),
        title: 'Başarılı',
        message: 'Fine-tuning işi başarıyla oluşturuldu.',
        type: 'success',
      });
      
      // Callback fonksiyonunu çağır
      if (onSubmitSuccess) {
        onSubmitSuccess(response.job_id);
      }
      
    } catch (error) {
      console.error('Error creating fine-tuning job:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Hata',
        message: 'Fine-tuning işi oluşturulurken bir hata oluştu.',
        type: 'error',
      });
    }
  };
  
  // Eğitim dosyalarını seç
  const handleTrainingFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };
  
  // Doğrulama dosyasını seç
  const handleValidationFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setValidationFile(e.target.files[0]);
    } else {
      setValidationFile(null);
    }
  };
  
  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Temel Bilgiler</h2>
        
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              İş Adı <span className="text-red-500">*</span>
            </label>
            <input
              id="name"
              type="text"
              {...register('name', { required: 'İş adı gereklidir' })}
              className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="İş adı"
            />
            {errors.name && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.name.message}</p>
            )}
          </div>
          
          <div>
            <label htmlFor="model_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Temel Model <span className="text-red-500">*</span>
            </label>
            <select
              id="model_id"
              {...register('model_id', { required: 'Temel model gereklidir' })}
              className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">Model Seçin</option>
              {availableModels.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name}
                </option>
              ))}
            </select>
            {errors.model_id && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.model_id.message}</p>
            )}
          </div>
          
          <div>
            <label htmlFor="model_type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Model Tipi <span className="text-red-500">*</span>
            </label>
            <select
              id="model_type"
              {...register('model_type', { required: 'Model tipi gereklidir' })}
              className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
            >
              <option value="">Tip Seçin</option>
              <option value="chat">Sohbet</option>
              <option value="completion">Tamamlama</option>
              <option value="multilingual">Çok Dilli</option>
              <option value="embeddings">Gömme</option>
            </select>
            {errors.model_type && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">{errors.model_type.message}</p>
            )}
          </div>
          
          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Açıklama
            </label>
            <textarea
              id="description"
              {...register('description')}
              rows={3}
              className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white resize-none"
              placeholder="İş açıklaması"
            />
          </div>
        </div>
      </div>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Eğitim Verileri</h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="training_files" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Eğitim Dosyaları <span className="text-red-500">*</span>
            </label>
            <div className="flex items-center space-x-3">
              <Button
                type="button"
                variant="secondary"
                leftIcon={<FiUpload />}
                onClick={() => document.getElementById('training_files')?.click()}
              >
                Dosya Seç
              </Button>
              <input
                id="training_files"
                type="file"
                multiple
                onChange={handleTrainingFilesChange}
                className="hidden"
                accept=".jsonl,.csv,.txt"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {selectedFiles.length > 0 
                  ? `${selectedFiles.length} dosya seçildi` 
                  : 'Dosya seçilmedi'}
              </span>
            </div>
            {selectedFiles.length > 0 && (
              <ul className="mt-2 text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {selectedFiles.map((file, index) => (
                  <li key={index}>{file.name} ({(file.size / 1024).toFixed(2)} KB)</li>
                ))}
              </ul>
            )}
            {selectedFiles.length === 0 && (
              <p className="mt-1 text-sm text-red-600 dark:text-red-400">En az bir eğitim dosyası gereklidir</p>
            )}
          </div>
          
          <div>
            <label htmlFor="validation_file" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Doğrulama Dosyası (İsteğe Bağlı)
            </label>
            <div className="flex items-center space-x-3">
              <Button
                type="button"
                variant="secondary"
                leftIcon={<FiUpload />}
                onClick={() => document.getElementById('validation_file')?.click()}
              >
                Dosya Seç
              </Button>
              <input
                id="validation_file"
                type="file"
                onChange={handleValidationFileChange}
                className="hidden"
                accept=".jsonl,.csv,.txt"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {validationFile 
                  ? `${validationFile.name} (${(validationFile.size / 1024).toFixed(2)} KB)` 
                  : 'Dosya seçilmedi'}
              </span>
            </div>
          </div>
          
          <div className="bg-blue-50 dark:bg-blue-900/20 p-3 rounded-md flex">
            <FiInfo className="text-blue-500 mt-1 flex-shrink-0 mr-2" />
            <div className="text-sm text-blue-800 dark:text-blue-300">
              <p>Desteklenen dosya formatları:</p>
              <ul className="list-disc list-inside ml-2 mt-1">
                <li>JSONL (.jsonl): Her satır geçerli bir JSON nesnesi olmalıdır</li>
                <li>CSV (.csv): Başlık satırı içermelidir</li>
                <li>Metin (.txt): Her satır bir örnek olarak kabul edilir</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Gelişmiş Ayarlar</h2>
        
        <div className="space-y-4">
          <div>
            <label htmlFor="tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Etiketler (virgülle ayırın)
            </label>
            <input
              id="tags"
              type="text"
              {...register('tags')}
              className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              placeholder="örnek, test, proje"
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Bu etiketler işi daha sonra filtrelemenize yardımcı olur.
            </p>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Hiperparametreler
            </label>
            
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="learning_rate" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Öğrenme Oranı
                </label>
                <Controller
                  name="hyperparameters.learning_rate"
                  control={control}
                  defaultValue={0.001}
                  render={({ field }) => (
                    <input
                      id="learning_rate"
                      type="number"
                      step="0.0001"
                      min="0.0001"
                      max="0.1"
                      className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      {...field}
                    />
                  )}
                />
              </div>
              
              <div>
                <label htmlFor="batch_size" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Batch Boyutu
                </label>
                <Controller
                  name="hyperparameters.batch_size"
                  control={control}
                  defaultValue={4}
                  render={({ field }) => (
                    <input
                      id="batch_size"
                      type="number"
                      step="1"
                      min="1"
                      max="64"
                      className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      {...field}
                    />
                  )}
                />
              </div>
              
              <div>
                <label htmlFor="num_epochs" className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                  Epoch Sayısı
                </label>
                <Controller
                  name="hyperparameters.num_epochs"
                  control={control}
                  defaultValue={3}
                  render={({ field }) => (
                    <input
                      id="num_epochs"
                      type="number"
                      step="1"
                      min="1"
                      max="10"
                      className="w-full px-3 py-2 border rounded-md focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                      {...field}
                    />
                  )}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="flex justify-end space-x-3">
        <Button
          type="button"
          variant="secondary"
          onClick={() => window.history.back()}
        >
          İptal
        </Button>
        <Button
          type="submit"
          leftIcon={<FiSave />}
          loading={isSubmitting}
          disabled={isSubmitting || selectedFiles.length === 0}
        >
          {isSubmitting ? 'Kaydediliyor...' : 'Fine-Tuning İşi Başlat'}
        </Button>
      </div>
    </form>
  );
};

export default FineTuningForm;