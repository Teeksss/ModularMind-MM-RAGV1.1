"""
Web API konnektörü.
"""

import logging
import json
from typing import Dict, List, Any, Optional
import urllib.parse

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class WebApiConnector(BaseConnector):
    """Web API konnektörü sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.base_url = config.options.get("base_url", "")
        self.session = None
    
    def connect(self) -> bool:
        """API'ye bağlanır."""
        try:
            import requests
            
            # Session oluştur
            self.session = requests.Session()
            
            # Base URL kontrolü
            if not self.base_url:
                logger.error("base_url belirtilmemiş")
                return False
            
            # Headers ekle
            headers = self.config.options.get("headers", {})
            if headers:
                self.session.headers.update(headers)
            
            # Kimlik doğrulama
            auth_type = self.config.options.get("auth_type", "")
            
            if auth_type == "basic":
                username = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                self.session.auth = (username, password)
            
            elif auth_type == "bearer":
                token = self.config.credentials.get("token", "")
                self.session.headers["Authorization"] = f"Bearer {token}"
            
            elif auth_type == "api_key":
                key_name = self.config.options.get("api_key_name", "api_key")
                key_value = self.config.credentials.get("api_key", "")
                key_location = self.config.options.get("api_key_location", "query")
                
                if key_location == "header":
                    self.session.headers[key_name] = key_value
                elif key_location == "query":
                    # Query parametreleri bağlantıda kullanılacak
                    pass
            
            # Bağlantıyı test et
            test_endpoint = self.config.options.get("test_endpoint", "")
            if test_endpoint:
                url = urllib.parse.urljoin(self.base_url, test_endpoint)
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("requests kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"API bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """API bağlantısını kapatır."""
        if self.session:
            self.session.close()
            self.session = None
        
        self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """API sorgusu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("API'ye bağlanılamadı")
        
        try:
            # Query bilgilerini ayır
            query_parts = query.split(" ", 1)
            if len(query_parts) < 2:
                raise ValueError("Geçersiz sorgu formatı. 'METHOD /endpoint' formatında olmalıdır.")
            
            method, endpoint = query_parts
            method = method.upper()
            
            # Tam URL oluştur
            url = urllib.parse.urljoin(self.base_url, endpoint)
            
            # API isteğini yap
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=params, timeout=30)
            elif method == "PUT":
                response = self.session.put(url, json=params, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(url, params=params, timeout=30)
            elif method == "PATCH":
                response = self.session.patch(url, json=params, timeout=30)
            else:
                raise ValueError(f"Desteklenmeyen HTTP metodu: {method}")
            
            # Yanıt durumunu kontrol et
            response.raise_for_status()
            
            # JSON yanıtı çözümle
            data = response.json()
            
            # Liste değil ise listeye dönüştür
            if not isinstance(data, list):
                if isinstance(data, dict) and "results" in data and isinstance(data["results"], list):
                    data = data["results"]
                elif isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
                    data = data["data"]
                elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                    data = data["items"]
                else:
                    data = [data]
            
            return data
            
        except Exception as e:
            logger.error(f"API sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """API metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("API'ye bağlanılamadı")
        
        metadata = {
            "base_url": self.base_url,
            "endpoints": [],
            "auth_type": self.config.options.get("auth_type", "")
        }
        
        # Swagger/OpenAPI desteği
        swagger_endpoint = self.config.options.get("swagger_endpoint", "")
        
        if swagger_endpoint:
            try:
                url = urllib.parse.urljoin(self.base_url, swagger_endpoint)
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                swagger_data = response.json()
                
                # OpenAPI yapısını analiz et
                if "paths" in swagger_data:
                    for path, methods in swagger_data["paths"].items():
                        for method, details in methods.items():
                            if method.lower() not in ["get", "post", "put", "delete", "patch"]:
                                continue
                                
                            endpoint_info = {
                                "path": path,
                                "method": method.upper(),
                                "summary": details.get("summary", ""),
                                "description": details.get("description", "")
                            }
                            
                            metadata["endpoints"].append(endpoint_info)
            except Exception as e:
                logger.warning(f"Swagger metadata hatası: {str(e)}")
        
        return metadata