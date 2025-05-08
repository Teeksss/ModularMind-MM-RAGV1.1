"""
Veri Kaynak Ajanları modelleri ve enum tanımlamaları.
"""

import time
import uuid
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

class AgentType(str, Enum):
    """Ajan türleri."""
    WEB_CRAWLER = "web_crawler"
    RSS_READER = "rss_reader"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    API_CONNECTOR = "api_connector"
    EMAIL = "email"
    CUSTOM = "custom"

class AgentStatus(str, Enum):
    """Ajan durumları."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class AgentConfig:
    """Ajan yapılandırması."""
    agent_id: str
    agent_type: AgentType
    name: str
    description: Optional[str] = ""
    source_url: Optional[str] = None
    credentials: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # "interval:10m", "cron:0 9 * * *", "daily:09:00"
    filters: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    metadata_mapping: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[float] = None
    error_count: int = 0
    max_items: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Ayarları sözlüğe dönüştürür."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "source_url": self.source_url,
            "credentials": self.credentials,
            "schedule": self.schedule,
            "filters": self.filters,
            "options": self.options,
            "metadata_mapping": self.metadata_mapping,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "error_count": self.error_count,
            "max_items": self.max_items
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Sözlükten yapılandırma oluşturur."""
        if "agent_type" in data and isinstance(data["agent_type"], str):
            data["agent_type"] = AgentType(data["agent_type"])
        return cls(**data)

@dataclass
class AgentResult:
    """Ajan çalışma sonucu."""
    agent_id: str
    success: bool
    documents: List[Any]  # Document objects
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    item_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Sonuçları sözlüğe dönüştürür."""
        return {
            "agent_id": self.agent_id,
            "success": self.success,
            "documents": [doc.to_dict() for doc in self.documents],
            "error_message": self.error_message,
            "metadata": self.metadata,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "item_count": self.item_count,
            "duration": (self.end_time - self.start_time) if self.end_time else None
        }