"""
Gelişmiş önbellek yönetimi.
Farklı önbellek stratejileri ve dağıtık önbellek desteği.
"""

import hashlib
import inspect
import json
import logging
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast

import redis
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ModularMind.API.core.cache import RedisCache

logger = logging.getLogger(__name__)

# Önbellek stratejileri
class CacheStrategy(str, Enum):
    """Önbellek stratejileri."""
    NONE = "none"  # Önbellek devre dışı
    SIMPLE = "simple"  # Basit anahtar-değer önbellek
    TIERED = "tiered"  # Çok katmanlı önbellek (memory -> redis)
    SHARDED = "sharded"  # Bölümlenmiş önbellek (cluster için)

# Önbellek etiketleri
class CacheTags(str, Enum):
    """Önbellek etiketleri."""
    USER = "user"  # Kullanıcı verileri
    DOCUMENT = "document"  # Dökümanlar
    QUERY = "query"  # Sorgular
    EMBEDDING = "embedding"  # Embeddingler
    CHAT = "chat"  # Sohbet verileri
    METADATA = "metadata"  # Metadata
    SYSTEM = "system"  # Sistem verileri

# Gelişmiş önbellek yöneticisi
class AdvancedCacheManager:
    """
    Gelişmiş önbellek yönetim sınıfı.
    Farklı önbellek stratejilerini ve saklama mekanizmalarını destekler.
    """
    
    # Singleton instance
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AdvancedCacheManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.TIERED,
        redis_url: Optional[str] = None,
        local_cache_size: int = 10000,
        default_ttl: int = 3600,
        prefix: str = "cache:"
    ):
        # Singleton için çift başlatma kontrolü
        if self._initialized:
            return
            
        # Yapılandırma
        self.strategy = strategy
        self.prefix = prefix
        self.default_ttl = default_ttl
        self.local_cache_size = local_cache_size
        
        # Bellek içi önbellek (LRU)
        self.memory_cache: Dict[str, Tuple[Any, float]] = {}
        self.access_counts: Dict[str, int] = {}
        
        # Redis bağlantısı (varsa)
        self.redis_url = redis_url
        self.redis_cache = None
        
        if self.redis_url and self.strategy in (CacheStrategy.TIERED, CacheStrategy.SHARDED):
            try:
                self.redis_cache = RedisCache()
                logger.info(f"Redis önbellek bağlantısı kuruldu: {self.redis_url}")
            except Exception as e:
                logger.error(f"Redis önbellek bağlantı hatası: {str(e)}")
        
        # Etiket-anahtar ilişkileri
        self.tag_to_keys: Dict[str, set] = {}
        
        self._initialized = True
        logger.info(f"Gelişmiş önbellek yöneticisi başlatıldı: strateji={strategy.value}")
    
    def _generate_key(self, *args, **kwargs) -> str:
        """
        Önbellek anahtarı oluşturur.
        
        Args:
            *args, **kwargs: Anahtar oluşturmak için kullanılacak değişkenler
            
        Returns:
            str: Önbellek anahtarı
        """
        # Karmaşık nesneleri hash'lemek için json çevirileri
        key_parts = []
        
        for arg in args:
            if hasattr(arg, 'json'):  # Pydantic model
                key_parts.append(arg.json())
            elif hasattr(arg, '__dict__'):  # Normal class
                key_parts.append(json.dumps(arg.__dict__, sort_keys=True))
            else:
                key_parts.append(str(arg))
                
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
            
        key_str = "_".join(key_parts)
        hashed = hashlib.md5(key_str.encode()).hexdigest()
        
        return f"{self.prefix}{hashed}"
    
    def _track_key_with_tags(self, key: str, tags: List[str]) -> None:
        """
        Belirli etiketlerle anahtarı ilişkilendirir.
        
        Args:
            key: Önbellek anahtarı
            tags: Etiket listesi
        """
        for tag in tags:
            if tag not in self.tag_to_keys:
                self.tag_to_keys[tag] = set()
            self.tag_to_keys[tag].add(key)
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            tags: Optional[List[str]] = None) -> bool:
        """
        Önbelleğe değer kaydeder.
        
        Args:
            key: Önbellek anahtarı
            value: Kaydedilecek değer
            ttl: Süre dolumu (saniye)
            tags: Etiket listesi
            
        Returns:
            bool: İşlem başarılı mı
        """
        if self.strategy == CacheStrategy.NONE:
            return False
            
        if ttl is None:
            ttl = self.default_ttl
            
        # Etiketleri izle
        if tags:
            self._track_key_with_tags(key, tags)
        
        # Strateji: Basit
        if self.strategy == CacheStrategy.SIMPLE:
            expiry = time.time() + ttl
            self.memory_cache[key] = (value, expiry)
            self.access_counts[key] = 0
            
            # Önbellek boyutu kontrolü
            self._evict_if_full()
            return True
        
        # Strateji: Çok katmanlı (memory + redis)
        elif self.strategy == CacheStrategy.TIERED:
            # Memory cache'e kaydet
            expiry = time.time() + ttl
            self.memory_cache[key] = (value, expiry)
            self.access_counts[key] = 0
            
            # Önbellek boyutu kontrolü
            self._evict_if_full()
            
            # Redis'e kaydet (varsa)
            if self.redis_cache:
                return self.redis_cache.set(key, value, ttl)
            return True
        
        # Strateji: Bölümlenmiş (yalnızca redis)
        elif self.strategy == CacheStrategy.SHARDED:
            if self.redis_cache:
                return self.redis_cache.set(key, value, ttl)
            return False
            
        return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Önbellekten değer getirir.
        
        Args:
            key: Önbellek anahtarı
            default: Değer bulunamazsa dönecek varsayılan değer
            
        Returns:
            Any: Önbellekteki değer veya varsayılan değer
        """
        if self.strategy == CacheStrategy.NONE:
            return default
        
        # Strateji: Basit
        if self.strategy == CacheStrategy.SIMPLE:
            if key in self.memory_cache:
                value, expiry = self.memory_cache[key]
                
                # Süresi dolduysa kaldır
                if time.time() > expiry:
                    self.delete(key)
                    return default
                
                # Erişim sayısını artır
                self.access_counts[key] = self.access_counts.get(key, 0) + 1
                return value
            return default
        
        # Strateji: Çok katmanlı (memory -> redis)
        elif self.strategy == CacheStrategy.TIERED:
            # Önce bellek cache'ini kontrol et
            if key in self.memory_cache:
                value, expiry = self.memory_cache[key]
                
                # Süresi dolduysa kaldır
                if time.time() > expiry:
                    self.delete(key)
                else:
                    # Erişim sayısını artır
                    self.access_counts[key] = self.access_counts.get(key, 0) + 1
                    return value
            
            # Redis'i kontrol et
            if self.redis_cache:
                value = self.redis_cache.get(key)
                if value is not None:
                    # Değeri memory cache'e ekle
                    expiry = time.time() + self.default_ttl
                    self.memory_cache[key] = (value, expiry)
                    self.access_counts[key] = 0
                    
                    # Önbellek boyutu kontrolü
                    self._evict_if_full()
                    return value
            
            return default
        
        # Strateji: Bölümlenmiş (yalnızca redis)
        elif self.strategy == CacheStrategy.SHARDED:
            if self.redis_cache:
                return self.redis_cache.get(key, default)
            return default
            
        return default
    
    def delete(self, key: str) -> bool:
        """
        Önbellekten değeri siler.
        
        Args:
            key: Önbellek anahtarı
            
        Returns:
            bool: İşlem başarılı mı
        """
        success = False
        
        # Bellek önbelleğinden sil
        if key in self.memory_cache:
            del self.memory_cache[key]
            if key in self.access_counts:
                del self.access_counts[key]
            success = True
        
        # Redis'ten sil (varsa)
        if self.redis_cache and self.strategy in (CacheStrategy.TIERED, CacheStrategy.SHARDED):
            redis_success = self.redis_cache.delete(key)
            success = success or redis_success
        
        # Etiket izlemelerinden kaldır
        for tag_keys in self.tag_to_keys.values():
            if key in tag_keys:
                tag_keys.remove(key)
        
        return success
    
    def invalidate_by_tags(self, tags: List[str]) -> int:
        """
        Belirlenen etiketlere sahip tüm önbellek değerlerini geçersiz kılar.
        
        Args:
            tags: Geçersiz kılınacak etiketler
            
        Returns:
            int: Geçersiz kılınan anahtar sayısı
        """
        keys_to_invalidate = set()
        
        # Etiketlerle ilişkili tüm anahtarları bul
        for tag in tags:
            if tag in self.tag_to_keys:
                keys_to_invalidate.update(self.tag_to_keys[tag])
        
        # Anahtarları geçersiz kıl
        count = 0
        for key in keys_to_invalidate:
            if self.delete(key):
                count += 1
        
        return count
    
    def _evict_if_full(self) -> None:
        """
        Bellek önbelleği dolduğunda LRU stratejisine göre eski değerleri çıkarır.
        """
        if len(self.memory_cache) <= self.local_cache_size:
            return
            
        # En az kullanılan anahtarları bul ve kaldır
        items_to_remove = len(self.memory_cache) - self.local_cache_size
        if items_to_remove <= 0:
            return
            
        # Erişim sayısına göre sırala
        sorted_keys = sorted(self.access_counts.keys(), key=lambda k: self.access_counts[k])
        
        # En az kullanılanları kaldır
        for key in sorted_keys[:items_to_remove]:
            if key in self.memory_cache:
                del self.memory_cache[key]
            if key in self.access_counts:
                del self.access_counts[key]
    
    def stats(self) -> Dict[str, Any]:
        """
        Önbellek istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        memory_stats = {
            "size": len(self.memory_cache),
            "max_size": self.local_cache_size,
            "usage_percent": (len(self.memory_cache) / self.local_cache_size) * 100 if self.local_cache_size > 0 else 0,
            "tags_count": len(self.tag_to_keys)
        }
        
        redis_stats = {}
        if self.redis_cache and self.redis_cache.get_client():
            try:
                info = self.redis_cache.get_client().info()
                redis_stats = {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "uptime_days": info.get("uptime_in_days", 0)
                }
            except Exception as e:
                redis_stats = {"error": str(e)}
        
        return {
            "strategy": self.strategy.value,
            "memory_cache": memory_stats,
            "redis_cache": redis_stats,
            "default_ttl": self.default_ttl
        }
    
    def clear_all(self) -> bool:
        """
        Tüm önbelleği temizler.
        
        Returns:
            bool: İşlem başarılı mı
        """
        # Bellek önbelleğini temizle
        self.memory_cache = {}
        self.access_counts = {}
        self.tag_to_keys = {}
        
        # Redis'i temizle (varsa)
        redis_success = True
        if self.redis_cache and self.strategy in (CacheStrategy.TIERED, CacheStrategy.SHARDED):
            redis_success = self.redis_cache.clear_all()
        
        return redis_success

# HTTP yanıt önbellekleme middleware'i
class CacheMiddleware(BaseHTTPMiddleware):
    """
    HTTP yanıtlarını önbellekleyen middleware.
    """
    
    def __init__(
        self,
        app: FastAPI,
        ttl: int = 60,
        exclude_paths: Optional[List[str]] = None,
        cache_by_query: bool = True,
        manager: Optional[AdvancedCacheManager] = None
    ):
        super().__init__(app)
        self.ttl = ttl
        self.exclude_paths = exclude_paths or ["/docs", "/redoc", "/openapi.json"]
        self.cache_by_query = cache_by_query
        self.manager = manager or AdvancedCacheManager()
    
    async def dispatch(self, request: Request, call_next):
        """
        HTTP isteklerini işleyen middleware fonksiyonu.
        GET isteklerinin yanıtlarını önbellekler.
        
        Args:
            request: HTTP istek nesnesi
            call_next: Sonraki middleware fonksiyonu
            
        Returns:
            Response: HTTP yanıt nesnesi
        """
        # Sadece GET isteklerini önbellekle
        if request.method != "GET":
            return await call_next(request)
        
        # Hariç tutulan yolları kontrol et
        for path in self.exclude_paths:
            if request.url.path.startswith(path):
                return await call_next(request)
        
        # Önbellek anahtarı oluştur
        cache_key = self._get_cache_key(request)
        
        # Önbellekte ara
        cached_response = self.manager.get(cache_key)
        if cached_response:
            # Önbellekteki yanıtı döndür
            content, status_code, content_type, headers = cached_response
            response = Response(content=content, status_code=status_code)
            
            # Başlıkları ayarla
            response.headers["Content-Type"] = content_type
            for key, value in headers.items():
                if key not in ("Content-Type", "Content-Length"):
                    response.headers[key] = value
            
            # Önbellek bilgisi ekle
            response.headers["X-Cache"] = "HIT"
            return response
        
        # Yanıt önbellekte değilse, normal işleme devam et
        response = await call_next(request)
        
        # Sadece başarılı yanıtları önbellekle
        if 200 <= response.status_code < 400:
            # Yanıt içeriğini al
            content = b""
            async for chunk in response.body_iterator:
                content += chunk
            
            # Önbelleğe ekle
            content_type = response.headers.get("Content-Type", "application/json")
            headers = {k: v for k, v in response.headers.items()}
            
            self.manager.set(
                cache_key,
                (content, response.status_code, content_type, headers),
                ttl=self.ttl,
                tags=[CacheTags.QUERY.value]
            )
            
            # Yeni yanıt oluştur ve döndür
            new_response = Response(content=content, status_code=response.status_code)
            
            # Başlıkları kopyala
            for k, v in headers.items():
                new_response.headers[k] = v
            
            # Önbellek bilgisi ekle
            new_response.headers["X-Cache"] = "MISS"
            return new_response
        
        return response
    
    def _get_cache_key(self, request: Request) -> str:
        """
        İstek için önbellek anahtarı oluşturur.
        
        Args:
            request: HTTP istek nesnesi
            
        Returns:
            str: Önbellek anahtarı
        """
        # Temel olarak path'i al
        key_parts = [request.url.path]
        
        # Sorgu parametrelerini ekle (isteğe bağlı)
        if self.cache_by_query and request.query_params:
            sorted_query = "&".join(
                f"{k}={v}" for k, v in sorted(request.query_params.items())
            )
            key_parts.append(sorted_query)
        
        # Host bilgisini ekle
        key_parts.append(request.headers.get("host", ""))
        
        # Kabul edilen içerik türünü ekle
        key_parts.append(request.headers.get("accept", ""))
        
        # Kullanıcıya özel önbellek için
        # auth_header = request.headers.get("authorization", "")
        # if auth_header:
        #    key_parts.append(auth_header)
        
        # Anahtar oluştur
        key_str = ":".join(key_parts)
        return f"http_cache:{hashlib.md5(key_str.encode()).hexdigest()}"

# Fonksiyon önbellekleme dekoratörü
T = TypeVar('T')

def advanced_cached(
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    strategy: Optional[CacheStrategy] = None,
    tags: Optional[List[str]] = None,
    manager: Optional[AdvancedCacheManager] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Fonksiyon sonuçlarını önbelleklemek için gelişmiş dekoratör.
    
    Args:
        ttl: Önbellek süresi (saniye)
        key_prefix: Anahtar öneki
        strategy: Önbellek stratejisi
        tags: Önbellek etiketleri
        manager: Önbellek yöneticisi
        
    Returns:
        Callable: Dekoratör fonksiyonu
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Fonksiyon bilgilerini al
        func_name = func.__name__
        module_name = func.__module__
        sig = inspect.signature(func)
        
        # Anahtar önekini oluştur
        prefix = key_prefix or f"{module_name}.{func_name}"
        
        # Önbellek yöneticisini al
        cache_manager = manager or AdvancedCacheManager()
        
        # Özel strateji belirlendiyse güncelle
        old_strategy = None
        if strategy is not None:
            old_strategy = cache_manager.strategy
            cache_manager.strategy = strategy
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # Önbellek anahtarı oluştur
            cache_key = f"{prefix}:{cache_manager._generate_key(*args, **kwargs)}"
            
            # Önbellekte ara
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Fonksiyonu çağır
            result = func(*args, **kwargs)
            
            # Sonucu önbelleğe ekle
            cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        # Async fonksiyonlar için ayrı bir wrapper
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            # Önbellek anahtarı oluştur
            cache_key = f"{prefix}:{cache_manager._generate_key(*args, **kwargs)}"
            
            # Önbellekte ara
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Fonksiyonu çağır
            result = await func(*args, **kwargs)
            
            # Sonucu önbelleğe ekle
            cache_manager.set(cache_key, result, ttl=ttl, tags=tags)
            
            return result
        
        # Fonksiyon tipine göre uygun wrapper'ı döndür
        if inspect.iscoroutinefunction(func):
            decorated = async_wrapper
        else:
            decorated = wrapper
        
        # Orijinal stratejiyi geri yükle
        if old_strategy is not None:
            cache_manager.strategy = old_strategy
        
        # Dekoratörlenmiş fonksiyonu döndür
        return decorated
    
    return decorator