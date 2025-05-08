"""
Vector Store arama yardımcı fonksiyonları.
"""

import re
from typing import List, Dict, Any, Optional, Set
import numpy as np

def extract_keywords(query: str) -> List[str]:
    """
    Sorgudan anahtar kelimeleri çıkarır.
    
    Args:
        query: Sorgu metni
        
    Returns:
        List[str]: Anahtar kelimeler
    """
    # Noktalama işaretlerini temizle
    cleaned_query = re.sub(r'[^\w\s]', ' ', query)
    
    # Küçük harfe çevir
    cleaned_query = cleaned_query.lower()
    
    # Yaygın stop kelimeleri
    stop_words = {
        'the', 'a', 'an', 'in', 'on', 'at', 'of', 'to', 'for', 'with', 'by', 'about',
        've', 'bu', 'şu', 'da', 'de', 'ki', 'ne', 'bir', 'bu', 'şu', 'o', 'için'
    }
    
    # Kelimelere ayır ve stop kelimeleri kaldır
    words = cleaned_query.split()
    keywords = [word for word in words if word not in stop_words and len(word) > 2]
    
    return keywords

def score_text_for_keywords(text: str, keywords: List[str]) -> float:
    """
    Metni anahtar kelimelere göre puanlar.
    
    Args:
        text: Puanlanacak metin
        keywords: Anahtar kelimeler
        
    Returns:
        float: Puan
    """
    if not text or not keywords:
        return 0.0
    
    # Metni küçük harfe çevir
    text = text.lower()
    
    # Her anahtar kelime için puan
    total_score = 0.0
    
    # Anahtar kelimelerin benzersiz seti
    unique_keywords = set(keywords)
    
    for keyword in unique_keywords:
        # Metin içinde anahtar kelime sayısı
        count = text.count(keyword)
        
        # Tam kelime eşleşmesi kontrolü için ek puan
        word_boundaries = r'\b' + re.escape(keyword) + r'\b'
        exact_matches = len(re.findall(word_boundaries, text))
        
        # Puanı hesapla
        score = (count * 0.5) + (exact_matches * 1.0)
        
        total_score += score
    
    return total_score

def combine_search_results(
    vector_results: List,
    keyword_results: List,
    alpha: float = 0.5,
    limit: int = 10,
    min_score_threshold: Optional[float] = None
) -> List:
    """
    Vektör ve anahtar kelime arama sonuçlarını birleştirir.
    
    Args:
        vector_results: Vektör arama sonuçları
        keyword_results: Anahtar kelime arama sonuçları
        alpha: Vektör ağırlığı (0-1 arası)
        limit: Maksimum sonuç sayısı
        min_score_threshold: Minimum benzerlik eşiği
        
    Returns:
        List: Birleştirilmiş sonuçlar
    """
    # Sonuç ID'lerini ve skorlarını sakla
    result_scores = {}
    result_objects = {}
    
    # Vektör sonuçlarını ekle
    for result in vector_results:
        chunk_id = result.chunk.id
        score = result.score * alpha
        result_scores[chunk_id] = score
        result_objects[chunk_id] = result
    
    # Anahtar kelime sonuçlarını ekle/güncelle
    for result in keyword_results:
        chunk_id = result.chunk.id
        keyword_score = result.score * (1 - alpha)
        
        if chunk_id in result_scores:
            # Var olan sonucu güncelle
            result_scores[chunk_id] += keyword_score
        else:
            # Yeni sonuç ekle
            result_scores[chunk_id] = keyword_score
            result_objects[chunk_id] = result
    
    # Sonuçları puana göre sırala
    sorted_results = sorted(
        [(chunk_id, score) for chunk_id, score in result_scores.items()],
        key=lambda x: x[1],
        reverse=True
    )
    
    # Eşik değeri uygula
    if min_score_threshold is not None:
        sorted_results = [(chunk_id, score) for chunk_id, score in sorted_results if score >= min_score_threshold]
    
    # Limit uygula
    sorted_results = sorted_results[:limit]
    
    # Sonuç nesnelerini oluştur
    combined_results = []
    
    for chunk_id, score in sorted_results:
        result = result_objects[chunk_id]
        
        # Skoru güncelle
        result.score = score
        
        # Karma arama kaynağı olarak işaretle
        result.source = "hybrid_search"
        
        combined_results.append(result)
    
    return combined_results

def check_metadata_filter(
    metadata: Dict[str, Any], 
    filter_metadata: Dict[str, Any]
) -> bool:
    """
    Metadata'nın filtreyi karşılayıp karşılamadığını kontrol eder.
    
    Args:
        metadata: Kontrol edilecek metadata
        filter_metadata: Metadata filtresi
        
    Returns:
        bool: Filtreye uygunluk durumu
    """
    if not metadata or not filter_metadata:
        return False
    
    for key, value in filter_metadata.items():
        # İç içe alanları işle (örn: "metadata.author")
        if "." in key:
            parts = key.split(".")
            current = metadata
            
            # İç içe alanları takip et
            for part in parts[:-1]:
                if part not in current or not isinstance(current[part], dict):
                    return False
                current = current[part]
                
            final_key = parts[-1]
            
            # Son anahtar mevcut değilse
            if final_key not in current:
                return False
                
            # Değeri kontrol et
            if not _match_filter_value(current[final_key], value):
                return False
        
        # Normal alanları işle
        elif key not in metadata:
            return False
        
        # Değeri kontrol et
        elif not _match_filter_value(metadata[key], value):
            return False
    
    return True

def _match_filter_value(actual_value: Any, filter_value: Any) -> bool:
    """
    Gerçek değerin filtre değerine uyup uymadığını kontrol eder.
    
    Args:
        actual_value: Gerçek değer
        filter_value: Filtre değeri
        
    Returns:
        bool: Uygunluk durumu
    """
    # Sözlük filtresi
    if isinstance(filter_value, dict) and "$" in next(iter(filter_value), ""):
        # Özel operatörler
        for op, val in filter_value.items():
            if op == "$eq":
                return actual_value == val
            elif op == "$ne":
                return actual_value != val
            elif op == "$gt":
                return _is_numeric(actual_value) and actual_value > val
            elif op == "$gte":
                return _is_numeric(actual_value) and actual_value >= val
            elif op == "$lt":
                return _is_numeric(actual_value) and actual_value < val
            elif op == "$lte":
                return _is_numeric(actual_value) and actual_value <= val
            elif op == "$in":
                return actual_value in val if isinstance(val, (list, tuple, set)) else False
            elif op == "$nin":
                return actual_value not in val if isinstance(val, (list, tuple, set)) else True
            elif op == "$regex":
                return bool(re.search(val, str(actual_value))) if isinstance(actual_value, str) else False
    
    # Liste filtresi (herhangi biri eşleşiyorsa)
    elif isinstance(filter_value, list):
        return actual_value in filter_value
    
    # Basit eşitlik
    else:
        return actual_value == filter_value

def _is_numeric(value: Any) -> bool:
    """
    Değerin sayısal olup olmadığını kontrol eder.
    
    Args:
        value: Kontrol edilecek değer
        
    Returns:
        bool: Sayısal olma durumu
    """
    return isinstance(value, (int, float, np.number))