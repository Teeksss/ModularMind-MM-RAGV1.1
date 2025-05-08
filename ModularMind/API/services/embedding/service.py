"""
Embedding service for generating vector embeddings from text.
"""

import os
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union

from .config import EmbeddingModelConfig
from .cache import EmbeddingCache
from .models.base import BaseEmbeddingModel
from .models import get_embedding_model
from .processors.text import preprocess_text
from .utils.batch import batch_processor

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Embedding service for generating vector embeddings from text.
    
    This service provides a unified interface for creating embeddings
    using various embedding models and providers.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Singleton pattern instance getter"""
        if cls._instance is None:
            raise ValueError("EmbeddingService has not been initialized yet")
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the embedding service
        
        Args:
            config_path: Path to the configuration file
        """
        self.models: Dict[str, EmbeddingModelConfig] = {}
        self.default_model_id: Optional[str] = None
        self._api_keys: Dict[str, str] = {}
        self._model_instances: Dict[str, BaseEmbeddingModel] = {}
        self.cache = EmbeddingCache()
        
        # Set as singleton instance
        EmbeddingService._instance = self
        
        # Load API keys from environment variables
        self._load_api_keys()
        
        # Load configuration from file if provided
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def _load_api_keys(self):
        """Load API keys from environment variables"""
        # OpenAI
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self._api_keys["openai"] = openai_api_key
        
        # Azure OpenAI
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if azure_api_key:
            self._api_keys["azure"] = azure_api_key
        
        # Cohere
        cohere_api_key = os.environ.get("COHERE_API_KEY")
        if cohere_api_key:
            self._api_keys["cohere"] = cohere_api_key
        
        # Log loaded API keys (not the actual keys, just the providers)
        logger.info(f"Loaded API keys for providers: {', '.join(self._api_keys.keys())}")
    
    def load_config(self, config_path: str) -> bool:
        """
        Load configuration from file
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            bool: True if loaded successfully
        """
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Load models
            if "models" in config_data and isinstance(config_data["models"], list):
                for model_data in config_data["models"]:
                    model_config = EmbeddingModelConfig.from_dict(model_data)
                    self.models[model_config.id] = model_config
            
            # Set default model
            if "default_model" in config_data:
                self.default_model_id = config_data["default_model"]
            elif self.models:
                # Use first model as default if not specified
                self.default_model_id = next(iter(self.models.keys()))
            
            logger.info(f"Loaded {len(self.models)} embedding models: {', '.join(self.models.keys())}")
            if self.default_model_id:
                logger.info(f"Default embedding model: {self.default_model_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error loading embedding configuration: {str(e)}")
            return False
    
    def save_config(self, config_path: str) -> bool:
        """
        Save configuration to file
        
        Args:
            config_path: Path to save configuration
            
        Returns:
            bool: True if saved successfully
        """
        try:
            config_data = {
                "models": [model.to_dict() for model in self.models.values()],
                "default_model": self.default_model_id
            }
            
            with open(config_path, "w") as f:
                json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Error saving embedding configuration: {str(e)}")
            return False
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for provider
        
        Args:
            provider: Provider name
            
        Returns:
            Optional[str]: API key or None if not found
        """
        return self._api_keys.get(provider)
    
    def get_model_config(self, model_id: Optional[str] = None) -> Optional[EmbeddingModelConfig]:
        """
        Get model configuration
        
        Args:
            model_id: Model ID (or None for default model)
            
        Returns:
            Optional[EmbeddingModelConfig]: Model configuration or None if not found
        """
        if model_id is None:
            model_id = self.default_model_id
        
        if model_id is None:
            logger.error("No default embedding model set")
            return None
        
        return self.models.get(model_id)
    
    def get_models(self) -> List[Dict[str, Any]]:
        """
        Get list of available models
        
        Returns:
            List[Dict[str, Any]]: List of model configurations as dictionaries
        """
        return [model.to_dict() for model in self.models.values()]
    
    def add_model(self, model_config: EmbeddingModelConfig) -> bool:
        """
        Add or update model configuration
        
        Args:
            model_config: Model configuration
            
        Returns:
            bool: True if added/updated successfully
        """
        try:
            self.models[model_config.id] = model_config
            return True
        except Exception as e:
            logger.error(f"Error adding model: {str(e)}")
            return False
    
    def remove_model(self, model_id: str) -> bool:
        """
        Remove model configuration
        
        Args:
            model_id: Model ID to remove
            
        Returns:
            bool: True if removed successfully
        """
        try:
            if model_id in self.models:
                # If removing default model, update default
                if model_id == self.default_model_id:
                    if len(self.models) > 1:
                        remaining_models = [m for m in self.models.keys() if m != model_id]
                        self.default_model_id = remaining_models[0]
                    else:
                        self.default_model_id = None
                
                # Remove model
                del self.models[model_id]
                
                # Remove model instance if loaded
                if model_id in self._model_instances:
                    del self._model_instances[model_id]
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing model: {str(e)}")
            return False
    
    def set_default_model(self, model_id: str) -> bool:
        """
        Set default model
        
        Args:
            model_id: Model ID to set as default
            
        Returns:
            bool: True if set successfully
        """
        if model_id in self.models:
            self.default_model_id = model_id
            return True
        return False
    
    def _get_model_instance(self, model_id: Optional[str] = None) -> Optional[BaseEmbeddingModel]:
        """
        Get model instance
        
        Args:
            model_id: Model ID (or None for default model)
            
        Returns:
            Optional[BaseEmbeddingModel]: Model instance or None if not found
        """
        # Get model configuration
        model_config = self.get_model_config(model_id)
        if not model_config:
            return None
        
        # Get model ID
        model_id = model_config.id
        
        # Create instance if not already created
        if model_id not in self._model_instances:
            # Get API key if needed
            api_key = None
            if model_config.api_key_env:
                api_key = self.get_api_key(model_config.provider)
            
            # Create model instance
            model_instance = get_embedding_model(
                model_config.provider,
                model_config.model_id,
                api_key=api_key,
                api_base_url=model_config.api_base_url,
                dimensions=model_config.dimensions,
                options=model_config.options
            )
            
            if model_instance:
                self._model_instances[model_id] = model_instance
            else:
                logger.error(f"Failed to create model instance for {model_id}")
                return None
        
        return self._model_instances.get(model_id)
    
    def create_embedding(self, text: str, model_id: Optional[str] = None) -> Optional[List[float]]:
        """
        Create embedding for text
        
        Args:
            text: Text to embed
            model_id: Model ID to use (or None for default model)
            
        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        # Get model configuration
        model_config = self.get_model_config(model_id)
        if not model_config:
            logger.error(f"Embedding model not found: {model_id}")
            return None
        
        # Check cache
        cache_key = f"{model_config.id}:{hash(text)}"
        cached_embedding = self.cache.get(cache_key)
        if cached_embedding is not None:
            return cached_embedding
        
        # Get model instance
        model = self._get_model_instance(model_config.id)
        if not model:
            return None
        
        try:
            # Preprocess text
            processed_text = preprocess_text(text)
            
            # Create embedding
            embedding = model.embed(processed_text)
            
            # Cache embedding
            if embedding is not None:
                self.cache.set(cache_key, embedding)
            
            return embedding
        except Exception as e:
            logger.error(f"Error creating embedding with {model_config.id}: {str(e)}")
            return None
    
    def create_batch_embeddings(self, texts: List[str], model_id: Optional[str] = None) -> Optional[List[List[float]]]:
        """
        Create embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            model_id: Model ID to use (or None for default model)
            
        Returns:
            Optional[List[List[float]]]: List of embedding vectors or None if failed
        """
        # Get model configuration
        model_config = self.get_model_config(model_id)
        if not model_config:
            logger.error(f"Embedding model not found: {model_id}")
            return None
        
        # Get model instance
        model = self._get_model_instance(model_config.id)
        if not model:
            return None
        
        try:
            # Check cache for each text
            embeddings = []
            texts_to_embed = []
            indices_to_embed = []
            
            for i, text in enumerate(texts):
                cache_key = f"{model_config.id}:{hash(text)}"
                cached_embedding = self.cache.get(cache_key)
                
                if cached_embedding is not None:
                    embeddings.append(cached_embedding)
                else:
                    # Add to list of texts to embed
                    texts_to_embed.append(preprocess_text(text))
                    indices_to_embed.append(i)
                    # Add placeholder
                    embeddings.append(None)
            
            # If there are texts to embed
            if texts_to_embed:
                # Create embeddings in batch
                batch_embeddings = model.embed_batch(texts_to_embed)
                
                if batch_embeddings is None:
                    return None
                
                # Update embeddings and cache
                for j, embedding in enumerate(batch_embeddings):
                    i = indices_to_embed[j]
                    text = texts[i]
                    cache_key = f"{model_config.id}:{hash(text)}"
                    
                    embeddings[i] = embedding
                    self.cache.set(cache_key, embedding)
            
            return embeddings
        except Exception as e:
            logger.error(f"Error creating batch embeddings with {model_config.id}: {str(e)}")
            return None
    
    def calculate_similarity(self, text1: str, text2: str, model_id: Optional[str] = None) -> Optional[float]:
        """
        Calculate similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            model_id: Model ID to use (or None for default model)
            
        Returns:
            Optional[float]: Similarity score (0-1) or None if failed
        """
        # Create embeddings
        embedding1 = self.create_embedding(text1, model_id)
        embedding2 = self.create_embedding(text2, model_id)
        
        if embedding1 is None or embedding2 is None:
            return None
        
        # Calculate cosine similarity
        return self._cosine_similarity(embedding1, embedding2)
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            float: Cosine similarity (0-1)
        """
        from .utils.metrics import cosine_similarity
        return cosine_similarity(vec1, vec2)