"""
Retrieval servisi - belge arama ve geri getirme için ana servis.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass

from .config import RetrievalConfig
from .search.hybrid import HybridSearcher
from .search.vector import VectorSearcher
from .search.keyword import KeywordSearcher
from .ranking.reranker import Reranker
from .chunking.base import Document, Chunk

logger = logging.getLogger(__name__)

@dataclass
class SearchOptions:
    """Arama seçenekleri"""
    
    limit: int = 5
    min_score_threshold: Optional[float] = None
    filter_metadata: Optional[Dict[str, Any]] = None
    include_metadata: bool = True
    embedding_model: Optional[str] = None
    search_type: str = "hybrid"
    use_multi_model: bool = False
    models_to_use: Optional[List[str]] = None

class RetrievalResult:
    """Arama sonucu"""
    
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "vector",
        model_id: Optional[str] = None
    ):
        """
        Arama sonucunu başlatır
        
        Args:
            chunk_id: Parça kimliği
            document_id: Belge kimliği
            text: Parça metni
            score: Benzerlik skoru
            metadata: Parça meta verileri
            source: Sonuç kaynağı (vector, keyword, hybrid)
            model_id: Embedding model kimliği
        """
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.score = score
        self.metadata = metadata or {}
        self.source = source
        self.model_id = model_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
            "source": self.source,
            "model_id": self.model_id
        }

class RetrievalService:
    """
    Belge arama ve geri getirme servisi
    
    Bu servis, vektör ve anahtar kelime tabanlı arama ile belge parçalarını 
    bulma ve getirme yetenekleri sağlar.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Retrieval servisini başlatır
        
        Args:
            config_path: Yapılandırma dosyası yolu
        """
        self.config = RetrievalConfig()
        
        # Alt bileşenler
        self.vector_store = None
        self.vector_searcher = None
        self.keyword_searcher = None
        self.hybrid_searcher = None
        self.reranker = None
        
        # Yapılandırma yükle
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        Yapılandırmayı dosyadan yükler
        
        Args:
            config_path: Yapılandırma dosyası yolu
            
        Returns:
            bool: Yükleme başarılı mı
        """
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Ana yapılandırmayı ayarla
            self.config = RetrievalConfig.from_dict(config_data)
            
            # Alt bileşenleri başlat
            self._init_components()
            
            logger.info(f"Retrieval yapılandırması yüklendi: {config_path}")
            return True
        except Exception as e:
            logger.error(f"Retrieval yapılandırması yükleme hatası: {str(e)}")
            return False
    
    def _init_components(self) -> None:
        """Alt bileşenleri başlatır"""
        # Vector store başlat
        from .vector_store import get_vector_store
        
        self.vector_store = get_vector_store(
            store_type=self.config.vector_store.store_type,
            config=self.config.vector_store.to_dict()
        )
        
        # Arama bileşenlerini başlat
        self.vector_searcher = VectorSearcher(self.vector_store)
        self.keyword_searcher = KeywordSearcher(self.vector_store)
        self.hybrid_searcher = HybridSearcher(
            vector_searcher=self.vector_searcher,
            keyword_searcher=self.keyword_searcher,
            vector_weight=self.config.hybrid_search.vector_weight,
            keyword_weight=self.config.hybrid_search.keyword_weight
        )
        
        # Reranker'ı başlat
        if self.config.reranking.enabled:
            self.reranker = Reranker(self.config.reranking.to_dict())
    
    def add_document(
        self,
        document: Dict[str, Any],
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Belge ekler
        
        Args:
            document: Eklenecek belge
            options: Ekleme seçenekleri
            
        Returns:
            Optional[str]: Belge kimliği veya None
        """
        options = options or {}
        
        try:
            # Belgeyi hazırla
            doc = self._prepare_document(document)
            
            # Belgeyi ekle
            doc_id = self.vector_store.add_document(doc, options)
            
            return doc_id
        except Exception as e:
            logger.error(f"Belge ekleme hatası: {str(e)}")
            return None
    
    def _prepare_document(self, document: Dict[str, Any]) -> Document:
        """
        Belgeyi işleme için hazırlar
        
        Args:
            document: Hazırlanacak belge
            
        Returns:
            Document: Hazırlanmış belge
        """
        # Belge kimliği
        doc_id = document.get("id")
        if not doc_id:
            # Kimlik yoksa oluştur
            import uuid
            doc_id = str(uuid.uuid4())
        
        # Belge metni
        text = document.get("text", "")
        
        # Belge meta verileri
        metadata = document.get("metadata", {})
        
        # Belge nesnesi oluştur
        doc = Document(
            text=text,
            metadata=metadata,
            doc_id=doc_id
        )
        
        return doc
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Belge kimliğine göre belge getirir
        
        Args:
            document_id: Belge kimliği
            
        Returns:
            Optional[Dict[str, Any]]: Belge veya None
        """
        try:
            return self.vector_store.get_document(document_id)
        except Exception as e:
            logger.error(f"Belge getirme hatası: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """
        Belge siler
        
        Args:
            document_id: Silinecek belge kimliği
            
        Returns:
            bool: Silme başarılı mı
        """
        try:
            return self.vector_store.delete_document(document_id)
        except Exception as e:
            logger.error(f"Belge silme hatası: {str(e)}")
            return False
    
    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Belgeleri listeler
        
        Args:
            limit: Sonuç limiti
            offset: Sonuç başlangıcı
            filter_metadata: Meta veri filtresi
            
        Returns:
            Dict[str, Any]: Belge listesi
        """
        try:
            return self.vector_store.list_documents(limit, offset, filter_metadata)
        except Exception as e:
            logger.error(f"Belge listeleme hatası: {str(e)}")
            return {"documents": [], "count": 0, "total": 0}
    
    def search(
        self,
        query: str,
        options: Optional[Union[SearchOptions, Dict[str, Any]]] = None
    ) -> List[RetrievalResult]:
        """
        Belgelerde arama yapar
        
        Args:
            query: Arama sorgusu
            options: Arama seçenekleri
            
        Returns:
            List[RetrievalResult]: Arama sonuçları
        """
        try:
            # Seçenekleri hazırla
            if isinstance(options, dict):
                options = SearchOptions(**options)
            elif options is None:
                options = SearchOptions()
            
            # Arama tipine göre arama yap
            search_type = options.search_type.lower()
            
            # Arama sonuçları
            results = []
            
            # Çoklu model kullanımı
            if options.use_multi_model and options.models_to_use and len(options.models_to_use) > 0:
                # Her model için arama yap
                all_results = []
                
                for model_id in options.models_to_use:
                    # Model için arama seçenekleri
                    model_options = SearchOptions(
                        limit=options.limit,
                        min_score_threshold=options.min_score_threshold,
                        filter_metadata=options.filter_metadata,
                        include_metadata=options.include_metadata,
                        embedding_model=model_id,
                        search_type=search_type
                    )
                    
                    # Model için arama yap
                    model_results = self._search_with_type(query, model_options, search_type)
                    
                    # Sonuçları modelle işaretle
                    for result in model_results:
                        result.model_id = model_id
                        all_results.append(result)
                
                # Tüm sonuçları skora göre sırala
                results = sorted(all_results, key=lambda x: x.score, reverse=True)
                
                # Limit uygula
                results = results[:options.limit]
            else:
                # Tek model ile arama
                results = self._search_with_type(query, options, search_type)
            
            # Skor eşiği uygula
            if options.min_score_threshold is not None:
                results = [r for r in results if r.score >= options.min_score_threshold]
            
            return results
        except Exception as e:
            logger.error(f"Arama hatası: {str(e)}")
            return []
    
    def _search_with_type(
        self,
        query: str,
        options: SearchOptions,
        search_type: str
    ) -> List[RetrievalResult]:
        """
        Belirli bir arama tipine göre arama yapar
        
        Args:
            query: Arama sorgusu
            options: Arama seçenekleri
            search_type: Arama tipi
            
        Returns:
            List[RetrievalResult]: Arama sonuçları
        """
        # Arama tipi kontrolü
        if search_type == "vector":
            results = self.vector_searcher.search(
                query=query,
                limit=options.limit,
                filter_metadata=options.filter_metadata,
                include_metadata=options.include_metadata,
                embedding_model=options.embedding_model
            )
        elif search_type == "keyword":
            results = self.keyword_searcher.search(
                query=query,
                limit=options.limit,
                filter_metadata=options.filter_metadata,
                include_metadata=options.include_metadata
            )
        elif search_type == "hybrid":
            results = self.hybrid_searcher.search(
                query=query,
                limit=options.limit,
                filter_metadata=options.filter_metadata,
                include_metadata=options.include_metadata,
                embedding_model=options.embedding_model
            )
        else:
            logger.warning(f"Bilinmeyen arama tipi: {search_type}, hybrid kullanılıyor")
            results = self.hybrid_searcher.search(
                query=query,
                limit=options.limit,
                filter_metadata=options.filter_metadata,
                include_metadata=options.include_metadata,
                embedding_model=options.embedding_model
            )
        
        # Reranking uygula
        if self.reranker and self.config.reranking.enabled:
            results = self.reranker.rerank(query, results)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Servis istatistiklerini alır
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        try:
            stats = {}
            
            # Vector store istatistikleri
            if self.vector_store:
                stats.update(self.vector_store.get_stats())
            
            return stats
        except Exception as e:
            logger.error(f"İstatistik alma hatası: {str(e)}")
            return {}
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Kullanılabilir embedding modellerini alır
        
        Returns:
            List[Dict[str, Any]]: Modeller listesi
        """
        try:
            return self.vector_store.get_available_models()
        except Exception as e:
            logger.error(f"Model listesi alma hatası: {str(e)}")
            return []
    
    def get_embedding_coverage(self) -> Dict[str, Dict[str, Any]]:
        """
        Belgelerin her model için kapsama oranını alır
        
        Returns:
            Dict[str, Dict[str, Any]]: Kapsama oranları
        """
        try:
            return self.vector_store.get_embedding_coverage()
        except Exception as e:
            logger.error(f"Embedding kapsama oranı alma hatası: {str(e)}")
            return {}