"""
Vector database index configuration classes
"""
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

class VectorDBType(str, Enum):
    """Vector database types supported by the platform"""
    HNSW = "hnsw"
    FAISS = "faiss"
    QDRANT = "qdrant"
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    MILVUS = "milvus"
    ELASTICSEARCH = "elasticsearch"

class DistanceMetric(str, Enum):
    """Distance metrics for vector similarity search"""
    COSINE = "cosine"      # Cosine similarity (1 - cos angle)
    EUCLIDEAN = "euclidean"  # L2 distance
    DOT = "dot"           # Dot product (inner product)
    MANHATTAN = "manhattan"  # L1 distance

@dataclass
class VectorIndexConfig:
    """Base configuration for vector indices"""
    dimensions: int
    metric: DistanceMetric = DistanceMetric.COSINE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "dimensions": self.dimensions,
            "metric": self.metric.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorIndexConfig':
        """Create from dictionary"""
        if "metric" in data and isinstance(data["metric"], str):
            data["metric"] = DistanceMetric(data["metric"])
        return cls(**data)

@dataclass
class HNSWConfig(VectorIndexConfig):
    """HNSW index configuration"""
    M: int = 16                      # Number of edges per node at layers > 0
    ef_construction: int = 200       # Size of dynamic candidate list for construction
    ef_search: int = 50              # Size of dynamic candidate list for search
    max_elements: Optional[int] = None  # Maximum number of elements in the index
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result.update({
            "M": self.M,
            "ef_construction": self.ef_construction,
            "ef_search": self.ef_search
        })
        if self.max_elements is not None:
            result["max_elements"] = self.max_elements
        return result

@dataclass
class FaissConfig(VectorIndexConfig):
    """FAISS index configuration"""
    index_type: str = "IndexFlatL2"  # FAISS index type
    nlist: int = 100                # Number of clusters (for IVF indices)
    nprobe: int = 10                # Number of clusters to visit during search
    use_gpu: bool = False           # Whether to use GPU
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result.update({
            "index_type": self.index_type,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
            "use_gpu": self.use_gpu
        })
        return result

@dataclass
class ExternalVectorDBConfig(VectorIndexConfig):
    """Configuration for external vector databases"""
    connection_string: Optional[str] = None
    api_key_env: Optional[str] = None
    api_key: Optional[str] = None
    namespace: Optional[str] = None
    collection_name: str = "modularmind_vectors"
    batch_size: int = 100
    additional_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = super().to_dict()
        result.update({
            "collection_name": self.collection_name,
            "batch_size": self.batch_size,
            "additional_params": self.additional_params
        })
        
        if self.connection_string:
            result["connection_string"] = self.connection_string
        if self.api_key_env:
            result["api_key_env"] = self.api_key_env
        if self.namespace:
            result["namespace"] = self.namespace
            
        # Don't include the actual API key in the serialized config
        return result