"""
Embedding model implementations
"""

import logging
from typing import Dict, List, Any, Optional, Union

from .base import BaseEmbeddingModel, EmbeddingError
from .openai import OpenAIEmbeddingModel
from .azure import AzureOpenAIEmbeddingModel
from .huggingface import HuggingFaceEmbeddingModel
from .cohere import CohereEmbeddingModel
from .local import SentenceTransformerModel

logger = logging.getLogger(__name__)

def get_embedding_model(
    provider: str,
    model_id: str,
    api_key: Optional[str] = None,
    api_base_url: Optional[str] = None,
    dimensions: int = 0,
    options: Optional[Dict[str, Any]] = None
) -> Optional[BaseEmbeddingModel]:
    """
    Factory function to create embedding model instances
    
    Args:
        provider: Model provider (openai, azure, huggingface, cohere, local)
        model_id: Model identifier
        api_key: API key if needed
        api_base_url: Base URL for API if needed
        dimensions: Embedding dimensions
        options: Additional options
        
    Returns:
        Optional[BaseEmbeddingModel]: Model instance or None if provider not supported
    """
    options = options or {}
    
    # Create appropriate model based on provider
    if provider == "openai":
        return OpenAIEmbeddingModel(
            model_id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            api_base_url=api_base_url,
            options=options
        )
    elif provider == "azure":
        return AzureOpenAIEmbeddingModel(
            model_id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            api_base_url=api_base_url,
            options=options
        )
    elif provider == "huggingface":
        return HuggingFaceEmbeddingModel(
            model_id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            options=options
        )
    elif provider == "cohere":
        return CohereEmbeddingModel(
            model_id=model_id,
            dimensions=dimensions,
            api_key=api_key,
            api_base_url=api_base_url,
            options=options
        )
    elif provider == "local":
        return SentenceTransformerModel(
            model_id=model_id,
            dimensions=dimensions,
            options=options
        )
    else:
        logger.error(f"Unsupported embedding provider: {provider}")
        return None

__all__ = [
    'BaseEmbeddingModel',
    'EmbeddingError',
    'OpenAIEmbeddingModel',
    'AzureOpenAIEmbeddingModel',
    'HuggingFaceEmbeddingModel',
    'CohereEmbeddingModel',
    'SentenceTransformerModel',
    'get_embedding_model'
]