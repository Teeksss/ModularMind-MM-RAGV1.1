"""
Anthropic LLM Sağlayıcısı.
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
    system_message: Optional[str],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    Anthropic modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        import anthropic
        
        # API anahtarını al
        api_key = api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Anthropic API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Anthropic istemci
        client = anthropic.Anthropic(api_key=api_key)
        
        # Sistem mesajı parametresi
        system_param = {"system": system_message} if system_message else {}
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Tamamlama isteği
            with client.messages.stream(
                model=model_config.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                messages=[{"role": "user", "content": prompt}],
                **system_param
            ) as stream:
                # Sonuçları işle
                for text in stream.text_stream:
                    response_text += text
                    streaming_callback(text)
            
            return response_text
        
        # Normal mod
        response = client.messages.create(
            model=model_config.model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
            messages=[{"role": "user", "content": prompt}],
            **system_param
        )
        
        return response.content[0].text
        
    except ImportError:
        logger.error("anthropic kütüphanesi bulunamadı, pip install anthropic komutuyla yükleyin")
        return "[Anthropic kütüphanesi bulunamadı]"

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
    Anthropic ile sohbet tamamlama.
    
    Returns:
        Dict[str, Any]: Yanıt
    """
    try:
        import anthropic
        
        # API anahtarını al
        api_key = llm_service.api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Anthropic API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Anthropic istemci
        client = anthropic.Anthropic(api_key=api_key)
        
        # Anthropic formatına dönüştür
        anthropic_messages = []
        system_message = None
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                system_message = content
            else:
                anthropic_messages.append({
                    "role": role,
                    "content": content
                })
        
        # Sistem mesajı parametresi
        system_param = {"system": system_message} if system_message else {}
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Tamamlama isteği
            with client.messages.stream(
                model=model_config.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop_sequences=stop_sequences,
                messages=anthropic_messages,
                **system_param
            ) as stream:
                # Sonuçları işle
                for text in stream.text_stream:
                    response_text += text
                    streaming_callback(text)
            
            return {
                "role": "assistant",
                "content": response_text
            }
        
        # Normal mod
        response = client.messages.create(
            model=model_config.model_id,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop_sequences=stop_sequences,
            messages=anthropic_messages,
            **system_param
        )
        
        return {
            "role": "assistant",
            "content": response.content[0].text
        }
        
    except ImportError:
        logger.error("anthropic kütüphanesi bulunamadı, pip install anthropic komutuyla yükleyin")
        return {"role": "assistant", "content": "[Anthropic kütüphanesi bulunamadı]"}