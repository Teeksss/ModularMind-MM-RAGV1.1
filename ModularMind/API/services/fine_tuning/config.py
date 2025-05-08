"""
Fine-tuning için yapılandırma sınıfları.
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field

@dataclass
class ProviderConfig:
    """Fine-tuning sağlayıcı yapılandırması"""
    
    api_key_env: Optional[str] = None
    api_base_url: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProviderConfig':
        """Dict'ten yapılandırma oluşturur"""
        return cls(
            api_key_env=data.get("api_key_env"),
            api_base_url=data.get("api_base_url"),
            options=data.get("options", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        result = {}
        
        if self.api_key_env:
            result["api_key_env"] = self.api_key_env
            
        if self.api_base_url:
            result["api_base_url"] = self.api_base_url
            
        if self.options:
            result["options"] = self.options
            
        return result

@dataclass
class FineTuningConfig:
    """Fine-tuning yapılandırması"""
    
    providers: Dict[str, ProviderConfig] = field(default_factory=dict)
    data_dir: str = "./data/fine_tuning"
    max_jobs: int = 5
    default_provider: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FineTuningConfig':
        """Dict'ten yapılandırma oluşturur"""
        providers = {}
        
        if "providers" in data:
            for provider_name, provider_data in data["providers"].items():
                providers[provider_name] = ProviderConfig.from_dict(provider_data)
        
        return cls(
            providers=providers,
            data_dir=data.get("data_dir", "./data/fine_tuning"),
            max_jobs=data.get("max_jobs", 5),
            default_provider=data.get("default_provider")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "providers": {name: config.to_dict() for name, config in self.providers.items()},
            "data_dir": self.data_dir,
            "max_jobs": self.max_jobs,
            "default_provider": self.default_provider
        }