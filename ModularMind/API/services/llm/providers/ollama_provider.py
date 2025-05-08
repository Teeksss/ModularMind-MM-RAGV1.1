"""
Ollama LLM Sağlayıcısı.
"""

import logging
import json
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
    system_message: Optional[str],
    options: Optional[Dict[str, Any]]
) -> str:
    """
    Ollama modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    # Ollama API URL'sini oluştur
    base_url = model_config.base_url or "http://localhost:11434"
    api_url = f"{base_url}/api/generate"
    
    # İstek parametreleri
    params = {
        "model": model_config.model_id,
        "prompt": prompt,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
    }
    
    if system_message:
        params["system"] = system_message
        
    if stop_sequences:
        params["options"]["stop"] = stop_sequences
        
    # Ek parametreler
    if options:
        for key, value in options.items():
            if key not in params["options"]:
                params["options"][key] = value
    
    # İstek gönder
    try:
        response = requests.post(
            api_url,
            json=params,
            timeout=model_config.timeout
        )
        
        # Yanıtı işle
        if response.status_code == 200:
            # Ollama JSON satırları döndürür
            lines = response.text.strip().split("\n")
            result = ""
            
            for line in lines:
                try:
                    data = json.loads(line)
                    result += data.get("response", "")
                except json.JSONDecodeError:
                    continue
            
            return result
        else:
            logger.error(f"Ollama API hatası: {response.status_code} - {response.text}")
            return f"[Ollama API hatası: {response.status_code}]"
            
    except Exception as e:
        logger.error(f"Ollama metin üretme hatası: {str(e)}")
        return f"[Ollama metin üretme hatası: {str(e)}]"