"""
Veri Kaynağı Konnektörleri yönetim modülü.
"""

import logging
import os
import json
import importlib
import uuid
from typing import List, Dict, Any, Optional, Callable, Type
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class ConnectorType(str, Enum):
    """Konnektör türleri."""
    DATABASE = "database"
    WEB_API = "web_api"
    DOCUMENT_STORE = "document_store"
    CLOUD_STORAGE = "cloud_storage"
    SEARCH_ENGINE = "search_engine"
    CUSTOM = "custom"

@dataclass
class ConnectorConfig:
    """Konnektör yapılandırması."""
    connector_id: str
    name: str
    connector_type: ConnectorType
    description: Optional[str] = ""
    credentials: Dict[str, Any] = field(default_factory=dict)
    connection_string: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    module_path: Optional[str] = None
    class_name: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Ayarları sözlüğe dönüştürür."""
        return {
            "connector_id": self.connector_id,
            "name": self.name,
            "connector_type": self.connector_type,
            "description": self.description,
            "credentials": self.credentials,
            "connection_string": self.connection_string,
            "options": self.options,
            "enabled": self.enabled,
            "module_path": self.module_path,
            "class_name": self.class_name
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorConfig':
        """Sözlükten yapılandırma oluşturur."""
        if "connector_type" in data and isinstance(data["connector_type"], str):
            data["connector_type"] = ConnectorType(data["connector_type"])
        return cls(**data)

class BaseConnector:
    """Temel konnektör sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.is_connected = False
    
    def connect(self) -> bool:
        """
        Veri kaynağına bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        raise NotImplementedError("Bu metod alt sınıflar tarafından uygulanmalıdır")
    
    def disconnect(self) -> None:
        """Veri kaynağı bağlantısını kapatır."""
        raise NotImplementedError("Bu metod alt sınıflar tarafından uygulanmalıdır")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Sorgu çalıştırır.
        
        Args:
            query: Çalıştırılacak sorgu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        raise NotImplementedError("Bu metod alt sınıflar tarafından uygulanmalıdır")
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Veri kaynağı metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        raise NotImplementedError("Bu metod alt sınıflar tarafından uygulanmalıdır")
    
    def test_connection(self) -> bool:
        """
        Bağlantı testi yapar.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Bağlan
            connected = self.connect()
            
            if connected:
                # Bağlantıyı kapat
                self.disconnect()
            
            return connected
        except Exception as e:
            logger.error(f"Bağlantı testi hatası: {str(e)}")
            return False

class DatabaseConnector(BaseConnector):
    """Veritabanı konnektörü."""
    
    def connect(self) -> bool:
        """
        Veritabanına bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Veritabanı tipini belirle
            db_type = self.config.options.get("db_type", "").lower()
            
            if db_type == "postgresql":
                self._connect_postgresql()
            elif db_type == "mysql":
                self._connect_mysql()
            elif db_type == "sqlite":
                self._connect_sqlite()
            elif db_type == "sqlserver":
                self._connect_sqlserver()
            elif db_type == "oracle":
                self._connect_oracle()
            else:
                raise ValueError(f"Desteklenmeyen veritabanı tipi: {db_type}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if hasattr(self, "connection") and self.connection:
            try:
                self.connection.close()
            except Exception as e:
                logger.error(f"Veritabanı bağlantısı kapatma hatası: {str(e)}")
            
            self.connection = None
            self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        SQL sorgusu çalıştırır.
        
        Args:
            query: SQL sorgusu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Veritabanına bağlanılamadı")
        
        try:
            # Cursor oluştur
            cursor = self.connection.cursor()
            
            # Sorguyu çalıştır
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Sonuçları al
            columns = [col[0] for col in cursor.description] if cursor.description else []
            results = []
            
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            # Cursor'ı kapat
            cursor.close()
            
            return results
            
        except Exception as e:
            logger.error(f"SQL sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Veritabanı metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Veritabanına bağlanılamadı")
        
        try:
            db_type = self.config.options.get("db_type", "").lower()
            metadata = {
                "type": db_type,
                "tables": []
            }
            
            # Tablo listesini al
            if db_type == "postgresql":
                tables = self.execute_query(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
                metadata["tables"] = [table["table_name"] for table in tables]
                
            elif db_type == "mysql":
                database = self.config.options.get("database", "")
                tables = self.execute_query(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                    {"database": database}
                )
                metadata["tables"] = [table["table_name"] for table in tables]
                
            elif db_type == "sqlite":
                tables = self.execute_query(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                metadata["tables"] = [table["name"] for table in tables]
                
            # Diğer veritabanı tipleri için benzer şekilde implemente edilebilir
            
            return metadata
            
        except Exception as e:
            logger.error(f"Metadata alma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _connect_postgresql(self) -> None:
        """PostgreSQL veritabanına bağlanır."""
        try:
            import psycopg2
            import psycopg2.extras
            
            # Bağlantı parametreleri
            conn_string = self.config.connection_string
            
            if conn_string:
                # Bağlantı dizesi varsa kullan
                self.connection = psycopg2.connect(conn_string)
            else:
                # Ayrı parametreler kullan
                host = self.config.options.get("host", "localhost")
                port = self.config.options.get("port", 5432)
                database = self.config.options.get("database", "")
                user = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                
                self.connection = psycopg2.connect(
                    host=host,
                    port=port,
                    dbname=database,
                    user=user,
                    password=password
                )
            
            # Dict cursor kullan
            self.connection.cursor_factory = psycopg2.extras.RealDictCursor
            
        except ImportError:
            raise ImportError("psycopg2 kütüphanesi bulunamadı. pip install psycopg2-binary komutuyla yükleyebilirsiniz.")
    
    def _connect_mysql(self) -> None:
        """MySQL veritabanına bağlanır."""
        try:
            import mysql.connector
            
            # Bağlantı parametreleri
            conn_string = self.config.connection_string
            
            if conn_string:
                # Bağlantı dizesi varsa ayrıştır
                import urllib.parse
                params = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(conn_string).query))
                
                host = urllib.parse.urlsplit(conn_string).hostname or "localhost"
                port = urllib.parse.urlsplit(conn_string).port or 3306
                database = urllib.parse.urlsplit(conn_string).path.lstrip("/")
                user = urllib.parse.urlsplit(conn_string).username or ""
                password = urllib.parse.urlsplit(conn_string).password or ""
                
                self.connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password,
                    **params
                )
            else:
                # Ayrı parametreler kullan
                host = self.config.options.get("host", "localhost")
                port = self.config.options.get("port", 3306)
                database = self.config.options.get("database", "")
                user = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                
                self.connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                )
            
            # Dict cursor için
            self.connection.cursor_class = mysql.connector.cursor.MySQLCursorDict
            
        except ImportError:
            raise ImportError("mysql-connector-python kütüphanesi bulunamadı. pip install mysql-connector-python komutuyla yükleyebilirsiniz.")
    
    def _connect_sqlite(self) -> None:
        """SQLite veritabanına bağlanır."""
        try:
            import sqlite3
            
            # Veritabanı dosyası
            database = self.config.options.get("database", ":memory:")
            
            self.connection = sqlite3.connect(database)
            self.connection.row_factory = sqlite3.Row
            
        except ImportError:
            raise ImportError("sqlite3 kütüphanesi bulunamadı.")
    
    def _connect_sqlserver(self) -> None:
        """SQL Server veritabanına bağlanır."""
        try:
            import pyodbc
            
            # Bağlantı parametreleri
            conn_string = self.config.connection_string
            
            if conn_string:
                # Bağlantı dizesi varsa kullan
                self.connection = pyodbc.connect(conn_string)
            else:
                # Ayrı parametreler kullan
                server = self.config.options.get("server", "localhost")
                database = self.config.options.get("database", "")
                user = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                driver = self.config.options.get("driver", "ODBC Driver 17 for SQL Server")
                
                conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={user};PWD={password}"
                self.connection = pyodbc.connect(conn_str)
            
        except ImportError:
            raise ImportError("pyodbc kütüphanesi bulunamadı. pip install pyodbc komutuyla yükleyebilirsiniz.")
    
    def _connect_oracle(self) -> None:
        """Oracle veritabanına bağlanır."""
        try:
            import cx_Oracle
            
            # Bağlantı parametreleri
            conn_string = self.config.connection_string
            
            if conn_string:
                # Bağlantı dizesi varsa kullan
                self.connection = cx_Oracle.connect(conn_string)
            else:
                # Ayrı parametreler kullan
                host = self.config.options.get("host", "localhost")
                port = self.config.options.get("port", 1521)
                sid = self.config.options.get("sid", "")
                service_name = self.config.options.get("service_name", "")
                user = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                
                if service_name:
                    dsn = cx_Oracle.makedsn(host, port, service_name=service_name)
                else:
                    dsn = cx_Oracle.makedsn(host, port, sid=sid)
                
                self.connection = cx_Oracle.connect(user, password, dsn)
            
        except ImportError:
            raise ImportError("cx_Oracle kütüphanesi bulunamadı. pip install cx_Oracle komutuyla yükleyebilirsiniz.")

class WebApiConnector(BaseConnector):
    """Web API konnektörü."""
    
    def connect(self) -> bool:
        """
        API'ye bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            import requests
            
            # API URL kontrolü
            api_url = self.config.options.get("api_url") or self.config.connection_string
            
            if not api_url:
                raise ValueError("API URL bulunamadı")
            
            # Test isteği gönder
            headers = self._get_headers()
            
            # Bağlantı testi için GET isteği
            test_endpoint = self.config.options.get("test_endpoint", "")
            test_url = f"{api_url}{test_endpoint}"
            
            response = requests.get(test_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            self.api_url = api_url
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"API bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """API bağlantısını kapatır."""
        # REST API için genellikle kapatma işlemi gerekmez
        self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        API sorgusu çalıştırır.
        
        Args:
            query: API endpoint veya sorgu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("API'ye bağlanılamadı")
        
        try:
            import requests
            
            # API URL
            api_url = self.api_url
            
            # Endpoint
            endpoint = query
            
            # Tam URL
            url = f"{api_url}{endpoint}"
            
            # Headers
            headers = self._get_headers()
            
            # HTTP metodu
            method = params.pop("method", "GET") if params else "GET"
            
            # İstek gönder
            if method == "GET":
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method == "POST":
                data = params.pop("data", None) if params else None
                json_data = params.pop("json", None) if params else None
                response = requests.post(url, params=params, data=data, json=json_data, headers=headers, timeout=30)
            elif method == "PUT":
                data = params.pop("data", None) if params else None
                json_data = params.pop("json", None) if params else None
                response = requests.put(url, params=params, data=data, json=json_data, headers=headers, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, params=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"Desteklenmeyen HTTP metodu: {method}")
            
            # Hata kontrolü
            response.raise_for_status()
            
            # JSON yanıtı
            results = response.json()
            
            # Sonuçları liste olarak döndür
            if isinstance(results, dict):
                # Veri alanını bul
                data_path = self.config.options.get("data_path", None)
                if data_path:
                    for key in data_path.split('.'):
                        if key in results:
                            results = results[key]
                        else:
                            results = []
                            break
                
                # Tek sonuç ise listeye çevir
                if not isinstance(results, list):
                    results = [results]
            
            return results
            
        except Exception as e:
            logger.error(f"API sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        API metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("API'ye bağlanılamadı")
        
        try:
            # API tipini ve bilgilerini döndür
            api_type = self.config.options.get("api_type", "REST")
            swagger_url = self.config.options.get("swagger_url", "")
            
            metadata = {
                "type": api_type,
                "base_url": self.api_url,
                "available_endpoints": []
            }
            
            # Swagger bilgisi varsa, API endpoint'lerini çek
            if swagger_url:
                import requests
                
                try:
                    swagger_response = requests.get(swagger_url, timeout=10)
                    swagger_data = swagger_response.json()
                    
                    if "paths" in swagger_data:
                        metadata["available_endpoints"] = list(swagger_data["paths"].keys())
                    elif "swagger" in swagger_data:
                        metadata["swagger_version"] = swagger_data["swagger"]
                except Exception as e:
                    logger.warning(f"Swagger bilgisi çekme hatası: {str(e)}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"API metadata alma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _get_headers(self) -> Dict[str, str]:
        """
        API istekleri için header'ları hazırlar.
        
        Returns:
            Dict[str, str]: Header bilgileri
        """
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Kimlik doğrulama türü
        auth_type = self.config.options.get("auth_type", "")
        
        if auth_type == "bearer":
            token = self.config.credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
            
        elif auth_type == "basic":
            import base64
            
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            auth_str = f"{username}:{password}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            
            headers["Authorization"] = f"Basic {auth_b64}"
            
        elif auth_type == "api_key":
            key_name = self.config.options.get("api_key_name", "X-API-Key")
            key_value = self.config.credentials.get("api_key", "")
            key_location = self.config.options.get("api_key_location", "header")
            
            if key_location == "header":
                headers[key_name] = key_value
        
        # Özel header'lar
        custom_headers = self.config.options.get("headers", {})
        headers.update(custom_headers)
        
        return headers

class CloudStorageConnector(BaseConnector):
    """Bulut depolama konnektörü."""
    
    def connect(self) -> bool:
        """
        Bulut depolamaya bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Bulut sağlayıcısını belirle
            cloud_provider = self.config.options.get("cloud_provider", "").lower()
            
            if cloud_provider == "aws":
                self._connect_aws()
            elif cloud_provider == "google":
                self._connect_gcp()
            elif cloud_provider == "azure":
                self._connect_azure()
            else:
                raise ValueError(f"Desteklenmeyen bulut sağlayıcısı: {cloud_provider}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Bulut depolama bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Bulut depolama bağlantısını kapatır."""
        # Genellikle kapatma işlemi gerekmez
        self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Bulut depolama sorgusunu çalıştırır.
        
        Args:
            query: Sorgu veya komut
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Bulut depolamaya bağlanılamadı")
        
        try:
            # Sorgu tipi
            operation = params.get("operation", "list") if params else "list"
            
            # Bulut sağlayıcısına göre işlem
            cloud_provider = self.config.options.get("cloud_provider", "").lower()
            
            if cloud_provider == "aws":
                return self._execute_aws_operation(operation, query, params)
            elif cloud_provider == "google":
                return self._execute_gcp_operation(operation, query, params)
            elif cloud_provider == "azure":
                return self._execute_azure_operation(operation, query, params)
            else:
                raise ValueError(f"Desteklenmeyen bulut sağlayıcısı: {cloud_provider}")
            
        except Exception as e:
            logger.error(f"Bulut depolama sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Bulut depolama metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Bulut depolamaya bağlanılamadı")
        
        try:
            # Bulut sağlayıcısını belirle
            cloud_provider = self.config.options.get("cloud_provider", "").lower()
            
            metadata = {
                "provider": cloud_provider,
                "buckets": []
            }
            
            # Sağlayıcıya göre bucket/container listesi
            if cloud_provider == "aws":
                metadata["buckets"] = self._list_aws_buckets()
            elif cloud_provider == "google":
                metadata["buckets"] = self._list_gcp_buckets()
            elif cloud_provider == "azure":
                metadata["containers"] = self._list_azure_containers()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Bulut depolama metadata alma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _connect_aws(self) -> None:
        """AWS S3'e bağlanır."""
        try:
            import boto3
            
            # AWS kimlik bilgileri
            aws_access_key = self.config.credentials.get("aws_access_key_id", "")
            aws_secret_key = self.config.credentials.get("aws_secret_access_key", "")
            aws_region = self.config.options.get("aws_region", "us-east-1")
            
            # S3 istemcisi oluştur
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key,
                aws_secret_access_key=aws_secret_key,
                region_name=aws_region
            )
            
        except ImportError:
            raise ImportError("boto3 kütüphanesi bulunamadı. pip install boto3 komutuyla yükleyebilirsiniz.")
    
    def _connect_gcp(self) -> None:
        """Google Cloud Storage'a bağlanır."""
        try:
            from google.cloud import storage
            
            # GCP kimlik dosyası
            credentials_file = self.config.credentials.get("credentials_file", "")
            
            if credentials_file:
                # Kimlik dosyasından istemci oluştur
                self.gcs_client = storage.Client.from_service_account_json(credentials_file)
            else:
                # Ortam değişkenlerinden veya varsayılan kimlikten istemci oluştur
                self.gcs_client = storage.Client()
            
        except ImportError:
            raise ImportError("google-cloud-storage kütüphanesi bulunamadı. pip install google-cloud-storage komutuyla yükleyebilirsiniz.")
    
    def _connect_azure(self) -> None:
        """Azure Blob Storage'a bağlanır."""
        try:
            from azure.storage.blob import BlobServiceClient
            
            # Azure bağlantı dizesi
            connection_string = self.config.connection_string
            account_key = self.config.credentials.get("account_key", "")
            account_name = self.config.credentials.get("account_name", "")
            
            if connection_string:
                # Bağlantı dizesinden istemci oluştur
                self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
            elif account_name and account_key:
                # Hesap adı ve anahtarından istemci oluştur
                self.blob_service_client = BlobServiceClient(
                    account_url=f"https://{account_name}.blob.core.windows.net",
                    credential=account_key
                )
            else:
                raise ValueError("Azure Blob Storage için bağlantı dizesi veya hesap adı/anahtarı gereklidir")
            
        except ImportError:
            raise ImportError("azure-storage-blob kütüphanesi bulunamadı. pip install azure-storage-blob komutuyla yükleyebilirsiniz.")
    
    def _execute_aws_operation(self, operation: str, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """AWS S3 operasyonu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _execute_gcp_operation(self, operation: str, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Google Cloud Storage operasyonu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _execute_azure_operation(self, operation: str, path: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Azure Blob Storage operasyonu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _list_aws_buckets(self) -> List[str]:
        """AWS S3 bucket'larını listeler."""
        response = self.s3_client.list_buckets()
        return [bucket["Name"] for bucket in response.get("Buckets", [])]
    
    def _list_gcp_buckets(self) -> List[str]:
        """Google Cloud Storage bucket'larını listeler."""
        return [bucket.name for bucket in self.gcs_client.list_buckets()]
    
    def _list_azure_containers(self) -> List[str]:
        """Azure Blob Storage container'larını listeler."""
        return [container["name"] for container in self.blob_service_client.list_containers()]

class DocumentStoreConnector(BaseConnector):
    """Belge deposu konnektörü."""
    
    def connect(self) -> bool:
        """
        Belge deposuna bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Belge deposu tipini belirle
            doc_store_type = self.config.options.get("doc_store_type", "").lower()
            
            if doc_store_type == "mongodb":
                self._connect_mongodb()
            elif doc_store_type == "elasticsearch":
                self._connect_elasticsearch()
            elif doc_store_type == "sharepoint":
                self._connect_sharepoint()
            elif doc_store_type == "local":
                self._connect_local()
            else:
                raise ValueError(f"Desteklenmeyen belge deposu tipi: {doc_store_type}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Belge deposu bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Belge deposu bağlantısını kapatır."""
        try:
            doc_store_type = self.config.options.get("doc_store_type", "").lower()
            
            if doc_store_type == "mongodb" and hasattr(self, "mongo_client"):
                self.mongo_client.close()
            elif doc_store_type == "elasticsearch" and hasattr(self, "es_client"):
                self.es_client.close()
            
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Belge deposu bağlantısı kapatma hatası: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Belge deposu sorgusunu çalıştırır.
        
        Args:
            query: Sorgu veya komut
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Belge deposuna bağlanılamadı")
        
        try:
            # Belge deposu tipine göre sorgu
            doc_store_type = self.config.options.get("doc_store_type", "").lower()
            
            if doc_store_type == "mongodb":
                return self._execute_mongodb_query(query, params)
            elif doc_store_type == "elasticsearch":
                return self._execute_elasticsearch_query(query, params)
            elif doc_store_type == "sharepoint":
                return self._execute_sharepoint_query(query, params)
            elif doc_store_type == "local":
                return self._execute_local_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen belge deposu tipi: {doc_store_type}")
            
        except Exception as e:
            logger.error(f"Belge deposu sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Belge deposu metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Belge deposuna bağlanılamadı")
        
        try:
            # Belge deposu tipine göre metadata
            doc_store_type = self.config.options.get("doc_store_type", "").lower()
            
            metadata = {
                "type": doc_store_type,
                "collections": []
            }
            
            if doc_store_type == "mongodb":
                metadata["collections"] = self._list_mongodb_collections()
            elif doc_store_type == "elasticsearch":
                metadata["indices"] = self._list_elasticsearch_indices()
            elif doc_store_type == "sharepoint":
                metadata["sites"] = self._list_sharepoint_sites()
            elif doc_store_type == "local":
                metadata["directories"] = self._list_local_directories()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Belge deposu metadata alma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _connect_mongodb(self) -> None:
        """MongoDB'ye bağlanır."""
        try:
            import pymongo
            
            # MongoDB bağlantı dizesi
            connection_string = self.config.connection_string
            
            if not connection_string:
                # Bağlantı dizesi yoksa, parametrelerden oluştur
                host = self.config.options.get("host", "localhost")
                port = self.config.options.get("port", 27017)
                database = self.config.options.get("database", "")
                username = self.config.credentials.get("username", "")
                password = self.config.credentials.get("password", "")
                
                if username and password:
                    connection_string = f"mongodb://{username}:{password}@{host}:{port}/{database}"
                else:
                    connection_string = f"mongodb://{host}:{port}/{database}"
            
            # MongoDB istemcisi oluştur
            self.mongo_client = pymongo.MongoClient(connection_string)
            
            # Veritabanı adı
            database_name = self.config.options.get("database", "")
            
            if database_name:
                self.mongo_db = self.mongo_client[database_name]
            else:
                # Veritabanı adı belirtilmemişse, varsayılan veritabanını kullan
                self.mongo_db = self.mongo_client.get_database()
            
        except ImportError:
            raise ImportError("pymongo kütüphanesi bulunamadı. pip install pymongo komutuyla yükleyebilirsiniz.")
    
    def _connect_elasticsearch(self) -> None:
        """Elasticsearch'e bağlanır."""
        try:
            from elasticsearch import Elasticsearch
            
            # Elasticsearch bağlantı dizesi
            hosts = self.config.options.get("hosts", ["http://localhost:9200"])
            api_key = self.config.credentials.get("api_key", "")
            cloud_id = self.config.credentials.get("cloud_id", "")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Elasticsearch istemcisi oluştur
            if cloud_id:
                # Elastic Cloud
                self.es_client = Elasticsearch(
                    cloud_id=cloud_id,
                    api_key=api_key if api_key else None,
                    basic_auth=(username, password) if username and password else None
                )
            else:
                # Normal Elasticsearch
                self.es_client = Elasticsearch(
                    hosts=hosts,
                    api_key=api_key if api_key else None,
                    basic_auth=(username, password) if username and password else None
                )
            
        except ImportError:
            raise ImportError("elasticsearch kütüphanesi bulunamadı. pip install elasticsearch komutuyla yükleyebilirsiniz.")
    
    def _connect_sharepoint(self) -> None:
        """SharePoint'e bağlanır."""
        try:
            from office365.runtime.auth.authentication_context import AuthenticationContext
            from office365.sharepoint.client_context import ClientContext
            
            # SharePoint kimlik bilgileri
            site_url = self.config.options.get("site_url", "")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            client_id = self.config.credentials.get("client_id", "")
            client_secret = self.config.credentials.get("client_secret", "")
            
            if not site_url:
                raise ValueError("SharePoint site URL'si gereklidir")
            
            # Kimlik doğrulama
            if client_id and client_secret:
                # App-only kimlik doğrulama
                auth_context = AuthenticationContext(site_url)
                auth_context.acquire_token_for_app(client_id, client_secret)
                self.sp_context = ClientContext(site_url, auth_context)
            elif username and password:
                # Kullanıcı kimlik doğrulama
                auth_context = AuthenticationContext(site_url)
                auth_context.acquire_token_for_user(username, password)
                self.sp_context = ClientContext(site_url, auth_context)
            else:
                raise ValueError("SharePoint için kimlik bilgileri gereklidir")
            
        except ImportError:
            raise ImportError("Office365-REST-Python-Client kütüphanesi bulunamadı. pip install Office365-REST-Python-Client komutuyla yükleyebilirsiniz.")
    
    def _connect_local(self) -> None:
        """Yerel belge klasörüne bağlanır."""
        # Dosya yolu
        base_directory = self.config.options.get("base_directory", "")
        
        if not base_directory or not os.path.isdir(base_directory):
            raise ValueError(f"Geçerli bir klasör yolu değil: {base_directory}")
        
        self.base_directory = base_directory
    
    def _execute_mongodb_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """MongoDB sorgusu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _execute_elasticsearch_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Elasticsearch sorgusu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _execute_sharepoint_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """SharePoint sorgusu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _execute_local_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Yerel dosya sorgusu çalıştırır."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _list_mongodb_collections(self) -> List[str]:
        """MongoDB koleksiyonlarını listeler."""
        return self.mongo_db.list_collection_names()
    
    def _list_elasticsearch_indices(self) -> List[str]:
        """Elasticsearch indekslerini listeler."""
        return list(self.es_client.indices.get_alias("*").keys())
    
    def _list_sharepoint_sites(self) -> List[str]:
        """SharePoint sitelerini listeler."""
        # Bu fonksiyon gerçek uygulamada tamamlanmalıdır
        return []
    
    def _list_local_directories(self) -> List[str]:
        """Yerel alt dizinleri listeler."""
        return [d for d in os.listdir(self.base_directory) if os.path.isdir(os.path.join(self.base_directory, d))]

class SearchEngineConnector(BaseConnector):
    """Arama motoru konnektörü."""
    
    def connect(self) -> bool:
        """
        Arama motoruna bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Arama motoru tipini belirle
            search_engine_type = self.config.options.get("search_engine_type", "").lower()
            
            if search_engine_type == "elasticsearch":
                self._connect_elasticsearch()
            elif search_engine_type == "solr":
                self._connect_solr()
            elif search_engine_type == "algolia":
                self._connect_algolia()
            elif search_engine_type == "meilisearch":
                self._connect_meilisearch()
            else:
                raise ValueError(f"Desteklenmeyen arama motoru tipi: {search_engine_type}")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            logger.error(f"Arama motoru bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Arama motoru bağlantısını kapatır."""
        try:
            search_engine_type = self.config.options.get("search_engine_type", "").lower()
            
            if search_engine_type == "elasticsearch" and hasattr(self, "es_client"):
                self.es_client.close()
            
            self.is_connected = False
            
        except Exception as e:
            logger.error(f"Arama motoru bağlantısı kapatma hatası: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Arama motoru sorgusunu çalıştırır.
        
        Args:
            query: Arama sorgusu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Arama motoruna bağlanılamadı")
        
        try:
            # Arama motoru tipine göre sorgu
            search_engine_type = self.config.options.get("search_engine_type", "").lower()
            
            if search_engine_type == "elasticsearch":
                return self._execute_elasticsearch_query(query, params)
            elif search_engine_type == "solr":
                return self._execute_solr_query(query, params)
            elif search_engine_type == "algolia":
                return self._execute_algolia_query(query, params)
            elif search_engine_type == "meilisearch":
                return self._execute_meilisearch_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen arama motoru tipi: {search_engine_type}")
            
        except Exception as e:
            logger.error(f"Arama motoru sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Arama motoru metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Arama motoruna bağlanılamadı")
        
        try:
            # Arama motoru tipine göre metadata
            search_engine_type = self.config.options.get("search_engine_type", "").lower()
            
            metadata = {
                "type": search_engine_type,
                "indices": []
            }
            
            if search_engine_type == "elasticsearch":
                metadata["indices"] = self._list_elasticsearch_indices()
            elif search_engine_type == "solr":
                metadata["cores"] = self._list_solr_cores()
            elif search_engine_type == "algolia":
                metadata["indices"] = self._list_algolia_indices()
            elif search_engine_type == "meilisearch":
                metadata["indices"] = self._list_meilisearch_indices()
            
            return metadata
            
        except Exception as e:
            logger.error(f"Arama motoru metadata alma hatası: {str(e)}")
            return {"error": str(e)}
    
    def _connect_elasticsearch(self) -> None:
        """Elasticsearch'e bağlanır."""
        try:
            from elasticsearch import Elasticsearch
            
            # Elasticsearch bağlantı dizesi
            hosts = self.config.options.get("hosts", ["http://localhost:9200"])
            api_key = self.config.credentials.get("api_key", "")
            cloud_id = self.config.credentials.get("cloud_id", "")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Elasticsearch istemcisi oluştur
            if cloud_id:
                # Elastic Cloud
                self.es_client = Elasticsearch(
                    cloud_id=cloud_id,
                    api_key=api_key if api_key else None,
                    basic_auth=(username, password) if username and password else None
                )
            else:
                # Normal Elasticsearch
                self.es_client = Elasticsearch(
                    hosts=hosts,
                    api_key=api_key if api_key else None,
                    basic_auth=(username, password) if username and password else None
                )
            
        except ImportError:
            raise ImportError("elasticsearch kütüphanesi bulunamadı. pip install elasticsearch komutuyla yükleyebilirsiniz.")
    
    def _connect_solr(self) -> None:
        """Solr'a bağlanır."""
        try:
            import pysolr
            
            # Solr URL
            solr_url = self.config.options.get("solr_url", "http://localhost:8983/solr")
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Solr core
            core = self.config.options.get("core", "")
            
            if not core:
                raise ValueError("Solr core ismi gereklidir")
            
            # Solr istemcisi oluştur
            auth = (username, password) if username and password else None
            self.solr_client = pysolr.Solr(f"{solr_url}/{core}", auth=auth)
            
        except ImportError:
            raise ImportError("pysolr kütüphanesi bulunamadı. pip install pysolr komutuyla yükleyebilirsiniz.")
    
    def _connect_algolia(self) -> None:
        """Algolia'ya bağlanır."""
        try:
            from algoliasearch.search_client import SearchClient
            
            # Algolia kimlik bilgileri
            app_id = self.config.credentials.get("app_id", "")
            api_key = self.config.credentials.get("api_key", "")
            
            if not app_id or not api_key:
                raise ValueError("Algolia için app_id ve api_key gereklidir")
            
            # Algolia istemcisi oluştur
            self.algolia_client = SearchClient.create(app_id, api_key)
            
        except ImportError:
            raise ImportError("algoliasearch kütüphanesi bulunamadı. pip install algoliasearch komutuyla yükleyebilirsiniz.")
    
    def _connect_meilisearch(self) -> None:
        """MeiliSearch'e bağlanır."""
        try:
            import meilisearch
            
            # MeiliSearch URL
            url = self.config.options.get("url", "http://localhost:7700")
            api_key = self.config.credentials.get("api_key", "")
            
            # MeiliSearch istemcisi oluştur
            self.meilisearch_client = meilisearch.Client(url, api_key)
            
        except ImportError:
            raise ImportError("meilisearch kütüphanesi bulunamadı. pip install meilisearch komutuyla yükleyebilirsiniz.")
    
    def _execute_elasticsearch_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Elasticsearch sorgusu çalıştırır."""
        # İndeks adı
        index = params.get("index", "_all") if params else "_all"
        
        # Elasticsearch sorgu DSL
        if params and "body" in params:
            # Doğrudan sorgu gövdesi
            body = params["body"]
        else:
            # Basit sorgu
            body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": params.get("fields", ["*"]) if params else ["*"]
                    }
                }
            }
        
        # Sıralama
        if params and "sort" in params:
            body["sort"] = params["sort"]
        
        # Boyut
        size = params.get("size", 10) if params else 10
        
        # Sorguyu çalıştır
        response = self.es_client.search(index=index, body=body, size=size)
        
        # Sonuçları dönüştür
        hits = response.get("hits", {}).get("hits", [])
        results = []
        
        for hit in hits:
            result = {
                "_id": hit["_id"],
                "_score": hit["_score"],
                "_index": hit["_index"]
            }
            result.update(hit["_source"])
            results.append(result)
        
        return results
    
    def _execute_solr_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Solr sorgusu çalıştırır."""
        # Sorgu parametreleri
        search_params = {}
        
        if params:
            # Parametreleri aktar
            for key, value in params.items():
                if key not in ["q", "query"]:  # q/query parametresini özel işle
                    search_params[key] = value
        
        # Sonuç sayısı
        rows = params.get("rows", 10) if params else 10
        search_params["rows"] = rows
        
        # Sorguyu çalıştır
        results = self.solr_client.search(query, **search_params)
        
        # Sonuçları dönüştür
        return [dict(doc) for doc in results]
    
    def _execute_algolia_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Algolia sorgusu çalıştırır."""
        # İndeks adı
        index_name = params.get("index", "") if params else ""
        
        if not index_name:
            raise ValueError("Algolia sorgusu için index parametresi gereklidir")
        
        # İndeksi al
        index = self.algolia_client.init_index(index_name)
        
        # Sorgu parametreleri
        search_params = {}
        
        if params:
            # Özel parametreleri işle
            for key, value in params.items():
                if key not in ["index", "query"]:
                    search_params[key] = value
        
        # Sorguyu çalıştır
        response = index.search(query, search_params)
        
        # Sonuçları döndür
        return response["hits"]
    
    def _execute_meilisearch_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """MeiliSearch sorgusu çalıştırır."""
        # İndeks adı
        index_name = params.get("index", "") if params else ""
        
        if not index_name:
            raise ValueError("MeiliSearch sorgusu için index parametresi gereklidir")
        
        # İndeksi al
        index = self.meilisearch_client.index(index_name)
        
        # Sorgu parametreleri
        search_params = {}
        
        if params:
            # Özel parametreleri işle
            for key, value in params.items():
                if key not in ["index", "query"]:
                    search_params[key] = value
        
        # Sorguyu çalıştır
        response = index.search(query, search_params)
        
        # Sonuçları döndür
        return response["hits"]
    
    def _list_elasticsearch_indices(self) -> List[str]:
        """Elasticsearch indekslerini listeler."""
        return list(self.es_client.indices.get_alias("*").keys())
    
    def _list_solr_cores(self) -> List[str]:
        """Solr core'larını listeler."""
        try:
            import requests
            
            # Solr admin URL
            solr_url = self.config.options.get("solr_url", "http://localhost:8983/solr")
            admin_url = f"{solr_url}/admin/cores?action=STATUS&wt=json"
            
            # Kimlik bilgileri
            username = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            auth = (username, password) if username and password else None
            
            # Core listesini al
            response = requests.get(admin_url, auth=auth, timeout=10)
            response.raise_for_status()
            
            # Core'ları çıkar
            data = response.json()
            cores = list(data.get("status", {}).keys())
            
            return cores
            
        except Exception as e:
            logger.error(f"Solr core listesi alma hatası: {str(e)}")
            return []
    
    def _list_algolia_indices(self) -> List[str]:
        """Algolia indekslerini listeler."""
        indices = self.algolia_client.list_indices()
        return [index["name"] for index in indices["items"]]
    
    def _list_meilisearch_indices(self) -> List[str]:
        """MeiliSearch indekslerini listeler."""
        indices = self.meilisearch_client.get_indexes()
        return [index.uid for index in indices]

class CustomConnector(BaseConnector):
    """Özel konnektör sınıfı."""
    
    def connect(self) -> bool:
        """
        Özel veri kaynağına bağlanır.
        
        Returns:
            bool: Bağlantı durumu
        """
        try:
            # Özel modül ve sınıf bilgilerini al
            module_path = self.config.module_path
            class_name = self.config.class_name
            
            if not module_path or not class_name:
                raise ValueError("Özel konnektör için module_path ve class_name gereklidir")
            
            # Modülü dinamik olarak yükle
            module = importlib.import_module(module_path)
            connector_class = getattr(module, class_name)
            
            # Konnektör sınıfını örnekle
            self.custom_connector = connector_class(self.config)
            
            # Bağlantıyı kur
            self.is_connected = self.custom_connector.connect()
            return self.is_connected
            
        except Exception as e:
            logger.error(f"Özel konnektör bağlantı hatası: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self) -> None:
        """Özel konnektör bağlantısını kapatır."""
        if hasattr(self, "custom_connector"):
            self.custom_connector.disconnect()
        
        self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Özel konnektör sorgusunu çalıştırır.
        
        Args:
            query: Sorgu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Özel konnektöre bağlanılamadı")
        
        return self.custom_connector.execute_query(query, params)
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Özel konnektör metadata bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        if not self.is_connected:
            if not self.connect():
                raise Exception("Özel konnektöre bağlanılamadı")
        
        return self.custom_connector.get_metadata()

class DataConnectorRegistry:
    """
    Veri kaynağı konnektörlerini yöneten sınıf.
    """
    
    def __init__(self, config_path: str = "./config/connectors"):
        """
        Args:
            config_path: Yapılandırma dosyaları dizini
        """
        self.config_path = config_path
        
        # Konnektör sınıfları
        self.connector_classes = {
            ConnectorType.DATABASE: DatabaseConnector,
            ConnectorType.WEB_API: WebApiConnector,
            ConnectorType.DOCUMENT_STORE: DocumentStoreConnector,
            ConnectorType.CLOUD_STORAGE: CloudStorageConnector,
            ConnectorType.SEARCH_ENGINE: SearchEngineConnector,
            ConnectorType.CUSTOM: CustomConnector
        }
        
        # Konnektör konfigürasyonları
        self.connectors: Dict[str, ConnectorConfig] = {}
        
        # Aktif konnektör örnekleri
        self.active_connectors: Dict[str, BaseConnector] = {}
        
        # Yapılandırmaları yükle
        self._load_configs()
        
        logger.info(f"DataConnectorRegistry başlatıldı, {len(self.connectors)} konnektör yapılandırması yüklendi")
    
    def register_connector(self, config: ConnectorConfig)