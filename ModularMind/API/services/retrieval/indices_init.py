"""
Vector Store indeks başlatma fonksiyonları.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

def _rebuild_index(vector_store) -> None:
    """
    İndeksi yeniden oluşturur.
    
    Args:
        vector_store: Vector store nesnesi
    """
    from ModularMind.API.services.retrieval.vector_models import IndexType
    
    # İndeks tipine göre yeniden oluştur
    if vector_store.config.index_type == IndexType.FLAT:
        # Düz indeks için özel bir işlem yapmaya gerek yok
        pass
        
    elif vector_store.config.index_type == IndexType.HNSW:
        _initialize_hnsw_index(vector_store)
        if vector_store.vectors:
            _update_hnsw_index(vector_store, vector_store.vectors, list(range(len(vector_store.vectors))))
        
    elif vector_store.config.index_type in [IndexType.IVF, IndexType.IVF_FLAT, IndexType.IVF_PQ]:
        _initialize_ivf_index(vector_store)
        if vector_store.vectors:
            _update_ivf_index(vector_store, vector_store.vectors, list(range(len(vector_store.vectors))))
        
    elif vector_store.config.index_type == IndexType.FAISS:
        _initialize_faiss_index(vector_store)
        if vector_store.vectors:
            _update_faiss_index(vector_store, vector_store.vectors, list(range(len(vector_store.vectors))))
    
    # Harici indeksler için özel işlem gerekebilir ama burada atlanmıştır

def delete_from_external_index(vector_store, chunk_id: str) -> None:
    """
    Harici indeksten bir chunk'ı siler.
    
    Args:
        vector_store: Vector store nesnesi
        chunk_id: Silinecek chunk ID'si
    """
    from ModularMind.API.services.retrieval.vector_models import IndexType
    
    try:
        if vector_store.config.index_type == IndexType.QDRANT:
            # Qdrant'dan sil
            if vector_store.index:
                vector_store.index.delete(
                    collection_name=vector_store.collection_name,
                    points_selector=[chunk_id]
                )
                
        elif vector_store.config.index_type == IndexType.PINECONE:
            # Pinecone'dan sil
            if vector_store.index:
                vector_store.index.delete(ids=[chunk_id])
                
        elif vector_store.config.index_type == IndexType.WEAVIATE:
            # Weaviate'den sil
            if vector_store.index:
                class_name = vector_store.config.collection_name
                vector_store.index.data_object.delete(
                    class_name=class_name,
                    uuid=chunk_id
                )
                
        elif vector_store.config.index_type == IndexType.MILVUS:
            # Milvus'tan sil
            # Burada gerçek implementasyon gerekir
            pass
    
    except Exception as e:
        logger.error(f"Harici indeksten silme hatası: {str(e)}")