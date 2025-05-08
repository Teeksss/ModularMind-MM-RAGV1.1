"""
Arama sonuçlarını yeniden sıralama işlemleri.
"""

import logging
from typing import Dict, List, Any, Optional, Union
import time

from ..base import SearchResult

logger = logging.getLogger(__name__)

class Reranker:
    """
    Arama sonuçlarını yeniden sıralama sınıfı.
    
    Bu sınıf, arama sonuçlarını sorgu ile olan ilişkilerine göre
    daha doğru bir şekilde sıralamak için kullanılır.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Yeniden sıralayıcıyı başlatır
        
        Args:
            config: Yapılandırma
        """
        self.config = config or {}
        self.model = None
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Yeniden sıralama modellerini yükler
        
        Returns:
            bool: Başlatma başarılı mı
        """
        try:
            model_type = self.config.get("model_type", "cross-encoder")
            
            if model_type == "cross-encoder":
                from sentence_transformers import CrossEncoder
                
                model_name = self.config.get("model_name", "cross-encoder/ms-marco-MiniLM-L-6-v2")
                
                logger.info(f"CrossEncoder modeli yükleniyor: {model_name}")
                self.model = CrossEncoder(model_name)
                logger.info("CrossEncoder modeli yüklendi")
            
            elif model_type == "custom":
                # Özel model implementasyonu
                model_path = self.config.get("model_path")
                if not model_path:
                    logger.error("Özel model için model_path belirtilmemiş")
                    return False
                
                # Özel modeli yükle
                logger.info(f"Özel model yükleniyor: {model_path}")
                # self.model = CustomRerankerModel(model_path)
                logger.info("Özel model yüklendi")
            
            else:
                logger.error(f"Bilinmeyen model tipi: {model_type}")
                return False
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Yeniden sıralama modeli başlatma hatası: {str(e)}")
            return False
    
    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None
    ) -> List[SearchResult]:
        """
        Sonuçları yeniden sıralar
        
        Args:
            query: Arama sorgusu
            results: Yeniden sıralanacak sonuçlar
            top_k: İlk kaç sonucu döndürmek
            
        Returns:
            List[SearchResult]: Yeniden sıralanmış sonuçlar
        """
        if not results:
            return []
        
        # Top-K belirtilmemişse tüm sonuçları kullan
        if top_k is None:
            top_k = len(results)
        
        try:
            # CrossEncoder modeli kullanılıyorsa
            if self.config.get("model_type") == "cross-encoder":
                if not self.initialized:
                    if not self.initialize():
                        logger.error("Yeniden sıralama başlatılamadı")
                        return results
                
                start_time = time.time()
                
                # Sorgu-belge çiftleri oluştur
                query_doc_pairs = [(query, result.text) for result in results]
                
                # CrossEncoder skorları hesapla
                scores = self.model.predict(query_doc_pairs)
                
                # Sonuçları yeni skorlarla güncelle
                for i, score in enumerate(scores):
                    results[i].score = float(score)
                
                # Sonuçları yeni skorlara göre sırala
                results = sorted(results, key=lambda x: x.score, reverse=True)
                
                # Top-K sonuçları seç
                results = results[:top_k]
                
                elapsed_time = time.time() - start_time
                logger.debug(f"Yeniden sıralama tamamlandı, süre: {elapsed_time:.4f} saniye")
            
            # BM25 bazlı yeniden sıralama
            elif self.config.get("reranking_method") == "bm25":
                from ModularMind.API.services.retrieval.search.keyword import KeywordSearcher
                
                # Anahtar kelimeleri çıkar
                keyword_searcher = KeywordSearcher(None)
                query_terms = keyword_searcher._extract_keywords(query).split()
                
                # Her sonuç için BM25 skoru hesapla
                for result in results:
                    bm25_score = keyword_searcher.calculate_bm25_score(query_terms, result.text)
                    
                    # Mevcut skoru BM25 ile birleştir
                    # Burada basit bir ağırlıklı ortalama kullanılıyor
                    vector_weight = self.config.get("vector_weight", 0.7)
                    bm25_weight = self.config.get("bm25_weight", 0.3)
                    
                    combined_score = (vector_weight * result.score) + (bm25_weight * bm25_score)
                    result.score = combined_score
                
                # Sonuçları yeni skorlara göre sırala
                results = sorted(results, key=lambda x: x.score, reverse=True)
                
                # Top-K sonuçları seç
                results = results[:top_k]
            
            # Varsayılan - Sonuçları olduğu gibi döndür
            else:
                # Top-K sonuçları seç
                results = results[:top_k]
            
            return results
        except Exception as e:
            logger.error(f"Yeniden sıralama hatası: {str(e)}")
            # Hata durumunda orijinal sonuçları döndür
            return results[:top_k]