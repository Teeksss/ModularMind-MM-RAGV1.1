"""
Embedding service for ModularMind RAG Platform.

This module provides embedding generation capabilities for the platform,
supporting various embedding models from different providers.
"""

from .service import EmbeddingService
from .config import EmbeddingModelConfig, EmbeddingCacheConfig
from .cache import EmbeddingCache
from .models.base import BaseEmbeddingModel, EmbeddingError
from .processors.text import preprocess_text
from .utils.metrics import cosine_similarity, euclidean_distance, dot_product

__all__ = [
    'EmbeddingService',
    'EmbeddingModelConfig',
    'EmbeddingCacheConfig',
    'EmbeddingCache',
    'BaseEmbeddingModel',
    'EmbeddingError',
    'preprocess_text',
    'cosine_similarity',
    'euclidean_distance',
    'dot_product'
]

# Create compatibility layer for backwards compatibility
# with the original monolithic embedding.py file
import sys
from types import ModuleType

class EmbeddingModuleCompat(ModuleType):
    """
    Compatibility module for backwards compatibility with the original embedding.py
    """
    
    def __init__(self):
        super().__init__('ModularMind.API.services.embedding')
        
        # Import all names from the new module structure
        from .service import EmbeddingService
        from .config import EmbeddingModelConfig, EmbeddingCacheConfig
        from .cache import EmbeddingCache
        from .models.base import BaseEmbeddingModel, EmbeddingError
        from .processors.text import preprocess_text
        from .utils.metrics import cosine_similarity, euclidean_distance, dot_product
        
        # Add to this module's namespace
        self.EmbeddingService = EmbeddingService
        self.EmbeddingModelConfig = EmbeddingModelConfig
        self.EmbeddingCacheConfig = EmbeddingCacheConfig
        self.EmbeddingCache = EmbeddingCache
        self.BaseEmbeddingModel = BaseEmbeddingModel
        self.EmbeddingError = EmbeddingError
        self.preprocess_text = preprocess_text
        self.cosine_similarity = cosine_similarity
        self.euclidean_distance = euclidean_distance
        self.dot_product = dot_product

# Replace this module with the compatibility module
sys.modules[__name__] = EmbeddingModuleCompat()