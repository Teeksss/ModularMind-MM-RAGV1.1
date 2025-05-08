"""
Vector Store Modülü.
Vektörel arama ve depolama işlevlerini sağlar.
"""

import logging
import os
import time
import uuid
import threading
from collections import defaultdict
from typing import List, Dict, Any, Optional, Union, Tuple, Set, Callable

from ModularMind.API.services.retrieval.models import Document, Chunk, SearchResult
from ModularMind.API.services.retrieval.vector_models import (
    IndexType, StorageType, MetadataIndexType, VectorStoreConfig
)
from ModularMind.API.services.embedding import EmbeddingService
from ModularMind.API.services.retrieval.search_utils import (
    extract_keywords, score_text_for_keywords, combine_search_results, 
    check_metadata_filter
)
from ModularMind.API.services.retrieval.storage import (
    save_to_disk, load_from_disk, save_to_sqlite, load_from_sqlite,
    save_to_postgres, load_from_postgres
)

logger = logging.getLogger(__name__)

class VectorStore:
    """
    Vector Store ana sınıfı.
    
    Vektör arama ve depolama işlevlerini sağlar.
    """
    
    def __init__(
        self, 
        config: Optional[VectorStoreConfig] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Args:
            config: Vector store yapılandırması
            embedding_service: Embedding servisi
        """
        self.config = config or VectorStoreConfig()
        self.embedding_service = embedding_service
        
        # Thread güvenliği için kilit
        self.lock = threading.RLock()
        
        # Depolama için veri yapıları
        self.vectors = []  # Vektörler
        self.ids = []      # Chunk ID'leri
        self.metadata = []  # Metadata bilgileri
        self.id_to_index = {}  # ID -> indeks eşlemesi
        
        # Metadata indeksi
        self.metadata_index = defaultdict(dict)
        
        # Değişiklik izleme
        self.is_dirty = False
        self.last_saved = time.time()
        
        # Indeks bağlantısı
        self.index = None
        
        # Koleksiyon bilgileri
        self.collection_name = self.config.collection_name
        self.collection_stats = {
            "total_chunks": 0,
            "total_documents": 0,
            "dimensions": self.config.dimensions,
            "size_bytes": 0,
            "creation_time": time.time(),
            "last_update": time.time()
        }
        
        # İndeksi başlat
        self._initialize_index()
        
        # Otomatik kaydetme için zamanlayıcı başlat
        if self.config.storage_type != StorageType.MEMORY and self.config.auto_save_interval > 0:
            self._start_auto_save_timer()
        
        logger.info(f"Vector Store başlatıldı: {self.config.index_type}, {self.config.storage_type}, {self.collection_name}")
    
    def add(self, chunk: Chunk) -> None:
        """
        Tek bir chunk ekler.
        
        Args:
            chunk: Eklenecek parça
        """
        from ModularMind.API.services.retrieval.vector_operations import add_chunk
        add_chunk(self, chunk)
    
    def add_batch(self, chunks: List[Chunk]) -> None:
        """
        Toplu chunk ekler.
        
        Args:
            chunks: Eklenecek parçalar
        """
        from ModularMind.API.services.retrieval.vector_operations import add_batch_chunks
        add_batch_chunks(self, chunks)
    
    def update(self, chunk: Chunk) -> None:
        """
        Mevcut bir chunk'ı günceller.
        
        Args:
            chunk: Güncellenecek parça
        """
        from ModularMind.API.services.retrieval.vector_operations import update_chunk
        update_chunk(self, chunk)
    
    def delete(self, chunk_id: str) -> bool:
        """
        Bir chunk'ı siler.
        
        Args:
            chunk_id: Silinecek chunk ID'si
            
        Returns:
            bool: Başarı durumu
        """
        from ModularMind.API.services.retrieval.vector_operations import delete_chunk
        return delete_chunk(self, chunk_id)
    
    def search(
        self, 
        query_vector: List[float], 
        limit: int = 10, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_distances: bool = True,
        min_score_threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Vektörel arama yapar.
        
        Args:
            query_vector: Sorgu vektörü
            limit: Maksimum sonuç sayısı
            filter_metadata: Metadata filtresi
            include_metadata: Sonuçlarda metadata dahil edilsin mi
            include_distances: Sonuçlarda uzaklık/benzerlik skoru dahil edilsin mi
            min_score_threshold: Minimum benzerlik eşiği
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        from ModularMind.API.services.retrieval.search import vector_search
        return vector_search(
            self, 
            query_vector, 
            limit, 
            filter_metadata, 
            include_metadata, 
            include_distances, 
            min_score_threshold
        )
    
    def search_by_text(
        self, 
        query_text: str, 
        limit: int = 10, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        include_distances: bool = True,
        min_score_threshold: Optional[float] = None,
        embedding_model: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Metin sorgusuyla arama yapar.
        
        Args:
            query_text: Sorgu metni
            limit: Maksimum sonuç sayısı
            filter_metadata: Metadata filtresi
            include_metadata: Sonuçlarda metadata dahil edilsin mi
            include_distances: Sonuçlarda uzaklık/benzerlik skoru dahil edilsin mi
            min_score_threshold: Minimum benzerlik eşiği
            embedding_model: Kullanılacak embedding model ID
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        from ModularMind.API.services.retrieval.search import text_search
        return text_search(
            self,
            query_text,
            limit,
            filter_metadata,
            include_metadata,
            include_distances,
            min_score_threshold,
            embedding_model
        )
    
    def hybrid_search(
        self, 
        query_text: str,
        limit: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        alpha: Optional[float] = None,
        keyword_fields: Optional[List[str]] = None,
        min_score_threshold: Optional[float] = None,
        embedding_model: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Karma arama yapar (vektörel + anahtar kelime).
        
        Args:
            query_text: Sorgu metni
            limit: Maksimum sonuç sayısı
            filter_metadata: Metadata filtresi
            alpha: Vektör ve anahtar kelime ağırlığı (0-1 arası)
            keyword_fields: Anahtar kelime araması için kullanılacak alanlar
            min_score_threshold: Minimum benzerlik eşiği
            embedding_model: Kullanılacak embedding model ID
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        from ModularMind.API.services.retrieval.search import hybrid_search
        return hybrid_search(
            self,
            query_text,
            limit,
            filter_metadata,
            alpha,
            keyword_fields,
            min_score_threshold,
            embedding_model
        )
    
    def keyword_search(
        self, 
        query_text: str, 
        limit: int = 10, 
        filter_metadata: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Anahtar kelime araması yapar.
        
        Args:
            query_text: Sorgu metni
            limit: Maksimum sonuç sayısı
            filter_metadata: Metadata filtresi
            fields: Arama yapılacak alanlar
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        from ModularMind.API.services.retrieval.search import keyword_search
        return keyword_search(self, query_text, limit, filter_metadata, fields)
    
    def metadata_search(
        self, 
        filter_metadata: Dict[str, Any], 
        limit: int = 10,
    ) -> List[SearchResult]:
        """
        Metadata araması yapar.
        
        Args:
            filter_metadata: Metadata filtresi
            limit: Maksimum sonuç sayısı
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        from ModularMind.API.services.retrieval.search import metadata_search
        return metadata_search(self, filter_metadata, limit)
    
    def get_documents(
        self, 
        document_id: Optional[str] = None,
        filter_metadata: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Belge bilgilerini döndürür.
        
        Args:
            document_id: Belge ID'si (None ise tüm belgeler)
            filter_metadata: Metadata filtresi
            limit: Maksimum sonuç sayısı
            offset: Başlangıç indeksi
            
        Returns:
            List[Dict[str, Any]]: Belge bilgileri
        """
        from ModularMind.API.services.retrieval.documents import get_documents_info
        return get_documents_info(self, document_id, filter_metadata, limit, offset)
    
    def save(self) -> bool:
        """
        Vector store'u kaydeder.
        
        Returns:
            bool: Başarı durumu
        """
        with self.lock:
            if not self.is_dirty:
                return True
            
            # Depolama tipine göre kaydet
            if self.config.storage_type == StorageType.MEMORY:
                # Bellekte tutuluyorsa kaydetmeye gerek yok
                return True
                
            elif self.config.storage_type == StorageType.DISK:
                return save_to_disk(self)
                
            elif self.config.storage_type == StorageType.SQLITE:
                return save_to_sqlite(self)
                
            elif self.config.storage_type == StorageType.POSTGRES:
                return save_to_postgres(self)
                
            elif self.config.storage_type == StorageType.EXTERNAL:
                # Harici depolamada veri zaten kaydedilmiş durumda
                return True
            
            return False
    
    def load(self) -> bool:
        """
        Vector store'u yükler.
        
        Returns:
            bool: Başarı durumu
        """
        with self.lock:
            # Depolama tipine göre yükle
            if self.config.storage_type == StorageType.MEMORY:
                # Bellekte tutuluyorsa yüklemeye gerek yok
                return True
                
            elif self.config.storage_type == StorageType.DISK:
                return load_from_disk(self)
                
            elif self.config.storage_type == StorageType.SQLITE:
                return load_from_sqlite(self)
                
            elif self.config