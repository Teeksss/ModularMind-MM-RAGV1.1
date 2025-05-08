"""
LLM Servisi.
Farklı LLM sağlayıcıları için arayüz sağlar.
"""

import logging
import os
import json
import time
import re
import threading
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

from ModularMind.API.services.llm.models import LLMProvider, PromptTemplate, LLMModelConfig, PromptConfig
from ModularMind.API.services.llm.providers import (
    openai_provider, azure_openai_provider, anthropic_provider, 
    google_provider, cohere_provider, huggingface_provider,
    replicate_provider, ollama_provider, local_provider, custom_provider
)
from ModularMind.API.services.llm.utils import estimate_tokens, extract_keywords

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
        
        # Prompt şablonlarını yükle
        self.prompt_templates = self._load_prompt_templates()
        
        # API anahtarlarını yükle
        self.api_keys = self._load_api_keys()
        
        # İstek sayaçları ve metrikler
        self.request_counters = {}
        self.response_times = {}
        self.error_counters = {}
        self.token_usage = {}
        
        # Hız sınırlama için zamanlayıcılar
        self.rate_limiters = {}
        
        # Local modeller için instance havuzu
        self.local_models = {}
        
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
            # Hız sınırlamasını kontrol et
            self._check_rate_limit(model_id)
            
            # Girdi token sayısını tahmin et
            estimated_input_tokens = estimate_tokens(prompt, model_config)
            
            # Model sağlayıcısına göre metin üret
            provider = model_config.provider
            
            if provider == LLMProvider.OPENAI:
                result = openai_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, system_message, options, self.api_keys)
                
            elif provider == LLMProvider.AZURE_OPENAI:
                result = azure_openai_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, system_message, options, self.api_keys)
                
            elif provider == LLMProvider.ANTHROPIC:
                result = anthropic_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, system_message, options, self.api_keys)
                
            elif provider == LLMProvider.GOOGLE:
                result = google_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, system_message, options, self.api_keys)
                
            elif provider == LLMProvider.COHERE:
                result = cohere_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options, self.api_keys)
                
            elif provider == LLMProvider.HUGGINGFACE:
                result = huggingface_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, options, self.api_keys)
                
            elif provider == LLMProvider.REPLICATE:
                result = replicate_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, system_message, options, self.api_keys)
                
            elif provider == LLMProvider.OLLAMA:
                result = ollama_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, system_message, options)
                
            elif provider == LLMProvider.LOCAL:
                result = local_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, system_message, options, self.local_models)
                
            elif provider == LLMProvider.CUSTOM:
                result = custom_provider.generate(self, prompt, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, system_message, options, self.api_keys)
                
            else:
                logger.error(f"Desteklenmeyen LLM sağlayıcısı: {provider}")
                return ""
            
            # Yanıt süresini ölç
            response_time = time.time() - start_time
            self._update_response_time(model_id, response_time)
            
            # Çıktı token sayısını tahmin et
            estimated_output_tokens = estimate_tokens(result, model_config)
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
        variables: Dict[str, str],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Şablondan metin üretir.
        
        Args:
            template_id: Şablon kimliği
            variables: Şablon değişkenleri
            model: Kullanılacak model ID
            max_tokens: Maksimum üretilecek token sayısı
            temperature: Yaratıcılık derecesi (0-1 arası)
            options: Ek model seçenekleri
            
        Returns:
            str: Üretilen metin
        """
        # Şablonu kontrol et
        if template_id not in self.prompt_templates:
            logger.error(f"Şablon bulunamadı: {template_id}")
            return f"[Şablon bulunamadı: {template_id}]"
        
        template_config = self.prompt_templates[template_id]
        
        # Zorunlu değişkenleri kontrol et
        for var in template_config.required_variables:
            if var not in variables:
                logger.error(f"Zorunlu değişken eksik: {var}")
                return f"[Zorunlu değişken eksik: {var}]"
        
        # Model seçimi
        selected_model = model or self.default_model
        
        # Model spesifik şablonları kontrol et
        if selected_model in template_config.model_specific:
            template_text = template_config.model_specific[selected_model]
        else:
            template_text = template_config.text
        
        # Değişkenleri yerleştir
        prompt = template_text
        for var, value in variables.items():
            prompt = prompt.replace(f"{{{var}}}", value)
        
        # Boş değişkenleri temizle
        prompt = re.sub(r'{[^{}]*}', '', prompt)
        
        # Metni üret
        return self.generate_text(
            prompt=prompt,
            model=selected_model,
            max_tokens=max_tokens,
            temperature=temperature,
            options=options
        )
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        streaming_callback: Optional[Callable[[str], None]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sohbet tamamlama için.
        
        Args:
            messages: Mesaj listesi (her biri {"role": "...", "content": "..."} formatında)
            model: Kullanılacak model ID
            max_tokens: Maksimum üretilecek token sayısı
            temperature: Yaratıcılık derecesi (0-1 arası)
            top_p: Olasılık eşiği (0-1 arası)
            stop_sequences: Üretimi durduracak metin dizileri
            streaming_callback: Streaming yanıtlar için geri çağırma fonksiyonu
            options: Ek model seçenekleri
            
        Returns:
            Dict[str, Any]: Yanıt, {"content": "...", "role": "assistant", ...} formatında
        """
        from ModularMind.API.services.llm.chat import process_chat_completion
        
        return process_chat_completion(
            self, 
            messages, 
            model, 
            max_tokens, 
            temperature, 
            top_p, 
            stop_sequences, 
            streaming_callback, 
            options
        )
    
    def get_system_and_user_messages(
        self,
        system_message: Optional[str] = None,
        prompt: str = "",
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Sistem mesajı, kullanıcı mesajı ve geçmiş sohbeti birleştirir.
        
        Args:
            system_message: Sistem mesajı
            prompt: Kullanıcı mesajı
            chat_history: Geçmiş sohbet mesajları
            
        Returns:
            List[Dict[str, str]]: Mesaj listesi
        """
        messages = []
        
        # Sistem mesajını ekle
        if system_message:
            messages.append({"role": "system", "content": system_message})
        
        # Geçmiş sohbeti ekle
        if chat_history:
            messages.extend(chat_history)
        
        # Kullanıcı mesajını ekle
        if prompt:
            messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Kullanılabilir modellerin bilgilerini döndürür.
        
        Returns:
            List[Dict[str, Any]]: Model bilgileri
        """
        models_info = []
        
        for model_id, config in self.models.items():
            # API anahtarının varlığını kontrol et
            api_key_env = config.api_key_env
            has_api_key = api_key_env in self.api_keys and bool(self.api_keys[api_key_env])
            
            models_info.append({
                "id": model_id,
                "provider": config.provider,
                "max_tokens": config.max_tokens,
                "context_window": config.context_window,
                "has_api_key": has_api_key,
                "supports_streaming": config.streaming
            })
        
        return models_info
    
    def get_available_templates(self) -> List[Dict[str, Any]]:
        """
        Kullanılabilir şablonların bilgilerini döndürür.
        
        Returns:
            List[Dict[str, Any]]: Şablon bilgileri
        """
        templates_info = []
        
        for template_id, config in self.prompt_templates.items():
            templates_info.append({
                "id": template_id,
                "type": config.template_type,
                "description": config.description,
                "variables": config.variables,
                "required_variables": config.required_variables
            })
        
        return templates_info
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Metrik bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metrikler
        """
        return {
            "request_counters": self.request_counters,
            "response_times": self.response_times,
            "error_counters": self.error_counters,
            "token_usage": self.token_usage,
            "available_models": len(self.get_available_models())
        }
    
    def _load_model_configs(self) -> Dict[str, LLMModelConfig]:
        """
        Model yapılandırmalarını yükler.
        
        Returns:
            Dict[str, LLMModelConfig]: Model yapılandırmaları
        """
        from ModularMind.API.services.llm.config_loader import load_model_configs
        return load_model_configs()
    
    def _load_prompt_templates(self) -> Dict[str, PromptConfig]:
        """
        Prompt şablonlarını yükler.
        
        Returns:
            Dict[str, PromptConfig]: Prompt şablonları
        """
        from ModularMind.API.services.llm.config_loader import load_prompt_templates
        return load_prompt_templates()
    
    def _load_api_keys(self) -> Dict[str, str]:
        """
        API anahtarlarını çevresel değişkenlerden yükler.
        
        Returns:
            Dict[str, str]: API anahtarları
        """
        api_keys = {}
        
        # Model yapılandırmalarında belirtilen tüm çevresel değişkenleri topla
        env_vars = set(model.api_key_env for model in self.models.values() if model.api_key_env)
        
        # Anahtarları yükle
        for env_var in env_vars:
            api_keys[env_var] = os.environ.get(env_var, "")
            
            if not api_keys[env_var] and env_var:
                logger.warning(f"API anahtarı bulunamadı: {env_var}")
        
        return api_keys
    
    def _update_counter(self, model_id: str) -> None:
        """
        İstek sayacını günceller.
        
        Args:
            model_id: Model ID
        """
        if model_id not in self.request_counters:
            self.request_counters[model_id] = 0
            
        self.request_counters[model_id] += 1
    
    def _update_response_time(self, model_id: str, response_time: float) -> None:
        """
        Yanıt süresini günceller.
        
        Args:
            model_id: Model ID
            response_time: Yanıt süresi (saniye)
        """
        if model_id not in self.response_times:
            self.response_times[model_id] = []
            
        self.response_times[model_id].append(response_time)
        
        # Maksimum 100 kayıt tut
        if len(self.response_times[model_id]) > 100:
            self.response_times[model_id].pop(0)
    
    def _update_error_counter(self, model_id: str) -> None:
        """
        Hata sayacını günceller.
        
        Args:
            model_id: Model ID
        """
        if model_id not in self.error_counters:
            self.error_counters[model_id] = 0
            
        self.error_counters[model_id] += 1
    
    def _update_token_usage(self, model_id: str, input_tokens: int, output_tokens: int) -> None:
        """
        Token kullanımını günceller.
        
        Args:
            model_id: Model ID
            input_tokens: Girdi token sayısı
            output_tokens: Çıktı token sayısı
        """
        if model_id not in self.token_usage:
            self.token_usage[model_id] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }
            
        self.token_usage[model_id]["input_tokens"] += input_tokens
        self.token_usage[model_id]["output_tokens"] += output_tokens
        self.token_usage[model_id]["total_tokens"] += input_tokens + output_tokens
    
    def _check_rate_limit(self, model_id: str) -> None:
        """
        Hız sınırlamasını kontrol eder.
        
        Args:
            model_id: Model ID
            
        Raises:
            Exception: Hız sınırı aşıldığında
        """
        model_config = self.models[model_id]
        rate_limit = model_config.rate_limit_rpm
        
        if not rate_limit:
            return
            
        # Zamanlayıcıyı başlat
        if model_id not in self.rate_limiters:
            self.rate_limiters[model_id] = {
                "count": 0,
                "last_reset": time.time()
            }
        
        # Geçen süreyi kontrol et
        limiter = self.rate_limiters[model_id]
        elapsed = time.time() - limiter["last_reset"]
        
        # 1 dakika geçtiyse sıfırla
        if elapsed >= 60:
            limiter["count"] = 0
            limiter["last_reset"] = time.time()
        
        # Sınırı kontrol et
        if limiter["count"] >= rate_limit:
            raise Exception(f"Hız sınırı aşıldı: {rate_limit} istek/dakika. Lütfen {60 - elapsed:.1f} saniye bekleyin.")
        
        # Sayacı artır
        limiter["count"] += 1