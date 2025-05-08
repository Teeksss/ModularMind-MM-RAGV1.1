"""
LLM servisi.
"""

import os
import json
import logging
import importlib
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

from ModularMind.API.services.llm.models import ModelManager, LLMModelConfig

logger = logging.getLogger(__name__)

class LLMService:
    """LLM servisi sınıfı."""
    
    def __init__(self, model_manager: ModelManager):
        self.model_manager = model_manager
        self._providers: Dict[str, Any] = {}
        self._api_keys: Dict[str, str] = {}
        
        # API anahtarlarını çevresel değişkenlerden al
        self._load_api_keys()
        
        # Provider modüllerini yükle
        self._load_providers()
    
    def _load_api_keys(self):
        """API anahtarlarını çevresel değişkenlerden yükler."""
        # OpenAI
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        if openai_api_key:
            self._api_keys["openai"] = openai_api_key
        
        # Anthropic
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self._api_keys["anthropic"] = anthropic_api_key
        
        # Cohere
        cohere_api_key = os.environ.get("COHERE_API_KEY")
        if cohere_api_key:
            self._api_keys["cohere"] = cohere_api_key
        
        # Azure
        azure_api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        if azure_api_key:
            self._api_keys["azure"] = azure_api_key
        
        # Hepsini loglama
        logger.info(f"Yüklenen API anahtarları: {', '.join(self._api_keys.keys())}")
    
    def _load_providers(self):
        """Provider modüllerini yükler."""
        # Yüklenecek providerlar
        providers = [
            ("openai", "ModularMind.API.services.llm.providers.openai_provider"),
            ("anthropic", "ModularMind.API.services.llm.providers.anthropic_provider"),
            ("cohere", "ModularMind.API.services.llm.providers.cohere_provider"),
            ("azure", "ModularMind.API.services.llm.providers.azure_provider"),
            ("local", "ModularMind.API.services.llm.providers.local_provider")
        ]
        
        for provider_name, module_path in providers:
            try:
                module = importlib.import_module(module_path)
                self._providers[provider_name] = module
                logger.info(f"Provider yüklendi: {provider_name}")
            except ImportError:
                logger.warning(f"Provider modülü bulunamadı: {module_path}")
            except Exception as e:
                logger.error(f"{provider_name} provider yükleme hatası: {str(e)}")
    
    def get_provider_module(self, provider: str) -> Optional[Any]:
        """Provider modülünü döndürür."""
        return self._providers.get(provider)
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Provider için API anahtarını döndürür."""
        return self._api_keys.get(provider)
    
    def _get_model_config(self, model_id: Optional[str] = None) -> Optional[LLMModelConfig]:
        """Model yapılandırmasını döndürür."""
        if model_id:
            return self.model_manager.get_model_config(model_id)
        
        # Model ID belirtilmemişse ilk modeli kullan
        model_ids = self.model_manager.get_model_ids()
        if model_ids:
            return self.model_manager.get_model_config(model_ids[0])
        
        return None
    
    def generate_text(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Metin üretir.
        
        Args:
            prompt: Giriş metni
            model_id: Model ID
            max_tokens: Maksimum token sayısı
            temperature: Sıcaklık
            top_p: Top-p
            stop_sequences: Durdurma dizileri
            system_message: Sistem mesajı
            options: Ek seçenekler
            
        Returns:
            str: Üretilen metin
        """
        # Model yapılandırmasını al
        model_config = self._get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model bulunamadı: {model_id}")
        
        # Provider'ı al
        provider_module = self.get_provider_module(model_config.provider)
        if not provider_module:
            raise ValueError(f"Provider bulunamadı: {model_config.provider}")
        
        # API anahtarını al
        api_key = None
        if model_config.api_key_env:
            api_key = os.environ.get(model_config.api_key_env)
        
        if not api_key:
            api_key = self.get_api_key(model_config.provider)
        
        if not api_key:
            raise ValueError(f"API anahtarı bulunamadı: {model_config.provider}")
        
        # Parametreleri ayarla
        actual_max_tokens = max_tokens or model_config.max_tokens
        actual_temperature = temperature if temperature is not None else model_config.temperature
        actual_top_p = top_p if top_p is not None else model_config.top_p
        actual_stop_sequences = stop_sequences or model_config.stop_sequences
        
        # API anahtarları
        api_keys = {model_config.provider: api_key}
        
        # Sistem mesajı varsa chat formatına dönüştür
        if system_message:
            if hasattr(provider_module, "generate_chat"):
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                
                return provider_module.generate_chat(
                    self,
                    messages,
                    model_config,
                    actual_max_tokens,
                    actual_temperature,
                    actual_top_p,
                    actual_stop_sequences,
                    options,
                    api_keys
                )
        
        # Metni oluştur
        return provider_module.generate(
            self,
            prompt,
            model_config,
            actual_max_tokens,
            actual_temperature,
            actual_top_p,
            actual_stop_sequences,
            options,
            api_keys
        )
    
    async def stream_text(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        system_message: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Metin üretimini stream eder.
        
        Args:
            prompt: Giriş metni
            model_id: Model ID
            max_tokens: Maksimum token sayısı
            temperature: Sıcaklık
            top_p: Top-p
            stop_sequences: Durdurma dizileri
            system_message: Sistem mesajı
            options: Ek seçenekler
            
        Yields:
            str: Üretilen metin parçaları
        """
        # Model yapılandırmasını al
        model_config = self._get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model bulunamadı: {model_id}")
        
        # Provider'ı al
        provider_module = self.get_provider_module(model_config.provider)
        if not provider_module:
            raise ValueError(f"Provider bulunamadı: {model_config.provider}")
        
        # Streaming desteği kontrolü
        if not hasattr(provider_module, "stream"):
            # Streaming desteklenmiyor, normal üretimle simüle et
            text = self.generate_text(
                prompt, 
                model_id, 
                max_tokens, 
                temperature, 
                top_p, 
                stop_sequences, 
                system_message, 
                options
            )
            
            yield text
            return
        
        # API anahtarını al
        api_key = None
        if model_config.api_key_env:
            api_key = os.environ.get(model_config.api_key_env)
        
        if not api_key:
            api_key = self.get_api_key(model_config.provider)
        
        if not api_key:
            raise ValueError(f"API anahtarı bulunamadı: {model_config.provider}")
        
        # Parametreleri ayarla
        actual_max_tokens = max_tokens or model_config.max_tokens
        actual_temperature = temperature if temperature is not None else model_config.temperature
        actual_top_p = top_p if top_p is not None else model_config.top_p
        actual_stop_sequences = stop_sequences or model_config.stop_sequences
        
        # API anahtarları
        api_keys = {model_config.provider: api_key}
        
        # Sistem mesajı varsa chat formatına dönüştür
        if system_message:
            if hasattr(provider_module, "stream_chat"):
                messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ]
                
                async for chunk in provider_module.stream_chat(
                    self,
                    messages,
                    model_config,
                    actual_max_tokens,
                    actual_temperature,
                    actual_top_p,
                    actual_stop_sequences,
                    options,
                    api_keys
                ):
                    yield chunk
                
                return
        
        # Metni stream et
        async for chunk in provider_module.stream(
            self,
            prompt,
            model_config,
            actual_max_tokens,
            actual_temperature,
            actual_top_p,
            actual_stop_sequences,
            options,
            api_keys
        ):
            yield chunk
    
    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Sohbet mesajı üretir.
        
        Args:
            messages: Sohbet mesajları
            model_id: Model ID
            max_tokens: Maksimum token sayısı
            temperature: Sıcaklık
            top_p: Top-p
            stop_sequences: Durdurma dizileri
            options: Ek seçenekler
            
        Returns:
            Dict[str, str]: Üretilen sohbet mesajı
        """
        # Model yapılandırmasını al
        model_config = self._get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model bulunamadı: {model_id}")
        
        # Provider'ı al
        provider_module = self.get_provider_module(model_config.provider)
        if not provider_module:
            raise ValueError(f"Provider bulunamadı: {model_config.provider}")
        
        # Chat desteği kontrolü
        if not hasattr(provider_module, "generate_chat"):
            # Chat desteklenmiyor, normal üretimle simüle et
            # Tüm mesajları birleştir
            combined_prompt = ""
            for message in messages:
                role = message.get("role", "")
                content = message.get("content", "")
                
                if role == "system":
                    combined_prompt += f"[SİSTEM]: {content}\n\n"
                elif role == "user":
                    combined_prompt += f"[KULLANICI]: {content}\n\n"
                elif role == "assistant":
                    combined_prompt += f"[ASİSTAN]: {content}\n\n"
            
            combined_prompt += "[ASİSTAN]: "
            
            # Metin üret
            response_text = self.generate_text(
                combined_prompt,
                model_id,
                max_tokens,
                temperature,
                top_p,
                stop_sequences,
                None,  # Sistem mesajı zaten prompt'a eklendi
                options
            )
            
            # Yanıtı sohbet mesajına dönüştür
            return {"role": "assistant", "content": response_text}
        
        # API anahtarını al
        api_key = None
        if model_config.api_key_env:
            api_key = os.environ.get(model_config.api_key_env)
        
        if not api_key:
            api_key = self.get_api_key(model_config.provider)
        
        if not api_key:
            raise ValueError(f"API anahtarı bulunamadı: {model_config.provider}")
        
        # Parametreleri ayarla
        actual_max_tokens = max_tokens or model_config.max_tokens
        actual_temperature = temperature if temperature is not None else model_config.temperature
        actual_top_p = top_p if top_p is not None else model_config.top_p
        actual_stop_sequences = stop_sequences or model_config.stop_sequences
        
        # API anahtarları
        api_keys = {model_config.provider: api_key}
        
        # Sohbet mesajı üret
        return provider_module.generate_chat(
            self,
            messages,
            model_config,
            actual_max_tokens,
            actual_temperature,
            actual_top_p,
            actual_stop_sequences,
            options,
            api_keys
        )
    
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Sohbet mesajı üretimini stream eder.
        
        Args:
            messages: Sohbet mesajları
            model_id: Model ID
            max_tokens: Maksimum token sayısı
            temperature: Sıcaklık
            top_p: Top-p
            stop_sequences: Durdurma dizileri
            options: Ek seçenekler
            
        Yields:
            str: Üretilen sohbet mesajı parçaları
        """
        # Model yapılandırmasını al
        model_config = self._get_model_config(model_id)
        if not model_config:
            raise ValueError(f"Model bulunamadı: {model_id}")
        
        # Provider'ı al
        provider_module = self.get_provider_module(model_config.provider)
        if not provider_module:
            raise ValueError(f"Provider bulunamadı: {model_config.provider}")
        
        # Streaming chat desteği kontrolü
        if not hasattr(provider_module, "stream_chat"):
            # Chat streaming desteklenmiyor
            # Normal chat ile yanıt alıp tek seferde dön
            response = self.generate_chat(
                messages,
                model_id,
                max_tokens,
                temperature,
                top_p,
                stop_sequences,
                options
            )
            
            yield response.get("content", "")
            return
        
        # API anahtarını al
        api_key = None
        if model_config.api_key_env:
            api_key = os.environ.get(model_config.api_key_env)
        
        if not api_key:
            api_key = self.get_api_key(model_config.provider)
        
        if not api_key:
            raise ValueError(f"API anahtarı bulunamadı: {model_config.provider}")
        
        # Parametreleri ayarla
        actual_max_tokens = max_tokens or model_config.max_tokens
        actual_temperature = temperature if temperature is not None else model_config.temperature
        actual_top_p = top_p if top_p is not None else model_config.top_p
        actual_stop_sequences = stop_sequences or model_config.stop_sequences
        
        # API anahtarları
        api_keys = {model_config.provider: api_key}
        
        # Sohbet mesajını stream et
        async for chunk in provider_module.stream_chat(
            self,
            messages,
            model_config,
            actual_max_tokens,
            actual_temperature,
            actual_top_p,
            actual_stop_sequences,
            options,
            api_keys
        ):
            yield chunk
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Tüm modellerin listesini döndürür."""
        return self.model_manager.get_models()