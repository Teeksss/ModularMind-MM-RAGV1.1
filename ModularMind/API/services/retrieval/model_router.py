"""
Akıllı model yönlendirme modülü.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Set, Union

from ModularMind.API.services.retrieval.models import VectorStore
from ModularMind.API.services.retrieval.service import RetrievalService, SearchOptions, RetrievalResult
from ModularMind.API.services.embedding.service import EmbeddingService

logger = logging.getLogger(__name__)

class ModelRouterConfig:
    """Model yönlendirici yapılandırması."""
    
    def __init__(
        self,
        default_model_id: str,
        language_models: Dict[str, str],
        domain_models: Dict[str, str],
        fallback_model_id: str,
        enable_auto_routing: bool = True,
        enable_ensemble: bool = True,
        ensemble_method: str = "rank_fusion",
        result_aggregation: str = "weighted_average"
    ):
        self.default_model_id = default_model_id
        self.language_models = language_models
        self.domain_models = domain_models
        self.fallback_model_id = fallback_model_id
        self.enable_auto_routing = enable_auto_routing
        self.enable_ensemble = enable_ensemble
        self.ensemble_method = ensemble_method
        self.result_aggregation = result_aggregation
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelRouterConfig':
        """Dict'ten yapılandırma oluşturur."""
        return cls(
            default_model_id=data.get("default_model_id", "default"),
            language_models=data.get("language_models", {}),
            domain_models=data.get("domain_models", {}),
            fallback_model_id=data.get("fallback_model_id", "default"),
            enable_auto_routing=data.get("enable_auto_routing", True),
            enable_ensemble=data.get("enable_ensemble", True),
            ensemble_method=data.get("ensemble_method", "rank_fusion"),
            result_aggregation=data.get("result_aggregation", "weighted_average")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür."""
        return {
            "default_model_id": self.default_model_id,
            "language_models": self.language_models,
            "domain_models": self.domain_models,
            "fallback_model_id": self.fallback_model_id,
            "enable_auto_routing": self.enable_auto_routing,
            "enable_ensemble": self.enable_ensemble,
            "ensemble_method": self.ensemble_method,
            "result_aggregation": self.result_aggregation
        }

class ModelRouter:
    """
    Akıllı model yönlendirici.
    
    Sorgulara göre en uygun embedding modelini seçer veya 
    birden fazla modelin sonuçlarını birleştirir.
    """
    
    def __init__(
        self,
        config: ModelRouterConfig,
        retrieval_service: RetrievalService,
        embedding_service: EmbeddingService
    ):
        self.config = config
        self.retrieval_service = retrieval_service
        self.embedding_service = embedding_service
        
        # Dil algılama
        self.language_patterns = {
            "tr": r"[çğıöşüÇĞİÖŞÜ]|[a-zA-Z]+[çğıöşüÇĞİÖŞÜ]|[çğıöşüÇĞİÖŞÜ][a-zA-Z]+",
            "en": r"\b(the|is|are|a|an|in|on|at|to|for|with|by)\b",
            "es": r"\b(el|la|los|las|es|son|en|para|con|por)\b",
            "fr": r"\b(le|la|les|est|sont|dans|sur|à|pour|avec|par)\b",
            "de": r"\b(der|die|das|ist|sind|in|auf|für|mit|durch)\b"
        }
        
        # Alan algılama
        self.domain_keywords = {}
        for domain, keywords in {
            "finance": ["financial", "bank", "money", "invest", "market", "stock", "economy", "finans", "banka", "para", "yatırım", "piyasa", "borsa", "ekonomi"],
            "legal": ["legal", "law", "court", "justice", "contract", "regulation", "yasal", "hukuk", "mahkeme", "adalet", "sözleşme", "mevzuat"],
            "medical": ["medical", "health", "doctor", "patient", "disease", "treatment", "tıbbi", "sağlık", "doktor", "hasta", "hastalık", "tedavi"],
            "tech": ["technology", "software", "hardware", "programming", "computer", "code", "teknoloji", "yazılım", "donanım", "programlama", "bilgisayar", "kod"]
        }.items():
            self.domain_keywords[domain] = [kw.lower() for kw in keywords]
    
    def detect_language(self, text: str) -> Optional[str]:
        """Metni analiz ederek dili saptar."""
        text = text.lower()
        
        # Her dil için şablonu kontrol et
        for lang, pattern in self.language_patterns.items():
            match_count = len(re.findall(pattern, text))
            
            if match_count > 0:
                # Türkçe karakterler ayırt edici
                if lang == "tr" and match_count > 0:
                    return "tr"
                
                # Diğer diller için kelime sayısına göre değerlendir
                words = len(text.split())
                if match_count / words > 0.1:  # %10 eşik
                    return lang
        
        return None
    
    def detect_domain(self, text: str) -> Optional[str]:
        """Metni analiz ederek konuyu saptar."""
        text = text.lower()
        
        # Alanlar için kelime sayılarını hesapla
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            
            domain_scores[domain] = score
        
        # En yüksek skora sahip alanı bul
        if domain_scores:
            max_domain = max(domain_scores.items(), key=lambda x: x[1])
            if max_domain[1] > 0:  # En az bir eşleşme varsa
                return max_domain[0]
        
        return None
    
    def select_model(self, query: str) -> List[str]:
        """
        Sorguya göre uygun modeli veya modelleri seçer.
        
        Args:
            query: Sorgu metni
            
        Returns:
            List[str]: Uygun model ID'leri
        """
        # Otomatik yönlendirme devre dışıysa varsayılan model
        if not self.config.enable_auto_routing:
            return [self.config.default_model_id]
        
        selected_models = []
        
        # Dil tespiti
        lang = self.detect_language(query)
        if lang and lang in self.config.language_models:
            selected_models.append(self.config.language_models[lang])
        
        # Alan tespiti
        domain = self.detect_domain(query)
        if domain and domain in self.config.domain_models:
            selected_models.append(self.config.domain_models[domain])
        
        # Eğer model seçilmediyse veya ensemble modu açıksa modeller listesine eklemeler yap
        if not selected_models:
            selected_models.append(self.config.default_model_id)
        elif self.config.enable_ensemble and len(selected_models) == 1:
            # Yedek model olarak varsayılan ekle
            if selected_models[0] != self.config.default_model_id:
                selected_models.append(self.config.default_model_id)
        
        return selected_models
    
    def combine_results(
        self,
        results_by_model: Dict[str, List[RetrievalResult]],
        method: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Farklı modellerden gelen sonuçları birleştirir.
        
        Args:
            results_by_model: Model bazında sonuçlar
            method: Birleştirme metodu (None ise config'ten alınır)
            
        Returns:
            List[RetrievalResult]: Birleştirilmiş sonuçlar
        """
        if method is None:
            method = self.config.ensemble_method
        
        if method == "rank_fusion":
            return self._rank_fusion(results_by_model)
        elif method == "max_score":
            return self._max_score(results_by_model)
        elif method == "weighted_average":
            return self._weighted_average(results_by_model)
        else:
            # Varsayılan olarak rank fusion kullan
            return self._rank_fusion(results_by_model)
    
    def _rank_fusion(self, results_by_model: Dict[str, List[RetrievalResult]]) -> List[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF) algoritması ile sonuçları birleştirir.
        """
        # Tüm chunk_id'leri topla
        all_chunk_ids = set()
        for results in results_by_model.values():
            for result in results:
                all_chunk_ids.add(result.chunk_id)
        
        # Her sonuç için RRF skorunu hesapla
        k = 60  # RRF parametresi
        rrf_scores = {}
        
        for chunk_id in all_chunk_ids:
            rrf_scores[chunk_id] = 0
            
            for model_id, results in results_by_model.items():
                # Bu sonucun modeldeki sırasını bul
                rank = None
                result_obj = None
                
                for i, result in enumerate(results):
                    if result.chunk_id == chunk_id:
                        rank = i + 1  # 1-tabanlı sıralama
                        result_obj = result
                        break
                
                # Sıralamaya göre RRF skoru ekle
                if rank is not None:
                    rrf_scores[chunk_id] += 1.0 / (k + rank)
        
        # En iyi sonuçları döndür
        combined_results = []
        
        for chunk_id, rrf_score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            # Bu chunk_id için en yüksek skorlu sonucu bul
            best_result = None
            best_score = -1
            
            for results in results_by_model.values():
                for result in results:
                    if result.chunk_id == chunk_id and result.score > best_score:
                        best_result = result
                        best_score = result.score
            
            if best_result:
                # RRF skorunu kullan ama orijinal sonuç nesnesini skor olarak güncelle
                best_result.score = rrf_score
                best_result.source = "ensemble:rank_fusion"
                combined_results.append(best_result)
        
        return combined_results
    
    def _max_score(self, results_by_model: Dict[str, List[RetrievalResult]]) -> List[RetrievalResult]:
        """
        Her chunk için maksimum skoru kullanarak sonuçları birleştirir.
        """
        # Tüm chunk_id'leri topla
        chunk_best_scores = {}
        chunk_best_results = {}
        
        for model_id, results in results_by_model.items():
            for result in results:
                chunk_id = result.chunk_id
                
                if chunk_id not in chunk_best_scores or result.score > chunk_best_scores[chunk_id]:
                    chunk_best_scores[chunk_id] = result.score
                    chunk_best_results[chunk_id] = result
        
        # En iyi sonuçları döndür
        combined_results = []
        
        for chunk_id, score in sorted(chunk_best_scores.items(), key=lambda x: x[1], reverse=True):
            result = chunk_best_results[chunk_id]
            result.source = "ensemble:max_score"
            combined_results.append(result)
        
        return combined_results
    
    def _weighted_average(self, results_by_model: Dict[str, List[RetrievalResult]]) -> List[RetrievalResult]:
        """
        Her chunk için ağırlıklı ortalama skoru hesaplayarak sonuçları birleştirir.
        """
        # Model ağırlıkları - basitlik için eşit ağırlık
        model_weights = {model_id: 1.0 for model_id in results_by_model.keys()}
        
        # Tüm chunk'ları ve skorları topla
        chunk_scores = {}
        chunk_counts = {}
        chunk_results = {}
        
        for model_id, results in results_by_model.items():
            model_weight = model_weights.get(model_id, 1.0)
            
            for result in results:
                chunk_id = result.chunk_id
                weighted_score = result.score * model_weight
                
                if chunk_id not in chunk_scores:
                    chunk_scores[chunk_id] = weighted_score
                    chunk_counts[chunk_id] = model_weight
                    chunk_results[chunk_id] = result
                else:
                    chunk_scores[chunk_id] += weighted_score
                    chunk_counts[chunk_id] += model_weight
        
        # Ortalama skorları hesapla
        average_scores = {}
        for chunk_id, total_score in chunk_scores.items():
            total_weight = chunk_counts[chunk_id]
            average_scores[chunk_id] = total_score / total_weight
        
        # En iyi sonuçları döndür
        combined_results = []
        
        for chunk_id, score in sorted(average_scores.items(), key=lambda x: x[1], reverse=True):
            result = chunk_results[chunk_id]
            result.score = score
            result.source = "ensemble:weighted_average"
            combined_results.append(result)
        
        return combined_results
    
    async def search(
        self,
        query: str,
        options: Optional[SearchOptions] = None
    ) -> List[RetrievalResult]:
        """
        Akıllı model seçimiyle arama yapar.
        
        Args:
            query: Sorgu metni
            options: Arama seçenekleri
            
        Returns:
            List[RetrievalResult]: Arama sonuçları
        """
        options = options or SearchOptions()
        
        # Belirli bir model belirtilmişse onu kullan
        if options.embedding_model:
            # Arama yap
            search_options = SearchOptions(
                limit=options.limit,
                min_score_threshold=options.min_score_threshold,
                filter_metadata=options.filter_metadata,
                embedding_model=options.embedding_model,
                search_type=options.search_type
            )
            
            return self.retrieval_service.search(query, search_options)
        else:
            # Sorguya göre model seç
            selected_models = self.select_model(query)
            
            # Tek model seçilmişse normal arama
            if len(selected_models) == 1 or not self.config.enable_ensemble:
                embedding_model = selected_models[0]
                
                # Arama yap
                search_options = SearchOptions(
                    limit=options.limit,
                    min_score_threshold=options.min_score_threshold,
                    filter_metadata=options.filter_metadata,
                    embedding_model=embedding_model,
                    search_type=options.search_type
                )
                
                return self.retrieval_service.search(query, search_options)
            else:
                # Çoklu model araması
                results_by_model = {}
                
                for model_id in selected_models:
                    # Arama yap
                    search_options = SearchOptions(
                        limit=options.limit,
                        min_score_threshold=options.min_score_threshold,
                        filter_metadata=options.filter_metadata,
                        embedding_model=model_id,
                        search_type=options.search_type
                    )
                    
                    results = self.retrieval_service.search(query, search_options)
                    results_by_model[model_id] = results
                
                # Sonuçları birleştir
                return self.combine_results(results_by_model)
    
    async def query(
        self,
        query: str,
        context_limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        llm_model: Optional[str] = None,
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        RAG sorgusu yapar.
        
        Args:
            query: Sorgu metni
            context_limit: Bağlam limiti
            filter_metadata: Metadata filtresi
            llm_model: LLM model ID
            system_message: Sistem mesajı
            
        Returns:
            Dict[str, Any]: RAG yanıtı
        """
        # Sorguya göre model seç
        selected_models = self.select_model(query)
        
        # Arama seçenekleri
        search_options = SearchOptions(
            limit=context_limit,
            filter_metadata=filter_metadata,
            search_type="hybrid"
        )
        
        results_by_model = {}
        all_results = []
        
        # Akıllı model yönlendirme aktifse ve birden fazla model seçildiyse
        if self.config.enable_auto_routing and len(selected_models) > 1 and self.config.enable_ensemble:
            # Her model için arama yap
            for model_id in selected_models:
                search_options.embedding_model = model_id
                results = self.retrieval_service.search(query, search_options)
                results_by_model[model_id] = results
            
            # Sonuçları birleştir
            all_results = self.combine_results(results_by_model)
            
            # Kullanılan modelleri kaydet
            used_models = list(results_by_model.keys())
        else:
            # Tek modelli arama
            model_id = selected_models[0]
            search_options.embedding_model = model_id
            all_results = self.retrieval_service.search(query, search_options)
            used_models = [model_id]
        
        # RAG yanıtını oluştur
        if all_results:
            # LLM servisini kullanarak yanıt oluştur
            from ModularMind.API.services.rag.service import generate_rag_response
            
            response = await generate_rag_response(
                query=query,
                contexts=all_results,
                llm_model=llm_model,
                system_message=system_message
            )
            
            return {
                "answer": response,
                "sources": [result.to_dict() for result in all_results],
                "embedding_models": used_models
            }
        else:
            # Sonuç bulunamadıysa LLM'i doğrudan kullan
            from ModularMind.API.services.llm.service import LLMService
            
            llm_service = LLMService.get_instance()
            
            response = llm_service.generate_text(
                f"Soru: {query}\n\nCevap:",
                model_id=llm_model,
                system_message=system_message or "Sen yardımcı bir asistansın."
            )
            
            return {
                "answer": response,
                "sources": [],
                "embedding_models": []
            }