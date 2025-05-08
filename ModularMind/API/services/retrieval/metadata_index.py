"""
Vector Store metadata indeksleme işlemleri.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

def search_metadata_index(vector_store, filter_metadata: Dict[str, Any]) -> Set[str]:
    """
    Metadata indeksinde arama yapar.
    
    Args:
        vector_store: Vector store nesnesi
        filter_metadata: Metadata filtresi
        
    Returns:
        Set[str]: Eşleşen chunk ID'leri
    """
    if not filter_metadata or vector_store.config.metadata_index_type == "none":
        return set()
    
    # Her filtre için eşleşen chunk ID'lerini bul
    matching_ids_per_filter = []
    
    for key, value in filter_metadata.items():
        # Anahtar için indeks var mı kontrol et
        if key not in vector_store.metadata_index:
            # Bu anahtar için indeks yoksa, tam taramaya geri dön
            return set()
        
        # Değer tipine göre işlem yap
        if isinstance(value, (str, int, float, bool)):
            # Basit değer sorgusu
            if value in vector_store.metadata_index[key]:
                matching_ids_per_filter.append(vector_store.metadata_index[key][value])
            else:
                # Değer indekste yoksa, eşleşme yok
                matching_ids_per_filter.append(set())
                
        elif isinstance(value, dict) and all(op.startswith("$") for op in value.keys()):
            # Operatör sorgusu
            matching_ids = set()
            for op, val in value.items():
                if op == "$eq":
                    # Eşitlik
                    if val in vector_store.metadata_index[key]:
                        matching_ids.update(vector_store.metadata_index[key][val])
                elif op == "$in":
                    # İçinde
                    if isinstance(val, (list, tuple)):
                        for v in val:
                            if v in vector_store.metadata_index[key]:
                                matching_ids.update(vector_store.metadata_index[key][v])
                
                # Diğer operatörler ($gt, $lt vb.) indeks üzerinde doğrudan uygulanamaz
                # Bu durumda tam taramaya geri dönmek gerekir
                else:
                    return set()
            
            matching_ids_per_filter.append(matching_ids)
            
        elif isinstance(value, list):
            # Liste sorgusu
            matching_ids = set()
            for val in value:
                if val in vector_store.metadata_index[key]:
                    matching_ids.update(vector_store.metadata_index[key][val])
            
            matching_ids_per_filter.append(matching_ids)
            
        else:
            # Desteklenmeyen değer tipi, tam taramaya geri dön
            return set()
    
    # Hiç eşleşme yoksa boş küme döndür
    if not matching_ids_per_filter:
        return set()
    
    # Tüm filtreler için kesişim kümesi (AND sorgusu)
    result = matching_ids_per_filter[0]
    for ids in matching_ids_per_filter[1:]:
        result = result.intersection(ids)
    
    return result

def build_metadata_index(vector_store) -> None:
    """
    Metadata indeksini oluşturur.
    
    Args:
        vector_store: Vector store nesnesi
    """
    # İndeksleme modu kontrolü
    if vector_store.config.metadata_index_type == "none":
        logger.info("Metadata indeksleme devre dışı")
        return
    
    # İndeksi sıfırla
    vector_store.metadata_index = {}
    
    # Tüm chunk'lar için indeksleme yap
    for idx, chunk_id in enumerate(vector_store.ids):
        metadata = vector_store.metadata[idx]
        if metadata:
            # Metadata değerlerini indeksle
            for key, value in metadata.items():
                if key not in vector_store.metadata_index:
                    vector_store.metadata_index[key] = {}
                
                # Sadece skaler değerleri indeksle
                if isinstance(value, (str, int, float, bool)):
                    if value not in vector_store.metadata_index[key]:
                        vector_store.metadata_index[key][value] = set()
                    
                    vector_store.metadata_index[key][value].add(chunk_id)
    
    logger.info(f"Metadata indeksi oluşturuldu: {len(vector_store.metadata_index)} alan")

def optimize_metadata_index(vector_store) -> None:
    """
    Metadata indeksini optimize eder.
    
    Args:
        vector_store: Vector store nesnesi
    """
    # Boş kümeleri temizle
    for key in list(vector_store.metadata_index.keys()):
        field_index = vector_store.metadata_index[key]
        
        for value in list(field_index.keys()):
            if not field_index[value]:
                del field_index[value]
        
        if not field_index:
            del vector_store.metadata_index[key]
    
    logger.info(f"Metadata indeksi optimize edildi: {len(vector_store.metadata_index)} alan")

def get_indexed_fields(vector_store) -> Dict[str, int]:
    """
    İndekslenmiş alanların istatistiklerini döndürür.
    
    Args:
        vector_store: Vector store nesnesi
        
    Returns:
        Dict[str, int]: Alan adı -> indeks boyutu
    """
    field_stats = {}
    
    for key, field_index in vector_store.metadata_index.items():
        # Alan için toplam indekslenmiş değer sayısı
        field_stats[key] = sum(len(value_set) for value_set in field_index.values())
    
    return field_stats