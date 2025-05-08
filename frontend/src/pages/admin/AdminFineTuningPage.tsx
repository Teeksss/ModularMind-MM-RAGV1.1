import React, { useState, useEffect } from 'react';
import { FiRefreshCw, FiPlusCircle, FiXCircle, FiClock, FiCheck, FiX, FiAlertTriangle, FiBox, FiGrid, FiList } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';

import Button from '@/components/common/Button';
import LoadingScreen from '@/components/common/LoadingScreen';
import { useNotificationStore } from '@/store/notificationStore';
import { fineTuningService } from '@/services/fineTuningService';

interface FineTuningJob {
  id: string;
  name: string;
  status: 'pending' | 'preparing' | 'training' | 'validating' | 'succeeded' | 'failed' | 'cancelled';
  model_id: string;
  model_type: 'chat' | 'completion' | 'multilingual' | 'embeddings';
  progress: number;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

interface FineTunedModel {
  id: string;
  name: string;
  base_model_id: string;
  model_type: 'chat' | 'completion' | 'multilingual' | 'embeddings';
  status: string;
  created_at: string;
  usage_count: number;
  performance_metrics: Record<string, any>;
}

const AdminFineTuningPage: React.FC = () => {
  // State
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [models, setModels] = useState<FineTunedModel[]>([]);
  const [isLoadingJobs, setIsLoadingJobs] = useState(false);
  const [isLoadingModels, setIsLoadingModels] = useState(false);
  const [activeTab, setActiveTab] = useState<'jobs' | 'models'>('jobs');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('list');
  
  const { addNotification } = useNotificationStore();
  
  // İşleri yükle
  const loadJobs = async () => {
    setIsLoadingJobs(true);
    
    try {
      const response = await fineTuningService.listJobs(
        statusFilter !== 'all' ? statusFilter : undefined
      );
      
      setJobs(response.jobs);
    } catch (error) {
      console.error('Error loading jobs:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Hata',
        message: 'Fine-tuning işleri yüklenirken bir hata oluştu.',
        type: 'error',
      });
    } finally {
      setIsLoadingJobs(false);
    }
  };
  
  // Modelleri yükle
  const loadModels = async () => {
    setIsLoadingModels(true);
    
    try {
      const response = await fineTuningService.listModels();
      
      setModels(response.models);
    } catch (error) {
      console.error('Error loading models:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Hata',
        message: 'Fine-tuned modeller yüklenirken bir hata oluştu.',
        type: 'error',
      });
    } finally {
      setIsLoadingModels(false);
    }
  };
  
  // Sayfa yüklendiğinde verileri getir
  useEffect(() => {
    loadJobs();
    loadModels();
  }, [statusFilter]);
  
  // İşi iptal et
  const handleCancelJob = async (jobId: string) => {
    if (!confirm('Bu fine-tuning işini iptal etmek istediğinizden emin misiniz?')) {
      return;
    }
    
    try {
      await fineTuningService.cancelJob(jobId);
      
      addNotification({
        id: Date.now().toString(),
        title: 'Başarılı',
        message: 'Fine-tuning işi başarıyla iptal edildi.',
        type: 'success',
      });
      
      // Verileri yenile
      loadJobs();
    } catch (error) {
      console.error('Error cancelling job:', error);
      addNotification({
        id: Date.now().toString(),
        title: 'Hata',
        message: 'Fine-tuning işi iptal edilirken bir hata oluştu.',
        type: 'error',
      });
    }
  };
  
  // Durum ikonu
  const renderStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <FiClock className="text-yellow-500" size={18} />;
      case 'preparing':
        return <FiBox className="text-blue-500" size={18} />;
      case 'training':
        return <motion.div 
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          <FiRefreshCw className="text-blue-500" size={18} />
        </motion.div>;
      case 'validating':
        return <FiCheck className="text-blue-400" size={18} />;
      case 'succeeded':
        return <FiCheck className="text-green-500" size={18} />;
      case 'failed':
        return <FiX className="text-red-500" size={18} />;
      case 'cancelled':
        return <FiXCircle className="text-gray-500" size={18} />;
      default:
        return <FiAlertTriangle className="text-gray-500" size={18} />;
    }
  };
  
  // Durum metni
  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Bekliyor';
      case 'preparing':
        return 'Hazırlanıyor';
      case 'training':
        return 'Eğitiliyor';
      case 'validating':
        return 'Doğrulanıyor';
      case 'succeeded':
        return 'Tamamlandı';
      case 'failed':
        return 'Başarısız';
      case 'cancelled':
        return 'İptal Edildi';
      default:
        return status;
    }
  };
  
  // Model tipi metni
  const getModelTypeText = (type: string) => {
    switch (type) {
      case 'chat':
        return 'Sohbet';
      case 'completion':
        return 'Tamamlama';
      case 'multilingual':
        return 'Çok Dilli';
      case 'embeddings':
        return 'Gömme';
      default:
        return type;
    }
  };
  
  // İşler grid görünümü
  const renderJobsGrid = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {jobs.map((job) => (
        <div
          key={job.id}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
        >
          <div className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-medium text-gray-900 dark:text-white">{job.name}</h3>
              <div className="flex items-center">
                {renderStatusIcon(job.status)}
                <span className="ml-1 text-sm text-gray-600 dark:text-gray-400">
                  {getStatusText(job.status)}
                </span>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <p>Model Tipi: {getModelTypeText(job.model_type)}</p>
              <p>Oluşturulma: {new Date(job.created_at).toLocaleString()}</p>
              
              {job.status === 'training' && (
                <div className="mt-2">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                    <div 
                      className="bg-blue-600 h-2.5 rounded-full" 
                      style={{ width: `${job.progress}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-right mt-1">{job.progress}%</p>
                </div>
              )}
              
              {job.error_message && (
                <div className="mt-2 p-2 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 text-xs rounded">
                  {job.error_message}
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex justify-end space-x-2">
            <Button
              size="xs"
              variant="secondary"
              onClick={() => window.location.href = `/admin/fine-tuning/${job.id}`}
            >
              Detaylar
            </Button>
            
            {(job.status === 'pending' || job.status === 'preparing' || job.status === 'training') && (
              <Button
                size="xs"
                variant="danger"
                onClick={() => handleCancelJob(job.id)}
              >
                İptal Et
              </Button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
  
  // İşler liste görünümü
  const renderJobsList = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Ad
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Durum
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Model Tipi
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              İlerleme
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Oluşturulma
            </th>
            <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              İşlemler
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          {jobs.map((job) => (
            <tr key={job.id}>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900 dark:text-white">{job.name}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center">
                  {renderStatusIcon(job.status)}
                  <span className="ml-1 text-sm text-gray-600 dark:text-gray-400">
                    {getStatusText(job.status)}
                  </span>
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{getModelTypeText(job.model_type)}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                {job.status === 'training' ? (
                  <div className="w-full max-w-xs">
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2.5">
                      <div 
                        className="bg-blue-600 h-2.5 rounded-full" 
                        style={{ width: `${job.progress}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-right mt-1">{job.progress}%</p>
                  </div>
                ) : (
                  <div className="text-sm text-gray-600 dark:text-gray-400">-</div>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{new Date(job.created_at).toLocaleString()}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
                <Button
                  size="xs"
                  variant="secondary"
                  onClick={() => window.location.href = `/admin/fine-tuning/${job.id}`}
                >
                  Detaylar
                </Button>
                
                {(job.status === 'pending' || job.status === 'preparing' || job.status === 'training') && (
                  <Button
                    size="xs"
                    variant="danger"
                    onClick={() => handleCancelJob(job.id)}
                  >
                    İptal Et
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  
  // Modeller grid görünümü
  const renderModelsGrid = () => (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {models.map((model) => (
        <div
          key={model.id}
          className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden"
        >
          <div className="p-4">
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-medium text-gray-900 dark:text-white">{model.name}</h3>
              <div className="flex items-center">
                <span className="px-2 py-1 text-xs rounded-full bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                  {model.status}
                </span>
              </div>
            </div>
            
            <div className="text-sm text-gray-600 dark:text-gray-400">
              <p>Model Tipi: {getModelTypeText(model.model_type)}</p>
              <p>Temel Model: {model.base_model_id}</p>
              <p>Kullanım: {model.usage_count} kez</p>
              <p>Oluşturulma: {new Date(model.created_at).toLocaleString()}</p>
              
              {model.performance_metrics && (
                <div className="mt-2 border-t dark:border-gray-700 pt-2">
                  <p className="font-medium text-xs text-gray-700 dark:text-gray-300 mb-1">Performans Metrikleri</p>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    {Object.entries(model.performance_metrics).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-500 dark:text-gray-400">{key}:</span>
                        <span className="font-medium">{typeof value === 'number' ? value.toFixed(4) : value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
          
          <div className="bg-gray-50 dark:bg-gray-700/50 px-4 py-3 flex justify-end space-x-2">
            <Button
              size="xs"
              variant="secondary"
              onClick={() => window.location.href = `/admin/models/${model.id}`}
            >
              Detaylar
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
  
  // Modeller liste görünümü
  const renderModelsList = () => (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Ad
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Durum
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Model Tipi
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Temel Model
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Kullanım
            </th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Oluşturulma
            </th>
            <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              İşlemler
            </th>
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
          {models.map((model) => (
            <tr key={model.id}>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900 dark:text-white">{model.name}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="px-2 py-1 text-xs rounded-full bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-400">
                  {model.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{getModelTypeText(model.model_type)}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{model.base_model_id}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{model.usage_count} kez</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600 dark:text-gray-400">{new Date(model.created_at).toLocaleString()}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <Button
                  size="xs"
                  variant="secondary"
                  onClick={() => window.location.href = `/admin/models/${model.id}`}
                >
                  Detaylar
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
  
  return (
    <div className="container mx-auto py-6 px-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          Model İnce Ayarı Yönetimi
        </h1>
        
        <div className="mt-4 sm:mt-0 flex space-x-2">
          <Button
            leftIcon={<FiPlusCircle />}
            onClick={() => window.location.href = '/admin/fine-tuning/new'}
          >
            Yeni İnce Ayar İşi
          </Button>
          
          <Button
            variant="secondary"
            leftIcon={<FiRefreshCw />}
            onClick={() => {
              loadJobs();
              loadModels();
            }}
          >
            Yenile
          </Button>
        </div>
      </div>
      
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm mb-6">
        <div className="flex border-b dark:border-gray-700">
          <button
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === 'jobs'
                ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('jobs')}
          >
            İnce Ayar İşleri
          </button>
          <button
            className={`px-4 py-3 text-sm font-medium ${
              activeTab === 'models'
                ? 'text-blue-600 dark:text-blue-400 border-b-2 border-blue-500'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
            onClick={() => setActiveTab('models')}
          >
            İnce Ayarlı Modeller
          </button>
        </div>
        
        <div className="p-4">
          <div className="flex flex-col sm:flex-row justify-between mb-4">
            {activeTab === 'jobs' && (
              <div className="flex flex-wrap gap-2 mb-3 sm:mb-0">
                <button
                  className={`px-3 py-1 text-xs rounded-full ${
                    statusFilter === 'all'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  onClick={() => setStatusFilter('all')}
                >
                  Tümü
                </button>
                <button
                  className={`px-3 py-1 text-xs rounded-full ${
                    statusFilter === 'pending'
                      ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  onClick={() => setStatusFilter('pending')}
                >
                  Bekleyenler
                </button>
                <button
                  className={`px-3 py-1 text-xs rounded-full ${
                    statusFilter === 'training'
                      ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  onClick={() => setStatusFilter('training')}
                >
                  Eğitilenler
                </button>
                <button
                  className={`px-3 py-1 text-xs rounded-full ${
                    statusFilter === 'succeeded'
                      ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  onClick={() => setStatusFilter('succeeded')}
                >
                  Tamamlananlar
                </button>
                <button
                  className={`px-3 py-1 text-xs rounded-full ${
                    statusFilter === 'failed'
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                  }`}
                  onClick={() => setStatusFilter('failed')}
                >
                  Başarısız
                </button>
              </div>
            )}
            
            <div className="flex">
              <div className="border rounded-lg overflow-hidden flex">
                <button
                  className={`p-2 ${viewMode === 'grid' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                  onClick={() => setViewMode('grid')}
                  title="Grid View"
                >
                  <FiGrid size={18} />
                </button>
                <button
                  className={`p-2 ${viewMode === 'list' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-300'}`}
                  onClick={() => setViewMode('list')}
                  title="List View"
                >
                  <FiList size={18} />
                </button>
              </div>
            </div>
          </div>
          
          {activeTab === 'jobs' && (
            <>
              {isLoadingJobs ? (
                <div className="py-10">
                  <LoadingScreen text="İnce ayar işleri yükleniyor..." fullScreen={false} />
                </div>
              ) : jobs.length === 0 ? (
                <div className="text-center py-10">
                  <p className="text-gray-500 dark:text-gray-400">Hiç fine-tuning işi bulunamadı.</p>
                  <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                    Yeni bir iş başlatmak için "Yeni İnce Ayar İşi" butonuna tıklayın.
                  </p>
                </div>
              ) : (
                viewMode === 'grid' ? renderJobsGrid() : renderJobsList()
              )}
            </>
          )}
          
          {activeTab === 'models' && (
            <>
              {isLoadingModels ? (
                <div className="py-10">
                  <LoadingScreen text="İnce ayarlı modeller yükleniyor..." fullScreen={false} />
                </div>
              ) : models.length === 0 ? (
                <div className="text-center py-10">
                  <p className="text-gray-500 dark:text-gray-400">Hiç ince ayarlı model bulunamadı.</p>
                  <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">
                    Önce bir ince ayar işi başlatın ve tamamlanmasını bekleyin.
                  </p>
                </div>
              ) : (
                viewMode === 'grid' ? renderModelsGrid() : renderModelsList()
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminFineTuningPage;