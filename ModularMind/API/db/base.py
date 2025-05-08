from typing import Dict, Any, Optional, List, Type
from contextlib import contextmanager
import os
import logging
from pydantic import BaseModel
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class DatabaseSettings(BaseModel):
    """Veritabanı bağlantı ayarları."""
    url: str
    database_name: str
    timeout_ms: int = 5000
    
    @classmethod
    def from_env(cls):
        """Ortam değişkenlerinden veritabanı ayarlarını yapılandırır."""
        return cls(
            url=os.getenv("DATABASE_URL", "mongodb://localhost:27017/modularmind"),
            database_name=os.getenv("DATABASE_NAME", "modularmind"),
            timeout_ms=int(os.getenv("DATABASE_TIMEOUT_MS", "5000"))
        )

class DatabaseManager:
    """
    MongoDB bağlantı yöneticisi.
    Singleton desen ile tüm uygulama için tek bir bağlantı havuzu sağlar.
    """
    _instance = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._settings = DatabaseSettings.from_env()
            cls._collections: Dict[str, Collection] = {}
            cls._initialize_connection()
        return cls._instance
    
    @classmethod
    def _initialize_connection(cls):
        """Veritabanı bağlantısını başlatır."""
        try:
            # MongoDB istemcisini oluştur
            cls._client = MongoClient(
                cls._settings.url,
                serverSelectionTimeoutMS=cls._settings.timeout_ms
            )
            
            # Bağlantıyı test et
            cls._client.admin.command('ping')
            
            # Veritabanı referansını al
            db_name = cls._settings.database_name
            cls._db = cls._client[db_name]
            
            logger.info(f"MongoDB bağlantısı başarıyla kuruldu: {db_name}")
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error(f"MongoDB bağlantı hatası: {str(e)}")
            raise
    
    @classmethod
    def get_database(cls) -> Database:
        """
        MongoDB veritabanı nesnesini döndürür.
        
        Returns:
            Database: MongoDB veritabanı nesnesi
        """
        if cls._db is None:
            cls._initialize_connection()
        return cls._db
    
    @classmethod
    def get_collection(cls, collection_name: str) -> Collection:
        """
        Belirtilen koleksiyon için MongoDB koleksiyon nesnesini döndürür.
        
        Args:
            collection_name: Koleksiyon adı
            
        Returns:
            Collection: MongoDB koleksiyon nesnesi
        """
        if collection_name not in cls._collections:
            cls._collections[collection_name] = cls.get_database()[collection_name]
        return cls._collections[collection_name]
    
    @classmethod
    @contextmanager
    def session(cls):
        """
        MongoDB oturum yöneticisi için context manager.
        
        Yields:
            MongoDB oturumu
        """
        if cls._client is None:
            cls._initialize_connection()
            
        session = cls._client.start_session()
        try:
            yield session
        finally:
            session.end_session()
    
    @classmethod
    def close(cls):
        """Veritabanı bağlantısını kapatır."""
        if cls._client is not None:
            cls._client.close()
            cls._client = None
            cls._db = None
            cls._collections = {}
            logger.info("MongoDB bağlantısı kapatıldı")
    
    @classmethod
    def create_indexes(cls, collection_name: str, indexes: List[Dict[str, Any]]):
        """
        Belirtilen koleksiyon için indeksler oluşturur.
        
        Args:
            collection_name: Koleksiyon adı
            indexes: İndeks tanımları listesi
        """
        collection = cls.get_collection(collection_name)
        for index in indexes:
            collection.create_index(**index)
            logger.info(f"Koleksiyon {collection_name} için indeks oluşturuldu: {index}")