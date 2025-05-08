"""
OpenAI fine-tuning sağlayıcısı.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union

from .base import BaseFineTuningProvider, FineTuningError
from ..config import ProviderConfig

logger = logging.getLogger(__name__)

class OpenAIFineTuning(BaseFineTuningProvider):
    """OpenAI fine-tuning sağlayıcısı"""
    
    def __init__(self, config: ProviderConfig):
        """
        OpenAI fine-tuning sağlayıcısını başlatır
        
        Args:
            config: Sağlayıcı yapılandırması
        """
        super().__init__(config)
        self.client = None
    
    def initialize(self) -> bool:
        """
        OpenAI API'sini başlatır
        
        Returns:
            bool: Başlatma başarılı mı
        """
        try:
            import openai
            
            # API anahtarını al
            api_key = None
            
            if self.config.api_key_env:
                api_key = os.environ.get(self.config.api_key_env)
            
            if not api_key:
                logger.error(f"OpenAI API anahtarı bulunamadı: {self.config.api_key_env}")
                return False
            
            # API client'ı oluştur
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=self.config.api_base_url
            )
            
            self.initialized = True
            return True
        except ImportError:
            logger.error("openai kütüphanesi bulunamadı. Kurulum: pip install openai")
            return False
        except Exception as e:
            logger.error(f"OpenAI başlatma hatası: {str(e)}")
            return False
    
    def create_fine_tuning_job(
        self,
        model_id: str,
        training_data: Union[str, List[Dict[str, Any]]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fine-tuning işi oluşturur
        
        Args:
            model_id: İnce ayar yapılacak model ID
            training_data: Eğitim verileri (dosya yolu veya veri listesi)
            options: Fine-tuning seçenekleri
            
        Returns:
            Dict[str, Any]: İş bilgileri
        """
        if not self.initialized:
            if not self.initialize():
                raise FineTuningError("OpenAI sağlayıcısı başlatılamadı")
        
        try:
            options = options or {}
            
            # Veri dosyası işle
            file_id = None
            
            if isinstance(training_data, str):
                # Dosya yolu
                if os.path.exists(training_data):
                    with open(training_data, "rb") as f:
                        response = self.client.files.create(
                            file=f,
                            purpose="fine-tune"
                        )
                        file_id = response.id
                else:
                    raise FineTuningError(f"Eğitim veri dosyası bulunamadı: {training_data}")
            else:
                # Veri listesi - geçici JSONL dosyası oluştur
                import tempfile
                
                with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
                    temp_file = f.name
                    for item in training_data:
                        f.write(json.dumps(item) + "\n")
                
                with open(temp_file, "rb") as f:
                    response = self.client.files.create(
                        file=f,
                        purpose="fine-tune"
                    )
                    file_id = response.id
                
                # Geçici dosyayı sil
                os.unlink(temp_file)
            
            # Fine-tuning seçenekleri
            hyperparameters = {
                "n_epochs": options.get("n_epochs", 4)
            }
            
            if "batch_size" in options:
                hyperparameters["batch_size"] = options["batch_size"]
            
            if "learning_rate_multiplier" in options:
                hyperparameters["learning_rate_multiplier"] = options["learning_rate_multiplier"]
            
            # Fine-tuning işi oluştur
            response = self.client.fine_tuning.jobs.create(
                training_file=file_id,
                model=model_id,
                hyperparameters=hyperparameters,
                suffix=options.get("suffix", "")
            )
            
            # İş bilgilerini döndür
            estimated_completion = None
            if hasattr(response, "created_at") and hasattr(response, "estimated_completion"):
                estimated_completion = response.estimated_completion
            
            return {
                "job_id": response.id,
                "status": response.status,
                "model": response.model,
                "created_at": response.created_at,
                "estimated_completion": estimated_completion,
                "file_id": file_id
            }
        except Exception as e:
            raise FineTuningError(f"OpenAI fine-tuning işi oluşturma hatası: {str(e)}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        İş durumunu alır
        
        Args:
            job_id: İş kimliği
            
        Returns:
            Dict[str, Any]: İş durumu
        """
        if not self.initialized:
            if not self.initialize():
                raise FineTuningError("OpenAI sağlayıcısı başlatılamadı")
        
        try:
            # İş durumunu al
            response = self.client.fine_tuning.jobs.retrieve(job_id)
            
            fine_tuned_model = None
            if hasattr(response, "fine_tuned_model") and response.fine_tuned_model:
                fine_tuned_model = response.fine_tuned_model
            
            # Durumu formatlayıp döndür
            return {
                "job_id": response.id,
                "status": response.status,
                "model": response.model,
                "created_at": response.created_at,
                "finished_at": response.finished_at,
                "fine_tuned_model": fine_tuned_model,
                "training_file": response.training_file,
                "validation_file": response.validation_file,
                "result_files": response.result_files
            }
        except Exception as e:
            raise FineTuningError(f"OpenAI iş durumu alma hatası: {str(e)}")
    
    def list_fine_tuned_models(self) -> List[Dict[str, Any]]:
        """
        Fine-tuned modelleri listeler
        
        Returns:
            List[Dict[str, Any]]: Fine-tuned modeller listesi
        """
        if not self.initialized:
            if not self.initialize():
                raise FineTuningError("OpenAI sağlayıcısı başlatılamadı")
        
        try:
            # Modelleri listele
            response = self.client.models.list()
            
            # Sadece fine-tuned modelleri filtrele
            fine_tuned_models = []
            
            for model in response.data:
                # Fine-tuned modeller genelde ft: ile başlar veya :ft ile biter
                model_id = model.id
                owned_by = getattr(model, "owned_by", "")
                
                if (model_id.startswith("ft:") or 
                    model_id.endswith(":ft") or 
                    "-ft-" in model_id or 
                    (owned_by and owned_by != "openai")):
                    
                    fine_tuned_models.append({
                        "id": model_id,
                        "created_at": model.created,
                        "owned_by": owned_by
                    })
            
            return fine_tuned_models
        except Exception as e:
            raise FineTuningError(f"OpenAI fine-tuned modelleri listeleme hatası: {str(e)}")
    
    def evaluate_model(
        self,
        model_id: str,
        eval_data: Union[str, List[Dict[str, Any]]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fine-tuned modeli değerlendirir
        
        Args:
            model_id: Model kimliği
            eval_data: Değerlendirme verileri
            options: Değerlendirme seçenekleri
            
        Returns:
            Dict[str, Any]: Değerlendirme sonuçları
        """
        if not self.initialized:
            if not self.initialize():
                raise FineTuningError("OpenAI sağlayıcısı başlatılamadı")
        
        try:
            options = options or {}
            
            # Değerlendirme verilerini hazırla
            eval_samples = []
            references = []
            
            if isinstance(eval_data, str):
                # Dosya yolu
                if os.path.exists(eval_data):
                    with open(eval_data, "r") as f:
                        for line in f:
                            sample = json.loads(line)
                            eval_samples.append(sample)
                            if "completion" in sample:
                                references.append(sample["completion"])
                else:
                    raise FineTuningError(f"Değerlendirme veri dosyası bulunamadı: {eval_data}")
            else:
                # Veri listesi
                eval_samples = eval_data
                for sample in eval_data:
                    if "completion" in sample:
                        references.append(sample["completion"])
            
            # Tahminler için OpenAI API kullan
            predictions = []
            
            max_samples = options.get("max_eval_samples", 100)
            temperature = options.get("temperature", 0)
            
            for i, sample in enumerate(eval_samples[:max_samples]):
                if "prompt" in sample:
                    response = self.client.completions.create(
                        model=model_id,
                        prompt=sample["prompt"],
                        temperature=temperature,
                        max_tokens=options.get("max_tokens", 256)
                    )
                    
                    prediction = response.choices[0].text.strip()
                    predictions.append(prediction)
            
            # Sonuçları döndür
            return {
                "model_id": model_id,
                "predictions": predictions,
                "references": references[:len(predictions)],
                "eval_count": len(predictions)
            }
        except Exception as e:
            raise FineTuningError(f"OpenAI model değerlendirme hatası: {str(e)}")