"""
Azure OpenAI LLM Sağlayıcısı.
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
    Azure OpenAI modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        import openai
        
        # API anahtarını ve endpoint'i al
        api_key = api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Azure OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
        
        if not model_config.base_url:
            raise ValueError("Azure OpenAI base URL bulunamadı")
        
        # Azure OpenAI istemci
        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=model_config.options.get("api_version", "2023-05-15"),
            azure_endpoint=model_config.base_url
        )
        
        # Mesajları hazırla
        messages = []
        
        if system_message:
            messages.append({"role": "system", "content": system_message})
            
        messages.append({"role": "user", "content": prompt})
        
        # Ek seçenekler
        extra_params = {}
        if options:
            if "logit_bias" in options:
                extra_params["logit_bias"] = options["logit_bias"]
            if "presence_penalty" in options:
                extra_params["presence_penalty"] = options["presence_penalty"]
            if "frequency_penalty" in options:
                extra_params["frequency_penalty"] = options["frequency_penalty"]
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Tamamlama isteği
            stream = client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop_sequences,
                stream=True,
                **extra_params
            )
            
            # Sonuçları işle
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    streaming_callback(content)
            
            return response_text
        
        # Normal mod
        response = client.chat.completions.create(
            model=model_config.model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences,
            **extra_params
        )
        
        return response.choices[0].message.content
        
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
        return "[OpenAI kütüphanesi bulunamadı]"

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
    Azure OpenAI ile sohbet tamamlama.
    
    Returns:
        Dict[str, Any]: Yanıt
    """
    try:
        import openai
        
        # API anahtarını ve endpoint'i al
        api_key = llm_service.api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Azure OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
        
        if not model_config.base_url:
            raise ValueError("Azure OpenAI base URL bulunamadı")
        
        # Azure OpenAI istemci
        client = openai.AzureOpenAI(
            api_key=api_key,
            api_version=model_config.options.get("api_version", "2023-05-15"),
            azure_endpoint=model_config.base_url
        )
        
        # Ek seçenekler
        extra_params = {}
        if options:
            if "logit_bias" in options:
                extra_params["logit_bias"] = options["logit_bias"]
            if "presence_penalty" in options:
                extra_params["presence_penalty"] = options["presence_penalty"]
            if "frequency_penalty" in options:
                extra_params["frequency_penalty"] = options["frequency_penalty"]
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Tamamlama isteği
            stream = client.chat.completions.create(
                model=model_config.model_id,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stop=stop_sequences,
                stream=True,
                **extra_params
            )
            
            # Sonuçları işle
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    response_text += content
                    streaming_callback(content)
            
            return {
                "role": "assistant",
                "content": response_text
            }
        
        # Normal mod
        response = client.chat.completions.create(
            model=model_config.model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences,
            **extra_params
        )
        
        return {
            "role": "assistant",
            "content": response.choices[0].message.content
        }
        
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
        return {"role": "assistant", "content": "[OpenAI kütüphanesi bulunamadı]"}