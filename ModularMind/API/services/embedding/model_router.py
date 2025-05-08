"""
Embedding modelleri için otomatik yönlendirme modülü.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Set
import langdetect
from collections import defaultdict

logger = logging.getLogger(__name__)

class ModelRouter:
    """
    Sorgulara ve belgelere uygun embedding modellerini otomatik seçen sınıf.
    
    Sorgu dili, domain alanı ve özel kuralları değerlendirerek en uygun 
    embedding modelini otomatik olarak belirler.
    """
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        embedding_service=None
    ):
        """
        Model router'ı başlatır
        
        Args:
            config: Router yapılandırması
            embedding_service: Embedding servisi 
        """
        self.config = config or {}
        self.embedding_service = embedding_service
        
        # Varsayılan model
        self.default_model_id = self.config.get("default_model_id")
        
        # Dil bazlı yönlendirme
        self.language_models = self.config.get("language_models", {})
        
        # Alan bazlı yönlendirme
        self.domain_models = self.config.get("domain_models", {})
        
        # Yedek model
        self.fallback_model_id = self.config.get("fallback_model_id")
        
        # Yönlendirme özelliği
        self.enable_auto_routing = self.config.get("enable_auto_routing", True)
        
        # Ensemble aktif mi
        self.enable_ensemble = self.config.get("enable_ensemble", False)
        
        # Ensemble yöntemi
        self.ensemble_method = self.config.get("ensemble_method", "weighted_average")
        
        # Ensemble ağırlıkları
        self.model_weights = self.config.get("model_weights", {})
        
        # Dil tanıma önbelleği
        self.language_cache = {}
        
        # Dil listesi
        self.supported_languages = set(self.language_models.keys())
    
    def select_model_for_text(self, text: str) -> str:
        """
        Verilen metin için en uygun modeli seçer
        
        Args:
            text: Değerlendirilecek metin
            
        Returns:
            str: Seçilen model kimliği
        """
        if not self.enable_auto_routing:
            # Otomatik yönlendirme devre dışıysa varsayılan modeli kullan
            return self.default_model_id or self._get_embedding_service_default()
        
        # Çok kısa metinler için varsayılan model kullan
        if len(text.strip()) < 10:
            return self.default_model_id or self._get_embedding_service_default()
        
        # Metni analiz et ve modeli seç
        lang = self._detect_language(text)
        domain = self._detect_domain(text)
        
        # Önce dil bazlı modellere bak
        if lang and lang in self.language_models:
            model_id = self.language_models.get(lang)
            if model_id:
                logger.debug(f"Dil bazlı model seçildi: {model_id} (dil: {lang})")
                return model_id
        
        # Sonra domain bazlı modellere bak
        if domain and domain in self.domain_models:
            model_id = self.domain_models.get(domain)
            if model_id:
                logger.debug(f"Domain bazlı model seçildi: {model_id} (domain: {domain})")
                return model_id
        
        # Hiçbiri yoksa varsayılan model
        if self.default_model_id:
            return self.default_model_id
        
        # Yedek model
        if self.fallback_model_id:
            return self.fallback_model_id
        
        # Embedding servisinin varsayılanını kullan
        return self._get_embedding_service_default()
    
    def select_models_for_text(self, text: str) -> List[str]:
        """
        Verilen metin için uygun modelleri seçer (ensemble için)
        
        Args:
            text: Değerlendirilecek metin
            
        Returns:
            List[str]: Seçilen model kimlikleri
        """
        if not self.enable_ensemble:
            # Ensemble devre dışıysa tek model döndür
            return [self.select_model_for_text(text)]
        
        selected_models = set()
        
        # Dil tespiti
        lang = self._detect_language(text)
        if lang and lang in self.language_models:
            selected_models.add(self.language_models[lang])
        
        # Domain tespiti
        domain = self._detect_domain(text)
        if domain and domain in self.domain_models:
            selected_models.add(self.domain_models[domain])
        
        # En az iki model olsun
        if len(selected_models) < 2:
            # Varsayılan model ekle
            if self.default_model_id and self.default_model_id not in selected_models:
                selected_models.add(self.default_model_id)
            
            # Hala 2 değilse yedek modeli ekle
            if len(selected_models) < 2 and self.fallback_model_id and self.fallback_model_id not in selected_models:
                selected_models.add(self.fallback_model_id)
            
            # Yine 2 değilse tüm özel modelleri ekle
            available_models = self._get_available_models()
            if len(selected_models) < 2 and available_models:
                for model_id in available_models:
                    if model_id not in selected_models:
                        selected_models.add(model_id)
                        if len(selected_models) >= 3:  # En fazla 3 model
                            break
        
        # Model listesini döndür
        return list(selected_models)
    
    def compute_ensemble_embedding(
        self,
        text: str,
        models_to_use: Optional[List[str]] = None
    ) -> Optional[List[float]]:
        """
        Verilen metin için ensemble embedding hesaplar
        
        Args:
            text: Embedding oluşturulacak metin
            models_to_use: Kullanılacak modeller listesi
            
        Returns:
            Optional[List[float]]: Ensemble embedding vektörü
        """
        if not self.embedding_service:
            logger.error("Embedding servis başlatılmamış")
            return None
        
        # Kullanılacak modelleri seç
        models = models_to_use or self.select_models_for_text(text)
        
        if not models:
            logger.error("Embedding için model seçilemedi")
            return None
        
        # Her model için embedding hesapla
        embeddings = {}
        for model_id in models:
            try:
                embedding = self.embedding_service.create_embedding(text, model_id)
                if embedding:
                    embeddings[model_id] = embedding
            except Exception as e:
                logger.error(f"{model_id} modeli ile embedding hesaplanırken hata: {str(e)}")
        
        # Embeddingler boşsa null döndür
        if not embeddings:
            logger.warning("Hiçbir model için embedding hesaplanamadı")
            return None
        
        # Tek model varsa direkt döndür
        if len(embeddings) == 1:
            return list(embeddings.values())[0]
        
        # Ensemble hesapla
        if self.ensemble_method == "weighted_average":
            return self._compute_weighted_average(embeddings)
        elif self.ensemble_method == "concatenate":
            return self._compute_concatenation(embeddings)
        else:
            # Varsayılan olarak ağırlıklı ortalama
            return self._compute_weighted_average(embeddings)
    
    def _compute_weighted_average(self, embeddings: Dict[str, List[float]]) -> List[float]:
        """
        Embeddingler için ağırlıklı ortalama hesaplar
        
        Args:
            embeddings: Model kimliği -> embedding vektörü eşlemesi
            
        Returns:
            List[float]: Ağırlıklı ortalama embedding
        """
        import numpy as np
        
        # Tüm vektörlerin aynı boyutta olduğunu kontrol et
        dims = {model_id: len(vec) for model_id, vec in embeddings.items()}
        
        # Farklı boyutlar varsa hata ver
        if len(set(dims.values())) > 1:
            logger.error(f"Farklı boyutlu embeddingler ensemble edilemez: {dims}")
            # En büyük vektörü döndür
            max_model = max(dims.items(), key=lambda x: x[1])[0]
            return embeddings[max_model]
        
        # Ağırlıkları belirle (varsayılan 1.0)
        weights = {}
        total_weight = 0.0
        
        for model_id in embeddings:
            weight = self.model_weights.get(model_id, 1.0)
            weights[model_id] = weight
            total_weight += weight
        
        # Ağırlıkları normalize et
        if total_weight > 0:
            weights = {model_id: w / total_weight for model_id, w in weights.items()}
        else:
            # Eşit ağırlık
            weights = {model_id: 1.0 / len(embeddings) for model_id in embeddings}
        
        # Ağırlıklı ortalama hesapla
        result = None
        for model_id, embedding in embeddings.items():
            weight = weights[model_id]
            embedding_np = np.array(embedding)
            
            if result is None:
                result = embedding_np * weight
            else:
                result += embedding_np * weight
        
        # Normalize et
        result_norm = np.linalg.norm(result)
        if result_norm > 0:
            result = result / result_norm
        
        return result.tolist()
    
    def _compute_concatenation(self, embeddings: Dict[str, List[float]]) -> List[float]:
        """
        Embeddinglari birleştirir
        
        Args:
            embeddings: Model kimliği -> embedding vektörü eşlemesi
            
        Returns:
            List[float]: Birleştirilmiş embedding
        """
        import numpy as np
        
        # Embeddinglari sırala (tutarlı sonuç için)
        sorted_models = sorted(embeddings.keys())
        concatenated = []
        
        for model_id in sorted_models:
            embedding = embeddings[model_id]
            concatenated.extend(embedding)
        
        # Boyut çok büyükse boyut azaltma uygula
        if len(concatenated) > 5000:
            logger.warning(f"Birleştirilmiş embedding çok büyük: {len(concatenated)}, boyut azaltma uygulanıyor")
            # PCA gibi bir boyut azaltma yöntemi uygulanabilir
            # Şimdilik basit bir örnekleme yapalım
            step = len(concatenated) // 2000
            concatenated = concatenated[::step]
        
        # Normalize et
        concatenated_np = np.array(concatenated)
        norm = np.linalg.norm(concatenated_np)
        if norm > 0:
            concatenated_np = concatenated_np / norm
        
        return concatenated_np.tolist()
    
    def _detect_language(self, text: str) -> Optional[str]:
        """
        Metnin dilini tespit eder
        
        Args:
            text: Dili tespit edilecek metin
            
        Returns:
            Optional[str]: Dil kodu veya None
        """
        # Çok kısa metinlerde dil tespiti güvenilir değildir
        if len(text.strip()) < 20:
            return None
        
        # Önbellekte varsa döndür
        text_hash = hash(text[:100])  # Performans için ilk 100 karakter
        if text_hash in self.language_cache:
            return self.language_cache[text_hash]
        
        try:
            # Dil tespiti
            lang = langdetect.detect(text)
            
            # Sadece desteklenen dilleri kabul et
            if lang in self.supported_languages:
                self.language_cache[text_hash] = lang
                return lang
            
            return None
        except Exception as e:
            logger.error(f"Dil tespiti hatası: {str(e)}")
            return None
    
    def _detect_domain(self, text: str) -> Optional[str]:
        """
        Metnin alan/domain'ini tespit eder
        
        Args:
            text: Alanı tespit edilecek metin
            
        Returns:
            Optional[str]: Alan/domain adı veya None
        """
        # Desteklenen alanlar
        domains = {
            "finance": [
                "finance", "financial", "money", "banking", "investment", "stock", "market",
                "economy", "economic", "currency", "profit", "loss", "budget", "tax", "interest rate"
            ],
            "legal": [
                "legal", "law", "lawyer", "attorney", "court", "judge", "lawsuit", "plaintiff",
                "defendant", "jurisdiction", "statute", "regulation", "compliance", "contract", "litigation"
            ],
            "medical": [
                "medical", "medicine", "health", "doctor", "patient", "hospital", "clinic", "disease",
                "symptom", "diagnosis", "treatment", "prescription", "surgery", "physician", "pharmacy"
            ],
            "tech": [
                "technology", "tech", "computer", "software", "hardware", "internet", "web", "cloud",
                "data", "programming", "algorithm", "database", "network", "server", "security", "AI", "code"
            ]
        }
        
        # Metin normalleştirme
        text_lower = text.lower()
        domain_scores = defaultdict(int)
        
        # Her alan için puan hesapla
        for domain, keywords in domains.items():
            for keyword in keywords:
                # Tam kelime eşleşmesi için regex kullan
                count = len(re.findall(rf'\b{re.escape(keyword)}\b', text_lower))
                domain_scores[domain] += count
        
        # En yüksek puanlı alanı seç
        if domain_scores:
            max_domain = max(domain_scores.items(), key=lambda x: x[1])
            # Minimum eşik
            if max_domain[1] >= 2:
                return max_domain[0]
        
        return None
    
    def _get_embedding_service_default(self) -> str:
        """Embedding servisinin varsayılan modelini döndürür"""
        if self.embedding_service:
            return self.embedding_service.default_model_id
        return "text-embedding-3-small"  # Genel varsayılan
    
    def _get_available_models(self) -> List[str]:
        """Kullanılabilir tüm modelleri döndürür"""
        if self.embedding_service:
            return list(self.embedding_service.models.keys())
        return []