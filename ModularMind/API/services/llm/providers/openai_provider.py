"""
OpenAI LLM provider modülü.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

from ModularMind.API.services.llm.models import LLMModelConfig

logger = logging.getLogger(__name__)

def generate(
    llm_service,
    prompt: str, 
    model_config: LLMModelConfig, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    stop_sequences: Optional[List[str]],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    OpenAI ile metin üretir.
    
    Args:
        llm_service: LLM servisi
        prompt: Giriş metni
        model_config: Model yapılandırması
        max_tokens: Maksimum token sayısı
        temperature: Sıcaklık
        top_p: Top-p
        stop_sequences: Durdurma dizileri
        options: Ek seçenekler
        api_keys: API anahtarları
        
    Returns:
        str: Üretilen metin
    """
    try:
        import openai
        
        # API key kontrolü
        api_key = api_keys.get("openai")
        if not api_key:
            raise ValueError("OpenAI API anahtarı bulunamadı")
        
        # API base URL (opsiyonel)
        api_base = model_config.api_base_url
        
        # OpenAI client
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        # Tamamlama isteği
        response = client.completions.create(
            model=model_config.model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences if stop_sequences else None
        )
        
        # Yanıtı dönüştür
        if response.choices and len(response.choices) > 0:
            return response.choices[0].text.strip()
        
        return ""
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı")
        return "ERROR: OpenAI kütüphanesi bulunamadı"
    except Exception as e:
        logger.error(f"OpenAI üretim hatası: {str(e)}")
        return f"ERROR: {str(e)}"

async def stream(
    llm_service,
    prompt: str, 
    model_config: LLMModelConfig, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    stop_sequences: Optional[List[str]],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> AsyncGenerator[str, None]:
    """
    OpenAI ile metin üretimini stream eder.
    
    Args:
        llm_service: LLM servisi
        prompt: Giriş metni
        model_config: Model yapılandırması
        max_tokens: Maksimum token sayısı
        temperature: Sıcaklık
        top_p: Top-p
        stop_sequences: Durdurma dizileri
        options: Ek seçenekler
        api_keys: API anahtarları
        
    Yields:
        str: Üretilen metin parçaları
    """
    try:
        import openai
        
        # API key kontrolü
        api_key = api_keys.get("openai")
        if not api_key:
            raise ValueError("OpenAI API anahtarı bulunamadı")
        
        # API base URL (opsiyonel)
        api_base = model_config.api_base_url
        
        # OpenAI client
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        # Tamamlama isteği
        response = client.completions.create(
            model=model_config.model_id,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences if stop_sequences else None,
            stream=True
        )
        
        # Yanıtı stream et
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                text = chunk.choices[0].text
                if text:
                    yield text
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı")
        yield "ERROR: OpenAI kütüphanesi bulunamadı"
    except Exception as e:
        logger.error(f"OpenAI streaming hatası: {str(e)}")
        yield f"ERROR: {str(e)}"

def generate_chat(
    llm_service,
    messages: List[Dict[str, str]], 
    model_config: LLMModelConfig, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    stop_sequences: Optional[List[str]],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> Dict[str, str]:
    """
    OpenAI ile sohbet mesajı üretir.
    
    Args:
        llm_service: LLM servisi
        messages: Sohbet mesajları
        model_config: Model yapılandırması
        max_tokens: Maksimum token sayısı
        temperature: Sıcaklık
        top_p: Top-p
        stop_sequences: Durdurma dizileri
        options: Ek seçenekler
        api_keys: API anahtarları
        
    Returns:
        Dict[str, str]: Üretilen sohbet mesajı
    """
    try:
        import openai
        
        # API key kontrolü
        api_key = api_keys.get("openai")
        if not api_key:
            raise ValueError("OpenAI API anahtarı bulunamadı")
        
        # API base URL (opsiyonel)
        api_base = model_config.api_base_url
        
        # OpenAI client
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        # OpenAI formatına dönüştür
        openai_messages = []
        for message in messages:
            openai_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        # Chat isteği
        response = client.chat.completions.create(
            model=model_config.model_id,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences if stop_sequences else None
        )
        
        # Yanıtı dönüştür
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            return {"role": message.role, "content": message.content}
        
        return {"role": "assistant", "content": ""}
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı")
        return {"role": "assistant", "content": "ERROR: OpenAI kütüphanesi bulunamadı"}
    except Exception as e:
        logger.error(f"OpenAI chat hatası: {str(e)}")
        return {"role": "assistant", "content": f"ERROR: {str(e)}"}

async def stream_chat(
    llm_service,
    messages: List[Dict[str, str]], 
    model_config: LLMModelConfig, 
    max_tokens: int, 
    temperature: float, 
    top_p: float, 
    stop_sequences: Optional[List[str]],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> AsyncGenerator[str, None]:
    """
    OpenAI ile sohbet mesajı üretimini stream eder.
    
    Args:
        llm_service: LLM servisi
        messages: Sohbet mesajları
        model_config: Model yapılandırması
        max_tokens: Maksimum token sayısı
        temperature: Sıcaklık
        top_p: Top-p
        stop_sequences: Durdurma dizileri
        options: Ek seçenekler
        api_keys: API anahtarları
        
    Yields:
        str: Üretilen sohbet mesajı parçaları
    """
    try:
        import openai
        
        # API key kontrolü
        api_key = api_keys.get("openai")
        if not api_key:
            raise ValueError("OpenAI API anahtarı bulunamadı")
        
        # API base URL (opsiyonel)
        api_base = model_config.api_base_url
        
        # OpenAI client
        client = openai.OpenAI(api_key=api_key, base_url=api_base)
        
        # OpenAI formatına dönüştür
        openai_messages = []
        for message in messages:
            openai_messages.append({
                "role": message["role"],
                "content": message["content"]
            })
        
        # Chat isteği
        response = client.chat.completions.create(
            model=model_config.model_id,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop_sequences if stop_sequences else None,
            stream=True
        )
        
        # Yanıtı stream et
        for chunk in response:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    yield content
    except ImportError:
        logger.error("openai kütüphanesi bulunamadı")
        yield "ERROR: OpenAI kütüphanesi bulunamadı"
    except Exception as e:
        logger.error(f"OpenAI chat streaming hatası: {str(e)}")
        yield f"ERROR: {str(e)}"