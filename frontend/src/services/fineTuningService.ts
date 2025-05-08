import api from './api';

export interface FineTuningJob {
  id: string;
  name: string;
  description?: string;
  model_id: string;
  model_type: 'chat' | 'completion' | 'multilingual' | 'embeddings';
  status: 'pending' | 'preparing' | 'training' | 'validating' | 'succeeded' | 'failed' | 'cancelled';
  training_file_ids: string[];
  validation_file_id?: string;
  hyperparameters: Record<string, any>;
  result_model_id?: string;
  created_at: string;
  updated_at: string;
  started_at?: string;
  finished_at?: string;
  validation_result?: Record<string, any>;
  error_message?: string;
  progress: number;
  tags: string[];
}

export interface FineTunedModel {
  id: string;
  user_id: string;
  job_id: string;
  name: string;
  description?: string;
  base_model_id: string;
  model_type: 'chat' | 'completion' | 'multilingual' | 'embeddings';
  status: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
  performance_metrics: Record<string, any>;
  tags: string[];
  is_public: boolean;
  usage_count: number;
  last_used_at?: string;
}

export interface CreateJobRequest {
  name: string;
  model_id: string;
  model_type: 'chat' | 'completion' | 'multilingual' | 'embeddings';
  training_file_ids: string[];
  validation_file_id?: string;
  description?: string;
  hyperparameters?: Record<string, any>;
  tags?: string[];
}

class FineTuningService {
  /**
   * Yeni bir fine-tuning işi oluşturur.
   */
  async createJob(data: CreateJobRequest): Promise<{ job_id: string; message: string }> {
    const response = await api.post('/api/v1/fine-tuning/jobs', data);
    return response.data;
  }
  
  /**
   * Belirli bir fine-tuning işinin detaylarını getirir.
   */
  async getJob(jobId: string): Promise<FineTuningJob> {
    const response = await api.get(`/api/v1/fine-tuning/jobs/${jobId}`);
    return response.data;
  }
  
  /**
   * Fine-tuning işlerini listeler.
   */
  async listJobs(status?: string): Promise<{ jobs: FineTuningJob[]; total_count: number; page: number; page_size: number }> {
    const params = status ? { status } : {};
    const response = await api.get('/api/v1/fine-tuning/jobs', { params });
    return response.data;
  }
  
  /**
   * Fine-tuning işini iptal eder.
   */
  async cancelJob(jobId: string): Promise<{ message: string }> {
    const response = await api.post(`/api/v1/fine-tuning/jobs/${jobId}/cancel`);
    return response.data;
  }
  
  /**
   * Fine-tuned modelleri listeler.
   */
  async listModels(): Promise<{ models: FineTunedModel[]; total_count: number; page: number; page_size: number }> {
    const response = await api.get('/api/v1/fine-tuning/models');
    return response.data;
  }
  
  /**
   * Belirli bir fine-tuned modelin detaylarını getirir.
   */
  async getModel(modelId: string): Promise<FineTunedModel> {
    const response = await api.get(`/api/v1/fine-tuning/models/${modelId}`);
    return response.data;
  }
  
  /**
   * Admin: Tüm fine-tuning işlerini listeler.
   */
  async adminListAllJobs(params?: { user_id?: string; status?: string }): Promise<{ jobs: FineTuningJob[]; total_count: number; page: number; page_size: number }> {
    const response = await api.get('/api/v1/fine-tuning/admin/all-jobs', { params });
    return response.data;
  }
}

export const fineTuningService = new FineTuningService();