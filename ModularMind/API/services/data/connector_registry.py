"""
Veri Kaynağı Konnektör Kayıt Yöneticisi.
"""

import logging
import os
import json
import uuid
from typing import Dict, List, Any, Optional, Type

from ModularMind.API.services.data.connector_models import ConnectorType, ConnectorConfig, BaseConnector
from ModularMind.API.services.data.connectors.database_connector import DatabaseConnector
from ModularMind.API.services.data.connectors.web_api_connector import WebApiConnector
from ModularMind.API.services.data.connectors.document_store_connector import DocumentStoreConnector
from ModularMind.API.services.data.connectors.cloud_storage_connector import CloudStorageConnector
from ModularMind.API.services.data.connectors.search_engine_connector import SearchEngineConnector
from ModularMind.API.services.data.connectors.custom_connector import CustomConnector

logger = logging.getLogger(__name__)

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
    
    def register_connector(self, config: ConnectorConfig) -> str:
        """
        Yeni bir konnektör kaydeder.
        
        Args:
            config: Konnektör yapılandırması
            
        Returns:
            str: Konnektör ID
        """
        # ID yoksa oluştur
        if not config.connector_id:
            config.connector_id = str(uuid.uuid4())
        
        # Konnektörü ekle
        self.connectors[config.connector_id] = config
        
        # Yapılandırmayı kaydet
        self._save_config(config)
        
        logger.info(f"Konnektör eklendi: {config.name} ({config.connector_id})")
        
        return config.connector_id
    
    def update_connector(self, connector_id: str, config_updates: Dict[str, Any]) -> Optional[ConnectorConfig]:
        """
        Konnektör yapılandırmasını günceller.
        
        Args:
            connector_id: Konnektör ID
            config_updates: Güncellenecek ayarlar
            
        Returns:
            Optional[ConnectorConfig]: Güncellenmiş konnektör yapılandırması
        """
        if connector_id not in self.connectors:
            logger.warning(f"Konnektör bulunamadı: {connector_id}")
            return None
        
        # Mevcut yapılandırmayı al
        config = self.connectors[connector_id]
        
        # Yapılandırmayı güncelle
        for key, value in config_updates.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # Yapılandırmayı kaydet
        self._save_config(config)
        
        # Aktif konnektörü kapat
        if connector_id in self.active_connectors:
            self.active_connectors[connector_id].disconnect()
            del self.active_connectors[connector_id]
        
        logger.info(f"Konnektör güncellendi: {config.name} ({connector_id})")
        
        return config
    
    def delete_connector(self, connector_id: str) -> bool:
        """
        Konnektörü siler.
        
        Args:
            connector_id: Konnektör ID
            
        Returns:
            bool: Başarı durumu
        """
        if connector_id not in self.connectors:
            logger.warning(f"Konnektör bulunamadı: {connector_id}")
            return False
        
        # Aktif konnektörü kapat
        if connector_id in self.active_connectors:
            self.active_connectors[connector_id].disconnect()
            del self.active_connectors[connector_id]
        
        # Konnektörü kaldır
        del self.connectors[connector_id]
        
        # Yapılandırma dosyasını sil
        config_file = os.path.join(self.config_path, f"{connector_id}.json")
        if os.path.exists(config_file):
            os.remove(config_file)
        
        logger.info(f"Konnektör silindi: {connector_id}")
        
        return True
    
    def get_connector(self, connector_id: str) -> Optional[ConnectorConfig]:
        """
        Konnektör yapılandırmasını döndürür.
        
        Args:
            connector_id: Konnektör ID
            
        Returns:
            Optional[ConnectorConfig]: Konnektör yapılandırması
        """
        return self.connectors.get(connector_id)
    
    def list_connectors(self) -> List[Dict[str, Any]]:
        """
        Tüm konnektörleri listeler.
        
        Returns:
            List[Dict[str, Any]]: Konnektör listesi
        """
        connectors_list = []
        
        for connector_id, config in self.connectors.items():
            # Temel bilgileri al
            connector_info = {
                "connector_id": connector_id,
                "name": config.name,
                "connector_type": config.connector_type,
                "description": config.description,
                "enabled": config.enabled,
                "is_connected": connector_id in self.active_connectors and self.active_connectors[connector_id].is_connected
            }
            
            connectors_list.append(connector_info)
        
        return connectors_list
    
    def get_connector_instance(self, connector_id: str) -> Optional[BaseConnector]:
        """
        Konnektör nesnesini döndürür.
        
        Args:
            connector_id: Konnektör ID
            
        Returns:
            Optional[BaseConnector]: Konnektör nesnesi
        """
        if connector_id not in self.connectors:
            logger.warning(f"Konnektör bulunamadı: {connector_id}")
            return None
        
        # Aktif konnektörü kontrol et
        if connector_id in self.active_connectors:
            # Konnektör bağlı mı kontrol et
            if not self.active_connectors[connector_id].is_connected:
                # Bağlantıyı yeniden kur
                self.active_connectors[connector_id].connect()
            
            return self.active_connectors[connector_id]
        
        # Konnektör sınıfını al
        config = self.connectors[connector_id]
        connector_class = self.connector_classes.get(config.connector_type)
        
        if not connector_class:
            logger.error(f"Desteklenmeyen konnektör tipi: {config.connector_type}")
            return None
        
        # Konnektör nesnesini oluştur
        connector = connector_class(config)
        
        # Bağlantı kur
        connector.connect()
        
        # Aktif konnektörler listesine ekle
        self.active_connectors[connector_id] = connector
        
        return connector
    
    def execute_query(self, connector_id: str, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Konnektör sorgusu çalıştırır.
        
        Args:
            connector_id: Konnektör ID
            query: Sorgu
            params: Sorgu parametreleri
            
        Returns:
            List[Dict[str, Any]]: Sorgu sonuçları
        """
        connector = self.get_connector_instance(connector_id)
        
        if not connector:
            raise ValueError(f"Konnektör bulunamadı veya bağlanamadı: {connector_id}")
        
        return connector.execute_query(query, params)
    
    def test_connection(self, connector_id: str) -> bool:
        """
        Konnektör bağlantısını test eder.
        
        Args:
            connector_id: Konnektör ID
            
        Returns:
            bool: Bağlantı durumu
        """
        if connector_id not in self.connectors:
            logger.warning(f"Konnektör bulunamadı: {connector_id}")
            return False
        
        # Mevcut yapılandırmayı al
        config = self.connectors[connector_id]
        
        # Konnektör sınıfını al
        connector_class = self.connector_classes.get(config.connector_type)
        
        if not connector_class:
            logger.error(f"Desteklenmeyen konnektör tipi: {config.connector_type}")
            return False
        
        # Test için geçici konnektör oluştur
        connector = connector_class(config)
        
        # Bağlantı testi yap
        return connector.test_connection()
    
    def get_metadata(self, connector_id: str) -> Dict[str, Any]:
        """
        Konnektör metadata bilgilerini döndürür.
        
        Args:
            connector_id: Konnektör ID
            
        Returns:
            Dict[str, Any]: Metadata bilgileri
        """
        connector = self.get_connector_instance(connector_id)
        
        if not connector:
            raise ValueError(f"Konnektör bulunamadı veya bağlanamadı: {connector_id}")
        
        return connector.get_metadata()
    
    def _load_configs(self) -> None:
        """
        Konnektör yapılandırmalarını yükler.
        """
        # Yapılandırma dizinini kontrol et
        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path, exist_ok=True)
            return
        
        # Yapılandırma dosyalarını yükle
        for filename in os.listdir(self.config_path):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.config_path, filename)
                    
                    with open(file_path, "r") as f:
                        config_data = json.load(f)
                    
                    # ConnectorConfig oluştur
                    config = ConnectorConfig.from_dict(config_data)
                    
                    # Konnektörü ekle
                    self.connectors[config.connector_id] = config
                    
                except Exception as e:
                    logger.error(f"Konnektör yapılandırması yükleme hatası: {filename}: {str(e)}")
    
    def _save_config(self, config: ConnectorConfig) -> None:
        """
        Konnektör yapılandırmasını kaydeder.
        
        Args:
            config: Konnektör yapılandırması
        """
        # Yapılandırma dizinini kontrol et
        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path, exist_ok=True)
        
        # Dosya yolu
        file_path = os.path.join(self.config_path, f"{config.connector_id}.json")
        
        # Yapılandırmayı kaydet
        try:
            with open(file_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Konnektör yapılandırması kaydetme hatası: {config.connector_id}: {str(e)}")
    
    def shutdown(self) -> None:
        """
        Tüm aktif konnektörleri kapatır.
        """
        for connector_id, connector in list(self.active_connectors.items()):
            try:
                connector.disconnect()
            except Exception as e:
                logger.error(f"Konnektör kapatma hatası {connector_id}: {str(e)}")
        
        self.active_connectors.clear()
        
        logger.info("Tüm konnektörler kapatıldı")