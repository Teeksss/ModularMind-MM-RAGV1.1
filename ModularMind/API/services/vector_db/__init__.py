"""
Vector database index managers and utilities.

This module provides a collection of index managers for various vector database
backends, along with utilities for vector operations and similarity search.
"""

from .base import BaseIndexManager
from .config import (
    VectorDBType,
    DistanceMetric,
    VectorIndexConfig,
    HNSWConfig,
    FaissConfig,
    ExternalVectorDBConfig
)
from .utils import normalize_vector, convert_distance_to_similarity
from .metrics import compute_similarity

# Import index managers
from .managers.hnsw import HNSWIndexManager
from .managers.faiss import FaissIndexManager
from .managers.qdrant import QdrantIndexManager
from .managers.pinecone import PineconeIndexManager
from .managers.weaviate import WeaviateIndexManager
from .managers.milvus import MilvusIndexManager
from .managers.elasticsearch import ElasticsearchIndexManager

# Import operations
from .operations.search import hybrid_search, multi_vector_search
from .operations.update import batch_update, incremental_update
from .operations.maintenance import optimize_index, reindex

# Registry of index managers
INDEX_MANAGER_REGISTRY = {
    VectorDBType.HNSW: HNSWIndexManager,
    VectorDBType.FAISS: FaissIndexManager,
    VectorDBType.QDRANT: QdrantIndexManager,
    VectorDBType.PINECONE: PineconeIndexManager,
    VectorDBType.WEAVIATE: WeaviateIndexManager,
    VectorDBType.MILVUS: MilvusIndexManager,
    VectorDBType.ELASTICSEARCH: ElasticsearchIndexManager,
}

def get_index_manager(db_type: Union[str, VectorDBType], config: Dict[str, Any]) -> BaseIndexManager:
    """
    Factory function for creating index managers
    
    Args:
        db_type: Vector database type
        config: Configuration dictionary
        
    Returns:
        BaseIndexManager: Instance of requested index manager
        
    Raises:
        ValueError: If db_type is not supported
    """
    if isinstance(db_type, str):
        db_type = VectorDBType(db_type)
        
    if db_type not in INDEX_MANAGER_REGISTRY:
        raise ValueError(f"Unsupported vector database type: {db_type}")
    
    manager_class = INDEX_MANAGER_REGISTRY[db_type]
    return manager_class(config)

__all__ = [
    'BaseIndexManager',
    'VectorDBType',
    'DistanceMetric',
    'VectorIndexConfig',
    'HNSWConfig',
    'FaissConfig',
    'ExternalVectorDBConfig',
    'normalize_vector',
    'convert_distance_to_similarity',
    'compute_similarity',
    'get_index_manager',
    'INDEX_MANAGER_REGISTRY',
    # Index managers
    'HNSWIndexManager',
    'FaissIndexManager',
    'QdrantIndexManager',
    'PineconeIndexManager',
    'WeaviateIndexManager',
    'MilvusIndexManager',
    'ElasticsearchIndexManager',
    # Operations
    'hybrid_search',
    'multi_vector_search',
    'batch_update',
    'incremental_update',
    'optimize_index',
    'reindex'
]