"""
Vector Store belge işlemleri.
"""

import logging
from typing import List, Dict, Any, Optional

from ModularMind.API.services.retrieval.search_utils import check_metadata_filter

logger = logging.getLogger(__name__)

def get_documents_info(
    vector_store,
    document_id: Optional[str] = None,
    filter_metadata: Optional[Dict[str, Any]] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Belge bilgilerini döndürür.
    
    Args:
        vector_store: Vector store nesnesi
        document_id: Belge ID'si (None ise tüm belgeler)
        filter_metadata: Metadata filtresi
        limit: Maksimum sonuç sayısı
        offset: Başlangıç indeksi
        
    Returns:
        List[Dict[str, Any]]: Belge bilgileri
    """
    with vector_store.lock:
        # Veri kontrolü
        if not vector_store.ids:
            return []
        
        # Belge ID'lerine göre gruplama
        document_groups = {}
        
        for idx, chunk_id in enumerate(vector_store.ids):
            metadata = vector_store.metadata[idx] or {}
            
            # Belge ID'sini al
            doc_id = metadata.get("document_id") or metadata.get("id")
            
            if not doc_id:
                continue
            
            # Belirli bir belge ID'si istenmişse kontrol et
            if document_id and doc_id != document_id:
                continue
            
            # Metadata filtresi varsa, sonuçları kontrol et
            if filter_metadata and not check_metadata_filter(metadata, filter_metadata):
                continue
            
            # Belge grubuna ekle
            if doc_id not in document_groups:
                document_groups[doc_id] = {
                    "document_id": doc_id,
                    "metadata": {},
                    "chunk_count": 0,
                    "chunks": []
                }
            
            # Belge meta verilerini güncelle
            for key in ["title", "source", "url", "author", "created_at", "document_type"]:
                if key in metadata and key not in document_groups[doc_id]["metadata"]:
                    document_groups[doc_id]["metadata"][key] = metadata[key]
            
            # Chunk bilgilerini ekle
            document_groups[doc_id]["chunk_count"] += 1
            document_groups[doc_id]["chunks"].append({
                "chunk_id": chunk_id,
                "metadata": metadata
            })
        
        # Sonuçları liste haline getir
        documents = list(document_groups.values())
        
        # Sayfa başı sonuçlar
        documents = documents[offset:offset+limit]
        
        return documents

def get_unique_document_ids(vector_store) -> List[str]:
    """
    Benzersiz belge ID'lerini döndürür.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        List[str]: Benzersiz belge ID'leri
    """
    document_ids = set()
    
    for metadata in vector_store.metadata:
        if metadata:
            doc_id = metadata.get("document_id") or metadata.get("id")
            if doc_id:
                document_ids.add(doc_id)
    
    return list(document_ids)