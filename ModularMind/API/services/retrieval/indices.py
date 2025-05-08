"""
Vektör indeksleme işlevleri - Çoklu model desteği eklendi.
"""

import logging
import os
import json
import pickle
import numpy as np
import time
from typing import Dict, List, Any, Optional, Tuple

from ModularMind.API.services.retrieval.models import (
    VectorStore, 
    Document, 
    DocumentChunk, 
    IndexType,
    get_unique_document_ids
)

logger = logging.getLogger(__name__)

def _create_hnsw_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    HNSW indeksi oluşturur.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    try:
        import hnswlib
        
        # Dosya yolu kontrol et
        if not vector_store.config.storage_path:
            logger.error("HNSW indeksi için storage_path gereklidir")
            return False
        
        # Model için boyutu al
        if model_id not in vector_store.config.dimensions:
            logger.error(f"Model için boyut bulunamadı: {model_id}")
            return False
        
        dim = vector_store.config.dimensions[model_id]
        
        # Model için vektörleri kontrol et
        embeddings_exist = False
        for chunk in vector_store.document_chunks.values():
            if chunk.has_embedding(model_id):
                embeddings_exist = True
                break
        
        if not embeddings_exist:
            logger.warning(f"Bu model için embedding yok: {model_id}")
            return False
        
        # HNSW parametreleri
        hnsw_params = vector_store.config.hnsw_params
        ef_construction = hnsw_params.get("ef_construction", 200)
        M = hnsw_params.get("M", 16)
        ef_search = hnsw_params.get("ef_search", 50)
        
        # Vektörleri ve ID'leri al
        vectors = []
        ids = []
        
        for chunk_id, chunk in vector_store.document_chunks.items():
            embedding = chunk.get_embedding(model_id)
            if embedding is not None:
                vectors.append(embedding)
                ids.append(int(hash(chunk_id)) % (2**31))
        
        if not vectors:
            logger.warning(f"İndeks oluşturmak için {model_id} modeli için vektör yok")
            return False
        
        # HNSW indeksi oluştur
        index = hnswlib.Index(space=vector_store.config.metric, dim=dim)
        index.init_index(max_elements=len(vectors) * 2, ef_construction=ef_construction, M=M)
        index.set_ef(ef_search)
        
        # Vektörleri ekle
        index.add_items(np.array(vectors), ids)
        
        # ID eşleştirme sözlüğünü kaydet
        id_map = {ids[i]: list(chunk_id for chunk_id, chunk in vector_store.document_chunks.items() 
                              if chunk.has_embedding(model_id))[i] for i in range(len(ids))}
        
        # İndeks klasörünü oluştur
        model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
        os.makedirs(model_folder, exist_ok=True)
        
        # İndeksi kaydet
        index_path = os.path.join(model_folder, "hnsw_index.bin")
        id_map_path = os.path.join(model_folder, "id_map.pkl")
        
        index.save_index(index_path)
        
        with open(id_map_path, "wb") as f:
            pickle.dump(id_map, f)
        
        # İndeksi vector_store'a kaydet
        if model_id not in vector_store.indices:
            vector_store.indices[model_id] = {}
        
        vector_store.indices[model_id] = index
        
        if model_id not in vector_store.id_maps:
            vector_store.id_maps[model_id] = {}
            
        vector_store.id_maps[model_id] = id_map
        
        return True
        
    except ImportError:
        logger.error("hnswlib kütüphanesi bulunamadı")
        return False
    except Exception as e:
        logger.error(f"HNSW indeksi oluşturma hatası ({model_id}): {str(e)}")
        return False

def _create_faiss_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    FAISS indeksi oluşturur.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    try:
        import faiss
        
        # Dosya yolu kontrol et
        if not vector_store.config.storage_path:
            logger.error("FAISS indeksi için storage_path gereklidir")
            return False
        
        # Model için boyutu al
        if model_id not in vector_store.config.dimensions:
            logger.error(f"Model için boyut bulunamadı: {model_id}")
            return False
        
        dim = vector_store.config.dimensions[model_id]
        
        # Model için vektörleri kontrol et
        embeddings_exist = False
        for chunk in vector_store.document_chunks.values():
            if chunk.has_embedding(model_id):
                embeddings_exist = True
                break
        
        if not embeddings_exist:
            logger.warning(f"Bu model için embedding yok: {model_id}")
            return False
        
        # Vektörleri ve ID'leri al
        vectors = []
        ids = []
        
        for chunk_id, chunk in vector_store.document_chunks.items():
            embedding = chunk.get_embedding(model_id)
            if embedding is not None:
                vectors.append(embedding)
                ids.append(int(hash(chunk_id)) % (2**31))
        
        if not vectors:
            logger.warning(f"İndeks oluşturmak için {model_id} modeli için vektör yok")
            return False
        
        # FAISS indeksi oluştur
        if vector_store.config.metric == "cosine":
            # Kosinüs benzerliği için vektörleri normalize et
            vectors_normalized = np.array(vectors, dtype=np.float32)
            faiss.normalize_L2(vectors_normalized)
            index = faiss.IndexFlatIP(dim)  # İç çarpım
        elif vector_store.config.metric == "l2":
            # L2 mesafesi için direkt Euclidean
            vectors_normalized = np.array(vectors, dtype=np.float32)
            index = faiss.IndexFlatL2(dim)
        else:
            # Varsayılan olarak L2
            vectors_normalized = np.array(vectors, dtype=np.float32)
            index = faiss.IndexFlatL2(dim)
        
        # ID eşleştirme için faiss.IndexIDMap oluştur
        id_map_index = faiss.IndexIDMap(index)
        id_map_index.add_with_ids(vectors_normalized, np.array(ids, dtype=np.int64))
        
        # ID eşleştirme sözlüğünü kaydet
        id_map = {ids[i]: list(chunk_id for chunk_id, chunk in vector_store.document_chunks.items() 
                              if chunk.has_embedding(model_id))[i] for i in range(len(ids))}
        
        # İndeks klasörünü oluştur
        model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
        os.makedirs(model_folder, exist_ok=True)
        
        # İndeksi kaydet
        index_path = os.path.join(model_folder, "faiss_index.bin")
        id_map_path = os.path.join(model_folder, "id_map.pkl")
        
        faiss.write_index(id_map_index, index_path)
        
        with open(id_map_path, "wb") as f:
            pickle.dump(id_map, f)
        
        # İndeksi vector_store'a kaydet
        if model_id not in vector_store.indices:
            vector_store.indices[model_id] = {}
            
        vector_store.indices[model_id] = id_map_index
        
        if model_id not in vector_store.id_maps:
            vector_store.id_maps[model_id] = {}
            
        vector_store.id_maps[model_id] = id_map
        
        return True
        
    except ImportError:
        logger.error("faiss-cpu kütüphanesi bulunamadı")
        return False
    except Exception as e:
        logger.error(f"FAISS indeksi oluşturma hatası ({model_id}): {str(e)}")
        return False

def _load_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    Mevcut indeksi yükler.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    if not vector_store.config.storage_path:
        logger.error("İndeks yüklemek için storage_path gereklidir")
        return False
    
    # Model klasörü
    model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
    if not os.path.exists(model_folder):
        logger.warning(f"İndeks klasörü bulunamadı: {model_id}")
        return False
    
    # ID eşleştirme dosyası
    id_map_path = os.path.join(model_folder, "id_map.pkl")
    
    # ID eşleştirmeyi yükle
    if os.path.exists(id_map_path):
        try:
            with open(id_map_path, "rb") as f:
                id_map = pickle.load(f)
                
            if model_id not in vector_store.id_maps:
                vector_store.id_maps[model_id] = {}
                
            vector_store.id_maps[model_id] = id_map
        except Exception as e:
            logger.error(f"ID eşleştirme yükleme hatası ({model_id}): {str(e)}")
            return False
    else:
        logger.warning(f"ID eşleştirme dosyası bulunamadı: {model_id}")
        return False
    
    # İndeks tipine göre yükleme
    if vector_store.config.index_type == IndexType.HNSW:
        return _load_hnsw_index(vector_store, model_id)
    elif vector_store.config.index_type == IndexType.FAISS:
        return _load_faiss_index(vector_store, model_id)
    else:
        logger.error(f"Desteklenmeyen indeks tipi: {vector_store.config.index_type}")
        return False

def _load_hnsw_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    HNSW indeksini yükler.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    try:
        import hnswlib
        
        # Model klasörü ve indeks dosyası
        model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
        index_path = os.path.join(model_folder, "hnsw_index.bin")
        
        if not os.path.exists(index_path):
            logger.warning(f"HNSW indeks dosyası bulunamadı: {model_id}")
            return False
        
        # Model için boyutu al
        if model_id not in vector_store.config.dimensions:
            logger.error(f"Model için boyut bulunamadı: {model_id}")
            return False
        
        dim = vector_store.config.dimensions[model_id]
        
        # HNSW parametreleri
        hnsw_params = vector_store.config.hnsw_params
        ef_search = hnsw_params.get("ef_search", 50)
        
        # HNSW indeksi oluştur
        index = hnswlib.Index(space=vector_store.config.metric, dim=dim)
        
        # İndeksi yükle
        index.load_index(index_path)
        index.set_ef(ef_search)
        
        # İndeksi vector_store'a kaydet
        if model_id not in vector_store.indices:
            vector_store.indices[model_id] = {}
            
        vector_store.indices[model_id] = index
        
        return True
        
    except ImportError:
        logger.error("hnswlib kütüphanesi bulunamadı")
        return False
    except Exception as e:
        logger.error(f"HNSW indeksi yükleme hatası ({model_id}): {str(e)}")
        return False

def _load_faiss_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    FAISS indeksini yükler.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    try:
        import faiss
        
        # Model klasörü ve indeks dosyası
        model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
        index_path = os.path.join(model_folder, "faiss_index.bin")
        
        if not os.path.exists(index_path):
            logger.warning(f"FAISS indeks dosyası bulunamadı: {model_id}")
            return False
        
        # İndeksi yükle
        index = faiss.read_index(index_path)
        
        # İndeksi vector_store'a kaydet
        if model_id not in vector_store.indices:
            vector_store.indices[model_id] = {}
            
        vector_store.indices[model_id] = index
        
        return True
        
    except ImportError:
        logger.error("faiss-cpu kütüphanesi bulunamadı")
        return False
    except Exception as e:
        logger.error(f"FAISS indeksi yükleme hatası ({model_id}): {str(e)}")
        return False

def create_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    Vektör indeksi oluşturur.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    # İndeks tipine göre oluşturma
    if vector_store.config.index_type == IndexType.HNSW:
        return _create_hnsw_index(vector_store, model_id)
    elif vector_store.config.index_type == IndexType.FAISS:
        return _create_faiss_index(vector_store, model_id)
    else:
        logger.error(f"Desteklenmeyen indeks tipi: {vector_store.config.index_type}")
        return False

def load_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    Mevcut indeksi yükler.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    return _load_index(vector_store, model_id)

def rebuild_index(vector_store: VectorStore, model_id: str) -> bool:
    """
    İndeksi yeniden oluşturur.
    
    Args:
        vector_store: Vektör deposu
        model_id: Embedding model ID'si
        
    Returns:
        bool: Başarı durumu
    """
    # Model klasörü ve indeks dosyalarını kaldır
    if vector_store.config.storage_path:
        model_folder = os.path.join(vector_store.config.storage_path, "indices", model_id)
        
        if os.path.exists(model_folder):
            index_files = [
                os.path.join(model_folder, "hnsw_index.bin"),
                os.path.join(model_folder, "faiss_index.bin"),
                os.path.join(model_folder, "id_map.pkl")
            ]
            
            for file_path in index_files:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"İndeks dosyası silme hatası: {str(e)}")
    
    # Yeni indeks oluştur
    return create_index(vector_store, model_id)

def search_index(
    vector_store: VectorStore, 
    query_vector: List[float], 
    model_id: str,
    limit: int = 5, 
    min_score_threshold: Optional[float] = None
) -> List[Tuple[str, float]]:
    """
    Vektör indeksinde arama yapar.
    
    Args:
        vector_store: Vektör deposu
        query_vector: Sorgu vektörü
        model_id: Embedding model ID'si
        limit: Sonuç limiti
        min_score_threshold: Minimum skor eşiği
        
    Returns:
        List[Tuple[str, float]]: (chunk_id, score) çiftleri
    """
    # Model kontrolü
    if model_id not in vector_store.indices:
        logger.error(f"Arama için model indeksi yüklenmemiş: {model_id}")
        return []
    
    # ID eşleştirme kontrolü
    if model_id not in vector_store.id_maps:
        logger.error(f"Arama için model ID eşleştirmesi yüklenmemiş: {model_id}")
        return []
    
    try:
        # İndeks tipine göre arama
        if vector_store.config.index_type == IndexType.HNSW:
            return _search_hnsw(vector_store, query_vector, model_id, limit, min_score_threshold)
        elif vector_store.config.index_type == IndexType.FAISS:
            return _search_faiss(vector_store, query_vector, model_id, limit, min_score_threshold)
        else:
            logger.error(f"Desteklenmeyen indeks tipi: {vector_store.config.index_type}")
            return []
    except Exception as e:
        logger.error(f"İndeks arama hatası ({model_id}): {str(e)}")
        return []

def _search_hnsw(
    vector_store: VectorStore, 
    query_vector: List[float], 
    model_id: str,
    limit: int = 5, 
    min_score_threshold: Optional[float] = None
) -> List[Tuple[str, float]]:
    """
    HNSW indeksinde arama yapar.
    
    Args:
        vector_store: Vektör deposu
        query_vector: Sorgu vektörü
        model_id: Embedding model ID'si
        limit: Sonuç limiti
        min_score_threshold: Minimum skor eşiği
        
    Returns:
        List[Tuple[str, float]]: (chunk_id, score) çiftleri
    """
    # HNSW indeksi ve ID eşleştirme
    index = vector_store.indices[model_id]
    id_map = vector_store.id_maps[model_id]
    
    # Sorgu vektörünü numpy dizisine dönüştür
    query_vector_np = np.array(query_vector, dtype=np.float32)
    
    # HNSW arama
    ids, distances = index.knn_query(query_vector_np, k=limit)
    
    # Sonuçları dönüştür
    results = []
    
    for i in range(len(ids[0])):
        idx = ids[0][i]
        distance = distances[0][i]
        
        # ID eşleştirme ile chunk_id bul
        if idx in id_map:
            chunk_id = id_map[idx]
            
            # Mesafeyi benzerlik skoruna dönüştür (0-1 aralığı)
            if vector_store.config.metric == "cosine":
                # Kosinüs mesafesi için 1 - distance / 2 (1 en benzer)
                score = 1.0 - distance / 2.0
            elif vector_store.config.metric == "l2":
                # L2 mesafesi için e^(-distance) (1 en benzer)
                score = np.exp(-distance)
            else:
                # Varsayılan olarak doğrudan 1 - normalize(distance)
                score = 1.0 - min(1.0, distance / 10.0)
            
            # Minimum skor eşiği kontrolü
            if min_score_threshold is not None and score < min_score_threshold:
                continue
            
            results.append((chunk_id, score))
    
    return results

def _search_faiss(
    vector_store: VectorStore, 
    query_vector: List[float], 
    model_id: str,
    limit: int = 5, 
    min_score_threshold: Optional[float] = None
) -> List[Tuple[str, float]]:
    """
    FAISS indeksinde arama yapar.
    
    Args:
        vector_store: Vektör deposu
        query_vector: Sorgu vektörü
        model_id: Embedding model ID'si
        limit: Sonuç limiti
        min_score_threshold: Minimum skor eşiği
        
    Returns:
        List[Tuple[str, float]]: (chunk_id, score) çiftleri
    """
    import faiss
    
    # FAISS indeksi ve ID eşleştirme
    index = vector_store.indices[model_id]
    id_map = vector_store.id_maps[model_id]
    
    # Sorgu vektörünü numpy dizisine dönüştür
    query_vector_np = np.array([query_vector], dtype=np.float32)
    
    # Kosinüs benzerliği için normalize et
    if vector_store.config.metric == "cosine":
        faiss.normalize_L2(query_vector_np)
    
    # FAISS arama
    distances, ids = index.search(query_vector_np, limit)
    
    # Sonuçları dönüştür
    results = []
    
    for i in range(len(ids[0])):
        idx = ids[0][i]
        distance = distances[0][i]
        
        # Geçersiz ID'leri atla
        if idx == -1:
            continue
        
        # ID eşleştirme ile chunk_id bul
        if idx in id_map:
            chunk_id = id_map[idx]
            
            # Mesafeyi benzerlik skoruna dönüştür (0-1 aralığı)
            if vector_store.config.metric == "cosine":
                # İç çarpım zaten benzerlik (-1 ile 1 arasında)
                # 0-1 aralığına normalize et
                score = (distance + 1.0) / 2.0
            elif vector_store.config.metric == "l2":
                # L2 mesafesi için e^(-distance) (1 en benzer)
                score = np.exp(-distance)
            else:
                # Varsayılan olarak doğrudan 1 - normalize(distance)
                score = 1.0 - min(1.0, distance / 10.0)
            
            # Minimum skor eşiği kontrolü
            if min_score_threshold is not None and score < min_score_threshold:
                continue
            
            results.append((chunk_id, score))
    
    return results