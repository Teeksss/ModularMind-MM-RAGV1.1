"""
Vektör tabanlı arama işlemleri.
"""

import logging
from typing import Dict, List, Any, Optional, Union

from ..base import BaseSearcher, SearchResult

logger = logging.getLogger(__name__)

class VectorSearcher(BaseSearcher):
    """
    Vektör tabanlı arama sınıfı.
    
    Bu sınıf, metin sorgularını vector embeddings'e dönüştürerek 
    vektör veritabanında en benzer belge parçalarını bulur.
    """
    
    def __init__(self, vector_store):
        """
        Vektör aramasını başlatır
        
        Args:
            vector_store: Arama yapılacak vektör deposu
        """
        self.vector_store = vector_store
        self.embedding_service = None
    
    def initialize(self) -> bool:
        """
        Aramayla ilgili servisleri başlatır
        
        Returns:
            bool: Başlatma başarılı mı
        """
        try:
            # Embedding servisini al (lazy loading)
            from ModularMind.API.services.embedding import EmbeddingService
            self.embedding_service = EmbeddingService.get_instance()
            return True
        except Exception as e:
            logger.error(f"Vektör arama başlatma hatası: {str(e)}")
            return False
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        embedding_model: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Vektör tabanlı arama yapar
        
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
            # Embedding servisini başlat (ilk kullanımda)
            if not self.embedding_service:
                if not self.initialize():
                    logger.error("Vektör arama başlatılamadı")
                    return []
            
            # Sorgu için embedding oluştur
            query_embedding = self.embedding_service.create_embedding(
                query, embedding_model
            )
            
            if not query_embedding:
                logger.error("Sorgu embedding'i oluşturulamadı")
                return []
            
            # Vektör deposunda benzer belgeler ara
            results = self.vector_store.search_by_vector(
                query_embedding,
                limit=limit,
                filter_metadata=filter_metadata,
                include_metadata=include_metadata,
                embedding_model=embedding_model
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
                    source="vector"
                )
                search_results.append(search_result)
            
            return search_results
        except Exception as e:
            logger.error(f"Vektör arama hatası: {str(e)}")
            return []
    
    def batch_search(
        self,
        queries: List[str],
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        embedding_model: Optional[str] = None
    ) -> List[List[SearchResult]]:
        """
        Toplu vektör araması yapar
        
        Args:
            queries: Arama sorguları listesi
            limit: Her sorgu için sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            embedding_model: Kullanılacak embedding modeli
            
        Returns:
            List[List[SearchResult]]: Her sorgu için arama sonuçları
        """
        if not queries:
            return []
        
        try:
            # Embedding servisini başlat (ilk kullanımda)
            if not self.embedding_service:
                if not self.initialize():
                    logger.error("Vektör arama başlatılamadı")
                    return [[] for _ in queries]
            
            # Sorgular için embeddingler oluştur
            query_embeddings = self.embedding_service.create_batch_embeddings(
                queries, embedding_model
            )
            
            if not query_embeddings:
                logger.error("Sorgu embedding'leri oluşturulamadı")
                return [[] for _ in queries]
            
            # Her sorgu için arama yap
            all_results = []
            for i, query_embedding in enumerate(query_embeddings):
                # Vektör deposunda benzer belgeler ara
                results = self.vector_store.search_by_vector(
                    query_embedding,
                    limit=limit,
                    filter_metadata=filter_metadata,
                    include_metadata=include_metadata,
                    embedding_model=embedding_model
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
                        source="vector"
                    )
                    search_results.append(search_result)
                
                all_results.append(search_results)
            
            return all_results
        except Exception as e:
            logger.error(f"Toplu vektör arama hatası: {str(e)}")
            return [[] for _ in queries]