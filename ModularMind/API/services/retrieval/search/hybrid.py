"""
Hibrit arama işlemleri.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import time

from ..base import BaseSearcher, SearchResult

logger = logging.getLogger(__name__)

class HybridSearcher(BaseSearcher):
    """
    Hibrit arama sınıfı.
    
    Bu sınıf, vektör tabanlı ve anahtar kelime tabanlı aramaları birleştirerek
    daha kapsamlı sonuçlar elde etmeyi amaçlar.
    """
    
    def __init__(
        self,
        vector_searcher,
        keyword_searcher,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3
    ):
        """
        Hibrit aramayı başlatır
        
        Args:
            vector_searcher: Vektör tabanlı arama sınıfı
            keyword_searcher: Anahtar kelime tabanlı arama sınıfı
            vector_weight: Vektör sonuçlarının ağırlığı (0-1)
            keyword_weight: Anahtar kelime sonuçlarının ağırlığı (0-1)
        """
        self.vector_searcher = vector_searcher
        self.keyword_searcher = keyword_searcher
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        embedding_model: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Hibrit arama yapar
        
        Args:
            query: Arama sorgusu
            limit: Sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            embedding_model: Kullanılacak embedding modeli
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        if not query:
            return []
        
        try:
            start_time = time.time()
            
            # Genişletilmiş limit (her iki aramaya da uygulanacak)
            extended_limit = limit * 2
            
            # Vektör ve anahtar kelime aramalarını paralel olarak gerçekleştir
            # Gerçek uygulamada bu async olarak yapılabilir
            
            # Vektör araması
            vector_results = self.vector_searcher.search(
                query=query,
                limit=extended_limit,
                filter_metadata=filter_metadata,
                include_metadata=include_metadata,
                embedding_model=embedding_model
            )
            
            # Anahtar kelime araması
            keyword_results = self.keyword_searcher.search(
                query=query,
                limit=extended_limit,
                filter_metadata=filter_metadata,
                include_metadata=include_metadata
            )
            
            # Sonuçları birleştir
            combined_results = self._combine_results(
                vector_results=vector_results,
                keyword_results=keyword_results,
                limit=limit
            )
            
            elapsed_time = time.time() - start_time
            logger.debug(f"Hibrit arama tamamlandı, süre: {elapsed_time:.4f} saniye")
            
            return combined_results
        except Exception as e:
            logger.error(f"Hibrit arama hatası: {str(e)}")
            return []
    
    def _combine_results(
        self,
        vector_results: List[SearchResult],
        keyword_results: List[SearchResult],
        limit: int
    ) -> List[SearchResult]:
        """
        Vektör ve anahtar kelime sonuçlarını birleştirir
        
        Args:
            vector_results: Vektör arama sonuçları
            keyword_results: Anahtar kelime arama sonuçları
            limit: Sonuç limiti
            
        Returns:
            List[SearchResult]: Birleştirilmiş sonuçlar
        """
        # Tüm sonuçları bir sözlükte topla (chunk_id'ye göre)
        all_results = {}
        
        # Vektör sonuçlarını işle
        for result in vector_results:
            result_id = result.chunk_id
            all_results[result_id] = {
                "result": result,
                "vector_score": result.score,
                "keyword_score": 0.0,
                "combined_score": result.score * self.vector_weight
            }
        
        # Anahtar kelime sonuçlarını işle
        for result in keyword_results:
            result_id = result.chunk_id
            
            if result_id in all_results:
                # Zaten var olan sonucu güncelle
                all_results[result_id]["keyword_score"] = result.score
                all_results[result_id]["combined_score"] += result.score * self.keyword_weight
            else:
                # Yeni sonuç ekle
                all_results[result_id] = {
                    "result": result,
                    "vector_score": 0.0,
                    "keyword_score": result.score,
                    "combined_score": result.score * self.keyword_weight
                }
        
        # Sonuçları kombine skora göre sırala
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x["combined_score"],
            reverse=True
        )
        
        # Sonuçları SearchResult nesnelerine dönüştür ve skoru güncelle
        final_results = []
        for item in sorted_results[:limit]:
            result = item["result"]
            # Kombine skoru sonuca ata
            result.score = item["combined_score"]
            result.source = "hybrid"
            final_results.append(result)
        
        return final_results