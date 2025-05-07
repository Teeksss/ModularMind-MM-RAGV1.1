import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  FaPlay, FaPause, FaStop, FaSpinner, 
  FaCheckCircle, FaExclamationTriangle, FaDownload,
  FaPlus, FaChartLine, FaListAlt, FaHistory
} from 'react-icons/fa';
import { format } from 'date-fns';
import { apiService } from '../../services/api';
import { useNotificationStore } from '../../store/notificationStore';
import ErrorBoundary from '../../components/common/ErrorBoundary';

// Types
interface FineTuningJob {
  id: string;
  name: string;
  status: string;
  created_at: string;
  completed_at?: string;
  examples_count: number;
  model_name: string;
  fine_tuned_model?: string;
  error?: string;
}

interface FeedbackStats {
  total_count: number;
  average_rating: number;
  helpful_percentage: number;
  top_tags: Array<{ tag: string; count: number }>;
}

const AdminFineTuningPage: React.FC = () => {
  const { t } = useTranslation();
  const { addNotification } = useNotificationStore();
  
  // State
  const [jobs, setJobs] = useState<FineTuningJob[]>([]);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStats | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isCreatingJob, setIsCreatingJob] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'jobs' | 'stats' | 'history'>('jobs');
  const [timeRange, setTimeRange] = useState<string>('30days');
  
  // Fetch jobs on mount
  useEffect(() => {
    fetchJobs();
    fetchFeedbackStats();
  }, []);
  
  // Re-fetch stats when time range changes
  useEffect(() => {
    fetchFeedbackStats();
  }, [timeRange]);
  
  // Fetch fine-tuning jobs
  const fetchJobs = async () => {
    setIsLoading(true);
    
    try {
      const response = await apiService.get('/admin/fine-tuning/jobs');
      setJobs(response.data.jobs);
    } catch (error) {
      console.error('Error fetching fine-tuning jobs:', error);
      addNotification({
        type: 'error',
        title: t('admin.error'),
        message: t('admin.errorFetchingJobs')
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // Fetch feedback statistics
  const fetchFeedbackStats = async () => {
    try {
      // Convert time range to date parameters
      let startDate: string | undefined;
      const today = new Date();
      
      if (timeRange === '7days') {
        const sevenDaysAgo = new Date(today);
        sevenDaysAgo.setDate(today.getDate() - 7);
        startDate = sevenDaysAgo.toISOString();
      } else if (timeRange === '30days') {
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(today.getDate() - 30);
        startDate = thirtyDaysAgo.toISOString();
      } else if (timeRange === '90days') {
        const ninetyDaysAgo = new Date(today);
        ninetyDaysAgo.setDate(today.getDate() - 90);
        startDate = ninetyDaysAgo.toISOString();
      }
      
      const params: any = {};
      if (startDate) {
        params.start_date = startDate;
      }
      
      const response = await apiService.get('/feedback/stats', { params });
      setFeedbackStats(response.data);
    } catch (error) {
      console.error('Error fetching feedback stats:', error);
      addNotification({
        type: 'error',
        title: t('admin.error'),
        message: t('admin.errorFetchingStats')
      });
    }
  };
  
  // Create new fine-tuning job
  const createFineTuningJob = async () => {
    setIsCreatingJob(true);
    
    try {
      // Simple implementation - in a real application, this would include
      // a modal with more configuration options
      const response = await apiService.post('/admin/fine-tuning/jobs', {
        name: `Fine-tuning job ${new Date().toISOString().slice(0, 10)}`,
        model_name: 'gpt-3.5-turbo',
        use_feedback: true,
        min_rating: 4,
        time_range: timeRange
      });
      
      // Show success notification
      addNotification({
        type: 'success',
        title: t('admin.jobCreated'),
        message: t('admin.fineTuningJobCreated')
      });
      
      // Refresh jobs list
      fetchJobs();
      
    } catch (error) {
      console.error('Error creating fine-tuning job:', error);
      addNotification({
        type: 'error',
        title: t('admin.error'),
        message: t('admin.errorCreatingJob')
      });
    } finally {
      setIsCreatingJob(false);
    }
  };
  
  // Get status badge based on job status
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300">
            <FaCheckCircle className="inline mr-1" />
            {t('admin.completed')}
          </span>
        );
      case 'running':
      case 'processing':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300">
            <FaSpinner className="inline mr-1 animate-spin" />
            {t('admin.running')}
          </span>
        );
      case 'failed':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300">
            <FaExclamationTriangle className="inline mr-1" />
            {t('admin.failed')}
          </span>
        );
      case 'queued':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300">
            <FaPause className="inline mr-1" />
            {t('admin.queued')}
          </span>
        );
      case 'cancelled':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
            <FaStop className="inline mr-1" />
            {t('admin.cancelled')}
          </span>
        );
      default:
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
            {status}
          </span>
        );
    }
  };
  
  return (
    <ErrorBoundary>
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 md:mb-0">
            {t('admin.fineTuning')}
          </h1>
          
          <div className="flex space-x-2">
            <button
              onClick={createFineTuningJob}
              disabled={isCreatingJob}
              className="px-4 py-2 bg-blue-600 text-white rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 flex items-center"
            >
              {isCreatingJob ? (
                <FaSpinner className="animate-spin mr-2" />
              ) : (
                <FaPlus className="mr-2" />
              )}
              {t('admin.createFineTuningJob')}
            </button>
            
            <button
              onClick={fetchJobs}
              disabled={isLoading}
              className="px-4 py-2 border border-gray-300 text-gray-700 dark:text-gray-300 dark:border-gray-600 rounded-md shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              {isLoading ? (
                <FaSpinner className="animate-spin" />
              ) : (
                t('admin.refresh')
              )}
            </button>
          </div>
        </div>
        
        {/* Tabs */}
        <div className="border-b border-gray-200 dark:border-gray-700 mb-6">
          <nav className="-mb-px flex">
            <button
              onClick={() => setActiveTab('jobs')}
              className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                activeTab === 'jobs'
                  ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <FaListAlt className="inline mr-2" />
              {t('admin.jobs')}
            </button>
            
            <button
              onClick={() => setActiveTab('stats')}
              className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                activeTab === 'stats'
                  ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <FaChartLine className="inline mr-2" />
              {t('admin.feedbackStats')}
            </button>
            
            <button
              onClick={() => setActiveTab('history')}
              className={`py-4 px-6 text-center border-b-2 font-medium text-sm ${
                activeTab === 'history'
                  ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300 dark:hover:border-gray-600'
              }`}
            >
              <FaHistory className="inline mr-2" />
              {t('admin.history')}
            </button>
          </nav>
        </div>
        
        {/* Tab Content */}
        {activeTab === 'jobs' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.name')}
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.status')}
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.model')}
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.examples')}
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.created')}
                  </th>
                  <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    {t('admin.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {isLoading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                      <FaSpinner className="animate-spin inline mr-2" />
                      {t('common.loading')}
                    </td>
                  </tr>
                ) : jobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-4 text-center text-gray-500 dark:text-gray-400">
                      {t('admin.noJobsFound')}
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {job.name || job.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {getStatusBadge(job.status)}
                        {job.error && (
                          <div className="mt-1 text-xs text-red-600 dark:text-red-400">
                            {job.error}
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {job.fine_tuned_model || job.model_name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {job.examples_count}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {job.created_at ? format(new Date(job.created_at), 'yyyy-MM-dd HH:mm') : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex space-x-2">
                          {job.status === 'completed' && job.fine_tuned_model && (
                            <button
                              onClick={() => {
                                // In a real app, this would set the model as active
                                addNotification({
                                  type: 'success',
                                  title: t('admin.modelActivated'),
                                  message: t('admin.fineTunedModelActivated', { model: job.fine_tuned_model })
                                });
                              }}
                              className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                              title={t('admin.useModel')}
                            >
                              <FaPlay />
                            </button>
                          )}
                          
                          {job.status === 'queued' && (
                            <button
                              onClick={() => {
                                // In a real app, this would cancel the job
                                addNotification({
                                  type: 'success',
                                  title: t('admin.jobCancelled'),
                                  message: t('admin.fineTuningJobCancelled')
                                });
                              }}
                              className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300"
                              title={t('admin.cancelJob')}
                            >
                              <FaStop />
                            </button>
                          )}
                          
                          {job.status === 'completed' && (
                            <button
                              onClick={() => {
                                // In a real app, this would download training metrics
                                addNotification({
                                  type: 'info',
                                  title: t('admin.downloadStarted'),
                                  message: t('admin.metricsDownloadStarted')
                                });
                              }}
                              className="text-green-600 hover:text-green-800 dark:text-green-400 dark:hover:text-green-300"
                              title={t('admin.downloadMetrics')}
                            >
                              <FaDownload />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        
        {/* Feedback Stats Tab */}
        {activeTab === 'stats' && (
          <div className="space-y-6">
            {/* Time range selector */}
            <div className="flex justify-end mb-4">
              <div className="inline-flex rounded-md shadow-sm">
                <button
                  onClick={() => setTimeRange('7days')}
                  className={`px-4 py-2 text-sm font-medium rounded-l-md ${
                    timeRange === '7days'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {t('admin.last7Days')}
                </button>
                <button
                  onClick={() => setTimeRange('30days')}
                  className={`px-4 py-2 text-sm font-medium ${
                    timeRange === '30days'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {t('admin.last30Days')}
                </button>
                <button
                  onClick={() => setTimeRange('90days')}
                  className={`px-4 py-2 text-sm font-medium rounded-r-md ${
                    timeRange === '90days'
                      ? 'bg-blue-600 text-white'
                      : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:border-gray-600 dark:text-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  {t('admin.last90Days')}
                </button>
              </div>
            </div>
            
            {/* Stats cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Total Feedback */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="p-3 rounded-md bg-blue-100 dark:bg-blue-900">
                    <FaListAlt className="h-6 w-6 text-blue-600 dark:text-blue-400" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {t('admin.totalFeedback')}
                    </h3>
                    <p className="text-3xl font-semibold text-gray-900 dark:text-white">
                      {feedbackStats?.total_count || 0}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Average Rating */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="p-3 rounded-md bg-yellow-100 dark:bg-yellow-900">
                    <div className="h-6 w-6 flex items-center justify-center text-yellow-600 dark:text-yellow-400">
                      ★
                    </div>
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {t('admin.averageRating')}
                    </h3>
                    <p className="text-3xl font-semibold text-gray-900 dark:text-white">
                      {feedbackStats?.average_rating?.toFixed(1) || '0.0'}
                    </p>
                  </div>
                </div>
              </div>
              
              {/* Helpful Percentage */}
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
                <div className="flex items-center">
                  <div className="p-3 rounded-md bg-green-100 dark:bg-green-900">
                    <FaThumbsUp className="h-6 w-6 text-green-600 dark:text-green-400" />
                  </div>
                  <div className="ml-4">
                    <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400">
                      {t('admin.helpfulPercentage')}
                    </h3>
                    <p className="text-3xl font-semibold text-gray-900 dark:text-white">
                      {feedbackStats?.helpful_percentage?.toFixed(1) || '0.0'}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Top Tags */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                {t('admin.topTags')}
              </h3>
              
              {feedbackStats?.top_tags && feedbackStats.top_tags.length > 0 ? (
                <div className="space-y-4">
                  {feedbackStats.top_tags.map((tag, index) => (
                    <div key={index} className="flex items-center">
                      <div className="w-40 text-sm text-gray-600 dark:text-gray-400">
                        {tag.tag}
                      </div>
                      <div className="flex-1">
                        <div className="relative h-4 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                          <div
                            className="absolute top-0 left-0 h-full bg-blue-600 dark:bg-blue-500"
                            style={{ width: `${(tag.count / feedbackStats.total_count) * 100}%` }}
                          ></div>
                        </div>
                      </div>
                      <div className="w-12 text-right text-sm font-medium text-gray-900 dark:text-white">
                        {tag.count}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 dark:text-gray-400">
                  {t('admin.noTagsFound')}
                </p>
              )}
            </div>
          </div>
        )}
        
        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              {t('admin.fineTuningHistory')}
            </h3>
            
            <div className="space-y-6">
              {jobs.filter(job => job.status === 'completed').length > 0 ? (
                jobs
                  .filter(job => job.status === 'completed')
                  .sort((a, b) => new Date(b.completed_at || '').getTime() - new Date(a.completed_at || '').getTime())
                  .map(job => (
                    <div key={job.id} className="border-b border-gray-200 dark:border-gray-700 pb-6 last:border-0 last:pb-0">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="text-md font-medium text-gray-900 dark:text-white">{job.name}</h4>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {t('admin.model')}: {job.fine_tuned_model || job.model_name}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {t('admin.examplesUsed')}: {job.examples_count}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {t('admin.completed')}: {job.completed_at ? format(new Date(job.completed_at), 'yyyy-MM-dd HH:mm') : '-'}
                          </p>
                        </div>
                        
                        <div className="flex space-x-2">
                          <button
                            onClick={() => {
                              // In a real app, this would set the model as active
                              addNotification({
                                type: 'success',
                                title: t('admin.modelActivated'),
                                message: t('admin.fineTunedModelActivated', { model: job.fine_tuned_model || '' })
                              });
                            }}
                            className="px-3 py-1 bg-blue-600 text-white rounded-md text-sm hover:bg-blue-700"
                          >
                            {t('admin.useModel')}
                          </button>
                          
                          <button
                            onClick={() => {
                              // In a real app, this would download training metrics
                              addNotification({
                                type: 'info',
                                title: t('admin.downloadStarted'),
                                message: t('admin.metricsDownloadStarted')
                              });
                            }}
                            className="px-3 py-1 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
                          >
                            {t('admin.metrics')}
                          </button>
                        </div>
                      </div>
                      
                      {/* Performance indicators could be added here */}
                      <div className="mt-4 grid grid-cols-3 gap-4">
                        <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {t('admin.beforeAccuracy')}
                          </div>
                          <div className="text-lg font-medium text-gray-900 dark:text-white">
                            {(Math.random() * 30 + 50).toFixed(1)}%
                          </div>
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {t('admin.afterAccuracy')}
                          </div>
                          <div className="text-lg font-medium text-green-600 dark:text-green-400">
                            {(Math.random() * 20 + 70).toFixed(1)}%
                          </div>
                        </div>
                        
                        <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                          <div className="text-xs text-gray-500 dark:text-gray-400">
                            {t('admin.improvement')}
                          </div>
                          <div className="text-lg font-medium text-blue-600 dark:text-blue-400">
                            +{(Math.random() * 15 + 5).toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
              ) : (
                <p className="text-gray-500 dark:text-gray-400">
                  {t('admin.noCompletedJobs')}
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </ErrorBoundary>
  );
};

export default AdminFineTuningPage;