"""
Vector Store depolama işlemleri.
"""

import logging
import os
import pickle
import json
import time
import sqlite3
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def save_to_disk(vector_store) -> bool:
    """
    Vector store'u diske kaydeder.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    try:
        # Depolama dizini kontrolü
        storage_path = vector_store.config.storage_path
        if not storage_path:
            logger.error("Depolama yolu belirtilmemiş")
            return False
        
        # Koleksiyon dizini
        collection_dir = os.path.join(storage_path, vector_store.collection_name)
        os.makedirs(collection_dir, exist_ok=True)
        
        # Vektörler
        vectors_path = os.path.join(collection_dir, "vectors.npy")
        np.save(vectors_path, np.array(vector_store.vectors, dtype=np.float32))
        
        # ID'ler
        ids_path = os.path.join(collection_dir, "ids.pkl")
        with open(ids_path, "wb") as f:
            pickle.dump(vector_store.ids, f)
        
        # Metadata
        metadata_path = os.path.join(collection_dir, "metadata.pkl")
        with open(metadata_path, "wb") as f:
            pickle.dump(vector_store.metadata, f)
        
        # ID -> indeks eşlemesi
        id_to_index_path = os.path.join(collection_dir, "id_to_index.pkl")
        with open(id_to_index_path, "wb") as f:
            pickle.dump(vector_store.id_to_index, f)
        
        # Metadata indeksi
        metadata_index_path = os.path.join(collection_dir, "metadata_index.pkl")
        with open(metadata_index_path, "wb") as f:
            pickle.dump(vector_store.metadata_index, f)
        
        # Koleksiyon istatistikleri
        stats_path = os.path.join(collection_dir, "stats.json")
        with open(stats_path, "w") as f:
            json.dump(vector_store.collection_stats, f, indent=2)
        
        # İndeksi kaydet (indeks tipine bağlı)
        from ModularMind.API.services.retrieval.vector_models import IndexType
        if vector_store.config.index_type == IndexType.HNSW and vector_store.index:
            index_path = os.path.join(collection_dir, "hnsw_index.bin")
            vector_store.index.save_index(index_path)
        
        # Son kayıt zamanını güncelle
        vector_store.last_saved = time.time()
        
        # Değişiklik bayrağını temizle
        vector_store.is_dirty = False
        
        logger.info(f"Vector store diske kaydedildi: {collection_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Diske kaydetme hatası: {str(e)}", exc_info=True)
        return False

def load_from_disk(vector_store) -> bool:
    """
    Vector store'u diskten yükler.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    try:
        # Depolama dizini kontrolü
        storage_path = vector_store.config.storage_path
        if not storage_path:
            logger.error("Depolama yolu belirtilmemiş")
            return False
        
        # Koleksiyon dizini
        collection_dir = os.path.join(storage_path, vector_store.collection_name)
        if not os.path.exists(collection_dir):
            logger.warning(f"Koleksiyon dizini bulunamadı: {collection_dir}")
            return False
        
        # Vektörler
        vectors_path = os.path.join(collection_dir, "vectors.npy")
        if os.path.exists(vectors_path):
            vector_store.vectors = np.load(vectors_path).tolist()
        else:
            logger.warning(f"Vektör dosyası bulunamadı: {vectors_path}")
            return False
        
        # ID'ler
        ids_path = os.path.join(collection_dir, "ids.pkl")
        if os.path.exists(ids_path):
            with open(ids_path, "rb") as f:
                vector_store.ids = pickle.load(f)
        else:
            logger.warning(f"ID dosyası bulunamadı: {ids_path}")
            return False
        
        # Metadata
        metadata_path = os.path.join(collection_dir, "metadata.pkl")
        if os.path.exists(metadata_path):
            with open(metadata_path, "rb") as f:
                vector_store.metadata = pickle.load(f)
        else:
            logger.warning(f"Metadata dosyası bulunamadı: {metadata_path}")
            return False
        
        # ID -> indeks eşlemesi
        id_to_index_path = os.path.join(collection_dir, "id_to_index.pkl")
        if os.path.exists(id_to_index_path):
            with open(id_to_index_path, "rb") as f:
                vector_store.id_to_index = pickle.load(f)
        else:
            # Yeniden oluştur
            vector_store.id_to_index = {chunk_id: idx for idx, chunk_id in enumerate(vector_store.ids)}
        
        # Metadata indeksi
        metadata_index_path = os.path.join(collection_dir, "metadata_index.pkl")
        if os.path.exists(metadata_index_path):
            with open(metadata_index_path, "rb") as f:
                vector_store.metadata_index = pickle.load(f)
        else:
            # Yeniden oluştur
            from ModularMind.API.services.retrieval.metadata_index import build_metadata_index
            build_metadata_index(vector_store)
        
        # Koleksiyon istatistikleri
        stats_path = os.path.join(collection_dir, "stats.json")
        if os.path.exists(stats_path):
            with open(stats_path, "r") as f:
                vector_store.collection_stats = json.load(f)
        else:
            # Yeniden hesapla
            vector_store.collection_stats = {
                "total_chunks": len(vector_store.ids),
                "total_documents": len(set(m.get("document_id") for m in vector_store.metadata if m and "document_id" in m)),
                "dimensions": vector_store.config.dimensions,
                "size_bytes": 0,
                "creation_time": time.time(),
                "last_update": time.time()
            }
        
        # İndeksi yükle (indeks tipine bağlı)
        from ModularMind.API.services.retrieval.vector_models import IndexType
        if vector_store.config.index_type == IndexType.HNSW:
            try:
                import hnswlib
                index_path = os.path.join(collection_dir, "hnsw_index.bin")
                
                if os.path.exists(index_path):
                    # İndeksi yeni oluştur
                    index = hnswlib.Index(space=vector_store.config.similarity_function, dim=vector_store.config.dimensions)
                    
                    # Yükleme için maksimum eleman sayısını belirle
                    index.load_index(index_path, max_elements=len(vector_store.vectors))
                    
                    # Arama parametresini ayarla
                    index.set_ef(vector_store.config.hnsw_ef_search)
                    
                    vector_store.index = index
                else:
                    # Disk indeksi yoksa bellek indeksi oluştur
                    from ModularMind.API.services.retrieval.indices import _initialize_hnsw_index, _update_hnsw_index
                    
                    # İndeksi başlat
                    _initialize_hnsw_index(vector_store)
                    
                    # Vektörleri ekle
                    _update_hnsw_index(vector_store, vector_store.vectors, list(range(len(vector_store.vectors))))
            except Exception as e:
                logger.error(f"HNSW indeksi yükleme hatası: {str(e)}", exc_info=True)
                
                # Düz indekse geri dön
                vector_store.config.index_type = IndexType.FLAT
                vector_store.index = None
        else:
            # Diğer indeks tipleri için yeniden oluştur
            from ModularMind.API.services.retrieval.indices import _rebuild_index
            _rebuild_index(vector_store)
        
        # Son kayıt zamanını güncelle
        vector_store.last_saved = time.time()
        
        # Değişiklik bayrağını temizle
        vector_store.is_dirty = False
        
        logger.info(f"Vector store diskten yüklendi: {collection_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Diskten yükleme hatası: {str(e)}", exc_info=True)
        return False

def save_to_sqlite(vector_store) -> bool:
    """
    Vector store'u SQLite veritabanına kaydeder.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    try:
        # Depolama dizini kontrolü
        storage_path = vector_store.config.storage_path
        if not storage_path:
            logger.error("Depolama yolu belirtilmemiş")
            return False
        
        # Veritabanı dosya yolu
        os.makedirs(storage_path, exist_ok=True)
        db_path = os.path.join(storage_path, f"{vector_store.collection_name}.db")
        
        # Veritabanı bağlantısı
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tablolar oluştur
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vectors (
            id TEXT PRIMARY KEY,
            vector BLOB,
            metadata TEXT,
            document_id TEXT,
            chunk_index INTEGER
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS collection_info (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        ''')
        
        # Mevcut verileri temizle
        cursor.execute("DELETE FROM vectors")
        cursor.execute("DELETE FROM collection_info")
        
        # Verileri ekle
        for idx, chunk_id in enumerate(vector_store.ids):
            vector_bytes = pickle.dumps(vector_store.vectors[idx])
            metadata_json = json.dumps(vector_store.metadata[idx] or {})
            
            # Belge ID'sini al
            document_id = None
            if vector_store.metadata[idx] and "document_id" in vector_store.metadata[idx]:
                document_id = vector_store.metadata[idx]["document_id"]
            
            # Vektörü ekle
            cursor.execute(
                "INSERT INTO vectors (id, vector, metadata, document_id, chunk_index) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, vector_bytes, metadata_json, document_id, idx)
            )
        
        # Koleksiyon bilgilerini ekle
        cursor.execute(
            "INSERT INTO collection_info (key, value) VALUES (?, ?)",
            ("stats", json.dumps(vector_store.collection_stats))
        )
        
        cursor.execute(
            "INSERT INTO collection_info (key, value) VALUES (?, ?)",
            ("dimensions", str(vector_store.config.dimensions))
        )
        
        cursor.execute(
            "INSERT INTO collection_info (key, value) VALUES (?, ?)",
            ("index_type", vector_store.config.index_type)
        )
        
        cursor.execute(
            "INSERT INTO collection_info (key, value) VALUES (?, ?)",
            ("similarity_function", vector_store.config.similarity_function)
        )
        
        # Değişiklikleri kaydet
        conn.commit()
        
        # Bağlantıyı kapat
        conn.close()
        
        # Son kayıt zamanını güncelle
        vector_store.last_saved = time.time()
        
        # Değişiklik bayrağını temizle
        vector_store.is_dirty = False
        
        logger.info(f"Vector store SQLite'a kaydedildi: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"SQLite'a kaydetme hatası: {str(e)}", exc_info=True)
        return False

def load_from_sqlite(vector_store) -> bool:
    """
    Vector store'u SQLite veritabanından yükler.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    try:
        # Depolama dizini kontrolü
        storage_path = vector_store.config.storage_path
        if not storage_path:
            logger.error("Depolama yolu belirtilmemiş")
            return False
        
        # Veritabanı dosya yolu
        db_path = os.path.join(storage_path, f"{vector_store.collection_name}.db")
        if not os.path.exists(db_path):
            logger.warning(f"Veritabanı dosyası bulunamadı: {db_path}")
            return False
        
        # Veritabanı bağlantısı
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Koleksiyon bilgilerini yükle
        cursor.execute("SELECT key, value FROM collection_info")
        info_rows = cursor.fetchall()
        
        # Bilgileri işle
        for key, value in info_rows:
            if key == "stats":
                vector_store.collection_stats = json.loads(value)
            elif key == "dimensions":
                vector_store.config.dimensions = int(value)
            elif key == "index_type":
                vector_store.config.index_type = value
            elif key == "similarity_function":
                vector_store.config.similarity_function = value
        
        # Vektörleri yükle
        cursor.execute("SELECT id, vector, metadata, document_id, chunk_index FROM vectors ORDER BY chunk_index")
        rows = cursor.fetchall()
        
        # Veri yapılarını temizle
        vector_store.vectors = []
        vector_store.ids = []
        vector_store.metadata = []
        vector_store.id_to_index = {}
        
        # Verileri işle
        for idx, (chunk_id, vector_bytes, metadata_json, document_id, chunk_index) in enumerate(rows):
            # Vektörü çöz
            vector = pickle.loads(vector_bytes)
            
            # Metadata'yı çöz
            metadata = json.loads(metadata_json)
            
            # Veri yapılarını güncelle
            vector_store.vectors.append(vector)
            vector_store.ids.append(chunk_id)
            vector_store.metadata.append(metadata)
            vector_store.id_to_index[chunk_id] = idx
        
        # Bağlantıyı kapat
        conn.close()
        
        # Metadata indeksini oluştur
        from ModularMind.API.services.retrieval.metadata_index import build_metadata_index
        build_metadata_index(vector_store)
        
        # İndeksi yeniden oluştur
        from ModularMind.API.services.retrieval.indices import _rebuild_index
        _rebuild_index(vector_store)
        
        # Son kayıt zamanını güncelle
        vector_store.last_saved = time.time()
        
        # Değişiklik bayrağını temizle
        vector_store.is_dirty = False
        
        logger.info(f"Vector store SQLite'dan yüklendi: {db_path}")
        return True
        
    except Exception as e:
        logger.error(f"SQLite'dan yükleme hatası: {str(e)}", exc_info=True)
        return False

def save_to_postgres(vector_store) -> bool:
    """
    Vector store'u PostgreSQL veritabanına kaydeder.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    # Bu fonksiyon, gerçek uygulamada özelleştirilmelidir
    logger.error("PostgreSQL desteği henüz uygulanmadı")
    return False

def load_from_postgres(vector_store) -> bool:
    """
    Vector store'u PostgreSQL veritabanından yükler.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        bool: Başarı durumu
    """
    # Bu fonksiyon, gerçek uygulamada özelleştirilmelidir
    logger.error("PostgreSQL desteği henüz uygulanmadı")
    return False