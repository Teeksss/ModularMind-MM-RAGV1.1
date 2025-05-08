"""
Replicate LLM Sağlayıcısı.
"""

import logging
import os
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
    system_message: Optional[str],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    Replicate modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        import replicate
        
        # API anahtarını al
        api_key = api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Replicate API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # API anahtarını ayarla
        os.environ["REPLICATE_API_TOKEN"] = api_key
        
        # Parametreler
        input_params = {
            "prompt": prompt,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if system_message:
            input_params["system_prompt"] = system_message
            
        if stop_sequences:
            input_params["stop_sequences"] = stop_sequences
            
        # Ek parametreler
        if options:
            for key, value in options.items():
                if key not in input_params:
                    input_params[key] = value
        
        # Metin üret
        output = replicate.run(
            model_config.model_id,
            input=input_params
        )
        
        # Çıktıyı birleştir
        if isinstance(output, list):
            return "".join(output)
        else:
            return str(output)
            
    except ImportError:
        logger.error("replicate kütüphanesi bulunamadı, pip install replicate komutuyla yükleyin")
        return "[Replicate kütüphanesi bulunamadı]"