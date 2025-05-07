import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';

export interface AgentInfo {
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  is_initialized: boolean;
  metrics: {
    processing_time: number;
    token_usage: number;
    successful_runs: number;
    failed_runs: number;
    last_run_timestamp: string | null;
  };
}

export interface UseAgentsReturn {
  agents: AgentInfo[];
  isLoading: boolean;
  error: string | null;
  refreshAgents: () => Promise<void>;
  executeAgent: (agentName: string, inputData: any) => Promise<any>;
}

export const useAgents = (): UseAgentsReturn => {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.get<AgentInfo[]>('/agents');
      setAgents(response.data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch agents');
      console.error('Error fetching agents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const executeAgent = useCallback(async (agentName: string, inputData: any) => {
    setError(null);
    
    try {
      const response = await api.post(`/agents/${agentName}/execute`, inputData);
      return response.data;
    } catch (err) {
      const errorMessage = err.message || `Failed to execute agent: ${agentName}`;
      setError(errorMessage);
      console.error(`Error executing agent ${agentName}:`, err);
      throw new Error(errorMessage);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  return {
    agents,
    isLoading,
    error,
    refreshAgents: fetchAgents,
    executeAgent
  };
};