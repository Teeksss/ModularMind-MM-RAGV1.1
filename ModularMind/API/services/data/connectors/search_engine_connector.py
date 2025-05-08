"""
Arama motoru konnektörü.
"""

import logging
import json
from typing import Dict, List, Any, Optional

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class SearchEngineConnector(BaseConnector):
    """Arama motoru konnektörü sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.client = None
        self.engine_type = config.options.get("engine_type", "elasticsearch")
    
    def connect(self) -> bool:
        """Arama motoruna bağlanır."""
        try:
            if self.engine_type == "elasticsearch":
                return self._connect_elasticsearch()
            elif self.engine_type == "solr":
                return self._connect_solr()
            elif self.engine_type == "algolia":
                return self._connect_algolia()
            else:
                logger.error(f"Desteklenmeyen arama motoru tipi: {self.engine_type}")
                return False
        except Exception as e:
            logger.error(f"Arama motoru bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Arama motoru bağlantısını kapatır."""
        if self.client:
            try:
                if self.engine_type == "elasticsearch":
                    # Elasticsearch istemcisi bağlantı yönetimi otomatik
                    pass
                elif self.engine_type == "solr":
                    # Solr HTTP istemcisi bağlantı yönetimi otomatik
                    pass
                elif self.engine_type == "algolia":
                    # Algolia istemcisi bağlantı yönetimi otomatik
                    pass
                
                self.client = None
                self.is_connected = False
            except Exception as e:
                logger.error(f"Arama motoru bağlantısı kapatılırken hata: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Arama motoru sorgusu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Arama motoruna bağlanılamadı")
        
        try:
            if self.engine_type == "elasticsearch":
                return self._execute_elasticsearch_query(query, params)
            elif self.engine_type == "solr":
                return self._execute_solr_query(query, params)
            elif self.engine_type == "algolia":
                return self._execute_algolia_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen arama motoru tipi: {self.engine_type}")
        except Exception as e:
            logger.error(f"Arama motoru sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Arama motoru metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Arama motoruna bağlanılamadı")
        
        try:
            if self.engine_type == "elasticsearch":
                return self._get_elasticsearch_metadata()
            elif self.engine_type == "solr":
                return self._get_solr_metadata()
            elif self.engine_type == "algolia":
                return self._get_algolia_metadata()
            else:
                raise ValueError(f"Desteklenmeyen arama motoru tipi: {self.engine_type}")
        except Exception as e:
            logger.error(f"Arama motoru metadata hatası: {str(e)}")
            raise
    
    def _connect_elasticsearch(self) -> bool:
        """Elasticsearch'e bağlanır."""
        try:
            from elasticsearch import Elasticsearch
            
            # Bağlantı bilgileri
            hosts = self.config.options.get("hosts", ["localhost:9200"])
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Elasticsearch istemcisi oluştur
            if username and password:
                self.client = Elasticsearch(hosts, basic_auth=(username, password))
            else:
                self.client = Elasticsearch(hosts)
            
            # Bağlantıyı test et
            if not self.client.ping():
                logger.error("Elasticsearch sunucusuna ping başarısız")
                return False
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("elasticsearch kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"Elasticsearch bağlantı hatası: {str(e)}")
            return False
    
    def _connect_solr(self) -> bool:
        """Solr'a bağlanır."""
        try:
            import pysolr
            
            # Bağlantı bilgileri
            solr_url = self.config.options.get("solr_url", "http://localhost:8983/solr/")
            collection = self.config.options.get("collection", "")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Solr URL'sini oluştur
            full_url = f"{solr_url.rstrip('/')}/{collection}"
            
            # Auth bilgileri varsa
            auth = None
            if username and password:
                auth = (username, password)
            
            # Solr istemcisi oluştur
            self.client = pysolr.Solr(full_url, auth=auth)
            
            # Bağlantıyı test et
            self.client.ping()
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("pysolr kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"Solr bağlantı hatası: {str(e)}")
            return False
    
    def _connect_algolia(self) -> bool:
        """Algolia'ya bağlanır."""
        try:
            from algoliasearch.search_client import SearchClient
            
            # Bağlantı bilgileri
            app_id = self.config.options.get("app_id", "")
            api_key = self.config.credentials.get("api_key", "")
            
            if not app_id or not api_key:
                logger.error("Algolia için app_id ve api_key gereklidir")
                return False
            
            # Algolia istemcisi oluştur
            self.client = SearchClient.create(app_id, api_key)
            
            # Bağlantıyı test et - uygulama bilgilerini al
            self.client.list_indices()
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("algoliasearch kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"Algolia bağlantı hatası: {str(e)}")
            return False
    
    def _execute_elasticsearch_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Elasticsearch sorgusu çalıştırır."""
        # Sorgudaki indeks ve sorgu kısmını ayır
        parts = query.strip().split(" ", 1)
        if len(parts) < 2:
            raise ValueError("Geçersiz sorgu formatı. 'index {\"query\": {...}}' formatında olmalıdır.")
        
        index_name = parts[0]
        query_body = parts[1]
        
        # Sorgu gövdesini JSON olarak çözümle
        if isinstance(query_body, str):
            try:
                query_body = json.loads(query_body)
            except json.JSONDecodeError:
                raise ValueError("Geçersiz JSON sorgu formatı")
        
        # Parametreleri birleştir
        if params:
            if isinstance(query_body, dict) and isinstance(params, dict):
                query_body.update(params)
        
        # Sorguyu çalıştır
        response = self.client.search(index=index_name, body=query_body)
        
        # Sonuçları dönüştür
        results = []
        for hit in response["hits"]["hits"]:
            doc = hit["_source"]
            doc["_id"] = hit["_id"]
            doc["_score"] = hit["_score"]
            results.append(doc)
        
        return results
    
    def _execute_solr_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Solr sorgusu çalıştırır."""
        # Temel Solr parametreleri
        solr_params = {
            "q": query,
            "wt": "json"
        }
        
        # Ek parametreleri ekle
        if params:
            solr_params.update(params)
        
        # Sorguyu çalıştır
        response = self.client.search(**solr_params)
        
        # Sonuçları dönüştür
        results = []
        
        for doc in response.docs:
            results.append(dict(doc))
        
        return results
    
    def _execute_algolia_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Algolia sorgusu çalıştırır."""
        # Sorgudaki indeks ve sorgu kısmını ayır
        parts = query.strip().split(" ", 1)
        if len(parts) < 1:
            raise ValueError("Geçersiz sorgu formatı. 'index_name [query_text]' formatında olmalıdır.")
        
        index_name = parts[0]
        query_text = parts[1] if len(parts) > 1 else ""
        
        # İndeksi al
        index = self.client.init_index(index_name)
        
        # Sorgu parametreleri
        search_params = {}
        
        if params:
            search_params.update(params)
        
        # Sorguyu çalıştır
        response = index.search(query_text, search_params)
        
        # Sonuçları dönüştür
        results = []
        
        for hit in response["hits"]:
            results.append(hit)
        
        return results
    
    def _get_elasticsearch_metadata(self) -> Dict[str, Any]:
        """Elasticsearch metadata bilgilerini döndürür."""
        metadata = {
            "indices": [],
            "version": "",
            "cluster_name": ""
        }
        
        try:
            # Elasticsearch bilgilerini al
            info = self.client.info()
            metadata["version"] = info["version"]["number"]
            metadata["cluster_name"] = info["cluster_name"]
            
            # İndeksleri listele
            indices_stats = self.client.indices.stats()
            metadata["indices"] = list(indices_stats["indices"].keys())
            
            return metadata
            
        except Exception as e:
            logger.error(f"Elasticsearch metadata hatası: {str(e)}")
            return metadata
    
    def _get_solr_metadata(self) -> Dict[str, Any]:
        """Solr metadata bilgilerini döndürür."""
        metadata = {
            "collections": [],
            "cores": [],
            "solr_version": ""
        }
        
        try:
            # Solr admin API'sından veri çekmek için gerçek uygulamada requests 
            # modülü ile doğrudan API çağrısı yapılabilir
            import requests
            
            solr_url = self.config.options.get("solr_url", "http://localhost:8983/solr/")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Auth bilgileri varsa
            auth = None
            if username and password:
                auth = (username, password)
            
            # Solr versiyonu
            system_url = f"{solr_url.rstrip('/')}/admin/info/system?wt=json"
            response = requests.get(system_url, auth=auth)
            if response.status_code == 200:
                system_info = response.json()
                metadata["solr_version"] = system_info.get("lucene", {}).get("solr-spec-version", "")
            
            # Koleksiyonları listele
            collections_url = f"{solr_url.rstrip('/')}/admin/collections?action=LIST&wt=json"
            response = requests.get(collections_url, auth=auth)
            if response.status_code == 200:
                collections_info = response.json()
                metadata["collections"] = collections_info.get("collections", [])
            
            # Core'ları listele
            cores_url = f"{solr_url.rstrip('/')}/admin/cores?action=STATUS&wt=json"
            response = requests.get(cores_url, auth=auth)
            if response.status_code == 200:
                cores_info = response.json()
                metadata["cores"] = list(cores_info.get("status", {}).keys())
            
            return metadata
            
        except Exception as e:
            logger.error(f"Solr metadata hatası: {str(e)}")
            return metadata
    
    def _get_algolia_metadata(self) -> Dict[str, Any]:
        """Algolia metadata bilgilerini döndürür."""
        metadata = {
            "indices": [],
            "app_id": self.config.options.get("app_id", "")
        }
        
        try:
            # İndeksleri listele
            indices = self.client.list_indices()
            
            for index in indices["items"]:
                metadata["indices"].append({
                    "name": index["name"],
                    "entries": index["entries"],
                    "updated_at": index["updatedAt"],
                    "primary": index["primary"]
                })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Algolia metadata hatası: {str(e)}")
            return metadata