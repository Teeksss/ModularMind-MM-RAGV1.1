"""
Özel LLM Sağlayıcısı.
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
    is_streaming: bool,
    streaming_callback: Optional[Callable[[str], None]],
    system_message: Optional[str],
    options: Optional[Dict[str, Any]],
    api_keys: Dict[str, str]
) -> str:
    """
    Özel API ile metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    # Base URL
    base_url = model_config.base_url
    if not base_url:
        raise ValueError("Özel API için URL gereklidir")
    
    # API anahtarını al
    api_key = ""
    if model_config.api_key_env:
        api_key = api_keys.get(model_config.api_key_env, "")
    
    # İstek başlıkları
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        # Özel API için başlık formatını belirle
        auth_header = model_config.options.get("auth_header", "Authorization")
        auth_prefix = model_config.options.get("auth_prefix", "Bearer")
        headers[auth_header] = f"{auth_prefix} {api_key}"
    
    # İstek parametreleri
    params = {
        "prompt": prompt,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p
    }
    
    if system_message:
        params["system_message"] = system_message
        
    if stop_sequences:
        params["stop"] = stop_sequences
        
    # Model özel parametreleri
    if model_config.options and "model_params" in model_config.options:
        params.update(model_config.options["model_params"])
        
    # Ek parametreler
    if options:
        for key, value in options.items():
            if key not in params:
                params[key] = value
    
    # İstek endpoint
    endpoint = model_config.options.get("endpoint", "/generate")
    api_url = f"{base_url}{endpoint}"
    
    # Streaming modunda
    if is_streaming and streaming_callback:
        return _stream_from_custom_api(api_url, params, headers, model_config, streaming_callback)
    
    # Normal istek
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=params,
            timeout=model_config.timeout
        )
        
        # Yanıtı işle
        if response.status_code == 200:
            result = response.json()
            
            # Farklı yanıt formatlarını kontrol et
            if "text" in result:
                return result["text"]
            elif "generated_text" in result:
                return result["generated_text"]
            elif "content" in result:
                return result["content"]
            elif "completion" in result:
                return result["completion"]
            elif "output" in result:
                return result["output"]
            else:
                return str(result)
        else:
            logger.error(f"Özel API hatası: {response.status_code} - {response.text}")
            return f"[Özel API hatası: {response.status_code}]"
            
    except Exception as e:
        logger.error(f"Özel API metin üretme hatası: {str(e)}")
        return f"[Özel API metin üretme hatası: {str(e)}]"

def _stream_from_custom_api(
    api_url: str,
    params: Dict[str, Any],
    headers: Dict[str, str],
    model_config,
    streaming_callback: Callable[[str], None]
) -> str:
    """
    Özel API'den streaming yanıt alır.
    
    Args:
        api_url: API URL
        params: İstek parametreleri
        headers: İstek başlıkları
        model_config: Model yapılandırması
        streaming_callback: Streaming yanıt işleme fonksiyonu
        
    Returns:
        str: Birleştirilmiş yanıt
    """
    # Streaming parametresini ekle
    params["stream"] = True
    
    try:
        # Streaming isteği gönder
        with requests.post(
            api_url,
            headers=headers,
            json=params,
            timeout=model_config.timeout,
            stream=True
        ) as response:
            response_text = ""
            
            if response.status_code != 200:
                logger.error(f"Özel API streaming hatası: {response.status_code} - {response.text}")
                return f"[Özel API streaming hatası: {response.status_code}]"
            
            # Streaming yanıtı işle
            for line in response.iter_lines():
                if not line:
                    continue
                
                try:
                    # JSON formatını kontrol et
                    if line.startswith(b"data: "):
                        line = line[6:]  # "data: " kısmını kaldır
                    
                    # JSON çözümle
                    data = json.loads(line)
                    
                    # API'ye göre değişen format
                    chunk = ""
                    if "text" in data:
                        chunk = data["text"]
                    elif "choices" in data and len(data["choices"]) > 0:
                        if "text" in data["choices"][0]:
                            chunk = data["choices"][0]["text"]
                        elif "delta" in data["choices"][0] and "content" in data["choices"][0]["delta"]:
                            chunk = data["choices"][0]["delta"]["content"]
                    elif "content" in data:
                        chunk = data["content"]
                    elif "token" in data:
                        chunk = data["token"]
                    
                    # Chunki işle
                    if chunk:
                        response_text += chunk
                        streaming_callback(chunk)
                    
                    # API'nin tamamlandığını bildirdiği durumları kontrol et
                    if data.get("done", False) or data.get("finished", False) or data.get("stop", False):
                        break
                        
                except json.JSONDecodeError:
                    # JSON olmayan satırlar olabilir, atla
                    pass
                except Exception as e:
                    logger.error(f"Özel API streaming satır işleme hatası: {str(e)}")
            
            return response_text
            
    except Exception as e:
        logger.error(f"Özel API streaming hatası: {str(e)}")
        return f"[Özel API streaming hatası: {str(e)}]"