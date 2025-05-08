"""
Konnektör model tanımları.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class ConnectorConfig:
    """Konnektör yapılandırma sınıfı."""
    connector_id: str
    name: str
    connector_type: str
    description: Optional[str] = None
    connection_string: Optional[str] = None
    module_path: Optional[str] = None
    class_name: Optional[str] = None
    enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)
    credentials: Dict[str, Any] = field(default_factory=dict)

class BaseConnector(ABC):
    """Temel konnektör sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """Konnektöre bağlanır."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Konnektör bağlantısını kapatır."""
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Konnektörde sorgu çalıştırır."""
        pass
    
    @abstractmethod
    def get_metadata(self) -> Dict[str, Any]:
        """Konnektör metadata bilgilerini döndürür."""
        pass
    
    def test_connection(self) -> bool:
        """Bağlantıyı test eder."""
        try:
            if not self.is_connected:
                self.connect()
            return self.is_connected
        except Exception as e:
            logger.error(f"Bağlantı testi hatası: {str(e)}")
            return False