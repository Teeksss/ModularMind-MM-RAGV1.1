"""
LLM provider şablon modülü.

Yeni bir LLM provider oluşturmak için kullanılabilir.
"""

import logging
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
    Metin üretir.
    
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
    # Bu kod şablon olarak kullanılabilir
    raise NotImplementedError("Bu metot implement edilmelidir")

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
    Metin üretimini stream eder.
    
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
    # Bu kod şablon olarak kullanılabilir
    raise NotImplementedError("Bu metot implement edilmelidir")

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
    Sohbet mesajı üretir.
    
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
    # Bu kod şablon olarak kullanılabilir
    raise NotImplementedError("Bu metot implement edilmelidir")

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
    Sohbet mesajı üretimini stream eder.
    
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
    # Bu kod şablon olarak kullanılabilir
    raise NotImplementedError("Bu metot implement edilmelidir")