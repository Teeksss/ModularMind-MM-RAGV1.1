"""
Anahtar kelime tabanlı arama işlemleri.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union

from ..base import BaseSearcher, SearchResult

logger = logging.getLogger(__name__)

class KeywordSearcher(BaseSearcher):
    """
    Anahtar kelime tabanlı arama sınıfı.
    
    Bu sınıf, metin sorgularını anahtar kelimelere ayırarak
    metin deposunda en benzer belge parçalarını bulur.
    """
    
    def __init__(self, vector_store):
        """
        Anahtar kelime aramasını başlatır
        
        Args:
            vector_store: Arama yapılacak vektör deposu
        """
        self.vector_store = vector_store
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[SearchResult]:
        """
        Anahtar kelime tabanlı arama yapar
        
        Args:
            query: Arama sorgusu
            limit: Sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        if not query:
            return []
        
        try:
            # Anahtar kelimeleri çıkar
            keywords = self._extract_keywords(query)
            
            if not keywords:
                logger.warning("Anahtar kelimeler çıkarılamadı")
                return []
            
            # Vektör deposunda metin araması yap
            results = self.vector_store.search_by_text(
                keywords,
                limit=limit,
                filter_metadata=filter_metadata,
                include_metadata=include_metadata
            )
            
            # Sonuçları SearchResult nesnelerine dönüştür
            search_results = []
            for result in results:
                search_result = SearchResult(
                    chunk_id=result.get("id"),
                    document_id=result.get("document_id"),
                    text=result.get("text", ""),
                    score=result.get("score", 0.0),
                    metadata=result.get("metadata") if include_metadata else None,
                    source="keyword"
                )
                search_results.append(search_result)
            
            return search_results
        except Exception as e:
            logger.error(f"Anahtar kelime arama hatası: {str(e)}")
            return []
    
    def _extract_keywords(self, query: str) -> str:
        """
        Sorgudan anahtar kelimeleri çıkarır
        
        Args:
            query: Arama sorgusu
            
        Returns:
            str: Çıkarılan anahtar kelimeler
        """
        # Basit bir anahtar kelime çıkarma yaklaşımı
        # Gerçek uygulamada daha karmaşık işlemler yapılabilir
        
        # Soru işaretlerini ve noktalama işaretlerini kaldır
        query = re.sub(r'[?.,;:!]', ' ', query)
        
        # Tüm metni küçük harfe çevir
        query = query.lower()
        
        # Stop kelimeleri kaldır (basit örnek)
        stop_words = {"a", "an", "the", "in", "on", "at", "for", "to", "with", "by", "from", "of", "and", "or", "is", "are", "was", "were", "be", "been"}
        
        words = query.split()
        keywords = [word for word in words if word not in stop_words and len(word) > 1]
        
        # Anahtar kelimeleri bir araya getir
        return " ".join(keywords)
    
    def calculate_bm25_score(self, query_terms: List[str], document: str) -> float:
        """
        BM25 skor hesaplaması yapar (basitleştirilmiş)
        
        Args:
            query_terms: Sorgu terimleri
            document: Belge metni
            
        Returns:
            float: BM25 skoru
        """
        # BM25 parametreleri
        k1 = 1.5  # Terim frekansı için ayar parametresi
        b = 0.75  # Belge uzunluğu normalizasyonu için ayar parametresi
        
        # Belge terimlerini al
        document_terms = self._extract_keywords(document).split()
        
        # Belge uzunluğu
        doc_length = len(document_terms)
        
        # Ortalama belge uzunluğu (gerçek uygulamada tüm belgelerin ortalaması alınmalı)
        avg_doc_length = 100
        
        # BM25 skoru
        score = 0.0
        
        for term in query_terms:
            # Terim frekansı
            term_freq = document_terms.count(term)
            
            if term_freq > 0:
                # IDF (gerçek uygulamada tüm belgelere göre hesaplanmalı)
                idf = 1.0
                
                # BM25 formülü
                numerator = term_freq * (k1 + 1)
                denominator = term_freq + k1 * (1 - b + b * (doc_length / avg_doc_length))
                
                term_score = idf * (numerator / denominator)
                score += term_score
        
        return score