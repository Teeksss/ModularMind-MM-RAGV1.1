"""
Vector Store arama fonksiyonları.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from ModularMind.API.services.retrieval.models import Chunk, SearchResult
from ModularMind.API.services.retrieval.search_utils import (
    extract_keywords, score_text_for_keywords, combine_search_results, 
    check_metadata_filter
)

logger = logging.getLogger(__name__)

def vector_search(
    vector_store,
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
        vector_store: Vector store nesnesi
        query_vector: Sorgu vektörü
        limit: Maksimum sonuç sayısı
        filter_metadata: Metadata filtresi
        include_metadata: Sonuçlarda metadata dahil edilsin mi
        include_distances: Sonuçlarda uzaklık/benzerlik skoru dahil edilsin mi
        min_score_threshold: Minimum benzerlik eşiği
        
    Returns:
        List[SearchResult]: Arama sonuçları
    """
    with vector_store.lock:
        # Vektör kontrolü
        if not vector_store.vectors:
            logger.warning("Boş vektör deposu, arama sonucu bulunamadı")
            return []
        
        # Vektör boyutu kontrolü
        if len(query_vector) != vector_store.config.dimensions:
            logger.error(f"Sorgu vektörü boyutu uyumsuz: {len(query_vector)} != {vector_store.config.dimensions}")
            return []
        
        # İndeks tipine göre arama yap
        from ModularMind.API.services.retrieval.vector_models import IndexType
        if vector_store.config.index_type in [IndexType.QDRANT, IndexType.MILVUS, IndexType.WEAVIATE, IndexType.PINECONE]:
            # Harici indeks araması
            from ModularMind.API.services.retrieval.indices import search_external_index
            index_results = search_external_index(vector_store, query_vector, limit, filter_metadata)
        else:
            # Dahili indeks araması
            from ModularMind.API.services.retrieval.indices import search_internal_index
            index_results = search_internal_index(vector_store, query_vector, limit, filter_metadata)
        
        # Sonuçların sayısını kontrol et
        if not index_results:
            return []
        
        # SearchResult nesneleri oluştur
        search_results = []
        
        for idx, score in index_results:
            # Metadata filtresi varsa, sonuçları kontrol et
            if filter_metadata and not check_metadata_filter(vector_store.metadata[idx], filter_metadata):
                continue
            
            # Eşik değeri kontrolü
            if min_score_threshold is not None and score < min_score_threshold:
                continue
            
            # Chunk ID'sini al
            chunk_id = vector_store.ids[idx]
            
            # Chunk meta datasını al (isteğe bağlı)
            chunk_metadata = vector_store.metadata[idx] if include_metadata else {}
            
            # Chunk oluştur
            chunk = Chunk(
                id=chunk_id,
                text="",  # Metin daha sonra ayrıca yüklenecek
                metadata=chunk_metadata,
                embedding=None,  # Embedding'i dahil etmiyoruz
            )
            
            # SearchResult oluştur
            result = SearchResult(
                chunk=chunk,
                score=score,
                source="vector_search"
            )
            
            search_results.append(result)
        
        return search_results

def text_search(
    vector_store,
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
        vector_store: Vector store nesnesi
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
    # Embedding servisi kontrolü
    if not vector_store.embedding_service:
        logger.error("Metin sorgusu için embedding servisi gerekli")
        return []
    
    # Embedding hesapla
    query_vector = vector_store.embedding_service.get_embedding(query_text, model=embedding_model)
    
    # Vektörel arama yap
    return vector_search(
        vector_store,
        query_vector=query_vector,
        limit=limit,
        filter_metadata=filter_metadata,
        include_metadata=include_metadata,
        include_distances=include_distances,
        min_score_threshold=min_score_threshold
    )

def hybrid_search(
    vector_store,
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
        vector_store: Vector store nesnesi
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
    # Alpha ayarı
    alpha = alpha if alpha is not None else vector_store.config.hybrid_search_alpha
    
    # Anahtar kelime alanları
    if not keyword_fields:
        keyword_fields = ["text", "title", "description", "content"]
    
    # Vektörel arama yap
    vector_results = text_search(
        vector_store,
        query_text=query_text,
        limit=limit * 2,  # Daha fazla sonuç al
        filter_metadata=filter_metadata,
        include_metadata=True,
        include_distances=True,
        embedding_model=embedding_model
    )
    
    # Vektörel sonuç yoksa, sadece anahtar kelime araması yap
    if not vector_results:
        return keyword_search(
            vector_store,
            query_text=query_text,
            limit=limit,
            filter_metadata=filter_metadata,
            fields=keyword_fields
        )
    
    # Anahtar kelime araması yap
    keyword_results = keyword_search(
        vector_store,
        query_text=query_text,
        limit=limit * 2,  # Daha fazla sonuç al
        filter_metadata=filter_metadata,
        fields=keyword_fields
    )
    
    # Anahtar kelime sonucu yoksa, sadece vektörel sonuçları döndür
    if not keyword_results:
        return vector_results[:limit]
    
    # Sonuçları birleştir ve yeniden sırala
    combined_results = combine_search_results(
        vector_results=vector_results,
        keyword_results=keyword_results,
        alpha=alpha,
        limit=limit,
        min_score_threshold=min_score_threshold
    )
    
    return combined_results

def keyword_search(
    vector_store,
    query_text: str, 
    limit: int = 10, 
    filter_metadata: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None
) -> List[SearchResult]:
    """
    Anahtar kelime araması yapar.
    
    Args:
        vector_store: Vector store nesnesi
        query_text: Sorgu metni
        limit: Maksimum sonuç sayısı
        filter_metadata: Metadata filtresi
        fields: Arama yapılacak alanlar
        
    Returns:
        List[SearchResult]: Arama sonuçları
    """
    # Arama alanları
    if not fields:
        fields = ["text", "title", "description", "content"]
    
    with vector_store.lock:
        # Veri kontrolü
        if not vector_store.ids:
            logger.warning("Boş veri deposu, arama sonucu bulunamadı")
            return []
        
        # Anahtar kelimeleri çıkar
        keywords = extract_keywords(query_text)
        
        if not keywords:
            logger.warning("Anahtar kelime bulunamadı")
            return []
        
        # Chunk'ları puanla
        scores = []
        
        for idx, chunk_id in enumerate(vector_store.ids):
            # Metadata filtresi varsa, sonuçları kontrol et
            if filter_metadata and not check_metadata_filter(vector_store.metadata[idx], filter_metadata):
                continue
            
            # Metin içeriğini al
            chunk_text = ""
            
            # Bu prototip sürümünde, metin içeriği veritabanından yüklenmemiş durumdadır
            # Gerçek uygulamada, metin içeriği talep üzerine veritabanından yüklenebilir
            # Şimdilik sadece metadata'da arama yapacağız
            
            # Puan hesapla
            score = 0
            metadata = vector_store.metadata[idx] or {}
            
            # Metadata'da belirtilen alanlarda ara
            for field in fields:
                if field in metadata and metadata[field]:
                    field_text = str(metadata[field])
                    field_score = score_text_for_keywords(field_text, keywords)
                    score += field_score
            
            if score > 0:
                scores.append((idx, score))
        
        # Sonuçları puana göre sırala
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Limit uygula
        scores = scores[:limit]
        
        # SearchResult nesneleri oluştur
        search_results = []
        
        for idx, score in scores:
            # Normalize edilmiş skor
            normalized_score = min(score / len(keywords), 1.0)
            
            # Chunk ID'sini al
            chunk_id = vector_store.ids[idx]
            
            # Chunk meta datasını al
            chunk_metadata = vector_store.metadata[idx] or {}
            
            # Chunk oluştur
            chunk = Chunk(
                id=chunk_id,
                text="",  # Metin daha sonra ayrıca yüklenecek
                metadata=chunk_metadata,
                embedding=None,  # Embedding'i dahil etmiyoruz
            )
            
            # SearchResult oluştur
            result = SearchResult(
                chunk=chunk,
                score=normalized_score,
                source="keyword_search"
            )
            
            search_results.append(result)
        
        return search_results

def metadata_search(
    vector_store,
    filter_metadata: Dict[str, Any], 
    limit: int = 10,
) -> List[SearchResult]:
    """
    Metadata araması yapar.
    
    Args:
        vector_store: Vector store nesnesi
        filter_metadata: Metadata filtresi
        limit: Maksimum sonuç sayısı
        
    Returns:
        List[SearchResult]: Arama sonuçları
    """
    with vector_store.lock:
        # Veri kontrolü
        if not vector_store.ids:
            logger.warning("Boş veri deposu, arama sonucu bulunamadı")
            return []
        
        # Metadata indeksi yoksa veya NONE ise tüm chunk'ları kontrol et
        from ModularMind.API.services.retrieval.vector_models import MetadataIndexType
        if vector_store.config.metadata_index_type == MetadataIndexType.NONE or not vector_store.metadata_index:
            # Chunk'ları filtrele
            matching_indices = []
            
            for idx, metadata in enumerate(vector_store.metadata):
                if check_metadata_filter(metadata, filter_metadata):
                    matching_indices.append(idx)
        else:
            # Metadata indeksini kullan
            from ModularMind.API.services.retrieval.metadata_index import search_metadata_index
            matching_ids = search_metadata_index(vector_store, filter_metadata)
            
            # ID'leri indekslere dönüştür
            matching_indices = [vector_store.id_to_index[chunk_id] for chunk_id in matching_ids if chunk_id in vector_store.id_to_index]
        
        # Limit uygula
        matching_indices = matching_indices[:limit]
        
        # SearchResult nesneleri oluştur
        search_results = []
        
        for idx in matching_indices:
            # Chunk ID'sini al
            chunk_id = vector_store.ids[idx]
            
            # Chunk meta datasını al
            chunk_metadata = vector_store.metadata[idx] or {}
            
            # Chunk oluştur
            chunk = Chunk(
                id=chunk_id,
                text="",  # Metin daha sonra ayrıca yüklenecek
                metadata=chunk_metadata,
                embedding=None,  # Embedding'i dahil etmiyoruz
            )
            
            # SearchResult oluştur
            result = SearchResult(
                chunk=chunk,
                score=1.0,  # Tam eşleşme için 1.0
                source="metadata_search"
            )
            
            search_results.append(result)
        
        return search_results