"""
LLM model tanımları ve yapılandırmaları.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class LLMModelConfig:
    """LLM model yapılandırması."""
    
    def __init__(
        self,
        id: str,
        provider: str,
        model_id: str,
        api_key_env: Optional[str] = None,
        api_base_url: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stop_sequences: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ):
        self.id = id
        self.provider = provider
        self.model_id = model_id
        self.api_key_env = api_key_env
        self.api_base_url = api_base_url
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.stop_sequences = stop_sequences or []
        self.options = options or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMModelConfig':
        """Sözlükten model yapılandırması oluşturur."""
        return cls(
            id=data["id"],
            provider=data["provider"],
            model_id=data["model_id"],
            api_key_env=data.get("api_key_env"),
            api_base_url=data.get("api_base_url"),
            max_tokens=data.get("max_tokens", 1024),
            temperature=data.get("temperature", 0.7),
            top_p=data.get("top_p", 1.0),
            stop_sequences=data.get("stop_sequences"),
            options=data.get("options")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Model yapılandırmasını sözlüğe dönüştürür."""
        return {
            "id": self.id,
            "provider": self.provider,
            "model_id": self.model_id,
            "api_key_env": self.api_key_env,
            "api_base_url": self.api_base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stop_sequences": self.stop_sequences,
            "options": self.options
        }
    
    def __str__(self) -> str:
        return f"LLMModelConfig(id={self.id}, provider={self.provider}, model={self.model_id})"

class ModelManager:
    """Model yöneticisi sınıfı."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.models: Dict[str, LLMModelConfig] = {}
        self.config_path = config_path
        
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """Yapılandırma dosyasından modelleri yükler."""
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Modelleri yükle
            if "models" in config_data and isinstance(config_data["models"], list):
                for model_data in config_data["models"]:
                    model_config = LLMModelConfig.from_dict(model_data)
                    self.models[model_config.id] = model_config
            
            return True
        except Exception as e:
            logger.error(f"Model yapılandırması yükleme hatası: {str(e)}")
            return False
    
    def get_model_config(self, model_id: str) -> Optional[LLMModelConfig]:
        """Model ID'sine göre model yapılandırmasını döndürür."""
        return self.models.get(model_id)
    
    def get_models(self) -> List[Dict[str, Any]]:
        """Tüm modellerin listesini döndürür."""
        return [model.to_dict() for model in self.models.values()]
    
    def get_model_ids(self) -> List[str]:
        """Tüm model ID'lerini döndürür."""
        return list(self.models.keys())
    
    def add_model(self, model_config: LLMModelConfig) -> bool:
        """Yeni model ekler."""
        try:
            self.models[model_config.id] = model_config
            return True
        except Exception as e:
            logger.error(f"Model ekleme hatası: {str(e)}")
            return False
    
    def remove_model(self, model_id: str) -> bool:
        """Model siler."""
        try:
            if model_id in self.models:
                del self.models[model_id]
                return True
            return False
        except Exception as e:
            logger.error(f"Model silme hatası: {str(e)}")
            return False
    
    def save_config(self, config_path: Optional[str] = None) -> bool:
        """Model yapılandırmalarını dosyaya kaydeder."""
        try:
            save_path = config_path or self.config_path
            if not save_path:
                logger.error("Kayıt dosyası belirtilmemiş")
                return False
            
            config_data = {
                "models": [model.to_dict() for model in self.models.values()]
            }
            
            with open(save_path, "w") as f:
                json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            logger.error(f"Model yapılandırması kaydetme hatası: {str(e)}")
            return False