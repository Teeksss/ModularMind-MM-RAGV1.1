"""
Model ince ayar (fine-tuning) servisi.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple

from .config import FineTuningConfig
from .data.preparation import DataPreparation
from .providers.base import BaseFineTuningProvider
from .evaluation.metrics import evaluate_model

logger = logging.getLogger(__name__)

class FineTuningService:
    """
    LLM ve embedding modelleri için ince ayar (fine-tuning) servisi.
    
    Bu servis, çeşitli sağlayıcılar (OpenAI, HuggingFace, yerel) üzerinden
    model ince ayarı yapabilme yetenekleri sağlar.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Singleton instance getter"""
        if cls._instance is None:
            raise ValueError("FineTuningService henüz başlatılmamış")
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Fine-tuning servisini başlatır
        
        Args:
            config_path: Yapılandırma dosyası yolu
        """
        self.config = FineTuningConfig()
        self.data_preparation = DataPreparation()
        self.providers: Dict[str, BaseFineTuningProvider] = {}
        self.active_jobs: Dict[str, Dict[str, Any]] = {}
        
        # Singleton instance
        FineTuningService._instance = self
        
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
            self.config = FineTuningConfig.from_dict(config_data)
            
            # Sağlayıcıları yükle
            self._load_providers()
            
            logger.info(f"Fine-tuning yapılandırması yüklendi: {config_path}")
            return True
        except Exception as e:
            logger.error(f"Fine-tuning yapılandırması yükleme hatası: {str(e)}")
            return False
    
    def _load_providers(self) -> None:
        """Yapılandırılmış sağlayıcıları yükler"""
        from .providers.openai import OpenAIFineTuning
        from .providers.huggingface import HuggingFaceFineTuning
        from .providers.local import LocalFineTuning
        
        # OpenAI sağlayıcı
        if "openai" in self.config.providers:
            self.providers["openai"] = OpenAIFineTuning(self.config.providers["openai"])
        
        # HuggingFace sağlayıcı
        if "huggingface" in self.config.providers:
            self.providers["huggingface"] = HuggingFaceFineTuning(self.config.providers["huggingface"])
        
        # Yerel sağlayıcı
        if "local" in self.config.providers:
            self.providers["local"] = LocalFineTuning(self.config.providers["local"])
    
    def prepare_data(
        self,
        data: Union[str, List[Dict[str, Any]]],
        provider: str,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        İnce ayar için veriyi hazırlar
        
        Args:
            data: Veri dosyası yolu veya veri listesi
            provider: Sağlayıcı kimliği
            options: Hazırlama seçenekleri
            
        Returns:
            Dict[str, Any]: Hazırlama sonuçları
        """
        if provider not in self.providers:
            raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
        
        # Veri hazırlama işlemi
        return self.data_preparation.prepare(
            data=data,
            provider=provider,
            provider_config=self.providers[provider].config,
            options=options
        )
    
    def create_fine_tuning_job(
        self,
        provider: str,
        model_id: str,
        training_data: Union[str, List[Dict[str, Any]]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        İnce ayar işi oluşturur
        
        Args:
            provider: Sağlayıcı kimliği
            model_id: İnce ayar yapılacak model kimliği
            training_data: Eğitim verileri
            options: İnce ayar seçenekleri
            
        Returns:
            Dict[str, Any]: İş bilgileri
        """
        if provider not in self.providers:
            raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
        
        options = options or {}
        
        # Veriyi hazırla
        prepared_data = self.prepare_data(training_data, provider, options.get("data_options"))
        
        # İnce ayar işi oluştur
        job_result = self.providers[provider].create_fine_tuning_job(
            model_id=model_id,
            training_data=prepared_data["prepared_data"],
            options=options
        )
        
        # İşi takip et
        job_id = job_result["job_id"]
        self.active_jobs[job_id] = {
            "provider": provider,
            "model_id": model_id,
            "status": job_result["status"],
            "created_at": time.time(),
            "details": job_result
        }
        
        return {
            "job_id": job_id,
            "status": job_result["status"],
            "provider": provider,
            "model_id": model_id,
            "data_stats": prepared_data.get("stats", {}),
            "estimated_completion": job_result.get("estimated_completion")
        }
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        İş durumunu alır
        
        Args:
            job_id: İş kimliği
            
        Returns:
            Dict[str, Any]: İş durumu
        """
        if job_id not in self.active_jobs:
            raise ValueError(f"Bilinmeyen iş kimliği: {job_id}")
        
        job_info = self.active_jobs[job_id]
        provider = job_info["provider"]
        
        # Sağlayıcıdan güncel durumu al
        status = self.providers[provider].get_job_status(job_id)
        
        # İş bilgisini güncelle
        job_info["status"] = status["status"]
        job_info["details"].update(status)
        
        return {
            "job_id": job_id,
            "status": status["status"],
            "provider": provider,
            "model_id": job_info["model_id"],
            "created_at": job_info["created_at"],
            "details": status
        }
    
    def list_fine_tuned_models(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        İnce ayar yapılmış modelleri listeler
        
        Args:
            provider: Listesi alınacak sağlayıcı (None ise tümü)
            
        Returns:
            List[Dict[str, Any]]: İnce ayarlı modeller listesi
        """
        models = []
        
        # Belirli bir sağlayıcı belirtilmişse sadece onu kontrol et
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
            
            provider_models = self.providers[provider].list_fine_tuned_models()
            for model in provider_models:
                model["provider"] = provider
                models.append(model)
        else:
            # Tüm sağlayıcılardan modelleri listele
            for provider_name, provider_instance in self.providers.items():
                provider_models = provider_instance.list_fine_tuned_models()
                for model in provider_models:
                    model["provider"] = provider_name
                    models.append(model)
        
        return models
    
    def evaluate_fine_tuned_model(
        self,
        provider: str,
        model_id: str,
        eval_data: Union[str, List[Dict[str, Any]]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        İnce ayar yapılmış modeli değerlendirir
        
        Args:
            provider: Sağlayıcı kimliği
            model_id: Model kimliği
            eval_data: Değerlendirme verileri
            options: Değerlendirme seçenekleri
            
        Returns:
            Dict[str, Any]: Değerlendirme sonuçları
        """
        if provider not in self.providers:
            raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
        
        # Değerlendirme yapılacak veriyi hazırla
        prepared_data = self.data_preparation.prepare(
            data=eval_data,
            provider=provider,
            provider_config=self.providers[provider].config,
            options=options
        )
        
        # Sağlayıcıya özel değerlendirme
        results = self.providers[provider].evaluate_model(
            model_id=model_id,
            eval_data=prepared_data["prepared_data"],
            options=options
        )
        
        # Genel değerlendirme metrikleri hesapla
        metrics = evaluate_model(results["predictions"], results["references"], options)
        results["metrics"] = metrics
        
        return results