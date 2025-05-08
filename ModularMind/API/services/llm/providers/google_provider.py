"""
Google AI LLM Sağlayıcısı.
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
    Google modeliyle metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        import google.generativeai as genai
        
        # API anahtarını al
        api_key = api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Google API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Google API yapılandırması
        genai.configure(api_key=api_key)
        
        # Generative model
        model = genai.GenerativeModel(model_config.model_id)
        
        # Sistem mesajı için Gemini formatı
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Sistem mesajını içeren prompt
            content = []
            if system_message:
                content.append({"role": "system", "parts": [system_message]})
            content.append({"role": "user", "parts": [prompt]})
            
            # Streaming yanıt
            responses = model.generate_content(
                content,
                generation_config=generation_config,
                stream=True
            )
            
            # Stream'i işle
            for response in responses:
                chunk = response.text
                response_text += chunk
                streaming_callback(chunk)
            
            return response_text
        
        # Normal mod
        if system_message:
            chat = model.start_chat(system_instruction=system_message)
            response = chat.send_message(
                prompt,
                generation_config=generation_config
            )
        else:
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
        
        return response.text
        
    except ImportError:
        logger.error("google-generativeai kütüphanesi bulunamadı, pip install google-generativeai komutuyla yükleyin")
        return "[Google Generative AI kütüphanesi bulunamadı]"

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
    Google ile sohbet tamamlama.
    
    Returns:
        Dict[str, Any]: Yanıt
    """
    try:
        import google.generativeai as genai
        
        # API anahtarını al
        api_key = llm_service.api_keys.get(model_config.api_key_env, "")
        if not api_key:
            raise ValueError(f"Google API anahtarı bulunamadı: {model_config.api_key_env}")
        
        # Google API yapılandırması
        genai.configure(api_key=api_key)
        
        # Generative model
        model = genai.GenerativeModel(model_config.model_id)
        
        # Generation config
        generation_config = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stop_sequences:
            generation_config["stop_sequences"] = stop_sequences
        
        # Sistem mesajını bul
        system_message = None
        gemini_messages = []
        
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            if role == "system":
                system_message = content
            else:
                gemini_messages.append({
                    "role": role,
                    "parts": [content]
                })
        
        # Streaming modunda
        if is_streaming and streaming_callback:
            response_text = ""
            
            # Sohbet başlat
            if system_message:
                chat = model.start_chat(system_instruction=system_message)
                
                # Önceki mesajları ekle
                for msg in gemini_messages[:-1]:
                    chat.send_message(msg["parts"][0])
                
                # Son mesajı streaming olarak gönder
                if gemini_messages:
                    latest_message = gemini_messages[-1]["parts"][0]
                    responses = chat.send_message(
                        latest_message,
                        generation_config=generation_config,
                        stream=True
                    )
                    
                    # Stream'i işle
                    for response in responses:
                        chunk = response.text
                        response_text += chunk
                        streaming_callback(chunk)
            else:
                # Doğrudan tüm mesajları gönder
                responses = model.generate_content(
                    gemini_messages,
                    generation_config=generation_config,
                    stream=True
                )
                
                # Stream'i işle
                for response in responses:
                    chunk = response.text
                    response_text += chunk
                    streaming_callback(chunk)
            
            return {
                "role": "assistant",
                "content": response_text
            }
        
        # Normal mod
        if system_message:
            chat = model.start_chat(system_instruction=system_message)
            
            # Önceki mesajları ekle
            for msg in gemini_messages[:-1]:
                chat.send_message(msg["parts"][0])
            
            # Son mesajı gönder
            if gemini_messages:
                response = chat.send_message(
                    gemini_messages[-1]["parts"][0],
                    generation_config=generation_config
                )
            else:
                response = chat.send_message(
                    "",
                    generation_config=generation_config
                )
        else:
            # Doğrudan tüm mesajları gönder
            response = model.generate_content(
                gemini_messages,
                generation_config=generation_config
            )
        
        return {
            "role": "assistant",
            "content": response.text
        }
        
    except ImportError:
        logger.error("google-generativeai kütüphanesi bulunamadı, pip install google-generativeai komutuyla yükleyin")
        return {"role": "assistant", "content": "[Google Generative AI kütüphanesi bulunamadı]"}