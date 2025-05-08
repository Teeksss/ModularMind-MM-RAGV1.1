"""
LLM Yardımcı fonksiyonları.
"""

import re
from typing import List, Dict, Any

def estimate_tokens(text: str, model_config) -> int:
    """
    Metindeki token sayısını tahmin eder.
    
    Args:
        text: Metin
        model_config: Model yapılandırması
        
    Returns:
        int: Tahmini token sayısı
    """
    if not text:
        return 0
        
    # Basit yaklaşım: 4 karakter = 1 token (ortalama)
    tokens_estimate = len(text) / 4
    
    return int(tokens_estimate)

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