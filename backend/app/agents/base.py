from typing import Dict, Any, List, Optional
import logging
import time
import asyncio
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the system.
    
    Agents are responsible for specific tasks like summarization,
    enrichment, relation building, etc.
    """
    
    def __init__(self):
        """Initialize the agent."""
        self.description = "Base agent class"
        self.version = "1.0"
        self.is_initialized = False
        self._load_resources()
        self.is_initialized = True
    
    def _load_resources(self):
        """
        Load any resources needed by the agent.
        
        This should be overridden by child classes to load models,
        prompts, etc. that the agent needs.
        """
        pass
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate that the input data contains everything needed by the agent.
        
        Args:
            input_data: Dictionary of input data
            
        Returns:
            True if input is valid, False otherwise
        """
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-process the input data before main processing.
        
        This can be used to format data, extract relevant parts, etc.
        
        Args:
            input_data: Dictionary of input data
            
        Returns:
            Pre-processed input data
        """
        return input_data
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing logic for the agent.
        
        This must be implemented by all agent classes.
        
        Args:
            input_data: Dictionary of input data
            
        Returns:
            Processing result
        """
        pass
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process the result after main processing.
        
        This can be used to format output, add metadata, etc.
        
        Args:
            result: Dictionary with processing result
            
        Returns:
            Post-processed result
        """
        return result
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's processing pipeline.
        
        This handles the full flow: validation, pre-processing,
        main processing, and post-processing.
        
        Args:
            input_data: Dictionary of input data
            
        Returns:
            Final processing result
        """
        start_time = time.time()
        
        # Ensure agent is initialized
        if not self.is_initialized:
            raise RuntimeError(f"Agent {self.__class__.__name__} is not initialized")
        
        # Validate input
        is_valid = await self.validate_input(input_data)
        if not is_valid:
            raise ValueError(f"Invalid input for agent {self.__class__.__name__}")
        
        # Pre-process input
        try:
            processed_input = await self.pre_process(input_data)
        except Exception as e:
            logger.error(f"Error in pre-processing: {str(e)}", exc_info=True)
            raise
        
        # Main processing
        try:
            result = await self.process(processed_input)
        except Exception as e:
            logger.error(f"Error in main processing: {str(e)}", exc_info=True)
            raise
        
        # Post-process result
        try:
            final_result = await self.post_process(result)
        except Exception as e:
            logger.error(f"Error in post-processing: {str(e)}", exc_info=True)
            raise
        
        # Add execution metadata
        execution_time = time.time() - start_time
        agent_metadata = {
            "agent_name": self.__class__.__name__,
            "agent_version": self.version,
            "execution_time": execution_time
        }
        
        # Add metadata to result
        if final_result is None:
            final_result = {}
        
        if isinstance(final_result, dict):
            final_result["_agent_metadata"] = agent_metadata
        
        logger.info(f"Agent {self.__class__.__name__} executed in {execution_time:.2f} seconds")
        
        return final_result