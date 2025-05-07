from typing import Dict, Any, List, Optional, Union, Type
import asyncio
import time
import logging
from enum import Enum
import importlib
import inspect
from pydantic import BaseModel

from app.agents.base import BaseAgent
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class AgentResult(BaseModel):
    """Result of an agent execution."""
    agent_name: str
    success: bool
    data: Dict[str, Any] = {}
    error: Optional[str] = None
    execution_time: float = 0.0


class AgentExecutionMode(str, Enum):
    """Execution mode for agent pipeline."""
    SERIAL = "serial"    # Execute agents one after another, passing results forward
    PARALLEL = "parallel"  # Execute all agents in parallel
    ADAPTIVE = "adaptive"  # Choose between serial and parallel based on dependencies


class Orchestrator:
    """
    Orchestrates the execution of multiple agents.
    
    Manages agent loading, execution pipeline, and result handling.
    """
    
    def __init__(self):
        """Initialize the orchestrator."""
        self.agents: Dict[str, Type[BaseAgent]] = {}
        self.agent_instances: Dict[str, BaseAgent] = {}
        self._load_agents()
    
    def _load_agents(self):
        """Dynamically load all available agents."""
        try:
            # Import all agent modules to register them
            from app.agents import metadata_extractor, summarization, semantic_expander
            from app.agents import contextual_tagger, relation_builder, synthetic_qa
            
            # Find all BaseAgent subclasses
            for module_name in [
                "metadata_extractor", "summarization", "semantic_expander",
                "contextual_tagger", "relation_builder", "synthetic_qa"
            ]:
                module = importlib.import_module(f"app.agents.{module_name}")
                
                # Find all classes in the module that are BaseAgent subclasses
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and issubclass(obj, BaseAgent) and 
                        obj != BaseAgent and name.endswith("Agent")):
                        self.agents[name] = obj
            
            # Initialize the agents for active ones
            active_agents = settings.agents.active_agents
            for agent_name in active_agents:
                if agent_name in self.agents:
                    self.agent_instances[agent_name] = self.agents[agent_name]()
                    logger.info(f"Initialized agent: {agent_name}")
                else:
                    logger.warning(f"Agent '{agent_name}' is in active list but not found")
            
            logger.info(f"Loaded {len(self.agent_instances)} active agents")
            
        except Exception as e:
            logger.error(f"Error loading agents: {str(e)}", exc_info=True)
    
    def get_agent_instance(self, agent_name: str) -> Optional[BaseAgent]:
        """Get an instance of an agent by name."""
        return self.agent_instances.get(agent_name)
    
    def get_active_agents(self) -> List[str]:
        """Get a list of active agent names."""
        return list(self.agent_instances.keys())
    
    async def execute_agent(self, agent_name: str, input_data: Dict[str, Any]) -> AgentResult:
        """
        Execute a single agent.
        
        Args:
            agent_name: Name of the agent to execute
            input_data: Input data for the agent
            
        Returns:
            AgentResult with execution results
        """
        agent = self.get_agent_instance(agent_name)
        
        if not agent:
            logger.error(f"Agent '{agent_name}' not found or not active")
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=f"Agent '{agent_name}' not found or not active"
            )
        
        try:
            start_time = time.time()
            
            # Execute the agent
            result = await agent.execute(input_data)
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_name=agent_name,
                success=True,
                data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing agent '{agent_name}': {str(e)}", exc_info=True)
            
            return AgentResult(
                agent_name=agent_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def execute_pipeline(
        self, 
        input_data: Dict[str, Any],
        pipeline: List[str],
        execution_mode: str = "serial"
    ) -> List[AgentResult]:
        """
        Execute a pipeline of agents.
        
        Args:
            input_data: Initial input data for the pipeline
            pipeline: List of agent names to execute
            execution_mode: Mode of execution (serial, parallel, adaptive)
            
        Returns:
            List of AgentResult objects
        """
        if not pipeline:
            logger.warning("Empty pipeline requested")
            return []
        
        # Convert string mode to enum
        try:
            mode = AgentExecutionMode(execution_mode.lower())
        except ValueError:
            logger.warning(f"Invalid execution mode '{execution_mode}', defaulting to SERIAL")
            mode = AgentExecutionMode.SERIAL
        
        # Filter out any invalid agents
        valid_pipeline = [
            agent_name for agent_name in pipeline 
            if agent_name in self.agent_instances
        ]
        
        if len(valid_pipeline) != len(pipeline):
            invalid_agents = set(pipeline) - set(valid_pipeline)
            logger.warning(f"Invalid agents in pipeline: {', '.join(invalid_agents)}")
        
        if not valid_pipeline:
            logger.error("No valid agents in pipeline")
            return []
        
        # Execute the pipeline
        if mode == AgentExecutionMode.PARALLEL:
            return await self._execute_parallel(input_data, valid_pipeline)
        elif mode == AgentExecutionMode.ADAPTIVE:
            return await self._execute_adaptive(input_data, valid_pipeline)
        else:  # Default to SERIAL
            return await self._execute_serial(input_data, valid_pipeline)
    
    async def _execute_serial(
        self,
        input_data: Dict[str, Any],
        pipeline: List[str]
    ) -> List[AgentResult]:
        """Execute agents in series, passing results forward."""
        results = []
        current_input = input_data.copy()
        
        for agent_name in pipeline:
            result = await self.execute_agent(agent_name, current_input)
            results.append(result)
            
            # If the agent failed, continue with the original input
            if result.success:
                # Merge result data into the input for the next agent
                current_input.update(result.data)
        
        return results
    
    async def _execute_parallel(
        self,
        input_data: Dict[str, Any],
        pipeline: List[str]
    ) -> List[AgentResult]:
        """Execute all agents in parallel with the same input."""
        # Create tasks for each agent
        tasks = [
            self.execute_agent(agent_name, input_data.copy()) 
            for agent_name in pipeline
        ]
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks)
        
        return results
    
    async def _execute_adaptive(
        self,
        input_data: Dict[str, Any],
        pipeline: List[str]
    ) -> List[AgentResult]:
        """
        Execute agents adaptively based on dependencies.
        
        In this implementation, we use a simple heuristic:
        - If less than 3 agents, run serially
        - If 3+ agents, create groups based on dependencies and run groups in series,
          but agents within a group in parallel
        """
        # For now, just implement a simple version - can be enhanced in the future
        if len(pipeline) < 3:
            return await self._execute_serial(input_data, pipeline)
        
        # Simple implementation: Split into two groups
        midpoint = len(pipeline) // 2
        group1 = pipeline[:midpoint]
        group2 = pipeline[midpoint:]
        
        # Execute group 1 in parallel
        results1 = await self._execute_parallel(input_data, group1)
        
        # Combine all successful results from group 1
        combined_input = input_data.copy()
        for result in results1:
            if result.success:
                combined_input.update(result.data)
        
        # Execute group 2 in parallel with the combined input
        results2 = await self._execute_parallel(combined_input, group2)
        
        # Combine all results
        return results1 + results2


# Create a singleton instance
_orchestrator = Orchestrator()

def get_orchestrator() -> Orchestrator:
    """Get the agent orchestrator singleton."""
    return _orchestrator