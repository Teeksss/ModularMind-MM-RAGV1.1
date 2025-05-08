"""
Vector Store modelleri ve temel tanımlamaları.
"""

import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class IndexType(str, Enum):
    """İndeks türleri."""
    FLAT = "flat"           # Düz indeks (tam tarama)
    HNSW = "hnsw"           # Hierarchical Navigable Small World
    IVF = "ivf"             # Inverted File Index
    IVF_FLAT = "ivf_flat"   # IVF + Flat
    IVF_PQ = "ivf_pq"       # IVF + Product Quantization
    FAISS = "faiss"         # Facebook AI Similarity Search
    QDRANT = "qdrant"       # Qdrant vektör DB
    MILVUS = "milvus"       # Milvus vektör DB
    WEAVIATE = "weaviate"   # Weaviate vektör DB
    PINECONE = "pinecone"   # Pinecone vektör DB

class StorageType(str, Enum):
    """Depolama türleri."""
    MEMORY = "memory"       # Bellekte depolama
    DISK = "disk"           # Disk üzerinde depolama
    SQLITE = "sqlite"       # SQLite veritabanı
    POSTGRES = "postgres"   # PostgreSQL veritabanı
    EXTERNAL = "external"   # Harici depolama (vektör DB)

class MetadataIndexType(str, Enum):
    """Metadata indeksleme türleri."""
    NONE = "none"           # Metadata indekslemesi yok
    BASIC = "basic"         # Temel indeksleme (eşitlik sorguları)
    FULL = "full"           # Tam indeksleme (tüm sorgu tipleri)

@dataclass
class VectorStoreConfig:
    """Vector store yapılandırması."""
    index_type: IndexType = IndexType.HNSW
    storage_type: StorageType = StorageType.MEMORY
    metadata_index_type: MetadataIndexType = MetadataIndexType.BASIC
    dimensions: int = 768
    similarity_function: str = "cosine"  # cosine, dot, euclidean
    storage_path: Optional[str] = "./data/vector_storage"
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 100
    hnsw_m: int = 16        # Maksimum bağlantı sayısı
    ivf_nlist: int = 100    # Bölüm sayısı
    pq_m: int = 8           # PQ alt vektör sayısı
    pq_nbits: int = 8       # PQ kod boyutu
    batch_size: int = 512   # Toplu işlem boyutu
    search_batch_size: int = 1024  # Arama batch boyutu
    external_url: Optional[str] = None   # Harici vektör DB URL
    external_api_key: Optional[str] = None  # Harici vektör DB API anahtarı
    external_options: Dict[str, Any] = field(default_factory=dict)  # Harici vektör DB seçenekleri
    num_workers: int = 2    # Paralel işlem için iş parçacığı sayısı
    hybrid_search_alpha: float = 0.5  # Hibrit aramada vektör ağırlığı (0-1)
    collection_name: str = "default"  # Koleksiyon adı
    auto_save_interval: int = 60      # Otomatik kaydetme aralığı (saniye)