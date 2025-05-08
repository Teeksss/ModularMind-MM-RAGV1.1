"""
Multi-stage retrieval pipeline modülü.
Çoklu aşamalı arama ile kompleks sorguları işler.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Union, Callable, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
import numpy as np

from ModularMind.API.services.retrieval.models import Document, Chunk
from ModularMind.API.services.retrieval.query_processing import QueryProcessor
from ModularMind.API.services.retrieval.reranking import Reranker
from ModularMind.API.services.llm_service import LLMService
from ModularMind.API.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class RetrievalStage(str, Enum):
    """Retrieval pipeline aşamaları."""
    QUERY_PROCESSING = "query_processing"     # Sorgu işleme (genişletme, ayırma)
    INITIAL_RETRIEVAL = "initial_retrieval"   # İlk arama
    RERANKING = "reranking"                   # Yeniden sıralama
    RECURSIVE_RETRIEVAL = "recursive_retrieval" # Özyinelemeli arama
    HYBRID_SEARCH = "hybrid_search"           # Hibrit arama
    CONSOLIDATION = "consolidation"           # Sonuçları birleştirme

@dataclass
class RetrievalStageConfig:
    """Retrieval aşaması yapılandırması."""
    stage_type: RetrievalStage
    enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MultiStageRetrieverConfig:
    """Multi-stage retriever yapılandırması."""
    stages: List[RetrievalStageConfig] = field(default_factory=list)
    top_k: int = 10
    reranking_top_k: int = 20
    timeout_seconds: float = 10.0
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600  # 1 saat
    
    def get_stage_config(self, stage_type: RetrievalStage) -> Optional[RetrievalStageConfig]:
        """Belirli bir aşamanın yapılandırmasını döndürür."""
        for stage in self.stages:
            if stage.stage_type == stage_type:
                return stage
        return None

class MultiStageRetriever:
    """
    Çok aşamalı retrieval pipeline sınıfı.
    
    Aşamalar:
    1. Sorgu İşleme: Kullanıcı sorgusunu genişletme, birden fazla alt sorguya ayırma
    2. İlk Arama: Temel vektör araması
    3. Yeniden Sıralama: İlk sonuçları yeniden puanlama
    4. Özyinelemeli Arama: İlk sonuçlardan ek sorgular oluşturma
    5. Hibrit Arama: Vektör + anahtar kelime kombinasyonu
    6. Birleştirme: Tüm sonuçları birleştirme ve sıralama
    """
    
    def __init__(
        self, 
        config: MultiStageRetrieverConfig,
        search_engine: Any,
        embedding_service: EmbeddingService,
        llm_service: LLMService
    ):
        """
        Args:
            config: Retriever yapılandırması
            search_engine: Arama motoru
            embedding_service: Embedding servisi
            llm_service: LLM servisi
        """
        self.config = config
        self.search_engine = search_engine
        self.embedding_service = embedding_service
        self.llm_service = llm_service
        
        # Sorgu işleyici
        self.query_processor = QueryProcessor(
            embedding_service=embedding_service,
            llm_service=llm_service
        )
        
        # Yeniden sıralayıcı
        self.reranker = Reranker(
            embedding_service=embedding_service,
            llm_service=llm_service
        )
        
        # Sonuç önbelleği
        self.result_cache = {}
        
        logger.info("MultiStageRetriever başlatıldı")
    
    def retrieve(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]] = None,
        top_k: Optional[int] = None
    ) -> List[Chunk]:
        """
        Sorgu için en iyi sonuçları almak üzere çok aşamalı arama yapar.
        
        Args:
            query: Kullanıcı sorgusu
            filters: Filtreleme kriterleri
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Chunk]: Arama sonuçları
        """
        if not top_k:
            top_k = self.config.top_k
            
        # Önbellekten sonuç kontrolü
        if self.config.enable_caching:
            cache_key = f"{query}_{str(filters)}_{top_k}"
            cached_result = self._get_cached_result(cache_key)
            
            if cached_result:
                logger.info(f"Önbellekten sonuç bulundu: {query}")
                return cached_result
        
        # Arama başlangıç zamanı
        start_time = time.time()
        
        # 1. Aşama: Sorgu İşleme
        processed_queries = self._process_query(query)
        
        # 2. Aşama: İlk Arama
        initial_results = self._initial_retrieval(processed_queries, filters, self.config.reranking_top_k)
        
        # 3. Aşama: Yeniden Sıralama
        reranked_results = self._rerank_results(query, initial_results)
        
        # 4. Aşama: Özyinelemeli Arama (opsiyonel)
        recursive_stage = self.config.get_stage_config(RetrievalStage.RECURSIVE_RETRIEVAL)
        recursive_results = []
        
        if recursive_stage and recursive_stage.enabled:
            recursive_results = self._recursive_retrieval(query, reranked_results[:5], filters)
        
        # 5. Aşama: Hibrit Arama (opsiyonel)
        hybrid_stage = self.config.get_stage_config(RetrievalStage.HYBRID_SEARCH)
        hybrid_results = []
        
        if hybrid_stage and hybrid_stage.enabled:
            hybrid_results = self._hybrid_search(query, filters, top_k)
        
        # 6. Aşama: Sonuçları Birleştir
        final_results = self._consolidate_results(
            query=query, 
            reranked_results=reranked_results,
            recursive_results=recursive_results, 
            hybrid_results=hybrid_results,
            top_k=top_k
        )
        
        # Toplam arama süresini hesapla
        elapsed = time.time() - start_time
        logger.info(f"Çok aşamalı arama tamamlandı: {len(final_results)} sonuç, {elapsed:.2f}s")
        
        # Sonuçları önbelleğe ekle
        if self.config.enable_caching:
            self._cache_result(cache_key, final_results)
        
        return final_results
    
    def generate_context(
        self, 
        query: str,
        context_size: int = 4000,
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Kullanıcı sorgusu için context oluşturur.
        
        Args:
            query: Kullanıcı sorgusu
            context_size: İstenen context boyutu (token)
            filters: Filtreleme kriterleri
            
        Returns:
            str: Birleştirilmiş context metni
        """
        # Sonuçları getir
        chunks = self.retrieve(query, filters)
        
        if not chunks:
            logger.warning(f"Sorgu için sonuç bulunamadı: {query}")
            return ""
        
        # Context'i oluştur
        context = ""
        current_size = 0
        token_estimate = 0.25  # Yaklaşık olarak 4 karakter = 1 token
        
        for i, chunk in enumerate(chunks):
            # Chunk boyutunu tahmin et
            chunk_size = int(len(chunk.text) * token_estimate)
            
            # Maksimum context boyutunu kontrol et
            if current_size + chunk_size > context_size:
                # Son eklenen chunk çok büyükse ve context boşsa, bu chunk'ı kırp
                if i == 0:
                    truncated_length = int(context_size / token_estimate)
                    context = chunk.text[:truncated_length] + "..."
                break
            
            # Chunk'ı ekle
            if i > 0:
                context += "\n\n"
            
            # Kaynak bilgisini ekle
            if chunk.metadata and ("source" in chunk.metadata or "title" in chunk.metadata):
                source = chunk.metadata.get("source", chunk.metadata.get("title", ""))
                context += f"[SOURCE: {source}]\n"
            
            # Chunk metnini ekle
            context += chunk.text
            
            # Boyutu güncelle
            current_size += chunk_size
        
        return context
    
    def _process_query(self, query: str) -> List[str]:
        """
        Sorguyu işler ve genişletir.
        
        Args:
            query: Orijinal sorgu
            
        Returns:
            List[str]: İşlenmiş ve genişletilmiş sorgular
        """
        stage_config = self.config.get_stage_config(RetrievalStage.QUERY_PROCESSING)
        
        if not stage_config or not stage_config.enabled:
            return [query]
        
        try:
            # Sorgu genişletme
            expanded_query = self.query_processor.expand_query(query)
            
            # Sorgu ayrıştırma
            should_decompose = stage_config.options.get("decompose_query", False)
            
            if should_decompose:
                sub_queries = self.query_processor.decompose_query(query)
                # Orijinal sorguyu ve alt sorguları birleştir
                return [expanded_query] + sub_queries
            else:
                return [expanded_query]
                
        except Exception as e:
            logger.error(f"Sorgu işleme hatası: {str(e)}")
            return [query]
    
    def _initial_retrieval(
        self, 
        queries: List[str], 
        filters: Optional[Dict[str, Any]], 
        top_k: int
    ) -> List[Chunk]:
        """
        İlk arama aşamasını gerçekleştirir.
        
        Args:
            queries: İşlenmiş sorgular
            filters: Filtreleme kriterleri
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Chunk]: İlk arama sonuçları
        """
        stage_config = self.config.get_stage_config(RetrievalStage.INITIAL_RETRIEVAL)
        
        if not stage_config or not stage_config.enabled:
            return []
        
        try:
            all_results = []
            seen_ids = set()
            
            for query in queries:
                # Her sorgu için bir vektör taraması yap
                query_embedding = self.embedding_service.get_embedding(query)
                
                # Arama
                search_results = self.search_engine.search(
                    query_embedding=query_embedding,
                    filters=filters,
                    limit=top_k
                )
                
                # Tekrarları önleyerek sonuçları birleştir
                for result in search_results:
                    if result.id not in seen_ids:
                        seen_ids.add(result.id)
                        all_results.append(result)
            
            return all_results
            
        except Exception as e:
            logger.error(f"İlk arama hatası: {str(e)}")
            return []
    
    def _rerank_results(self, query: str, initial_results: List[Chunk]) -> List[Chunk]:
        """
        İlk sonuçları yeniden sıralar.
        
        Args:
            query: Orijinal sorgu
            initial_results: İlk arama sonuçları
            
        Returns:
            List[Chunk]: Yeniden sıralanmış sonuçlar
        """
        stage_config = self.config.get_stage_config(RetrievalStage.RERANKING)
        
        if not stage_config or not stage_config.enabled or not initial_results:
            return initial_results
        
        try:
            # Yeniden sıralama modelini seç
            reranker_model = stage_config.options.get("model", "default")
            
            # Sonuçları yeniden sırala
            reranked_results = self.reranker.rerank(
                query=query,
                documents=initial_results,
                model=reranker_model
            )
            
            return reranked_results
            
        except Exception as e:
            logger.error(f"Yeniden sıralama hatası: {str(e)}")
            return initial_results
    
    def _recursive_retrieval(
        self, 
        original_query: str, 
        top_results: List[Chunk],
        filters: Optional[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        İlk sonuçlara dayalı özyinelemeli arama yapar.
        
        Args:
            original_query: Orijinal sorgu
            top_results: İlk N sonuç
            filters: Filtreleme kriterleri
            
        Returns:
            List[Chunk]: Özyinelemeli arama sonuçları
        """
        if not top_results:
            return []
            
        stage_config = self.config.get_stage_config(RetrievalStage.RECURSIVE_RETRIEVAL)
        
        if not stage_config or not stage_config.enabled:
            return []
        
        try:
            # İlk sonuçların metinlerini al
            context_texts = [chunk.text for chunk in top_results]
            context = "\n\n".join(context_texts)
            
            # İlk sonuçları kullanarak ek sorgular oluştur
            follow_up_query_prompt = f"""
            Orijinal Sorgu: {original_query}
            
            İlk arama sonuçlarına göre, orijinal sorguyu cevaplamak için ek bilgi toplayacak 1-3 adet takip sorusu oluşturun.
            
            İlk sonuçlardan bazı bilgiler:
            {context}
            
            Takip Soruları (maddeler halinde):
            """
            
            # LLM ile ek sorgular oluştur
            llm_response = self.llm_service.generate_text(
                prompt=follow_up_query_prompt,
                max_tokens=200
            )
            
            # Yanıtı ayrıştır ve sorguları çıkar
            follow_up_queries = []
            for line in llm_response.split("\n"):
                line = line.strip()
                if line.startswith("-") or line.startswith("*") or line.startswith("1.") or line.startswith("2.") or line.startswith("3."):
                    query_text = line.lstrip("- *123.").strip()
                    if query_text:
                        follow_up_queries.append(query_text)
            
            # En fazla 3 takip sorusu kullan
            follow_up_queries = follow_up_queries[:3]
            
            if not follow_up_queries:
                return []
                
            logger.info(f"Özyinelemeli sorgular oluşturuldu: {follow_up_queries}")
            
            # Her takip sorusu için arama yap
            recursive_results = []
            seen_ids = set([chunk.id for chunk in top_results])  # İlk sonuçları tekrar getirme
            
            for query in follow_up_queries:
                # Her sorgu için bir vektör taraması yap
                query_embedding = self.embedding_service.get_embedding(query)
                
                # Arama
                search_results = self.search_engine.search(
                    query_embedding=query_embedding,
                    filters=filters,
                    limit=5  # Her takip sorgusu için daha az sonuç getir
                )
                
                # Tekrarları önleyerek sonuçları birleştir
                for result in search_results:
                    if result.id not in seen_ids:
                        seen_ids.add(result.id)
                        recursive_results.append(result)
            
            return recursive_results
            
        except Exception as e:
            logger.error(f"Özyinelemeli arama hatası: {str(e)}")
            return []
    
    def _hybrid_search(
        self, 
        query: str, 
        filters: Optional[Dict[str, Any]],
        top_k: int
    ) -> List[Chunk]:
        """
        Hibrit arama yapar (vektör + anahtar kelime).
        
        Args:
            query: Orijinal sorgu
            filters: Filtreleme kriterleri
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Chunk]: Hibrit arama sonuçları
        """
        stage_config = self.config.get_stage_config(RetrievalStage.HYBRID_SEARCH)
        
        if not stage_config or not stage_config.enabled:
            return []
        
        try:
            # Vektör arama ağırlığı (0-1 arası)
            vector_weight = stage_config.options.get("vector_weight", 0.7)
            
            # Hibrit arama (arama motoru destekliyorsa)
            if hasattr(self.search_engine, "hybrid_search"):
                hybrid_results = self.search_engine.hybrid_search(
                    query=query,
                    filters=filters,
                    limit=top_k,
                    vector_weight=vector_weight
                )
                
                return hybrid_results
                
            # Hybrit arama destek yoksa, manuel olarak iki aramayı birleştir
            else:
                # Vektör araması
                query_embedding = self.embedding_service.get_embedding(query)
                vector_results = self.search_engine.search(
                    query_embedding=query_embedding,
                    filters=filters,
                    limit=top_k
                )
                
                # Anahtar kelime araması (arama motoru destekliyorsa)
                keyword_results = []
                if hasattr(self.search_engine, "keyword_search"):
                    keyword_results = self.search_engine.keyword_search(
                        query=query,
                        filters=filters,
                        limit=top_k
                    )
                
                # Manuel hibrit sıralama yap
                return self._blend_search_results(vector_results, keyword_results, vector_weight, top_k)
            
        except Exception as e:
            logger.error(f"Hibrit arama hatası: {str(e)}")
            return []
    
    def _consolidate_results(
        self,
        query: str,
        reranked_results: List[Chunk],
        recursive_results: List[Chunk],
        hybrid_results: List[Chunk],
        top_k: int
    ) -> List[Chunk]:
        """
        Tüm arama sonuçlarını birleştirir ve en iyi N sonucu döndürür.
        
        Args:
            query: Orijinal sorgu
            reranked_results: Yeniden sıralanmış sonuçlar
            recursive_results: Özyinelemeli arama sonuçları
            hybrid_results: Hibrit arama sonuçları
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Chunk]: Birleştirilmiş ve sıralanmış sonuçlar
        """
        stage_config = self.config.get_stage_config(RetrievalStage.CONSOLIDATION)
        
        if not stage_config or not stage_config.enabled:
            # Sadece yeniden sıralanmış sonuçları döndür
            return reranked_results[:top_k]
        
        try:
            # Tüm sonuçları birleştir, tekrarları önle
            all_results = []
            seen_ids = set()
            
            # Yeniden sıralanmış sonuçlara öncelik ver
            for chunk in reranked_results:
                if chunk.id not in seen_ids:
                    seen_ids.add(chunk.id)
                    all_results.append(chunk)
            
            # Sonra özyinelemeli arama sonuçlarını ekle
            for chunk in recursive_results:
                if chunk.id not in seen_ids:
                    seen_ids.add(chunk.id)
                    all_results.append(chunk)
            
            # Son olarak hibrit arama sonuçlarını ekle
            for chunk in hybrid_results:
                if chunk.id not in seen_ids:
                    seen_ids.add(chunk.id)
                    all_results.append(chunk)
            
            # Sonuçlar zaten sıralanmış olduğundan, sadece ilk N'i döndür
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Sonuç birleştirme hatası: {str(e)}")
            return reranked_results[:top_k]
    
    def _blend_search_results(
        self,
        vector_results: List[Chunk],
        keyword_results: List[Chunk],
        vector_weight: float,
        top_k: int
    ) -> List[Chunk]:
        """
        Vektör ve anahtar kelime arama sonuçlarını birleştirir.
        
        Args:
            vector_results: Vektör arama sonuçları
            keyword_results: Anahtar kelime arama sonuçları
            vector_weight: Vektör araması ağırlığı (0-1)
            top_k: Getirilecek en fazla sonuç sayısı
            
        Returns:
            List[Chunk]: Birleştirilmiş sonuçlar
        """
        if not keyword_results:
            return vector_results[:top_k]
            
        if not vector_results:
            return keyword_results[:top_k]
        
        # Tüm sonuçları birleştir
        all_results = {}
        
        # Vektör sonuçlarını ekle
        for i, chunk in enumerate(vector_results):
            # Vektör sıralamasına göre puan hesapla
            vector_score = 1.0 - (i / len(vector_results))
            all_results[chunk.id] = {
                "chunk": chunk,
                "vector_score": vector_score,
                "keyword_score": 0.0
            }
        
        # Anahtar kelime sonuçlarını ekle
        for i, chunk in enumerate(keyword_results):
            # Anahtar kelime sıralamasına göre puan hesapla
            keyword_score = 1.0 - (i / len(keyword_results))
            
            if chunk.id in all_results:
                all_results[chunk.id]["keyword_score"] = keyword_score
            else:
                all_results[chunk.id] = {
                    "chunk": chunk,
                    "vector_score": 0.0,
                    "keyword_score": keyword_score
                }
        
        # Hibrit puanı hesapla ve sonuçları sırala
        scored_results = []
        
        for chunk_id, scores in all_results.items():
            # Hibrit puanı hesapla
            hybrid_score = (vector_weight * scores["vector_score"]) + ((1 - vector_weight) * scores["keyword_score"])
            
            scored_results.append({
                "chunk": scores["chunk"],
                "score": hybrid_score
            })
        
        # Puana göre sırala ve en iyi N sonucu al
        scored_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = [item["chunk"] for item in scored_results[:top_k]]
        
        return top_results
    
    def _get_cached_result(self, cache_key: str) -> Optional[List[Chunk]]:
        """Önbellekten sonuç getir."""
        if cache_key in self.result_cache:
            entry = self.result_cache[cache_key]
            cache_time = entry["timestamp"]
            current_time = time.time()
            
            # Önbellek TTL kontrolü
            if current_time - cache_time <= self.config.cache_ttl_seconds:
                return entry["results"]
                
            # Önbellek süresi dolmuş
            del self.result_cache[cache_key]
            
        return None
    
    def _cache_result(self, cache_key: str, results: List[Chunk]) -> None:
        """Sonuçları önbelleğe ekle."""
        self.result_cache[cache_key] = {
            "results": results,
            "timestamp": time.time()
        }
        
        # Önbellek temizliği
        if len(self.result_cache) > 1000:  # Önbellek boyutu limiti
            self._clean_cache()
    
    def _clean_cache(self) -> None:
        """Süresi dolmuş önbellek girdilerini temizle."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.result_cache.items():
            if current_time - entry["timestamp"] > self.config.cache_ttl_seconds:
                expired_keys.append(key)
        
        # Süresi dolmuş girdileri kaldır
        for key in expired_keys:
            del self.result_cache[key]
        
        # Eğer hala çok fazla girdi varsa, en eski girdileri kaldır
        if len(self.result_cache) > 800:  # Hedef boyut
            sorted_entries = sorted(
                [(k, v["timestamp"]) for k, v in self.result_cache.items()],
                key=lambda x: x[1]
            )
            
            # En eski girdileri sil
            for key, _ in sorted_entries[:200]:  # En eski 200 girdiyi sil
                del self.result_cache[key]