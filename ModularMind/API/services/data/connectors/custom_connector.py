"""
Özel konnektör uygulaması.
"""

import logging
import importlib
from typing import Dict, List, Any, Optional

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class CustomConnector(BaseConnector):
    """Özel konnektör sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.custom_connector = None
    
    def connect(self) -> bool:
        """Özel konnektöre bağlanır."""
        try:
            # Özel modül bilgilerini al
            module_path = self.config.module_path
            class_name = self.config.class_name
            
            if not module_path or not class_name:
                logger.error("Özel konnektör için module_path ve class_name gereklidir")
                return False
            
            # Dinamik modül yükleme
            module = importlib.import_module(module_path)
            connector_class = getattr(module, class_name)
            
            # Konnektör örneğini oluştur
            self.custom_connector = connector_class(self.config)
            
            # Bağlantıyı test et
            if hasattr(self.custom_connector, 'connect'):
                connection_success = self.custom_connector.connect()
                self.is_connected = connection_success
                return connection_success
            else:
                # Connect metodu yoksa bağlantıyı başarılı kabul et
                self.is_connected = True
                return True
            
        except ImportError as e:
            logger.error(f"Özel konnektör modülü bulunamadı: {str(e)}")
            return False
        except AttributeError as e:
            logger.error(f"Özel konnektör sınıfı bulunamadı: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Özel konnektör bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Özel konnektör bağlantısını kapatır."""
        if self.custom_connector:
            try:
                # Disconnect metodu varsa çağır
                if hasattr(self.custom_connector, 'disconnect'):
                    self.custom_connector.disconnect()
                
                self.custom_connector = None
                self.is_connected = False
            except Exception as e:
                logger.error(f"Özel konnektör bağlantısı kapatılırken hata: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Özel konnektör sorgusu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Özel konnektöre bağlanılamadı")
        
        try:
            # Execute_query metodu kontrol et
            if hasattr(self.custom_connector, 'execute_query'):
                return self.custom_connector.execute_query(query, params)
            else:
                # Alternatif olarak query metodu ara
                if hasattr(self.custom_connector, 'query'):
                    return self.custom_connector.query(query, params)
                else:
                    raise ValueError("Özel konnektör execute_query veya query metodu içermiyor")
            
        except Exception as e:
            logger.error(f"Özel konnektör sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Özel konnektör metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Özel konnektöre bağlanılamadı")
        
        try:
            # Get_metadata metodu kontrol et
            if hasattr(self.custom_connector, 'get_metadata'):
                return self.custom_connector.get_metadata()
            else:
                # Alternatif olarak metadata metodu ara
                if hasattr(self.custom_connector, 'metadata'):
                    return self.custom_connector.metadata()
                else:
                    # Varsayılan metadata
                    return {
                        "connector_type": "custom",
                        "module_path": self.config.module_path,
                        "class_name": self.config.class_name
                    }
            
        except Exception as e:
            logger.error(f"Özel konnektör metadata hatası: {str(e)}")
            raise