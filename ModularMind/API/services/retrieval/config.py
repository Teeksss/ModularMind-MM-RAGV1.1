"""
Retrieval servisi yapılandırma sınıfları.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Union

@dataclass
class VectorStoreConfig:
    """Vektör deposu yapılandırması"""
    
    store_type: str = "hnsw"
    storage_path: str = "./data/vector_store"
    dimensions: Dict[str, int] = field(default_factory=dict)
    metric: str = "cosine"
    embed_batch_size: int = 32
    default_embedding_model: str = "text-embedding-3-small"
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "store_type": self.store_type,
            "storage_path": self.storage_path,
            "dimensions": self.dimensions,
            "metric": self.metric,
            "embed_batch_size": self.embed_batch_size,
            "default_embedding_model": self.default_embedding_model
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorStoreConfig':
        """Dict'ten nesne oluşturur"""
        return cls(
            store_type=data.get("store_type", "hnsw"),
            storage_path=data.get("storage_path", "./data/vector_store"),
            dimensions=data.get("dimensions", {}),
            metric=data.get("metric", "cosine"),
            embed_batch_size=data.get("embed_batch_size", 32),
            default_embedding_model=data.get("default_embedding_model", "text-embedding-3-small")
        )

@dataclass
class HybridSearchConfig:
    """Hibrit arama yapılandırması"""
    
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    enable_reranking: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "vector_weight": self.vector_weight,
            "keyword_weight": self.keyword_weight,
            "enable_reranking": self.enable_reranking
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HybridSearchConfig':
        """Dict'ten nesne oluşturur"""
        return cls(
            vector_weight=data.get("vector_weight", 0.7),
            keyword_weight=data.get("keyword_weight", 0.3),
            enable_reranking=data.get("enable_reranking", True)
        )

@dataclass
class ReRankingConfig:
    """Yeniden sıralama yapılandırması"""
    
    enabled: bool = False
    model_type: str = "cross-encoder"
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranking_method: str = "model"  # model, bm25, custom
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "enabled": self.enabled,
            "model_type": self.model_type,
            "model_name": self.model_name,
            "reranking_method": self.reranking_method
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReRankingConfig':
        """Dict'ten nesne oluşturur"""
        return cls(
            enabled=data.get("enabled", False),
            model_type=data.get("model_type", "cross-encoder"),
            model_name=data.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
            reranking_method=data.get("reranking_method", "model")
        )

@dataclass
class ChunkingConfig:
    """Bölümleme yapılandırması"""
    
    default_chunk_size: int = 500
    default_chunk_overlap: int = 50
    default_strategy: str = "size"  # size, token, recursive, semantic
    semantic_chunking_enabled: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "default_chunk_size": self.default_chunk_size,
            "default_chunk_overlap": self.default_chunk_overlap,
            "default_strategy": self.default_strategy,
            "semantic_chunking_enabled": self.semantic_chunking_enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChunkingConfig':
        """Dict'ten nesne oluşturur"""
        return cls(
            default_chunk_size=data.get("default_chunk_size", 500),
            default_chunk_overlap=data.get("default_chunk_overlap", 50),
            default_strategy=data.get("default_strategy", "size"),
            semantic_chunking_enabled=data.get("semantic_chunking_enabled", False)
        )

@dataclass
class RetrievalConfig:
    """Retrieval servisi ana yapılandırması"""
    
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    hybrid_search: HybridSearchConfig = field(default_factory=HybridSearchConfig)
    reranking: ReRankingConfig = field(default_factory=ReRankingConfig)
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    
    cache_search_results: bool = True
    search_result_cache_ttl: int = 3600  # saniye
    highlight_matches: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "vector_store": self.vector_store.to_dict(),
            "hybrid_search": self.hybrid_search.to_dict(),
            "reranking": self.reranking.to_dict(),
            "chunking": self.chunking.to_dict(),
            "cache_search_results": self.cache_search_results,
            "search_result_cache_ttl": self.search_result_cache_ttl,
            "highlight_matches": self.highlight_matches
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetrievalConfig':
        """Dict'ten nesne oluşturur"""
        return cls(
            vector_store=VectorStoreConfig.from_dict(data.get("vector_store", {})),
            hybrid_search=HybridSearchConfig.from_dict(data.get("hybrid_search", {})),
            reranking=ReRankingConfig.from_dict(data.get("reranking", {})),
            chunking=ChunkingConfig.from_dict(data.get("chunking", {})),
            cache_search_results=data.get("cache_search_results", True),
            search_result_cache_ttl=data.get("search_result_cache_ttl", 3600),
            highlight_matches=data.get("highlight_matches", True)
        )