"""
HuggingFace LLM Sağlayıcısı.
"""

import logging
import requests
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
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    Hugging Face modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    # API anahtarını al
    api_key = api_keys.get(model_config.api_key_env, "")
    
    # API kullanarak metin üret
    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else "",
        "Content-Type": "application/json"
    }
    
    # Base URL
    base_url = model_config.base_url or "https://api-inference.huggingface.co/models"
    model_url = f"{base_url}/{model_config.model_id}"
    
    # İstek parametreleri
    params = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "return_full_text": False
        }
    }
    
    if stop_sequences:
        params["parameters"]["stop"] = stop_sequences
    
    # Ek parametreler
    if options:
        for key, value in options.items():
            if key not in params["parameters"]:
                params["parameters"][key] = value
    
    # İstek gönder
    try:
        response = requests.post(
            model_url,
            headers=headers,
            json=params,
            timeout=model_config.timeout
        )
        
        # Yanıtı işle
        if response.status_code == 200:
            result = response.json()
            
            # Yanıt formatını kontrol et
            if isinstance(result, list) and len(result) > 0:
                if "generated_text" in result[0]:
                    return result[0]["generated_text"]
                else:
                    return str(result[0])
            elif isinstance(result, dict):
                if "generated_text" in result:
                    return result["generated_text"]
                else:
                    return str(result)
            else:
                return str(result)
        else:
            logger.error(f"Hugging Face API hatası: {response.status_code} - {response.text}")
            return f"[Hugging Face API hatası: {response.status_code}]"
            
    except Exception as e:
        logger.error(f"Hugging Face metin üretme hatası: {str(e)}")
        return f"[Hugging Face metin üretme hatası: {str(e)}]"