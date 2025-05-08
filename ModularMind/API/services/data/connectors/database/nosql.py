"""
NoSQL veritabanı bağlayıcıları
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import json

from ..base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

class MongoDBConnector(BaseConnector):
    """MongoDB veritabanı bağlayıcısı"""
    
    def __init__(self, config: Dict[str, Any]):
        """MongoDB bağlayıcısını başlatır"""
        super().__init__(config)
        self.client = None
        self.db = None
    
    def connect(self) -> bool:
        """
        MongoDB veritabanına bağlanır
        
        Returns:
            bool: Bağlantı başarılı mı
        """
        try:
            import pymongo
            
            # Bağlantı parametrelerini al
            connection_string = self.config.get('connection_string')
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 27017)
            database = self.config.get('database')
            username = self.config.get('username')
            password = self.config.get('password')
            
            if not database:
                raise ConnectorError("Veritabanı adı gerekli")
            
            # Bağlantı oluştur
            if connection_string:
                self.client = pymongo.MongoClient(connection_string)
            else:
                # Kimlik bilgileri varsa kullan
                if username and password:
                    self.client = pymongo.MongoClient(
                        host=host,
                        port=port,
                        username=username,
                        password=password
                    )
                else:
                    self.client = pymongo.MongoClient(host=host, port=port)
            
            # Veritabanı seç
            self.db = self.client[database]
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("pymongo modülü bulunamadı. Kurulum: pip install pymongo")
            raise ConnectorError("pymongo modülü bulunamadı")
        except Exception as e:
            logger.error(f"MongoDB bağlantı hatası: {e}")
            raise ConnectorError(f"MongoDB bağlantı hatası: {str(e)}")
    
    def disconnect(self) -> bool:
        """
        MongoDB bağlantısını kapatır
        
        Returns:
            bool: Kapatma başarılı mı
        """
        if self.client:
            try:
                self.client.close()
                self.is_connected = False
                self.client = None
                self.db = None
                return True
            except Exception as e:
                logger.error(f"MongoDB bağlantı kapatma hatası: {e}")
                return False
        return True
    
    def test_connection(self) -> bool:
        """
        MongoDB bağlantısını test eder
        
        Returns:
            bool: Test başarılı mı
        """
        try:
            if not self.is_connected:
                self.connect()
            
            # Basit bir sorgu ile bağlantıyı test et
            self.client.server_info()
            return True
        except Exception as e:
            logger.error(f"MongoDB bağlantı testi hatası: {e}")
            return False
    
    def fetch_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        MongoDB'den veri çeker
        
        Args:
            query: Sorgu parametreleri
                collection: Koleksiyon adı
                filter: Filtre kriterleri
                projection: Döndürülecek alanlar
                sort: Sıralama kriterleri
                limit: Sonuç limiti
                skip: Atlanacak sonuç sayısı
            
        Returns:
            List[Dict[str, Any]]: Sonuç listesi
        """
        if not self.is_connected:
            self.connect()
        
        try:
            collection_name = query.get('collection')
            if not collection_name:
                raise ConnectorError("Koleksiyon adı gerekli")
            
            collection = self.db[collection_name]
            
            # Filtre kriterleri
            filter_criteria = query.get('filter', {})
            projection = query.get('projection')
            sort = query.get('sort')
            limit = query.get('limit')
            skip = query.get('skip')
            
            # Sorguyu oluştur
            cursor = collection.find(filter_criteria, projection)
            
            # Sıralama
            if sort:
                cursor = cursor.sort(sort)
            
            # Sayfalama
            if skip:
                cursor = cursor.skip(skip)
            
            if limit:
                cursor = cursor.limit(limit)
            
            # Sonuçları döndür
            results = []
            for doc in cursor:
                # ObjectId'yi stringe çevir
                if '_id' in doc and hasattr(doc['_id'], '__str__'):
                    doc['_id'] = str(doc['_id'])
                results.append(doc)
            
            return results
        except Exception as e:
            logger.error(f"MongoDB veri çekme hatası: {e}")
            raise ConnectorError(f"MongoDB veri çekme hatası: {str(e)}")

class ElasticsearchConnector(BaseConnector):
    """Elasticsearch veritabanı bağlayıcısı"""
    
    def __init__(self, config: Dict[str, Any]):
        """Elasticsearch bağlayıcısını başlatır"""
        super().__init__(config)
        self.client = None
    
    def connect(self) -> bool:
        """
        Elasticsearch'e bağlanır
        
        Returns:
            bool: Bağlantı başarılı mı
        """
        try:
            from elasticsearch import Elasticsearch
            
            # Bağlantı parametrelerini al
            hosts = self.config.get('hosts')
            api_key = self.config.get('api_key')
            cloud_id = self.config.get('cloud_id')
            username = self.config.get('username')
            password = self.config.get('password')
            
            if not hosts and not cloud_id:
                raise ConnectorError("Elasticsearch için hosts veya cloud_id gerekli")
            
            # Bağlantı seçenekleri
            options = {}
            
            # Kimlik bilgileri
            if api_key:
                options['api_key'] = api_key
            elif username and password:
                options['basic_auth'] = (username, password)
            
            # SSL/TLS
            if self.config.get('use_ssl'):
                options['verify_certs'] = self.config.get('verify_certs', True)
                options['ca_certs'] = self.config.get('ca_certs')
            
            # Client oluştur
            if cloud_id:
                self.client = Elasticsearch(cloud_id=cloud_id, **options)
            else:
                self.client = Elasticsearch(hosts, **options)
            
            # Bağlantıyı test et
            if not self.client.ping():
                raise ConnectorError("Elasticsearch bağlantı testi başarısız")
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("elasticsearch modülü bulunamadı. Kurulum: pip install elasticsearch")
            raise ConnectorError("elasticsearch modülü bulunamadı")
        except Exception as e:
            logger.error(f"Elasticsearch bağlantı hatası: {e}")
            raise ConnectorError(f"Elasticsearch bağlantı hatası: {str(e)}")
    
    def disconnect(self) -> bool:
        """
        Elasticsearch bağlantısını kapatır
        
        Returns:
            bool: Kapatma başarılı mı
        """
        if self.client:
            try:
                self.client.close()
                self.is_connected = False
                self.client = None
                return True
            except Exception as e:
                logger.error(f"Elasticsearch bağlantı kapatma hatası: {e}")
                return False
        return True
    
    def test_connection(self) -> bool:
        """
        Elasticsearch bağlantısını test eder
        
        Returns:
            bool: Test başarılı mı
        """
        try:
            if not self.is_connected:
                self.connect()
            
            # Bağlantıyı ping ile test et
            return self.client.ping()
        except Exception as e:
            logger.error(f"Elasticsearch bağlantı testi hatası: {e}")
            return False
    
    def fetch_data(self, query: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Elasticsearch'ten veri çeker
        
        Args:
            query: Sorgu parametreleri
                index: İndeks adı
                body: Sorgu gövdesi
                size: Sonuç sayısı
                from_: Başlangıç sonucu
            
        Returns:
            List[Dict[str, Any]]: Sonuç listesi
        """
        if not self.is_connected:
            self.connect()
        
        try:
            index = query.get('index')
            if not index:
                raise ConnectorError("İndeks adı gerekli")
            
            body = query.get('body', {"query": {"match_all": {}}})
            size = query.get('size', 10)
            from_ = query.get('from_', 0)
            
            # Sorgu yap
            response = self.client.search(
                index=index,
                body=body,
                size=size,
                from_=from_
            )
            
            # Sonuçları döndür
            results = []
            for hit in response['hits']['hits']:
                # Sonuç verisini düzenle
                result = hit['_source']
                result['_id'] = hit['_id']
                result['_score'] = hit['_score']
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Elasticsearch veri çekme hatası: {e}")
            raise ConnectorError(f"Elasticsearch veri çekme hatası: {str(e)}")