"""
Cohere LLM Sağlayıcısı.
"""

import logging
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

def generate(
    llm_service,
    prompt: str, 
    model_config, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    stop_sequences: Optional[List[str]], 
    is_streaming: bool, 
    streaming_callback: Optional[Callable[[str], None]],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    Cohere modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        import cohere
        
        # API anahtarını al
        api_key = api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Cohere API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Cohere istemci
        client = cohere.Client(api_key)
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Streaming yanıt
            for event in client.chat_stream(
                message=prompt,
                model=model_config.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                p=top_p,
                stop_sequences=stop_sequences
            ):
                if hasattr(event, 'text') and event.text:
                    response_text += event.text
                    streaming_callback(event.text)
            
            return response_text
        
        # Normal mod
        response = client.chat(
            message=prompt,
            model=model_config.model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            p=top_p,
            stop_sequences=stop_sequences
        )
        
        return response.text
        
    except ImportError:
        logger.error("cohere kütüphanesi bulunamadı, pip install cohere komutuyla yükleyin")
        return "[Cohere kütüphanesi bulunamadı]"

def chat(
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
    Cohere ile sohbet tamamlama.
    
    Returns:
        Dict[str, Any]: Yanıt
    """
    try:
        import cohere
        
        # API anahtarını al
        api_key = llm_service.api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Cohere API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Cohere istemci
        client = cohere.Client(api_key)
        
        # Cohere chat history formatına dönüştür
        chat_history = []
        query = ""
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "user":
                if chat_history:  # Geçmiş varsa şu an ki mesajı sorgu olarak ayarla
                    query = content
                else:  # İlk kullanıcı mesajı
                    query = content
            elif role == "assistant":
                if query:  # Sorgu ve yanıt çifti oluştur
                    chat_history.append({"role": "USER", "message": query})
                    chat_history.append({"role": "CHATBOT", "message": content})
                    query = ""
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Son kullanıcı mesajını sorgu olarak kullan
            stream = client.chat_stream(
                message=query,
                model=model_config.model_id,
                chat_history=chat_history,
                max_tokens=max_tokens,
                temperature=temperature,
                p=top_p,
                stop_sequences=stop_sequences
            )
            
            # Sonuçları işle
            for event in stream:
                if hasattr(event, 'text') and event.text:
                    response_text += event.text
                    streaming_callback(event.text)
            
            return {
                "role": "assistant",
                "content": response_text
            }
        
        # Normal mod
        response = client.chat(
            message=query,
            model=model_config.model_id,
            chat_history=chat_history,
            max_tokens=max_tokens,
            temperature=temperature,
            p=top_p,
            stop_sequences=stop_sequences
        )
        
        return {
            "role": "assistant",
            "content": response.text
        }
        
    except ImportError:
        logger.error("cohere kütüphanesi bulunamadı, pip install cohere komutuyla yükleyin")
        return {"role": "assistant", "content": "[Cohere kütüphanesi bulunamadı]"}