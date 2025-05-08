"""
Vector Store vektör işlemleri.
Temel vektör ekleme, güncelleme ve silme fonksiyonları içerir.
"""

import logging
import uuid
import numpy as np
from typing import List, Dict, Any, Optional, Set

from ModularMind.API.services.retrieval.models import Chunk
from ModularMind.API.services.retrieval.indices import _rebuild_index

logger = logging.getLogger(__name__)

def add_chunk(vector_store, chunk: Chunk) -> None:
    """
    Tek bir chunk ekler.
    
    Args:
        vector_store: Vector store nesnesi
        chunk: Eklenecek parça
    """
    with vector_store.lock:
        # ID kontrolü
        if not chunk.id:
            chunk.id = str(uuid.uuid4())
        
        # Zaten mevcut mu kontrol et
        if chunk.id in vector_store.id_to_index:
            # Güncelle
            update_chunk(vector_store, chunk)
            return
        
        # Gömme vektörü kontrol et/hesapla
        if chunk.embedding is None and vector_store.embedding_service:
            chunk.embedding = vector_store.embedding_service.get_embedding(chunk.text)
        
        if chunk.embedding is None:
            logger.error(f"Embedding bulunamadı ve hesaplanamadı: {chunk.id}")
            return
        
        # Vektörü ekle
        vector_store.vectors.append(chunk.embedding)
        
        # ID'yi ekle
        vector_store.ids.append(chunk.id)
        
        # Metadata'yı ekle
        vector_store.metadata.append(chunk.metadata)
        
        # ID -> indeks eşlemesini güncelle
        vector_store.id_to_index[chunk.id] = len(vector_store.ids) - 1
        
        # Metadata indeksini güncelle
        if vector_store.config.metadata_index_type != "none":
            update_metadata_index(vector_store, chunk.id, chunk.metadata)
        
        # İndeksi güncelle
        update_index(vector_store, [chunk.embedding], [len(vector_store.ids) - 1])
        
        # Koleksiyon istatistiklerini güncelle
        vector_store.collection_stats["total_chunks"] += 1
        
        # Belge ID'sine göre document sayısını güncelle
        if chunk.document_id and chunk.document_id not in get_unique_document_ids(vector_store):
            vector_store.collection_stats["total_documents"] += 1
        
        # Değişiklik bayrağını ayarla
        vector_store.is_dirty = True

def add_batch_chunks(vector_store, chunks: List[Chunk]) -> None:
    """
    Toplu chunk ekler.
    
    Args:
        vector_store: Vector store nesnesi
        chunks: Eklenecek parçalar
    """
    if not chunks:
        return
        
    with vector_store.lock:
        # Yeni ve güncellenecek chunk'ları ayır
        new_chunks = []
        update_chunks = []
        
        for chunk in chunks:
            # ID kontrolü
            if not chunk.id:
                chunk.id = str(uuid.uuid4())
            
            # Zaten mevcut mu kontrol et
            if chunk.id in vector_store.id_to_index:
                update_chunks.append(chunk)
            else:
                new_chunks.append(chunk)
        
        # Önce güncellemeleri yap
        if update_chunks:
            for chunk in update_chunks:
                update_chunk(vector_store, chunk)
        
        # Yeni chunk'lar yoksa bitir
        if not new_chunks:
            return
        
        # Eksik embeddinglwri toplu hesapla
        chunks_without_embedding = [c for c in new_chunks if c.embedding is None]
        if chunks_without_embedding and vector_store.embedding_service:
            texts = [c.text for c in chunks_without_embedding]
            embeddings = vector_store.embedding_service.get_embeddings(texts)
            
            # Embedding'leri eşle
            for i, chunk in enumerate(chunks_without_embedding):
                chunk.embedding = embeddings[i]
        
        # Embedding'i olmayanları filtrele
        valid_chunks = [c for c in new_chunks if c.embedding is not None]
        
        if not valid_chunks:
            logger.warning("Geçerli embeddingi olan chunk bulunamadı")
            return
        
        # Yeni başlangıç indeksi
        start_index = len(vector_store.ids)
        
        # Verileri ekle
        for chunk in valid_chunks:
            vector_store.vectors.append(chunk.embedding)
            vector_store.ids.append(chunk.id)
            vector_store.metadata.append(chunk.metadata)
            vector_store.id_to_index[chunk.id] = start_index + len(vector_store.id_to_index)
            
            # Metadata indeksi güncelle
            if vector_store.config.metadata_index_type != "none":
                update_metadata_index(vector_store, chunk.id, chunk.metadata)
        
        # İndeksi toplu güncelle
        vectors_to_add = [c.embedding for c in valid_chunks]
        indices = list(range(start_index, start_index + len(valid_chunks)))
        update_index(vector_store, vectors_to_add, indices)
        
        # İstatistikleri güncelle
        vector_store.collection_stats["total_chunks"] += len(valid_chunks)
        
        # Belge sayısını güncelle
        unique_docs = set()
        for chunk in valid_chunks:
            if chunk.document_id:
                unique_docs.add(chunk.document_id)
        
        # Mevcut belge ID'lerini çıkar
        existing_docs = get_unique_document_ids(vector_store)
        new_docs = [doc_id for doc_id in unique_docs if doc_id not in existing_docs]
        
        vector_store.collection_stats["total_documents"] += len(new_docs)
        
        # Değişiklik bayrağını ayarla
        vector_store.is_dirty = True

def update_chunk(vector_store, chunk: Chunk) -> None:
    """
    Mevcut bir chunk'ı günceller.
    
    Args:
        vector_store: Vector store nesnesi
        chunk: Güncellenecek parça
    """
    with vector_store.lock:
        # ID kontrolü
        if not chunk.id or chunk.id not in vector_store.id_to_index:
            logger.warning(f"Güncellenecek chunk bulunamadı: {chunk.id}")
            return
        
        # Indeksi al
        index = vector_store.id_to_index[chunk.id]
        
        # Gömme vektörü kontrol et/hesapla
        if chunk.embedding is None and vector_store.embedding_service:
            chunk.embedding = vector_store.embedding_service.get_embedding(chunk.text)
        
        if chunk.embedding is None:
            logger.error(f"Embedding bulunamadı ve hesaplanamadı: {chunk.id}")
            return
        
        # Vektörü güncelle
        vector_store.vectors[index] = chunk.embedding
        
        # Metadata'yı güncelle
        vector_store.metadata[index] = chunk.metadata
        
        # Metadata indeksini güncelle
        if vector_store.config.metadata_index_type != "none":
            update_metadata_index(vector_store, chunk.id, chunk.metadata)
        
        # İndeksi güncelle
        update_index_at_position(vector_store, chunk.embedding, index)
        
        # Değişiklik bayrağını ayarla
        vector_store.is_dirty = True

def delete_chunk(vector_store, chunk_id: str) -> bool:
    """
    Bir chunk'ı siler.
    
    Args:
        vector_store: Vector store nesnesi
        chunk_id: Silinecek chunk ID'si
        
    Returns:
        bool: Başarı durumu
    """
    with vector_store.lock:
        # ID kontrolü
        if chunk_id not in vector_store.id_to_index:
            logger.warning(f"Silinecek chunk bulunamadı: {chunk_id}")
            return False
        
        # Indeksi al
        index = vector_store.id_to_index[chunk_id]
        
        # Chunk bilgilerini al
        document_id = None
        if vector_store.metadata[index] and "document_id" in vector_store.metadata[index]:
            document_id = vector_store.metadata[index]["document_id"]
        
        # Silme işlemi için indeks tipine göre işlem yap
        from ModularMind.API.services.retrieval.vector_models import IndexType
        if vector_store.config.index_type in [IndexType.QDRANT, IndexType.MILVUS, IndexType.WEAVIATE, IndexType.PINECONE]:
            # Harici indeks için doğrudan silme
            from ModularMind.API.services.retrieval.indices import delete_from_external_index
            delete_from_external_index(vector_store, chunk_id)
        else:
            # Bu yaklaşım indeksler için ideal değil, yeniden oluşturmak gerekebilir
            # Ancak basit durumlar için çalışır
            
            # Vektörü, ID'yi ve metadata'yı sil
            del vector_store.vectors[index]
            del vector_store.ids[index]
            del vector_store.metadata[index]
            
            # ID -> indeks eşlemesini güncelle
            del vector_store.id_to_index[chunk_id]
            
            # Silinen indeksten sonraki tüm indeksleri güncelle
            for i, cid in enumerate(vector_store.ids[index:], index):
                vector_store.id_to_index[cid] = i
            
            # Metadata indeksinden sil
            if vector_store.config.metadata_index_type != "none":
                remove_from_metadata_index(vector_store, chunk_id)
            
            # İndeksi yeniden oluştur
            _rebuild_index(vector_store)
        
        # Koleksiyon istatistiklerini güncelle
        vector_store.collection_stats["total_chunks"] -= 1
        
        # Belge ID'si varsa ve başka chunk'lar tarafından kullanılmıyorsa belge sayısını azalt
        if document_id and document_id not in get_document_ids_except(vector_store, chunk_id):
            vector_store.collection_stats["total_documents"] -= 1
        
        # Değişiklik bayrağını ayarla
        vector_store.is_dirty = True
        
        return True

def update_metadata_index(vector_store, chunk_id: str, metadata: Dict[str, Any]) -> None:
    """
    Metadata indeksini günceller.
    
    Args:
        vector_store: Vector store nesnesi
        chunk_id: Chunk ID
        metadata: Güncellenecek metadata
    """
    # Eski indeksi kaldır
    remove_from_metadata_index(vector_store, chunk_id)
    
    # Yeni değerleri indeksle
    if not metadata:
        return
    
    # Düz alanlara göre indeksle
    for key, value in metadata.items():
        # Sadece skaler değerleri indeksle
        if isinstance(value, (str, int, float, bool)):
            # Değer -> chunk ID haritası
            if value not in vector_store.metadata_index[key]:
                vector_store.metadata_index[key][value] = set()
            
            vector_store.metadata_index[key][value].add(chunk_id)

def remove_from_metadata_index(vector_store, chunk_id: str) -> None:
    """
    Metadata indeksinden chunk ID'sini kaldırır.
    
    Args:
        vector_store: Vector store nesnesi
        chunk_id: Kaldırılacak chunk ID
    """
    # Tüm indekslerde chunk ID'sini ara ve kaldır
    for field_index in vector_store.metadata_index.values():
        for value_set in field_index.values():
            if chunk_id in value_set:
                value_set.remove(chunk_id)

def update_index(vector_store, vectors: List[List[float]], indices: List[int]) -> None:
    """
    İndeksi günceller.
    
    Args:
        vector_store: Vector store nesnesi
        vectors: Eklenecek vektörler
        indices: Vektörlerin indeksleri
    """
    if not vectors:
        return

    from ModularMind.API.services.retrieval.indices import (
        _update_hnsw_index, _update_ivf_index, _update_faiss_index,
        _update_external_index
    )
        
    # İndeks tipine göre güncelleme
    from ModularMind.API.services.retrieval.vector_models import IndexType
    if vector_store.config.index_type == IndexType.FLAT:
        # Düz indeks için özel bir işlem yapmaya gerek yok
        pass
        
    elif vector_store.config.index_type == IndexType.HNSW:
        _update_hnsw_index(vector_store, vectors, indices)
        
    elif vector_store.config.index_type in [IndexType.IVF, IndexType.IVF_FLAT, IndexType.IVF_PQ]:
        _update_ivf_index(vector_store, vectors, indices)
        
    elif vector_store.config.index_type == IndexType.FAISS:
        _update_faiss_index(vector_store, vectors, indices)
        
    elif vector_store.config.index_type in [IndexType.QDRANT, IndexType.MILVUS, IndexType.WEAVIATE, IndexType.PINECONE]:
        _update_external_index(vector_store, vectors, indices)

def update_index_at_position(vector_store, vector: List[float], index: int) -> None:
    """
    Belirli bir indeksteki vektörü günceller.
    
    Args:
        vector_store: Vector store nesnesi
        vector: Yeni vektör
        index: Güncellenecek indeks
    """
    update_index(vector_store, [vector], [index])

def get_unique_document_ids(vector_store) -> Set[str]:
    """
    Benzersiz belge ID'lerini döndürür.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        Set[str]: Benzersiz belge ID'leri
    """
    document_ids = set()
    
    for metadata in vector_store.metadata:
        if metadata:
            doc_id = metadata.get("document_id")
            if doc_id:
                document_ids.add(doc_id)
    
    return document_ids

def get_document_ids_except(vector_store, exclude_chunk_id: str) -> Set[str]:
    """
    Belirli bir chunk ID'si hariç, tüm belge ID'lerini döndürür.
    
    Args:
        vector_store: Vector store nesnesi
        exclude_chunk_id: Hariç tutulacak chunk ID'si
        
    Returns:
        Set[str]: Belge ID'leri
    """
    document_ids = set()
    
    for idx, chunk_id in enumerate(vector_store.ids):
        if chunk_id != exclude_chunk_id:
            metadata = vector_store.metadata[idx]
            if metadata and "document_id" in metadata:
                document_ids.add(metadata["document_id"])
    
    return document_ids