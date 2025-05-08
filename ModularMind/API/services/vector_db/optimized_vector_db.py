"""
Optimize edilmiş vektör veritabanı modülü.
Gelişmiş indeksleme, kuantizasyon ve filtreleme stratejileri sunar.
"""

import logging
import time
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import uuid
from enum import Enum
from dataclasses import dataclass

from ModularMind.API.services.retrieval.models import Document, Chunk
from ModularMind.API.db.base import DatabaseManager

logger = logging.getLogger(__name__)

class IndexType(str, Enum):
    """Vektör indeks türleri."""
    FLAT = "flat"         # Brute force (tam doğrulukta)
    IVF = "ivf"           # Inverted File Index (sınırlı arama)
    HNSW = "hnsw"         # Hierarchical Navigable Small World (ANN)
    PQ = "pq"             # Product Quantization (sıkıştırma)
    IVFPQ = "ivfpq"       # IVF + PQ kombinasyonu
    IVFHNSW = "ivfhnsw"   # IVF + HNSW kombinasyonu
    CUSTOM = "custom"     # Özel indeks tipi

@dataclass
class VectorDBConfig:
    """Vektör veritabanı yapılandırması."""
    index_type: IndexType = IndexType.HNSW
    dimension: int = 1536
    metric_type: str = "cosine"  # cosine, l2, dot
    num_partitions: int = 100    # IVF için bölüm sayısı
    m_parameter: int = 16        # HNSW için bağlantı sayısı
    ef_construction: int = 200   # HNSW inşası için arama genişliği
    ef_search: int = 100         # HNSW araması için arama genişliği
    num_subvectors: int = 8      # PQ için alt vektör sayısı
    bits_per_subvector: int = 8  # PQ için alt vektör başına bit sayısı
    use_metadata_index: bool = True
    shard_count: int = 1
    cache_vectors: bool = True
    max_cache_size: int = 10000  # Maksimum önbellek boyutu

class OptimizedVectorDB:
    """
    Optimize edilmiş vektör veritabanı işlemlerini gerçekleştiren sınıf.
    """
    
    def __init__(self, config: VectorDBConfig, collection_name: str = "vector_index"):
        """
        Args:
            config: Vektör veritabanı yapılandırması
            collection_name: Koleksiyon adı
        """
        self.config = config
        self.collection_name = collection_name
        
        # Veritabanı bağlantısı
        self.db_manager = DatabaseManager()
        self.db = self.db_manager.get_database()
        
        # Koleksiyonlar
        self.vector_collection = self.db[f"{collection_name}_vectors"]
        self.metadata_collection = self.db[f"{collection_name}_metadata"]
        
        # Vektör önbelleği
        self.vector_cache = {}
        
        # Koleksiyonları hazırla
        self._initialize_collections()
        
        # İndeks yöneticisi
        self.index_manager = None
        self._initialize_index()
        
        logger.info(f"OptimizedVectorDB başlatıldı: {collection_name}, index_type={config.index_type.value}")
    
    def _initialize_collections(self) -> None:
        """Koleksiyonları ve indeksleri hazırlar."""
        # Vektör koleksiyonu indeksleri
        self.vector_collection.create_index("vector_id", unique=True)
        
        # Metadata koleksiyonu indeksleri
        self.metadata_collection.create_index("vector_id", unique=True)
        
        if self.config.use_metadata_index:
            # Filtreleme için yaygın alanlarda indeksler oluştur
            self.metadata_collection.create_index("doc_id")
            self.metadata_collection.create_index("chunk_index")
            self.metadata_collection.create_index("metadata.source")
            self.metadata_collection.create_index([("metadata.created_at", -1)])
        
        logger.info(f"Veritabanı koleksiyonları ve indeksleri hazırlandı: {self.collection_name}")
    
    def _initialize_index(self) -> None:
        """Vektör indeksini başlatır."""
        # İndeks türüne göre uygun yöneticiyi seç
        if self.config.index_type == IndexType.FLAT:
            self.index_manager = FlatIndex(self.config)
        elif self.config.index_type == IndexType.HNSW:
            self.index_manager = HNSWIndex(self.config)
        elif self.config.index_type == IndexType.IVF:
            self.index_manager = IVFIndex(self.config)
        elif self.config.index_type == IndexType.PQ:
            self.index_manager = PQIndex(self.config)
        elif self.config.index_type == IndexType.IVFPQ:
            self.index_manager = IVFPQIndex(self.config)
        else:
            # Varsayılan olarak HNSW kullan
            logger.warning(f"Desteklenmeyen indeks türü: {self.config.index_type.value}, varsayılan HNSW kullanılıyor")
            self.index_manager = HNSWIndex(self.config)
        
        # İndeks yöneticisini başlat
        self.index_manager.initialize()
        
        logger.info(f"Vektör indeksi başlatıldı: {self.config.index_type.value}")
    
    def add_vectors(self, vectors: List[np.ndarray], metadatas: List[Dict[str, Any]] = None) -> List[str]:
        """
        Vektörleri ve metadataları ekler.
        
        Args:
            vectors: Eklenecek vektörler
            metadatas: Vektör metadataları (isteğe bağlı)
            
        Returns:
            List[str]: Eklenen vektörlerin ID'leri
        """
        if not vectors:
            return []
        
        # Metadataları kontrol et
        if metadatas is None:
            metadatas = [{} for _ in range(len(vectors))]
        
        if len(vectors) != len(metadatas):
            raise ValueError(f"Vektör sayısı ({len(vectors)}) ile metadata sayısı ({len(metadatas)}) eşleşmiyor")
        
        # Vektör ID'leri oluştur
        vector_ids = [str(uuid.uuid4()) for _ in range(len(vectors))]
        
        # Vektörleri indekse ekle
        self.index_manager.add_vectors(vector_ids, vectors)
        
        # Vektörleri veritabanına kaydet
        vector_docs = []
        for i, (vector_id, vector) in enumerate(zip(vector_ids, vectors)):
            # Vektörü float32 dizisi olarak kaydet
            vector_docs.append({
                "vector_id": vector_id,
                "vector": vector.tolist(),
                "dimension": len(vector),
                "created_at": time.time()
            })
        
        # Toplu ekleme
        if vector_docs:
            self.vector_collection.insert_many(vector_docs)
        
        # Metadataları veritabanına kaydet
        metadata_docs = []
        for i, (vector_id, metadata) in enumerate(zip(vector_ids, metadatas)):
            metadata_docs.append({
                "vector_id": vector_id,
                "metadata": metadata,
                "doc_id": metadata.get("doc_id", ""),
                "chunk_index": metadata.get("chunk_index", i),
                "created_at": time.time()
            })
        
        # Toplu ekleme
        if metadata_docs:
            self.metadata_collection.insert_many(metadata_docs)
        
        # Vektörleri önbelleğe ekle
        if self.config.cache_vectors:
            for vector_id, vector in zip(vector_ids, vectors):
                self._cache_vector(vector_id, vector)
        
        logger.info(f"{len(vector_ids)} vektör eklendi")
        return vector_ids
    
    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray], metadatas: List[Dict[str, Any]] = None) -> bool:
        """
        Mevcut vektörleri ve metadataları günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
            metadatas: Yeni metadatalar (isteğe bağlı)
            
        Returns:
            bool: Başarılı ise True
        """
        if not vector_ids or not vectors:
            return False
        
        if len(vector_ids) != len(vectors):
            raise ValueError(f"Vektör ID sayısı ({len(vector_ids)}) ile vektör sayısı ({len(vectors)}) eşleşmiyor")
        
        # Metadataları kontrol et
        if metadatas is not None and len(vector_ids) != len(metadatas):
            raise ValueError(f"Vektör ID sayısı ({len(vector_ids)}) ile metadata sayısı ({len(metadatas)}) eşleşmiyor")
        
        # Vektörleri indekste güncelle
        self.index_manager.update_vectors(vector_ids, vectors)
        
        # Vektörleri veritabanında güncelle
        for i, (vector_id, vector) in enumerate(zip(vector_ids, vectors)):
            self.vector_collection.update_one(
                {"vector_id": vector_id},
                {"$set": {
                    "vector": vector.tolist(),
                    "updated_at": time.time()
                }}
            )
            
            # Vektörü önbellekte güncelle
            if self.config.cache_vectors:
                self._cache_vector(vector_id, vector)
        
        # Metadataları güncelle (varsa)
        if metadatas:
            for i, (vector_id, metadata) in enumerate(zip(vector_ids, metadatas)):
                self.metadata_collection.update_one(
                    {"vector_id": vector_id},
                    {"$set": {
                        "metadata": metadata,
                        "doc_id": metadata.get("doc_id", ""),
                        "chunk_index": metadata.get("chunk_index", i),
                        "updated_at": time.time()
                    }}
                )
        
        logger.info(f"{len(vector_ids)} vektör güncellendi")
        return True
    
    def delete_vectors(self, vector_ids: List[str]) -> bool:
        """
        Vektörleri ve ilişkili metadataları siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
            
        Returns:
            bool: Başarılı ise True
        """
        if not vector_ids:
            return False
        
        # Vektörleri indeksten sil
        self.index_manager.delete_vectors(vector_ids)
        
        # Vektörleri veritabanından sil
        self.vector_collection.delete_many({"vector_id": {"$in": vector_ids}})
        
        # Metadataları veritabanından sil
        self.metadata_collection.delete_many({"vector_id": {"$in": vector_ids}})
        
        # Vektörleri önbellekten sil
        if self.config.cache_vectors:
            for vector_id in vector_ids:
                if vector_id in self.vector_cache:
                    del self.vector_cache[vector_id]
        
        logger.info(f"{len(vector_ids)} vektör silindi")
        return True
    
    def query(self, query_vector: np.ndarray, top_k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            filter: Metadata filtreleri (isteğe bağlı)
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        search_start_time = time.time()
        
        # Sorgu vektörünü kontrol et
        if len(query_vector) != self.config.dimension:
            raise ValueError(f"Sorgu vektörü boyutu ({len(query_vector)}) beklenen boyut ({self.config.dimension}) ile eşleşmiyor")
        
        # Filtre durumuna göre strateji belirle
        if filter:
            # Filtre varsa, önce metadata filtreleme yap
            vector_ids, metadata_list = self._filter_metadata(filter, limit=top_k * 10)  # Daha fazla sonuç getir ve sonra sırala
            
            if not vector_ids:
                logger.info(f"Filtrelemeye uyan sonuç bulunamadı: {filter}")
                return []
            
            # Filtrelenmiş vektörlerle arama yap
            results = self.index_manager.query_by_ids(query_vector, vector_ids, top_k)
        else:
            # Filtre yoksa, doğrudan indeks araması yap
            results = self.index_manager.query(query_vector, top_k)
        
        # Sonuçları zenginleştir (metadataları ekle)
        enriched_results = self._enrich_results(results)
        
        search_time = time.time() - search_start_time
        logger.info(f"Vektör araması tamamlandı: {len(enriched_results)} sonuç, {search_time:.4f} saniye")
        
        return enriched_results
    
    def _filter_metadata(self, filter: Dict[str, Any], limit: int = 100) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Metadata'ya göre filtreleme yapar.
        
        Args:
            filter: Filtreleme kriterleri
            limit: Maksimum sonuç sayısı
            
        Returns:
            Tuple[List[str], List[Dict[str, Any]]]: Filtrelenmiş vektör ID'leri ve metadatalar
        """
        # MongoDB sorgusu oluştur
        query = {}
        
        # Filtre kriterlerini işle
        for key, value in filter.items():
            if key == "doc_id" or key == "chunk_index":
                # Doğrudan alanlar
                query[key] = value
            elif key.startswith("metadata."):
                # Doğrudan metadata alt alanı
                query[key] = value
            else:
                # Varsayılan olarak metadata altında ara
                query[f"metadata.{key}"] = value
        
        # Sorguyu çalıştır
        cursor = self.metadata_collection.find(query).limit(limit)
        
        # Sonuçları topla
        vector_ids = []
        metadata_list = []
        
        for doc in cursor:
            vector_ids.append(doc["vector_id"])
            metadata_list.append(doc)
        
        logger.info(f"Metadata filtreleme: {len(vector_ids)} sonuç, filtre={filter}")
        return vector_ids, metadata_list
    
    def _enrich_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Arama sonuçlarını metadata ile zenginleştirir.
        
        Args:
            results: Arama sonuçları (vector_id ve distance içerir)
            
        Returns:
            List[Dict[str, Any]]: Zenginleştirilmiş sonuçlar
        """
        if not results:
            return []
        
        # Vektör ID'lerini topla
        vector_ids = [result["vector_id"] for result in results]
        
        # Metadata'ları getir
        metadata_docs = {}
        cursor = self.metadata_collection.find({"vector_id": {"$in": vector_ids}})
        
        for doc in cursor:
            # _id alanını kaldır
            if "_id" in doc:
                del doc["_id"]
            
            metadata_docs[doc["vector_id"]] = doc
        
        # Sonuçları zenginleştir
        enriched_results = []
        
        for result in results:
            vector_id = result["vector_id"]
            
            # Metadata'yı sonuca ekle
            if vector_id in metadata_docs:
                metadata = metadata_docs[vector_id]
                
                # Mesafeyi benzerliğe dönüştür (0-1 arası, 1 en benzer)
                similarity = 1.0 - min(1.0, result["distance"])
                
                enriched_result = {
                    "vector_id": vector_id,
                    "similarity": similarity,
                    "distance": result["distance"]
                }
                
                # Metadata alanlarını ekle
                if "metadata" in metadata:
                    enriched_result["metadata"] = metadata["metadata"]
                if "doc_id" in metadata:
                    enriched_result["doc_id"] = metadata["doc_id"]
                if "chunk_index" in metadata:
                    enriched_result["chunk_index"] = metadata["chunk_index"]
                
                enriched_results.append(enriched_result)
        
        return enriched_results
    
    def _cache_vector(self, vector_id: str, vector: np.ndarray) -> None:
        """
        Vektörü önbelleğe ekler.
        
        Args:
            vector_id: Vektör ID'si
            vector: Vektör
        """
        # Önbellek boyutu limitini kontrol et
        if len(self.vector_cache) >= self.config.max_cache_size:
            # Basit LRU: Rastgele bir öğeyi kaldır
            key_to_remove = next(iter(self.vector_cache))
            del self.vector_cache[key_to_remove]
        
        # Vektörü önbelleğe ekle
        self.vector_cache[vector_id] = vector
    
    def get_vector(self, vector_id: str) -> Optional[np.ndarray]:
        """
        Belirli bir vektörü getirir.
        
        Args:
            vector_id: Vektör ID'si
            
        Returns:
            Optional[np.ndarray]: Vektör veya bulunamazsa None
        """
        # Önbellekte kontrol et
        if self.config.cache_vectors and vector_id in self.vector_cache:
            return self.vector_cache[vector_id]
        
        # Veritabanında ara
        doc = self.vector_collection.find_one({"vector_id": vector_id})
        
        if not doc:
            return None
        
        # Vektörü numpy dizisine dönüştür
        vector = np.array(doc["vector"], dtype=np.float32)
        
        # Önbelleğe ekle
        if self.config.cache_vectors:
            self._cache_vector(vector_id, vector)
        
        return vector
    
    def get_metadata(self, vector_id: str) -> Optional[Dict[str, Any]]:
        """
        Belirli bir vektörün metadatasını getirir.
        
        Args:
            vector_id: Vektör ID'si
            
        Returns:
            Optional[Dict[str, Any]]: Metadata veya bulunamazsa None
        """
        doc = self.metadata_collection.find_one({"vector_id": vector_id})
        
        if not doc:
            return None
        
        # _id alanını kaldır
        if "_id" in doc:
            del doc["_id"]
        
        return doc
    
    def stats(self) -> Dict[str, Any]:
        """
        Vektör veritabanı istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        # Vektör sayısı
        vector_count = self.vector_collection.count_documents({})
        
        # Metadata sayısı
        metadata_count = self.metadata_collection.count_documents({})
        
        # İndeks istatistikleri
        index_stats = self.index_manager.stats()
        
        # Önbellek istatistikleri
        cache_stats = {
            "size": len(self.vector_cache),
            "max_size": self.config.max_cache_size,
            "usage_percentage": len(self.vector_cache) / max(1, self.config.max_cache_size) * 100
        }
        
        return {
            "vector_count": vector_count,
            "metadata_count": metadata_count,
            "cache_stats": cache_stats,
            "index_stats": index_stats,
            "config": {
                "index_type": self.config.index_type.value,
                "dimension": self.config.dimension,
                "metric_type": self.config.metric_type,
            }
        }