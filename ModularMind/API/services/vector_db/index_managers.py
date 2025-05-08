"""
Vektör indeks yöneticileri.
Farklı indeks stratejileri için implementasyonlar sağlar (HNSW, IVF, PQ vb.).
"""

import logging
import time
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union, Callable
import uuid
from enum import Enum
from abc import ABC, abstractmethod
import shutil
import pickle
import threading

logger = logging.getLogger(__name__)

class VectorIndexManager(ABC):
    """Vektör indeks yönetimi için temel sınıf."""

    def __init__(self, config):
        """
        Args:
            config: İndeks yapılandırması
        """
        self.config = config
        self.dimension = config.dimension
        self.metric_type = config.metric_type
        self.is_initialized = False
        self.index = None
        self.id_to_index = {}  # vector_id -> index eşleştirmesi
        self.index_to_id = {}  # index -> vector_id eşleştirmesi
        self.next_index = 0    # Bir sonraki eklenecek vektörün indeksi
        self.index_lock = threading.RLock()  # İndeks işlemleri için lock

    @abstractmethod
    def initialize(self) -> None:
        """İndeksi başlatır."""
        pass

    @abstractmethod
    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        pass

    @abstractmethod
    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        pass

    @abstractmethod
    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        pass

    @abstractmethod
    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        pass

    def query_by_ids(self, query_vector: np.ndarray, vector_ids: List[str], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Belirli ID'lere sahip vektörler arasında arama yapar.
        
        Args:
            query_vector: Sorgu vektörü
            vector_ids: Aranacak vektör ID'leri
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        # Bu metodu alt sınıflar override edebilir
        # Varsayılan implementasyon: Tüm vektörleri getir ve filtrele
        all_results = self.query(query_vector, len(vector_ids))
        
        # vector_ids'e uyanları filtrele
        filtered_results = [r for r in all_results if r["vector_id"] in vector_ids]
        
        # Top_k ile sınırla
        return filtered_results[:top_k]

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        pass

    def _register_vectors(self, vector_ids: List[str], start_index: int) -> Dict[str, int]:
        """
        Vektör ID'lerini indeks konumlarına kaydeder.
        
        Args:
            vector_ids: Vektör ID'leri
            start_index: Başlangıç indeks değeri
            
        Returns:
            Dict[str, int]: ID -> indeks eşleştirmesi
        """
        with self.index_lock:
            id_to_idx = {}
            for i, vector_id in enumerate(vector_ids):
                idx = start_index + i
                id_to_idx[vector_id] = idx
                self.id_to_index[vector_id] = idx
                self.index_to_id[idx] = vector_id
            
            # Sonraki indeks değerini güncelle
            self.next_index = start_index + len(vector_ids)
            
            return id_to_idx


class FlatIndex(VectorIndexManager):
    """Düz (brute-force) vektör indeksi."""

    def initialize(self) -> None:
        """İndeksi başlatır."""
        # Numpy dizisi olarak düz indeks
        self.index = np.zeros((0, self.dimension), dtype=np.float32)
        self.is_initialized = True
        logger.info("Flat indeks başlatıldı")

    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Vektörleri numpy dizisine dönüştür
            vectors_array = np.array([v for v in vectors], dtype=np.float32)
            
            # Vektörleri indekse ekle
            self.index = np.vstack((self.index, vectors_array))
            
            # ID'leri kaydet
            self._register_vectors(vector_ids, self.next_index)
            
            logger.info(f"Flat indekse {len(vectors)} vektör eklendi")

    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Her vektörü güncelle
            for vector_id, vector in zip(vector_ids, vectors):
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    self.index[idx] = vector
            
            logger.info(f"Flat indekste {len(vectors)} vektör güncellendi")

    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        if not vector_ids:
            return
        
        with self.index_lock:
            # Silinecek indeksleri topla
            indices_to_delete = []
            for vector_id in vector_ids:
                if vector_id in self.id_to_index:
                    indices_to_delete.append(self.id_to_index[vector_id])
                    # Mapping'lerden kaldır
                    idx = self.id_to_index[vector_id]
                    del self.id_to_index[vector_id]
                    del self.index_to_id[idx]
            
            if indices_to_delete:
                # Maske oluştur (silinecek olmayan indeksler True olacak)
                mask = np.ones(len(self.index), dtype=bool)
                mask[indices_to_delete] = False
                
                # Maske ile filtreleme yaparak silme işlemi
                self.index = self.index[mask]
                
                logger.info(f"Flat indeksten {len(indices_to_delete)} vektör silindi")
                
                # Mapping'leri yeniden oluştur
                self._rebuild_mappings()

    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        if len(self.index) == 0:
            return []
        
        with self.index_lock:
            # Mesafeleri hesapla
            if self.metric_type == "cosine":
                # Vektörleri normalize et
                query_norm = np.linalg.norm(query_vector)
                if query_norm > 0:
                    query_vector = query_vector / query_norm
                
                # Normalize edilmiş indeks vektörleri ile dot product
                # (Cosine benzerliği, 1 - benzerlik = mesafe)
                similarities = np.dot(self.index, query_vector)
                distances = 1.0 - similarities
            
            elif self.metric_type == "l2":
                # L2 (Euclidean) mesafesi
                distances = np.linalg.norm(self.index - query_vector, axis=1)
            
            elif self.metric_type == "dot":
                # Negatif dot product (maksimum dot product = minimum mesafe)
                similarities = np.dot(self.index, query_vector)
                distances = -similarities
            
            else:
                raise ValueError(f"Desteklenmeyen metrik türü: {self.metric_type}")
            
            # Top-k indekslerini al
            if len(distances) <= top_k:
                top_indices = np.argsort(distances)
            else:
                top_indices = np.argpartition(distances, top_k)[:top_k]
                top_indices = top_indices[np.argsort(distances[top_indices])]
            
            # Sonuçları oluştur
            results = []
            for idx in top_indices:
                if idx in self.index_to_id:
                    vector_id = self.index_to_id[idx]
                    results.append({
                        "vector_id": vector_id,
                        "distance": float(distances[idx])
                    })
            
            return results

    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self.index_lock:
            return {
                "type": "flat",
                "vector_count": len(self.index),
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "memory_usage_mb": self.index.nbytes / 1024 / 1024
            }

    def _rebuild_mappings(self) -> None:
        """ID ve indeks eşleştirmelerini yeniden oluşturur."""
        # Yeni mapping'ler
        new_id_to_index = {}
        new_index_to_id = {}
        
        # Kalan ID'ler için yeni indeksler ata
        for new_idx, old_idx in enumerate(range(len(self.index))):
            if old_idx in self.index_to_id:
                vector_id = self.index_to_id[old_idx]
                new_id_to_index[vector_id] = new_idx
                new_index_to_id[new_idx] = vector_id
        
        # Mapping'leri güncelle
        self.id_to_index = new_id_to_index
        self.index_to_id = new_index_to_id
        self.next_index = len(self.index)


class HNSWIndex(VectorIndexManager):
    """HNSW (Hierarchical Navigable Small World) vektör indeksi."""

    def initialize(self) -> None:
        """İndeksi başlatır."""
        try:
            import hnswlib
            self.hnswlib = hnswlib
        except ImportError:
            logger.error("hnswlib kütüphanesi bulunamadı, lütfen yükleyin: pip install hnswlib")
            raise ImportError("hnswlib kütüphanesi bulunamadı, lütfen yükleyin: pip install hnswlib")
        
        # Metrik türünü HNSW formatına dönüştür
        if self.metric_type == "cosine":
            space = "cosine"
        elif self.metric_type == "l2":
            space = "l2"
        elif self.metric_type == "dot":
            space = "ip"  # Inner product (hnswlib'de dot product için)
        else:
            raise ValueError(f"HNSW için desteklenmeyen metrik türü: {self.metric_type}")
        
        # HNSW indeksini oluştur
        self.index = self.hnswlib.Index(space=space, dim=self.dimension)
        
        # Başlangıç kapasitesi (otomatik olarak büyüyecektir)
        initial_capacity = 1000
        self.index.init_index(max_elements=initial_capacity, ef_construction=self.config.ef_construction, M=self.config.m_parameter)
        
        # Arama parametresi
        self.index.set_ef(self.config.ef_search)
        
        self.is_initialized = True
        self.current_capacity = initial_capacity
        logger.info(f"HNSW indeks başlatıldı: dim={self.dimension}, M={self.config.m_parameter}, ef_construction={self.config.ef_construction}")

    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Mevcut kapasite kontrolü
            required_capacity = self.next_index + len(vectors)
            if required_capacity > self.current_capacity:
                # Kapasiteyi artır (2 kat veya ihtiyaç duyulan miktarın 1.5 katı, hangisi büyükse)
                new_capacity = max(self.current_capacity * 2, int(required_capacity * 1.5))
                self.index.resize_index(new_capacity)
                self.current_capacity = new_capacity
                logger.info(f"HNSW indeks kapasitesi artırıldı: {self.current_capacity}")
            
            # Vektörleri numpy dizisine dönüştür
            vectors_array = np.array([v for v in vectors], dtype=np.float32)
            
            # ID'leri kaydet ve indeks konumlarını al
            id_to_idx = self._register_vectors(vector_ids, self.next_index)
            
            # Vektörleri indekse ekle
            indices = list(id_to_idx.values())
            self.index.add_items(vectors_array, indices)
            
            logger.info(f"HNSW indekse {len(vectors)} vektör eklendi")

    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Her vektörü güncelle
            for vector_id, vector in zip(vector_ids, vectors):
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    # HNSW güncellemesi
                    self.index.mark_deleted(idx)  # Eski vektörü sil
                    self.index.add_items(np.array([vector]), np.array([idx]))  # Yeni vektörü ekle
            
            logger.info(f"HNSW indekste {len(vectors)} vektör güncellendi")

    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        if not vector_ids:
            return
        
        with self.index_lock:
            # Silinecek indeksleri topla
            deleted_count = 0
            for vector_id in vector_ids:
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    # HNSW'den sil
                    self.index.mark_deleted(idx)
                    # Mapping'lerden kaldır
                    del self.id_to_index[vector_id]
                    del self.index_to_id[idx]
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"HNSW indeksten {deleted_count} vektör silindi")

    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        if self.next_index == 0:
            return []
        
        with self.index_lock:
            # K değerini mevcut vektör sayısına göre sınırla
            actual_k = min(top_k, self.next_index)
            if actual_k == 0:
                return []
            
            # HNSW araması yap
            try:
                labels, distances = self.index.knn_query(query_vector, k=actual_k)
            except Exception as e:
                logger.error(f"HNSW arama hatası: {str(e)}")
                return []
            
            # Sonuçları oluştur
            results = []
            for idx, distance in zip(labels[0], distances[0]):
                if idx in self.index_to_id:
                    vector_id = self.index_to_id[idx]
                    results.append({
                        "vector_id": vector_id,
                        "distance": float(distance)
                    })
            
            return results

    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self.index_lock:
            # HNSW'ye özgü istatistikler
            return {
                "type": "hnsw",
                "vector_count": self.next_index,
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "capacity": self.current_capacity,
                "m_parameter": self.config.m_parameter,
                "ef_construction": self.config.ef_construction,
                "ef_search": self.config.ef_search
            }


class IVFIndex(VectorIndexManager):
    """IVF (Inverted File Index) vektör indeksi."""

    def initialize(self) -> None:
        """İndeksi başlatır."""
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            logger.error("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
            raise ImportError("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
        
        # Metrik türünü faiss formatına dönüştür
        if self.metric_type == "l2":
            metric = self.faiss.METRIC_L2
        elif self.metric_type == "cosine" or self.metric_type == "dot":
            metric = self.faiss.METRIC_INNER_PRODUCT
        else:
            raise ValueError(f"IVF için desteklenmeyen metrik türü: {self.metric_type}")
        
        # Bölüm sayısı
        nlist = self.config.num_partitions
        
        # IVF indeksini oluştur
        self.quantizer = self.faiss.IndexFlatL2(self.dimension)
        self.index = self.faiss.IndexIVFFlat(self.quantizer, self.dimension, nlist, metric)
        
        # Eğitim için boş vektörler
        # Not: Gerçek veri ile eğitim daha sonra yapılacak
        empty_vectors = np.zeros((max(nlist, 100), self.dimension), dtype=np.float32)
        self.index.train(empty_vectors)
        
        # Arama parametresi
        self.index.nprobe = min(nlist, 10)  # Aramalarda incelenecek bölüm sayısı
        
        self.is_initialized = True
        self.is_trained_with_real_data = False
        logger.info(f"IVF indeks başlatıldı: dim={self.dimension}, nlist={nlist}")
        
        # Vektör verilerini saklamak için numpy dizisi
        self.vectors = np.zeros((0, self.dimension), dtype=np.float32)

    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Vektörleri numpy dizisine dönüştür
            vectors_array = np.array([v for v in vectors], dtype=np.float32)
            
            # ID'leri kaydet
            self._register_vectors(vector_ids, self.next_index)
            
            # Cosine benzerliği için normalizasyon
            if self.metric_type == "cosine":
                # Vektörleri normalize et
                norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
                vectors_array = vectors_array / np.maximum(norms, 1e-10)
            
            # Vektörleri sakla
            self.vectors = np.vstack((self.vectors, vectors_array))
            
            # Vektörleri indekse ekle
            self.index.add(vectors_array)
            
            # Eğer indeks henüz gerçek verilerle eğitilmediyse ve yeterli veri varsa
            if not self.is_trained_with_real_data and len(self.vectors) >= self.config.num_partitions:
                # İndeksi gerçek verilerle yeniden eğit
                self.index.reset()
                self.index.train(self.vectors)
                # Tüm vektörleri tekrar ekle
                self.index.add(self.vectors)
                self.is_trained_with_real_data = True
                logger.info(f"IVF indeks gerçek verilerle eğitildi: {len(self.vectors)} vektör")
            
            logger.info(f"IVF indekse {len(vectors)} vektör eklendi")

    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Faiss IVF indeksinde doğrudan güncelleme yok
            # İndeksi yeniden oluşturmamız gerekiyor
            
            # Her vektörü güncelle
            updated_indices = []
            for vector_id, vector in zip(vector_ids, vectors):
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    updated_indices.append(idx)
                    
                    # Vektörü numpy dizisinde güncelle
                    if self.metric_type == "cosine":
                        # Cosine benzerliği için normalize et
                        norm = np.linalg.norm(vector)
                        if norm > 0:
                            self.vectors[idx] = vector / norm
                    else:
                        self.vectors[idx] = vector
            
            if updated_indices:
                # İndeksi yeniden oluştur
                self.index.reset()
                self.index.train(self.vectors)
                self.index.add(self.vectors)
                logger.info(f"IVF indekste {len(updated_indices)} vektör güncellendi (indeks yeniden oluşturuldu)")

    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        if not vector_ids:
            return
        
        with self.index_lock:
            # Silinecek indeksleri topla
            deleted_indices = []
            for vector_id in vector_ids:
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    deleted_indices.append(idx)
                    # Mapping'lerden kaldır
                    del self.id_to_index[vector_id]
                    del self.index_to_id[idx]
            
            if deleted_indices:
                # Silinecek olmayan vektörleri seç
                mask = np.ones(len(self.vectors), dtype=bool)
                mask[deleted_indices] = False
                
                # Maskeyi uygula
                self.vectors = self.vectors[mask]
                
                # Mapping'leri güncelle
                self._rebuild_mappings()
                
                # İndeksi yeniden oluştur
                self.index.reset()
                if len(self.vectors) > 0:
                    self.index.train(self.vectors)
                    self.index.add(self.vectors)
                
                logger.info(f"IVF indeksten {len(deleted_indices)} vektör silindi (indeks yeniden oluşturuldu)")

    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        if len(self.vectors) == 0:
            return []
        
        with self.index_lock:
            # Sorgu vektörünü hazırla
            query = query_vector.reshape(1, -1).astype(np.float32)
            
            # Cosine benzerliği için normalize
            if self.metric_type == "cosine":
                query_norm = np.linalg.norm(query)
                if query_norm > 0:
                    query = query / query_norm
            
            # K değerini mevcut vektör sayısına göre sınırla
            actual_k = min(top_k, len(self.vectors))
            if actual_k == 0:
                return []
            
            # Faiss araması yap
            try:
                distances, indices = self.index.search(query, actual_k)
            except Exception as e:
                logger.error(f"IVF arama hatası: {str(e)}")
                return []
            
            # Sonuçları oluştur
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1 and idx in self.index_to_id:  # -1, bulunamayan sonuçlar için
                    vector_id = self.index_to_id[idx]
                    
                    # Dot ürünü benzerliği mesafeye dönüştür
                    if self.metric_type == "dot":
                        # Dot product yüksek = düşük mesafe
                        distance = -distance
                    
                    results.append({
                        "vector_id": vector_id,
                        "distance": float(distance)
                    })
            
            return results

    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self.index_lock:
            return {
                "type": "ivf",
                "vector_count": len(self.vectors),
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "num_partitions": self.config.num_partitions,
                "nprobe": self.index.nprobe,
                "is_trained_with_real_data": self.is_trained_with_real_data,
                "memory_usage_mb": self.vectors.nbytes / 1024 / 1024
            }

    def _rebuild_mappings(self) -> None:
        """ID ve indeks eşleştirmelerini yeniden oluşturur."""
        # Yeni mapping'ler
        new_id_to_index = {}
        new_index_to_id = {}
        
        # Mevcut ID'leri al
        current_ids = set(self.id_to_index.keys())
        
        # Her ID için yeni indeks ata
        for new_idx, vector_id in enumerate(current_ids):
            new_id_to_index[vector_id] = new_idx
            new_index_to_id[new_idx] = vector_id
        
        # Mapping'leri güncelle
        self.id_to_index = new_id_to_index
        self.index_to_id = new_index_to_id
        self.next_index = len(self.vectors)


class PQIndex(VectorIndexManager):
    """PQ (Product Quantization) vektör indeksi."""

    def initialize(self) -> None:
        """İndeksi başlatır."""
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            logger.error("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
            raise ImportError("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
        
        # Metrik türünü faiss formatına dönüştür
        if self.metric_type == "l2":
            metric = self.faiss.METRIC_L2
        elif self.metric_type == "cosine" or self.metric_type == "dot":
            metric = self.faiss.METRIC_INNER_PRODUCT
        else:
            raise ValueError(f"PQ için desteklenmeyen metrik türü: {self.metric_type}")
        
        # PQ parametreleri
        M = self.config.num_subvectors  # Alt vektör sayısı
        nbits = self.config.bits_per_subvector  # Alt vektör başına bit sayısı
        
        # M değeri, boyutun bir böleni olmalı
        if self.dimension % M != 0:
            original_M = M
            # Boyuta uygun bir bölen bul
            for i in range(M, 0, -1):
                if self.dimension % i == 0:
                    M = i
                    break
            logger.warning(f"PQ alt vektör sayısı {original_M}, boyutun ({self.dimension}) böleni değil. {M} değeri kullanılacak.")
        
        # PQ indeksini oluştur
        if self.metric_type == "cosine":
            # Cosine benzerliği için normalize edilmiş vektörler kullanılacak
            self.index = self.faiss.IndexPQ(self.dimension, M, nbits, metric)
        else:
            self.index = self.faiss.IndexPQ(self.dimension, M, nbits, metric)
        
        # Eğitim için boş vektörler
        # Not: Gerçek veri ile eğitim daha sonra yapılacak
        empty_vectors = np.zeros((max(256, M * 10), self.dimension), dtype=np.float32)
        self.index.train(empty_vectors)
        
        self.is_initialized = True
        self.is_trained_with_real_data = False
        logger.info(f"PQ indeks başlatıldı: dim={self.dimension}, M={M}, nbits={nbits}")
        
        # Vektör verilerini saklamak için numpy dizisi (original vektörler)
        self.vectors = np.zeros((0, self.dimension), dtype=np.float32)

    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Vektörleri numpy dizisine dönüştür
            vectors_array = np.array([v for v in vectors], dtype=np.float32)
            
            # ID'leri kaydet
            self._register_vectors(vector_ids, self.next_index)
            
            # Orijinal vektörleri sakla
            self.vectors = np.vstack((self.vectors, vectors_array.copy()))
            
            # Cosine benzerliği için normalizasyon
            if self.metric_type == "cosine":
                # Vektörleri normalize et
                norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
                vectors_array = vectors_array / np.maximum(norms, 1e-10)
            
            # Vektörleri indekse ekle
            self.index.add(vectors_array)
            
            # Eğer indeks henüz gerçek verilerle eğitilmediyse ve yeterli veri varsa
            if not self.is_trained_with_real_data and len(self.vectors) >= 1000:
                # Gerçek verilerle eğitilecek vektörleri hazırla
                train_vectors = self.vectors.copy()
                
                if self.metric_type == "cosine":
                    # Vektörleri normalize et
                    norms = np.linalg.norm(train_vectors, axis=1, keepdims=True)
                    train_vectors = train_vectors / np.maximum(norms, 1e-10)
                
                # İndeksi gerçek verilerle yeniden eğit
                self.index.reset()
                self.index.train(train_vectors)
                
                # Tüm vektörleri tekrar ekle
                if self.metric_type == "cosine":
                    self.index.add(train_vectors)
                else:
                    self.index.add(self.vectors)
                
                self.is_trained_with_real_data = True
                logger.info(f"PQ indeks gerçek verilerle eğitildi: {len(self.vectors)} vektör")
            
            logger.info(f"PQ indekse {len(vectors)} vektör eklendi")

    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # PQ indeksinde doğrudan güncelleme yok
            # İndeksi yeniden oluşturmamız gerekiyor
            
            # Her vektörü güncelle
            updated_indices = []
            for vector_id, vector in zip(vector_ids, vectors):
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    updated_indices.append(idx)
                    
                    # Vektörü numpy dizisinde güncelle
                    self.vectors[idx] = vector
            
            if updated_indices:
                # Normalize edilmiş vektörleri hazırla
                normalized_vectors = self.vectors.copy()
                if self.metric_type == "cosine":
                    norms = np.linalg.norm(normalized_vectors, axis=1, keepdims=True)
                    normalized_vectors = normalized_vectors / np.maximum(norms, 1e-10)
                
                # İndeksi yeniden oluştur
                self.index.reset()
                self.index.train(normalized_vectors)
                self.index.add(normalized_vectors)
                logger.info(f"PQ indekste {len(updated_indices)} vektör güncellendi (indeks yeniden oluşturuldu)")

    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        if not vector_ids:
            return
        
        with self.index_lock:
            # Silinecek indeksleri topla
            deleted_indices = []
            for vector_id in vector_ids:
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    deleted_indices.append(idx)
                    # Mapping'lerden kaldır
                    del self.id_to_index[vector_id]
                    del self.index_to_id[idx]
            
            if deleted_indices:
                # Silinecek olmayan vektörleri seç
                mask = np.ones(len(self.vectors), dtype=bool)
                mask[deleted_indices] = False
                
                # Maskeyi uygula
                self.vectors = self.vectors[mask]
                
                # Mapping'leri güncelle
                self._rebuild_mappings()
                
                # İndeksi yeniden oluştur
                normalized_vectors = self.vectors.copy()
                if self.metric_type == "cosine":
                    norms = np.linalg.norm(normalized_vectors, axis=1, keepdims=True)
                    normalized_vectors = normalized_vectors / np.maximum(norms, 1e-10)
                
                self.index.reset()
                if len(self.vectors) > 0:
                    self.index.train(normalized_vectors)
                    self.index.add(normalized_vectors)
                
                logger.info(f"PQ indeksten {len(deleted_indices)} vektör silindi (indeks yeniden oluşturuldu)")

    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        if len(self.vectors) == 0:
            return []
        
        with self.index_lock:
            # Sorgu vektörünü hazırla
            query = query_vector.reshape(1, -1).astype(np.float32)
            
            # Cosine benzerliği için normalize
            if self.metric_type == "cosine":
                query_norm = np.linalg.norm(query)
                if query_norm > 0:
                    query = query / query_norm
            
            # K değerini mevcut vektör sayısına göre sınırla
            actual_k = min(top_k, len(self.vectors))
            if actual_k == 0:
                return []
            
            # PQ araması yap
            try:
                distances, indices = self.index.search(query, actual_k)
            except Exception as e:
                logger.error(f"PQ arama hatası: {str(e)}")
                return []
            
            # Sonuçları oluştur
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1 and idx in self.index_to_id:  # -1, bulunamayan sonuçlar için
                    vector_id = self.index_to_id[idx]
                    
                    # Dot ürünü benzerliği mesafeye dönüştür
                    if self.metric_type == "dot":
                        # Dot product yüksek = düşük mesafe
                        distance = -distance
                    
                    results.append({
                        "vector_id": vector_id,
                        "distance": float(distance)
                    })
            
            return results

    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self.index_lock:
            return {
                "type": "pq",
                "vector_count": len(self.vectors),
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "num_subvectors": self.config.num_subvectors,
                "bits_per_subvector": self.config.bits_per_subvector,
                "is_trained_with_real_data": self.is_trained_with_real_data,
                "memory_usage_mb": self.vectors.nbytes / 1024 / 1024,
                "compression_ratio": (self.vectors.nbytes / (self.config.num_subvectors * (2**self.config.bits_per_subvector) * 4))
            }

    def _rebuild_mappings(self) -> None:
        """ID ve indeks eşleştirmelerini yeniden oluşturur."""
        # Yeni mapping'ler
        new_id_to_index = {}
        new_index_to_id = {}
        
        # Mevcut ID'leri al
        current_ids = list(self.id_to_index.keys())
        
        # Her ID için yeni indeks ata
        for new_idx, vector_id in enumerate(current_ids):
            new_id_to_index[vector_id] = new_idx
            new_index_to_id[new_idx] = vector_id
        
        # Mapping'leri güncelle
        self.id_to_index = new_id_to_index
        self.index_to_id = new_index_to_id
        self.next_index = len(self.vectors)


class IVFPQIndex(VectorIndexManager):
    """IVFPQ (Inverted File Index + Product Quantization) vektör indeksi."""

    def initialize(self) -> None:
        """İndeksi başlatır."""
        try:
            import faiss
            self.faiss = faiss
        except ImportError:
            logger.error("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
            raise ImportError("faiss kütüphanesi bulunamadı, lütfen yükleyin: pip install faiss-cpu veya faiss-gpu")
        
        # Metrik türünü faiss formatına dönüştür
        if self.metric_type == "l2":
            metric = self.faiss.METRIC_L2
        elif self.metric_type == "cosine" or self.metric_type == "dot":
            metric = self.faiss.METRIC_INNER_PRODUCT
        else:
            raise ValueError(f"IVFPQ için desteklenmeyen metrik türü: {self.metric_type}")
        
        # IVF parametreleri
        nlist = self.config.num_partitions
        
        # PQ parametreleri
        M = self.config.num_subvectors
        nbits = self.config.bits_per_subvector
        
        # M değeri, boyutun bir böleni olmalı
        if self.dimension % M != 0:
            original_M = M
            # Boyuta uygun bir bölen bul
            for i in range(M, 0, -1):
                if self.dimension % i == 0:
                    M = i
                    break
            logger.warning(f"PQ alt vektör sayısı {original_M}, boyutun ({self.dimension}) böleni değil. {M} değeri kullanılacak.")
        
        # IVFPQ indeksini oluştur
        self.quantizer = self.faiss.IndexFlatL2(self.dimension)
        self.index = self.faiss.IndexIVFPQ(self.quantizer, self.dimension, nlist, M, nbits, metric)
        
        # Eğitim için boş vektörler
        # Not: Gerçek veri ile eğitim daha sonra yapılacak
        empty_vectors = np.zeros((max(nlist * 10, 1000), self.dimension), dtype=np.float32)
        self.index.train(empty_vectors)
        
        # Arama parametresi
        self.index.nprobe = min(nlist, 10)  # Aramalarda incelenecek bölüm sayısı
        
        self.is_initialized = True
        self.is_trained_with_real_data = False
        logger.info(f"IVFPQ indeks başlatıldı: dim={self.dimension}, nlist={nlist}, M={M}, nbits={nbits}")
        
        # Vektör verilerini saklamak için numpy dizisi
        self.vectors = np.zeros((0, self.dimension), dtype=np.float32)

    def add_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekse ekler.
        
        Args:
            vector_ids: Eklenecek vektör ID'leri
            vectors: Eklenecek vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # Vektörleri numpy dizisine dönüştür
            vectors_array = np.array([v for v in vectors], dtype=np.float32)
            
            # ID'leri kaydet
            self._register_vectors(vector_ids, self.next_index)
            
            # Orijinal vektörleri sakla
            self.vectors = np.vstack((self.vectors, vectors_array.copy()))
            
            # Cosine benzerliği için normalizasyon
            if self.metric_type == "cosine":
                # Vektörleri normalize et
                norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
                vectors_array = vectors_array / np.maximum(norms, 1e-10)
            
            # Vektörleri indekse ekle
            self.index.add(vectors_array)
            
            # Eğer indeks henüz gerçek verilerle eğitilmediyse ve yeterli veri varsa
            if not self.is_trained_with_real_data and len(self.vectors) >= self.config.num_partitions:
                # Gerçek verilerle eğitilecek vektörleri hazırla
                train_vectors = self.vectors.copy()
                
                if self.metric_type == "cosine":
                    # Vektörleri normalize et
                    norms = np.linalg.norm(train_vectors, axis=1, keepdims=True)
                    train_vectors = train_vectors / np.maximum(norms, 1e-10)
                
                # İndeksi gerçek verilerle yeniden eğit
                self.index.reset()
                self.index.train(train_vectors)
                
                # Tüm vektörleri tekrar ekle
                if self.metric_type == "cosine":
                    self.index.add(train_vectors)
                else:
                    self.index.add(self.vectors)
                
                self.is_trained_with_real_data = True
                logger.info(f"IVFPQ indeks gerçek verilerle eğitildi: {len(self.vectors)} vektör")
            
            logger.info(f"IVFPQ indekse {len(vectors)} vektör eklendi")

    def update_vectors(self, vector_ids: List[str], vectors: List[np.ndarray]) -> None:
        """
        Vektörleri indekste günceller.
        
        Args:
            vector_ids: Güncellenecek vektör ID'leri
            vectors: Yeni vektörler
        """
        if not vectors:
            return
        
        with self.index_lock:
            # IVFPQ indeksinde doğrudan güncelleme yok
            # İndeksi yeniden oluşturmamız gerekiyor
            
            # Her vektörü güncelle
            updated_indices = []
            for vector_id, vector in zip(vector_ids, vectors):
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    updated_indices.append(idx)
                    
                    # Vektörü numpy dizisinde güncelle
                    self.vectors[idx] = vector
            
            if updated_indices:
                # Normalize edilmiş vektörleri hazırla
                normalized_vectors = self.vectors.copy()
                if self.metric_type == "cosine":
                    norms = np.linalg.norm(normalized_vectors, axis=1, keepdims=True)
                    normalized_vectors = normalized_vectors / np.maximum(norms, 1e-10)
                
                # İndeksi yeniden oluştur
                self.index.reset()
                self.index.train(normalized_vectors)
                self.index.add(normalized_vectors)
                logger.info(f"IVFPQ indekste {len(updated_indices)} vektör güncellendi (indeks yeniden oluşturuldu)")

    def delete_vectors(self, vector_ids: List[str]) -> None:
        """
        Vektörleri indeksten siler.
        
        Args:
            vector_ids: Silinecek vektör ID'leri
        """
        if not vector_ids:
            return
        
        with self.index_lock:
            # Silinecek indeksleri topla
            deleted_indices = []
            for vector_id in vector_ids:
                if vector_id in self.id_to_index:
                    idx = self.id_to_index[vector_id]
                    deleted_indices.append(idx)
                    # Mapping'lerden kaldır
                    del self.id_to_index[vector_id]
                    del self.index_to_id[idx]
            
            if deleted_indices:
                # Silinecek olmayan vektörleri seç
                mask = np.ones(len(self.vectors), dtype=bool)
                mask[deleted_indices] = False
                
                # Maskeyi uygula
                self.vectors = self.vectors[mask]
                
                # Mapping'leri güncelle
                self._rebuild_mappings()
                
                # İndeksi yeniden oluştur
                normalized_vectors = self.vectors.copy()
                if self.metric_type == "cosine":
                    norms = np.linalg.norm(normalized_vectors, axis=1, keepdims=True)
                    normalized_vectors = normalized_vectors / np.maximum(norms, 1e-10)
                
                self.index.reset()
                if len(self.vectors) > 0:
                    self.index.train(normalized_vectors)
                    self.index.add(normalized_vectors)
                
                logger.info(f"IVFPQ indeksten {len(deleted_indices)} vektör silindi (indeks yeniden oluşturuldu)")

    def query(self, query_vector: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları (vector_id ve distance içerir)
        """
        if len(self.vectors) == 0:
            return []
        
        with self.index_lock:
            # Sorgu vektörünü hazırla
            query = query_vector.reshape(1, -1).astype(np.float32)
            
            # Cosine benzerliği için normalize
            if self.metric_type == "cosine":
                query_norm = np.linalg.norm(query)
                if query_norm > 0:
                    query = query / query_norm
            
            # K değerini mevcut vektör sayısına göre sınırla
            actual_k = min(top_k, len(self.vectors))
            if actual_k == 0:
                return []
            
            # IVFPQ araması yap
            try:
                distances, indices = self.index.search(query, actual_k)
            except Exception as e:
                logger.error(f"IVFPQ arama hatası: {str(e)}")
                return []
            
            # Sonuçları oluştur
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1 and idx in self.index_to_id:  # -1, bulunamayan sonuçlar için
                    vector_id = self.index_to_id[idx]
                    
                    # Dot ürünü benzerliği mesafeye dönüştür
                    if self.metric_type == "dot":
                        # Dot product yüksek = düşük mesafe
                        distance = -distance
                    
                    results.append({
                        "vector_id": vector_id,
                        "distance": float(distance)
                    })
            
            return results

    def stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        with self.index_lock:
            return {
                "type": "ivfpq",
                "vector_count": len(self.vectors),
                "dimension": self.dimension,
                "metric_type": self.metric_type,
                "num_partitions": self.config.num_partitions,
                "nprobe": self.index.nprobe,
                "num_subvectors": self.config.num_subvectors,
                "bits_per_subvector": self.config.bits_per_subvector,
                "is_trained_with_real_data": self.is_trained_with_real_data,
                "memory_usage_mb": self.vectors.nbytes / 1024 / 1024
            }

    def _rebuild_mappings(self) -> None:
        """ID ve indeks eşleştirmelerini yeniden oluşturur."""
        # Yeni mapping'ler
        new_id_to_index = {}
        new_index_to_id = {}
        
        # Mevcut ID'leri al
        current_ids = list(self.id_to_index.keys())
        
        # Her ID için yeni indeks ata
        for new_idx, vector_id in enumerate(current_ids):
            new_id_to_index[vector_id] = new_idx
            new_index_to_id[new_idx] = vector_id
        
        # Mapping'leri güncelle
        self.id_to_index = new_id_to_index
        self.index_to_id = new_index_to_id
        self.next_index = len(self.vectors)