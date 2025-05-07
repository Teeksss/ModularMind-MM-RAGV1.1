import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Task, TaskStatus } from '../types/tasks';

/**
 * Hook for tracking task progress
 */
export const useTaskProgress = (taskId: string | null, pollingInterval = 2000) => {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    
    let isMounted = true;
    let intervalId: NodeJS.Timeout;
    
    const fetchTaskStatus = async () => {
      try {
        setLoading(true);
        const response = await apiService.get(`/tasks/${taskId}`);
        
        if (isMounted) {
          setTask(response.data);
          setError(null);
          
          // Stop polling if task is completed, failed, or cancelled
          if (['completed', 'failed', 'cancelled'].includes(response.data.status)) {
            clearInterval(intervalId);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.translatedMessage || 'Failed to fetch task status');
          clearInterval(intervalId);
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    // Fetch immediately
    fetchTaskStatus();
    
    // Set up polling
    intervalId = setInterval(fetchTaskStatus, pollingInterval);
    
    // Cleanup
    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [taskId, pollingInterval]);
  
  // Cancel task function
  const cancelTask = async () => {
    if (!taskId) return;
    
    try {
      setLoading(true);
      await apiService.post(`/tasks/${taskId}/cancel`);
      
      // Refresh task data
      const response = await apiService.get(`/tasks/${taskId}`);
      setTask(response.data);
    } catch (err: any) {
      setError(err.translatedMessage || 'Failed to cancel task');
    } finally {
      setLoading(false);
    }
  };
  
  return { task, loading, error, cancelTask };
};