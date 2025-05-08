"""
Bulut depolama konnektörü.
"""

import logging
import os
from typing import Dict, List, Any, Optional

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class CloudStorageConnector(BaseConnector):
    """Bulut depolama konnektörü sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.client = None
        self.storage_type = config.options.get("storage_type", "s3")
    
    def connect(self) -> bool:
        """Bulut depolamaya bağlanır."""
        try:
            if self.storage_type == "s3":
                return self._connect_s3()
            elif self.storage_type == "azure_blob":
                return self._connect_azure_blob()
            elif self.storage_type == "gcs":
                return self._connect_gcs()
            else:
                logger.error(f"Desteklenmeyen bulut depolama tipi: {self.storage_type}")
                return False
        except Exception as e:
            logger.error(f"Bulut depolama bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Bulut depolama bağlantısını kapatır."""
        self.client = None
        self.is_connected = False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Bulut depolama sorgusu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Bulut depolamaya bağlanılamadı")
        
        try:
            if self.storage_type == "s3":
                return self._execute_s3_query(query, params)
            elif self.storage_type == "azure_blob":
                return self._execute_azure_blob_query(query, params)
            elif self.storage_type == "gcs":
                return self._execute_gcs_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen bulut depolama tipi: {self.storage_type}")
        except Exception as e:
            logger.error(f"Bulut depolama sorgu hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Bulut depolama metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Bulut depolamaya bağlanılamadı")
        
        try:
            if self.storage_type == "s3":
                return self._get_s3_metadata()
            elif self.storage_type == "azure_blob":
                return self._get_azure_blob_metadata()
            elif self.storage_type == "gcs":
                return self._get_gcs_metadata()
            else:
                raise ValueError(f"Desteklenmeyen bulut depolama tipi: {self.storage_type}")
        except Exception as e:
            logger.error(f"Bulut depolama metadata hatası: {str(e)}")
            raise
    
    def _connect_s3(self) -> bool:
        """AWS S3'e bağlanır."""
        try:
            import boto3
            
            # Bağlantı bilgileri
            region = self.config.options.get("region", "us-east-1")
            access_key = self.config.credentials.get("access_key", "")
            secret_key = self.config.credentials.get("secret_key", "")
            endpoint_url = self.config.options.get("endpoint_url", None)
            
            # S3 istemcisi oluştur
            if access_key and secret_key:
                self.client = boto3.client(
                    's3',
                    region_name=region,
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    endpoint_url=endpoint_url
                )
            else:
                # Kimlik bilgileri yoksa varsayılan kimlik sağlayıcıları kullan
                self.client = boto3.client('s3', region_name=region, endpoint_url=endpoint_url)
            
            # Bağlantıyı test et - bucket'ları listele
            self.client.list_buckets()
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("boto3 kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"S3 bağlantı hatası: {str(e)}")
            return False
    
    def _connect_azure_blob(self) -> bool:
        """Azure Blob Storage'a bağlanır."""
        try:
            from azure.storage.blob import BlobServiceClient
            
            # Bağlantı bilgileri
            connection_string = self.config.connection_string
            account_name = self.config.options.get("account_name", "")
            account_key = self.config.credentials.get("account_key", "")
            
            # Azure Blob istemcisi oluştur
            if connection_string:
                self.client = BlobServiceClient.from_connection_string(connection_string)
            elif account_name and account_key:
                from azure.storage.blob import BlobServiceClient
                # Azure SDK ile oluşturulmalıdır
                self.client = BlobServiceClient(
                    account_url=f"https://{account_name}.blob.core.windows.net",
                    credential=account_key
                )
            else:
                logger.error("Bağlantı dizesi veya hesap bilgileri gereklidir")
                return False
            
            # Bağlantıyı test et - container'ları listele
            containers = list(self.client.list_containers(max_results=1))
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("azure-storage-blob kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"Azure Blob bağlantı hatası: {str(e)}")
            return False
    
    def _connect_gcs(self) -> bool:
        """Google Cloud Storage'a bağlanır."""
        try:
            from google.cloud import storage
            
            # Bağlantı bilgileri
            project_id = self.config.options.get("project_id", "")
            credentials_path = self.config.credentials.get("credentials_path", "")
            
            # GCS istemcisi oluştur
            if credentials_path:
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
            
            self.client = storage.Client(project=project_id)
            
            # Bağlantıyı test et - bucket'ları listele
            list(self.client.list_buckets(max_results=1))
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("google-cloud-storage kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"GCS bağlantı hatası: {str(e)}")
            return False
    
    def _execute_s3_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """AWS S3 sorgusu çalıştırır."""
        # S3 sorgusu için format: "bucket_name prefix"
        parts = query.strip().split(" ", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        
        # Komut parametreleri
        max_results = params.get("max_results", 1000) if params else 1000
        filter_suffix = params.get("filter_suffix", "") if params else ""
        
        # Sorguyu çalıştır - nesneleri listele
        if filter_suffix:
            response = self.client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_results
            )
        else:
            response = self.client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_results
            )
        
        # Sonuçları dönüştür
        results = []
        
        if "Contents" in response:
            for obj in response["Contents"]:
                # Suffix filtresi varsa kontrol et
                if filter_suffix and not obj["Key"].endswith(filter_suffix):
                    continue
                    
                # Nesne bilgilerini ekle
                result = {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"].isoformat(),
                    "etag": obj["ETag"].strip('"'),
                    "storage_class": obj.get("StorageClass", "STANDARD"),
                    "bucket": bucket_name
                }
                
                results.append(result)
        
        return results
    
    def _execute_azure_blob_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Azure Blob Storage sorgusu çalıştırır."""
        # Azure Blob sorgusu için format: "container_name prefix"
        parts = query.strip().split(" ", 1)
        container_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        
        # Komut parametreleri
        max_results = params.get("max_results", 1000) if params else 1000
        filter_suffix = params.get("filter_suffix", "") if params else ""
        
        # Container'ı al
        container_client = self.client.get_container_client(container_name)
        
        # Sorguyu çalıştır - blob'ları listele
        blobs = container_client.list_blobs(name_starts_with=prefix, max_results=max_results)
        
        # Sonuçları dönüştür
        results = []
        
        for blob in blobs:
            # Suffix filtresi varsa kontrol et
            if filter_suffix and not blob.name.endswith(filter_suffix):
                continue
                
            # Blob bilgilerini ekle
            result = {
                "name": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified.isoformat(),
                "etag": blob.etag.strip('"'),
                "content_type": blob.content_settings.content_type,
                "container": container_name
            }
            
            results.append(result)
        
        return results
    
    def _execute_gcs_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Google Cloud Storage sorgusu çalıştırır."""
        # GCS sorgusu için format: "bucket_name prefix"
        parts = query.strip().split(" ", 1)
        bucket_name = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        
        # Komut parametreleri
        max_results = params.get("max_results", 1000) if params else 1000
        filter_suffix = params.get("filter_suffix", "") if params else ""
        
        # Bucket'ı al
        bucket = self.client.get_bucket(bucket_name)
        
        # Sorguyu çalıştır - nesneleri listele
        blobs = self.client.list_blobs(bucket_name, prefix=prefix, max_results=max_results)
        
        # Sonuçları dönüştür
        results = []
        
        for blob in blobs:
            # Suffix filtresi varsa kontrol et
            if filter_suffix and not blob.name.endswith(filter_suffix):
                continue
                
            # Blob bilgilerini ekle
            result = {
                "name": blob.name,
                "size": blob.size,
                "updated": blob.updated.isoformat(),
                "md5_hash": blob.md5_hash,
                "content_type": blob.content_type,
                "bucket": bucket_name
            }
            
            results.append(result)
        
        return results
    
    def _get_s3_metadata(self) -> Dict[str, Any]:
        """AWS S3 metadata bilgilerini döndürür."""
        metadata = {
            "buckets": [],
            "region": self.config.options.get("region", "us-east-1")
        }
        
        try:
            # Bucket'ları listele
            response = self.client.list_buckets()
            
            if "Buckets" in response:
                for bucket in response["Buckets"]:
                    bucket_name = bucket["Name"]
                    
                    # Bucket bölgesini al
                    try:
                        location = self.client.get_bucket_location(Bucket=bucket_name)
                        region = location.get("LocationConstraint", "us-east-1")
                        if region is None:
                            region = "us-east-1"  # LocationConstraint None olduğunda us-east-1'dir
                    except Exception:
                        region = "unknown"
                    
                    metadata["buckets"].append({
                        "name": bucket_name,
                        "creation_date": bucket["CreationDate"].isoformat(),
                        "region": region
                    })
            
            return metadata
            
        except Exception as e:
            logger.error(f"S3 metadata hatası: {str(e)}")
            return metadata
    
    def _get_azure_blob_metadata(self) -> Dict[str, Any]:
        """Azure Blob Storage metadata bilgilerini döndürür."""
        metadata = {
            "containers": []
        }
        
        try:
            # Container'ları listele
            containers = self.client.list_containers()
            
            for container in containers:
                # Container'daki blob sayısını al
                container_client = self.client.get_container_client(container.name)
                blob_count = 0
                
                try:
                    # Blob sayısını hesapla (ilk 5000 ile sınırlı)
                    blob_count = sum(1 for _ in container_client.list_blobs(max_results=5000))
                except Exception:
                    blob_count = -1
                
                metadata["containers"].append({
                    "name": container.name,
                    "last_modified": container.last_modified.isoformat() if container.last_modified else None,
                    "blob_count": blob_count
                })
            
            return metadata
            
        except Exception as e:
            logger.error(f"Azure Blob metadata hatası: {str(e)}")
            return metadata
    
    def _get_gcs_metadata(self) -> Dict[str, Any]:
        """Google Cloud Storage metadata bilgilerini döndürür."""
        metadata = {
            "buckets": [],
            "project_id": self.config.options.get("project_id", "")
        }
        
        try:
            # Bucket'ları listele
            buckets = self.client.list_buckets()
            
            for bucket in buckets:
                # Bucket'taki nesne sayısını al
                blob_count = 0
                
                try:
                    # Blob sayısını hesapla (ilk 5000 ile sınırlı)
                    blobs = self.client.list_blobs(bucket.name, max_results=5000)
                    blob_count = sum(1 for _ in blobs)
                except Exception:
                    blob_count = -1
                
                metadata["buckets"].append({
                    "name": bucket.name,
                    "created": bucket._properties.get("timeCreated"),
                    "location": bucket.location,
                    "storage_class": bucket.storage_class,
                    "blob_count": blob_count
                })
            
            return metadata
            
        except Exception as e:
            logger.error(f"GCS metadata hatası: {str(e)}")
            return metadata