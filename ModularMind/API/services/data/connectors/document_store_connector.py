"""
Doküman deposu konnektörü.
"""

import logging
import os
from typing import Dict, List, Any, Optional

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class DocumentStoreConnector(BaseConnector):
    """Doküman deposu konnektörü sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.client = None
        self.store_type = config.options.get("store_type", "elasticsearch")
    
    def connect(self) -> bool:
        """Doküman deposuna bağlanır."""
        try:
            if self.store_type == "elasticsearch":
                return self._connect_elasticsearch()
            elif self.store_type == "opensearch":
                return self._connect_opensearch()
            elif self.store_type == "mongo":
                return self._connect_mongodb()
            else:
                logger.error(f"Desteklenmeyen doküman deposu tipi: {self.store_type}")
                return False
        except Exception as e:
            logger.error(f"Doküman deposu bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Doküman deposu bağlantısını kapatır."""
        if self.client:
            try:
                if self.store_type == "elasticsearch" or self.store_type == "opensearch":
                    # Elasticsearch/OpenSearch istemcisi bağlantı yönetimi otomatik
                    pass
                elif self.store_type == "mongo":
                    self.client.close()
                
                self.client = None
                self.is_connected = False
            except Exception as e:
                logger.error(f"Doküman deposu bağlantısı kapatılırken hata: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Doküman deposu sorgusu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Doküman deposuna bağlanılamadı")
        
        try:
            if self.store_type == "elasticsearch":
                return self._execute_elasticsearch_query(query, params)
            elif self.store_type == "opensearch":
                return self._execute_opensearch_query(query, params)
            elif self.store_type == "mongo":
                return self._execute_mongodb_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen doküman deposu tipi: {self.store_type}")
        except Exception as e:
            logger.error(f"Doküman deposu sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Doküman deposu metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Doküman deposuna bağlanılamadı")
        
        try:
            if self.store_type == "elasticsearch":
                return self._get_elasticsearch_metadata()
            elif self.store_type == "opensearch":
                return self._get_opensearch_metadata()
            elif self.store_type == "mongo":
                return self._get_mongodb_metadata()
            else:
                raise ValueError(f"Desteklenmeyen doküman deposu tipi: {self.store_type}")
        except Exception as e:
            logger.error(f"Doküman deposu metadata hatası: {str(e)}")
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
                self.client = Elasticsearch(
                    hosts,
                    basic_auth=(username, password)
                )
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
    
    def _connect_opensearch(self) -> bool:
        """OpenSearch'e bağlanır."""
        try:
            from opensearchpy import OpenSearch
            
            # Bağlantı bilgileri
            hosts = self.config.options.get("hosts", [{"host": "localhost", "port": 9200}])
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # OpenSearch istemcisi oluştur
            if username and password:
                self.client = OpenSearch(
                    hosts=hosts,
                    http_auth=(username, password)
                )
            else:
                self.client = OpenSearch(hosts=hosts)
            
            # Bağlantıyı test et
            if not self.client.ping():
                logger.error("OpenSearch sunucusuna ping başarısız")
                return False
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("opensearch-py kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"OpenSearch bağlantı hatası: {str(e)}")
            return False
    
    def _connect_mongodb(self) -> bool:
        """MongoDB'ye bağlanır."""
        try:
            import pymongo
            
            # Bağlantı bilgileri
            connection_string = self.config.connection_string
            host = self.config.options.get("host", "localhost")
            port = self.config.options.get("port", 27017)
            database = self.config.options.get("database", "")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # MongoDB istemcisi oluştur
            if connection_string:
                self.client = pymongo.MongoClient(connection_string)
            else:
                if username and password:
                    self.client = pymongo.MongoClient(
                        host=host,
                        port=port,
                        username=username,
                        password=password
                    )
                else:
                    self.client = pymongo.MongoClient(host=host, port=port)
            
            # Bağlantıyı test et
            self.client.admin.command('ping')
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("pymongo kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"MongoDB bağlantı hatası: {str(e)}")
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
    
    def _execute_opensearch_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """OpenSearch sorgusu çalıştırır."""
        # OpenSearch sorguları Elasticsearch ile aynı
        return self._execute_elasticsearch_query(query, params)
    
    def _execute_mongodb_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """MongoDB sorgusu çalıştırır."""
        # Sorgudaki koleksiyon ve sorgu kısmını ayır
        parts = query.strip().split(" ", 1)
        if len(parts) < 2:
            raise ValueError("Geçersiz sorgu formatı. 'database.collection {\"query\": {...}}' formatında olmalıdır.")
        
        collection_name = parts[0]
        query_str = parts[1]
        
        # Veritabanı ve koleksiyon adını ayır
        db_parts = collection_name.split(".", 1)
        if len(db_parts) < 2:
            raise ValueError("Geçersiz koleksiyon formatı. 'database.collection' formatında olmalıdır.")
        
        db_name, coll_name = db_parts
        
        # Veritabanı ve koleksiyonu al
        db = self.client[db_name]
        collection = db[coll_name]
        
        # Sorgu gövdesini JSON olarak çözümle
        if isinstance(query_str, str):
            try:
                query_body = json.loads(query_str)
            except json.JSONDecodeError:
                raise ValueError("Geçersiz JSON sorgu formatı")
        else:
            query_body = query_str
        
        # Parametreleri birleştir
        if params:
            if isinstance(query_body, dict) and isinstance(params, dict):
                query_body.update(params)
        
        # Sorguyu çalıştır
        result_cursor = collection.find(query_body)
        
        # ObjectId'leri string'e dönüştür
        import json
        from bson import json_util
        
        results = []
        for document in result_cursor:
            # BSON ObjectId'leri JSON uyumlu hale getir
            document_str = json.dumps(document, default=json_util.default)
            document_json = json.loads(document_str)
            results.append(document_json)
        
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
    
    def _get_opensearch_metadata(self) -> Dict[str, Any]:
        """OpenSearch metadata bilgilerini döndürür."""
        # OpenSearch metadata'sı Elasticsearch ile benzer
        return self._get_elasticsearch_metadata()
    
    def _get_mongodb_metadata(self) -> Dict[str, Any]:
        """MongoDB metadata bilgilerini döndürür."""
        metadata = {
            "databases": [],
            "collections": {},
            "version": ""
        }
        
        try:
            # MongoDB versiyonu
            server_info = self.client.server_info()
            metadata["version"] = server_info.get("version", "")
            
            # Veritabanlarını listele
            database_names = self.client.list_database_names()
            metadata["databases"] = database_names
            
            # Her veritabanı için koleksiyonları listele
            for db_name in database_names:
                if db_name not in ["admin", "local", "config"]:
                    db = self.client[db_name]
                    collection_names = db.list_collection_names()
                    metadata["collections"][db_name] = collection_names
            
            return metadata
            
        except Exception as e:
            logger.error(f"MongoDB metadata hatası: {str(e)}")
            return metadata