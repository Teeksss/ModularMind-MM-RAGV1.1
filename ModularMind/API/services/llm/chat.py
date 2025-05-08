"""
LLM Sohbet işlemleri.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Callable

from ModularMind.API.services.llm.models import LLMProvider
from ModularMind.API.services.llm.utils import estimate_tokens

logger = logging.getLogger(__name__)

def process_chat_completion(
    llm_service,
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
    Sohbet tamamlama işlemini gerçekleştirir.
    
    Args:
        llm_service: LLM servisi
        messages: Mesaj listesi
        model: Kullanılacak model ID
        max_tokens: Maksimum üretilecek token sayısı
        temperature: Yaratıcılık derecesi (0-1 arası)
        top_p: Olasılık eşiği (0-1 arası)
        stop_sequences: Üretimi durduracak metin dizileri
        streaming_callback: Streaming yanıtlar için geri çağırma fonksiyonu
        options: Ek model seçenekleri
        
    Returns:
        Dict[str, Any]: Yanıt
    """
    # Model seçimi
    model_id = model or llm_service.default_model
    
    if model_id not in llm_service.models:
        logger.warning(f"Model bulunamadı: {model_id}, varsayılan model kullanılıyor: {llm_service.default_model}")
        model_id = llm_service.default_model
    
    # Model yapılandırmasını al
    model_config = llm_service.models[model_id]
    
    # Parametreleri ayarla
    tokens = max_tokens or model_config.max_tokens
    temp = temperature if temperature is not None else model_config.temperature
    p = top_p if top_p is not None else model_config.top_p
    
    # Streaming ayarını belirle
    is_streaming = bool(streaming_callback) and model_config.streaming
    
    # Metrik sayacını güncelle
    llm_service._update_counter(model_id)
    
    # Başlangıç zamanı
    start_time = time.time()
    
    try:
        # Hız sınırlamasını kontrol et
        llm_service._check_rate_limit(model_id)
        
        # Girdi token sayısını tahmin et
        estimated_input_tokens = sum(estimate_tokens(m["content"], model_config) for m in messages)
        
        # Model sağlayıcısına göre sohbet tamamlama
        provider = model_config.provider
        
        if provider == LLMProvider.OPENAI:
            from ModularMind.API.services.llm.providers import openai_provider
            result = openai_provider.chat(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        elif provider == LLMProvider.AZURE_OPENAI:
            from ModularMind.API.services.llm.providers import azure_openai_provider
            result = azure_openai_provider.chat(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        elif provider == LLMProvider.ANTHROPIC:
            from ModularMind.API.services.llm.providers import anthropic_provider
            result = anthropic_provider.chat(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        elif provider == LLMProvider.GOOGLE:
            from ModularMind.API.services.llm.providers import google_provider
            result = google_provider.chat(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        elif provider == LLMProvider.COHERE:
            from ModularMind.API.services.llm.providers import cohere_provider
            result = cohere_provider.chat(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        elif provider in [LLMProvider.HUGGINGFACE, LLMProvider.REPLICATE, LLMProvider.OLLAMA, LLMProvider.LOCAL, LLMProvider.CUSTOM]:
            # Sohbet formatlı olmayan modeller için uyarlama
            result = adapt_messages_to_completion(llm_service, messages, model_config, tokens, temp, p, stop_sequences, is_streaming, streaming_callback, options)
            
        else:
            logger.error(f"Desteklenmeyen LLM sağlayıcısı: {provider}")
            return {"role": "assistant", "content": ""}
        
        # Yanıt süresini ölç
        response_time = time.time() - start_time
        llm_service._update_response_time(model_id, response_time)
        
        # Çıktı token sayısını tahmin et
        estimated_output_tokens = estimate_tokens(result.get("content", ""), model_config)
        llm_service._update_token_usage(model_id, estimated_input_tokens, estimated_output_tokens)
        
        return result
        
    except Exception as e:
        # Hata sayacını güncelle
        llm_service._update_error_counter(model_id)
        
        logger.error(f"Sohbet tamamlama hatası: {str(e)}", exc_info=True)
        
        # Yeniden deneme
        if options and options.get("retry_on_error", True):
            retry_count = options.get("retry_count", 0)
            if retry_count < model_config.max_retries:
                retry_options = options.copy() if options else {}
                retry_options["retry_count"] = retry_count + 1
                
                logger.info(f"Yeniden deneniyor ({retry_count + 1}/{model_config.max_retries}): {model_id}")
                time.sleep(model_config.retry_interval * (2 ** retry_count))  # Exponential backoff
                
                return process_chat_completion(
                    llm_service,
                    messages=messages,
                    model=model_id,
                    max_tokens=tokens,
                    temperature=temp,
                    top_p=p,
                    stop_sequences=stop_sequences,
                    streaming_callback=streaming_callback,
                    options=retry_options
                )
        
        return {"role": "assistant", "content": f"[Sohbet tamamlama hatası: {str(e)}]"}

def adapt_messages_to_completion(
    llm_service,
    messages: List[Dict[str, str]],
    model_config,
    max_tokens: int,
    temperature: float,
    top_p: float,
    stop_sequences: Optional[List[str]],
    is_streaming: bool,
    streaming_callback: Optional[Callable[[str], None]],
    options: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Sohbet mesajlarını düz metin tamamlamaya dönüştürür.
    
    Args:
        llm_service: LLM servisi
        messages: Mesaj listesi
        model_config: Model yapılandırması
        max_tokens: Maksimum üretilecek token sayısı
        temperature: Yaratıcılık derecesi (0-1 arası)
        top_p: Olasılık eşiği (0-1 arası)
        stop_sequences: Üretimi durduracak metin dizileri
        is_streaming: Streaming modu
        streaming_callback: Streaming yanıtlar için geri çağırma fonksiyonu
        options: Ek model seçenekleri
        
    Returns:
        Dict[str, Any]: Yanıt
    """
    # Mesajları birleştir
    system_message = None
    prompt = ""
    
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        
        if role == "system":
            system_message = content
        elif role == "user":
            prompt += f"\nUser: {content}\n"
        elif role == "assistant":
            prompt += f"\nAssistant: {content}\n"
    
    # Son kullanıcı mesajının olduğundan emin ol
    prompt += "\nAssistant: "
    
    # Metin tamamlama
    completion = llm_service.generate_text(
        prompt=prompt,
        model=model_config.model_id,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        stop_sequences=stop_sequences,
        streaming_callback=streaming_callback,
        system_message=system_message,
        options=options
    )
    
    # Yanıtı döndür
    return {
        "role": "assistant",
        "content": completion
    }