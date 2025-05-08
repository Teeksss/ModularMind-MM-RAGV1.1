from typing import Any, Optional, TypeVar, Callable, Union, Dict
import os
import json
import pickle
import hashlib
import logging
import redis
from functools import wraps
from datetime import timedelta
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

T = TypeVar('T')  # Generic type for return values

class CacheSettings:
    """Önbellek ayarları."""
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    DEFAULT_TTL = int(os.getenv("CACHE_TTL", "3600"))  # Varsayılan 1 saat
    KEY_PREFIX = os.getenv("CACHE_KEY_PREFIX", "mm:")
    ENABLED = os.getenv("CACHE_ENABLED", "True").lower() == "true"

class RedisCache:
    """
    Redis tabanlı önbellek servisi.
    Singleton desen kullanarak uygulama genelinde tek önbellek bağlantısı sağlar.
    """
    _instance = None
    _redis_client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisCache, cls).__new__(cls)
            cls._initialize()
        return cls._instance
    
    @classmethod
    def _initialize(cls):
        """Redis bağlantısını başlatır."""
        if not CacheSettings.ENABLED:
            logger.info("Önbellek devre dışı bırakıldı.")
            return
            
        try:
            cls._redis_client = redis.from_url(
                CacheSettings.REDIS_URL, 
                socket_timeout=5.0
            )
            # Bağlantıyı test et
            cls._redis_client.ping()
            logger.info(f"Redis bağlantısı başarılı: {CacheSettings.REDIS_URL}")
        except RedisError as e:
            logger.error(f"Redis bağlantı hatası: {str(e)}")
            cls._redis_client = None
    
    @classmethod
    def get_client(cls):
        """Redis istemcisini döndürür."""
        if cls._redis_client is None and CacheSettings.ENABLED:
            cls._initialize()
        return cls._redis_client
    
    @classmethod
    def generate_key(cls, *args, **kwargs) -> str:
        """
        Önbellek anahtarı oluşturur.
        
        Args:
            *args, **kwargs: Anahtarı oluşturmak için kullanılacak değişkenler
            
        Returns:
            str: Önbellek anahtarı
        """
        # Karmaşık nesneleri (örn. Pydantic modelleri) hash'lemek için JSON'a dönüştür
        key_parts = []
        
        for arg in args:
            if hasattr(arg, 'json'):  # Pydantic model
                key_parts.append(arg.json())
            elif hasattr(arg, '__dict__'):  # Regular class
                key_parts.append(json.dumps(arg.__dict__, sort_keys=True))
            else:
                key_parts.append(str(arg))
                
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
            
        key_str = "_".join(key_parts)
        hashed = hashlib.md5(key_str.encode()).hexdigest()
        
        return f"{CacheSettings.KEY_PREFIX}{hashed}"
    
    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        Önbellekten değer getirir.
        
        Args:
            key: Önbellek anahtarı
            default: Değer bulunamazsa dönecek varsayılan değer
            
        Returns:
            Any: Önbellekteki değer veya varsayılan değer
        """
        if not CacheSettings.ENABLED or cls._redis_client is None:
            return default
            
        try:
            value = cls._redis_client.get(key)
            if value is None:
                return default
                
            return pickle.loads(value)
        except (RedisError, pickle.PickleError) as e:
            logger.error(f"Önbellek okuma hatası: {str(e)}")
            return default
    
    @classmethod
    def set(cls, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Değeri önbelleğe kaydeder.
        
        Args:
            key: Önbellek anahtarı
            value: Kaydedilecek değer
            ttl: Süre dolumu (saniye), None ise DEFAULT_TTL kullanılır
            
        Returns:
            bool: İşlem başarılı mı
        """
        if not CacheSettings.ENABLED or cls._redis_client is None:
            return False
            
        if ttl is None:
            ttl = CacheSettings.DEFAULT_TTL
            
        try:
            serialized = pickle.dumps(value)
            return cls._redis_client.setex(key, ttl, serialized)
        except (RedisError, pickle.PickleError) as e:
            logger.error(f"Önbellek yazma hatası: {str(e)}")
            return False
    
    @classmethod
    def delete(cls, key: str) -> bool:
        """
        Önbellekten değeri siler.
        
        Args:
            key: Önbellek anahtarı
            
        Returns:
            bool: İşlem başarılı mı
        """
        if not CacheSettings.ENABLED or cls._redis_client is None:
            return False
            
        try:
            return bool(cls._redis_client.delete(key))
        except RedisError as e:
            logger.error(f"Önbellek silme hatası: {str(e)}")
            return False
    
    @classmethod
    def clear_pattern(cls, pattern: str) -> int:
        """
        Desene uyan tüm anahtarları siler.
        
        Args:
            pattern: Anahtar deseni (örn. "mm:user:*")
            
        Returns:
            int: Silinen anahtar sayısı
        """
        if not CacheSettings.ENABLED or cls._redis_client is None:
            return 0
            
        try:
            keys = cls._redis_client.keys(pattern)
            if not keys:
                return 0
                
            return cls._redis_client.delete(*keys)
        except RedisError as e:
            logger.error(f"Önbellek desen silme hatası: {str(e)}")
            return 0
    
    @classmethod
    def clear_all(cls) -> bool:
        """
        Tüm önbelleği temizler.
        
        Returns:
            bool: İşlem başarılı mı
        """
        if not CacheSettings.ENABLED or cls._redis_client is None:
            return False
            
        try:
            return cls._redis_client.flushdb()
        except RedisError as e:
            logger.error(f"Önbellek temizleme hatası: {str(e)}")
            return False


def cached(ttl: Optional[int] = None, key_prefix: Optional[str] = None):
    """
    Fonksiyon sonuçlarını önbellekleme için dekoratör.
    
    Args:
        ttl: Önbellek süresi (saniye)
        key_prefix: Anahtar öneki
    
    Returns:
        Callable: Dekoratör fonksiyonu
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not CacheSettings.ENABLED:
                return func(*args, **kwargs)
                
            cache = RedisCache()
            
            # Önbellek anahtarı oluştur
            prefix = key_prefix or f"{func.__module__}.{func.__name__}"
            cache_key = f"{prefix}:{cache.generate_key(*args, **kwargs)}"
            
            # Önbellekten kontrol et
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Önbellek hit: {cache_key}")
                return cached_value
            
            # Fonksiyonu çalıştır ve sonucu önbelleğe al
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Önbellek miss: {cache_key}")
            
            return result
        return wrapper
    return decorator