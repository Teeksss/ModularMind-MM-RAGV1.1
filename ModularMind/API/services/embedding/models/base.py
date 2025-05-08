"""
Base classes for embedding models
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class EmbeddingError(Exception):
    """Base exception for embedding errors"""
    pass

class BaseEmbeddingModel(ABC):
    """Base embedding model interface"""
    
    def __init__(
        self,
        model_id: str,
        dimensions: int,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize embedding model
        
        Args:
            model_id: Model identifier
            dimensions: Embedding dimensions
            api_key: API key if needed
            api_base_url: Base URL for API
            options: Additional options
        """
        self.model_id = model_id
        self.dimensions = dimensions
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.options = options or {}
        self._initialized = False
        
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the model
        
        Returns:
            bool: True if initialized successfully
        """
        pass
    
    @abstractmethod
    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        pass
    
    @abstractmethod
    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Optional[List[List[float]]]: List of embedding vectors or None if failed
        """
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(model_id={self.model_id}, dimensions={self.dimensions})"

class LocalEmbeddingModelBase(BaseEmbeddingModel):
    """Base class for local embedding models"""
    
    def __init__(
        self,
        model_id: str,
        dimensions: int,
        options: Optional[Dict[str, Any]] = None
    ):
        """Initialize local embedding model"""
        super().__init__(
            model_id=model_id,
            dimensions=dimensions,
            options=options
        )
        self.model = None
    
    def initialize(self) -> bool:
        """
        Load the model
        
        Returns:
            bool: True if loaded successfully
        """
        if self._initialized:
            return True
            
        try:
            self._load_model()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing model: {str(e)}")
            return False
    
    @abstractmethod
    def _load_model(self) -> None:
        """Load the model"""
        pass

class APIEmbeddingModelBase(BaseEmbeddingModel):
    """Base class for API-based embedding models"""
    
    def __init__(
        self,
        model_id: str,
        dimensions: int,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        """Initialize API embedding model"""
        super().__init__(
            model_id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            api_base_url=api_base_url,
            options=options
        )
        self.client = None
    
    def initialize(self) -> bool:
        """
        Initialize API client
        
        Returns:
            bool: True if initialized successfully
        """
        if self._initialized:
            return True
            
        try:
            self._init_client()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"Error initializing API client: {str(e)}")
            return False
    
    @abstractmethod
    def _init_client(self) -> None:
        """Initialize API client"""
        pass