"""
Configuration classes for embedding models
"""

from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field

@dataclass
class EmbeddingModelConfig:
    """Configuration for embedding models"""
    
    id: str
    provider: str
    model_id: str
    dimensions: int
    name: Optional[str] = None
    api_key_env: Optional[str] = None
    api_base_url: Optional[str] = None
    options: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Set name to ID if not provided
        if not self.name:
            self.name = self.id
        
        # Set API key environment variable based on provider if not set
        if not self.api_key_env and self.provider in ["openai", "azure", "cohere"]:
            provider_env_map = {
                "openai": "OPENAI_API_KEY",
                "azure": "AZURE_OPENAI_API_KEY",
                "cohere": "COHERE_API_KEY"
            }
            self.api_key_env = provider_env_map.get(self.provider)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingModelConfig':
        """Create instance from dictionary"""
        return cls(
            id=data["id"],
            provider=data["provider"],
            model_id=data["model_id"],
            dimensions=data["dimensions"],
            name=data.get("name"),
            api_key_env=data.get("api_key_env"),
            api_base_url=data.get("api_base_url"),
            options=data.get("options", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "provider": self.provider,
            "model_id": self.model_id,
            "dimensions": self.dimensions
        }
        
        if self.name and self.name != self.id:
            result["name"] = self.name
            
        if self.api_key_env:
            result["api_key_env"] = self.api_key_env
            
        if self.api_base_url:
            result["api_base_url"] = self.api_base_url
            
        if self.options:
            result["options"] = self.options
            
        return result
    
    def __str__(self) -> str:
        return f"EmbeddingModelConfig(id={self.id}, provider={self.provider}, model={self.model_id})"

@dataclass
class EmbeddingCacheConfig:
    """Configuration for embedding cache"""
    
    enabled: bool = True
    max_size: int = 10000  # Maximum number of cached embeddings
    ttl: int = 3600  # Time to live in seconds (1 hour)
    persistent: bool = False  # Whether to save cache to disk
    persistent_path: Optional[str] = None  # Path to save cache to
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmbeddingCacheConfig':
        """Create instance from dictionary"""
        return cls(
            enabled=data.get("enabled", True),
            max_size=data.get("max_size", 10000),
            ttl=data.get("ttl", 3600),
            persistent=data.get("persistent", False),
            persistent_path=data.get("persistent_path")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "enabled": self.enabled,
            "max_size": self.max_size,
            "ttl": self.ttl,
            "persistent": self.persistent
        }
        
        if self.persistent_path:
            result["persistent_path"] = self.persistent_path
            
        return result