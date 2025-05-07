export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface Task {
  id: string;
  name: string;
  status: TaskStatus;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  progress?: number;
  metadata: Record<string, any>;
}

export interface TaskProgress {
  taskId: string;
  progress: number;
  status: TaskStatus;
  message?: string;
}