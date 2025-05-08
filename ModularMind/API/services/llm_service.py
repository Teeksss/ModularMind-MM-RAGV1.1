"""
LLM Servisi Ana Modülü.
LLM modellerini yönetmek için arayüz sağlar.
"""

import logging
import os
import json
import time
from typing import List, Dict, Any, Optional, Union, Callable
from enum import Enum

from ModularMind.API.services.llm.providers.base_provider import LLMProvider
from ModularMind.API.services.llm.models import LLMModelConfig, PromptConfig, PromptTemplate
from ModularMind.API.services.llm.prompt_manager import PromptManager
from ModularMind.API.services.llm.provider_factory import ProviderFactory
from ModularMind.API.services.llm.utils import count_tokens, normalize_response

logger = logging.getLogger(__name__)

class LLMService:
    """
    LLM (Large Language Model) servisi ana sınıfı.
    """
    
    def __init__(self, default_model: str = None):
        """
        Args:
            default_model: Varsayılan model kimliği
        """
        # Model yapılandırmalarını yükle
        self.models = self._load_model_configs()
        
        # Varsayılan model
        self.default_model = default_model or next(iter(self.models.keys()), None)
        
        if not self.default_model:
            logger.warning("Hiçbir LLM modeli yapılandırılmamış!")
        
        # Prompt yöneticisini oluştur
        self.prompt_manager = PromptManager()
        
        # API anahtarlarını yükle
        self.api_keys = self._load_api_keys()
        
        # Provider fabrikası
        self.provider_factory = ProviderFactory(self.api_keys)
        
        # İstek sayaçları ve metrikler
        self.request_counters = {}
        self.response_times = {}
        self.error_counters = {}
        self.token_usage = {}
        
        logger.info(f"LLM servisi başlatıldı, {len(self.models)} model yapılandırması yüklendi")
    
    def generate_text(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        streaming_callback: Optional[Callable[[str], None]] = None,
        system_message: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Metinden metin üretir.
        
        Args:
            prompt: Giriş metni
            model: Kullanılacak model ID (None ise varsayılan model kullanılır)
            max_tokens: Maksimum üretilecek token sayısı
            temperature: Yaratıcılık derecesi (0-1 arası)
            top_p: Olasılık eşiği (0-1 arası)
            stop_sequences: Üretimi durduracak metin dizileri
            streaming_callback: Streaming yanıtlar için geri çağırma fonksiyonu
            system_message: Sistem mesajı (model destekliyorsa)
            options: Ek model seçenekleri
            
        Returns:
            str: Üretilen metin
        """
        # Model seçimi
        model_id = model or self.default_model
        
        if model_id not in self.models:
            logger.warning(f"Model bulunamadı: {model_id}, varsayılan model kullanılıyor: {self.default_model}")
            model_id = self.default_model
        
        # Model yapılandırmasını al
        model_config = self.models[model_id]
        
        # Parametreleri ayarla
        tokens = max_tokens or model_config.max_tokens
        temp = temperature if temperature is not None else model_config.temperature
        p = top_p if top_p is not None else model_config.top_p
        
        # Streaming ayarını belirle
        is_streaming = bool(streaming_callback) and model_config.streaming
        
        # Metrik sayacını güncelle
        self._update_counter(model_id)
        
        # Başlangıç zamanı
        start_time = time.time()
        
        try:
            # Girdi token sayısını tahmin et
            estimated_input_tokens = count_tokens(prompt, model_config)
            
            # Provider'ı seç ve oluştur
            provider = self.provider_factory.create_provider(model_config)
            
            # Metin üret
            result = provider.generate_text(
                prompt=prompt,
                max_tokens=tokens,
                temperature=temp,
                top_p=p,
                stop_sequences=stop_sequences,
                streaming=is_streaming,
                streaming_callback=streaming_callback,
                system_message=system_message,
                options=options
            )
            
            # Yanıt süresini ölç
            response_time = time.time() - start_time
            self._update_response_time(model_id, response_time)
            
            # Çıktı token sayısını tahmin et
            estimated_output_tokens = count_tokens(result, model_config)
            self._update_token_usage(model_id, estimated_input_tokens, estimated_output_tokens)
            
            return result
            
        except Exception as e:
            # Hata sayacını güncelle
            self._update_error_counter(model_id)
            
            logger.error(f"Metin üretme hatası: {str(e)}", exc_info=True)
            
            # Yeniden deneme
            if options and options.get("retry_on_error", True):
                retry_count = options.get("retry_count", 0)
                if retry_count < model_config.max_retries:
                    retry_options = options.copy() if options else {}
                    retry_options["retry_count"] = retry_count + 1
                    
                    logger.info(f"Yeniden deneniyor ({retry_count + 1}/{model_config.max_retries}): {model_id}")
                    time.sleep(model_config.retry_interval * (2 ** retry_count))  # Exponential backoff
                    
                    return self.generate_text(
                        prompt=prompt,
                        model=model_id,
                        max_tokens=tokens,
                        temperature=temp,
                        top_p=p,
                        stop_sequences=stop_sequences,
                        streaming_callback=streaming_callback,
                        system_message=system_message,
                        options=retry_options
                    )
            
            return f"[Metin üretme hatası: {str(e)}]"
    
    def generate_from_template(
        self,
        template_id: str,
        variables