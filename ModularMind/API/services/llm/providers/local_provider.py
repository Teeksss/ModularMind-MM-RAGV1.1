"""
Yerel LLM Sağlayıcısı.
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
    system_message: Optional[str],
    options: Optional[Dict[str, Any]],
    local_models: Dict[str, Any]
) -> str:
    """
    Yerel model ile metin üretir.
    
    Returns:
        str: Üretilen metin
    """
    try:
        # Modeli yükle
        model = _load_local_model(local_models, model_config.model_id)
        
        # Parametreler
        generation_kwargs = {
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        if stop_sequences:
            generation_kwargs["stopping_criteria"] = _get_stopping_criteria(model, stop_sequences)
            
        # Ek parametreler
        if options:
            for key, value in options.items():
                if key not in generation_kwargs:
                    generation_kwargs[key] = value
        
        # Sistem mesajını hazırla
        if system_message:
            full_prompt = f"{system_message}\n\n{prompt}"
        else:
            full_prompt = prompt
        
        # Metin üret
        result = model.generate_text(full_prompt, **generation_kwargs)
        
        return result
        
    except ImportError:
        logger.error("Yerel model kütüphaneleri bulunamadı, gerekli kütüphaneleri yükleyin")
        return "[Yerel model kütüphaneleri bulunamadı]"
    except Exception as e:
        logger.error(f"Yerel model metin üretme hatası: {str(e)}")
        return f"[Yerel model metin üretme hatası: {str(e)}]"

def _load_local_model(local_models, model_id):
    """
    Yerel modeli yükler veya önbellekten alır.
    
    Args:
        local_models: Önbellekteki modeller sözlüğü
        model_id: Model ID
        
    Returns:
        Model: Yerel model nesnesi
    """
    # Önbellekte kontrol et
    if model_id in local_models:
        return local_models[model_id]
    
    try:
        # Model tipini ve yolunu ayır
        if "/" in model_id:
            model_type, model_path = model_id.split("/", 1)
        else:
            model_type = "transformers"
            model_path = model_id
        
        # Model tipine göre yükleme
        if model_type == "transformers":
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForCausalLM.from_pretrained(model_path)
            generator = pipeline("text-generation", model=model, tokenizer=tokenizer)
            
            # Modeli önbelleğe ekle
            local_models[model_id] = generator
            return generator
            
        elif model_type == "llamacpp":
            from llama_cpp import Llama
            
            # LlamaCpp modeli
            model = Llama(model_path=model_path)
            
            # Modeli önbelleğe ekle
            local_models[model_id] = model
            return model
            
        elif model_type == "ctransformers":
            from ctransformers import AutoModelForCausalLM
            
            # CTransformers modeli
            model = AutoModelForCausalLM.from_pretrained(model_path)
            
            # Modeli önbelleğe ekle
            local_models[model_id] = model
            return model
            
        else:
            raise ValueError(f"Desteklenmeyen yerel model tipi: {model_type}")
            
    except ImportError as e:
        logger.error(f"Model yükleme için gerekli kütüphane bulunamadı: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Model yükleme hatası: {str(e)}")
        raise

def _get_stopping_criteria(model, stop_sequences):
    """
    Durdurma kriterlerini oluşturur.
    
    Args:
        model: Model nesnesi
        stop_sequences: Durdurma dizileri
        
    Returns:
        StoppingCriteria: Durdurma kriterleri
    """
    try:
        from transformers import StoppingCriteria, StoppingCriteriaList
        
        class StopOnTokens(StoppingCriteria):
            def __init__(self, stop_token_ids):
                self.stop_token_ids = stop_token_ids
                
            def __call__(self, input_ids, scores, **kwargs):
                for stop_id in self.stop_token_ids:
                    if input_ids[0][-1] == stop_id:
                        return True
                return False
        
        # Durdurma dizilerini token ID'lerine dönüştür
        if hasattr(model, "tokenizer"):
            tokenizer = model.tokenizer
        elif hasattr(model, "model") and hasattr(model.model, "tokenizer"):
            tokenizer = model.model.tokenizer
        else:
            # Durdurma kriterleri oluşturulamadı
            return None
            
        stop_token_ids = []
        for seq in stop_sequences:
            token_ids = tokenizer.encode(seq, add_special_tokens=False)
            if token_ids:
                stop_token_ids.append(token_ids[-1])
        
        return StoppingCriteriaList([StopOnTokens(stop_token_ids)])
        
    except Exception as e:
        logger.error(f"Durdurma kriterleri oluşturma hatası: {str(e)}")
        return None