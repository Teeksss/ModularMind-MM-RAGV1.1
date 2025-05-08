"""
API sürüm yönetimi ve geriye doğru uyumluluk.
"""

import re
from enum import Enum
from typing import Dict, Any, Optional, Callable, List, Type, Union, TypeVar, Generic
from fastapi import FastAPI, APIRouter, Request, Response, Depends, HTTPException, status
from pydantic import BaseModel, create_model, Field
from datetime import date, datetime

# API sürüm modları
class VersioningMode(str, Enum):
    """API sürümleme modları."""
    PATH = "path"        # /v1/users, /v2/users
    HEADER = "header"    # X-API-Version: 1.0
    PARAM = "param"      # ?version=1.0
    MIXED = "mixed"      # Yukarıdakilerin kombinasyonu

class APIVersion:
    """API sürüm bilgisi için yardımcı sınıf."""
    
    def __init__(self, major: int, minor: int = 0, patch: int = 0, 
                 sunset_date: Optional[date] = None, deprecated: bool = False):
        """
        Args:
            major: Ana sürüm numarası
            minor: Alt sürüm numarası
            patch: Yama sürüm numarası
            sunset_date: Bu sürümün kullanımdan kaldırılacağı tarih
            deprecated: Bu sürüm kullanımdan kaldırıldı mı
        """
        self.major = major
        self.minor = minor
        self.patch = patch
        self.sunset_date = sunset_date
        self.deprecated = deprecated
    
    @property
    def full_version(self) -> str:
        """Tam sürüm stringi."""
        return f"{self.major}.{self.minor}.{self.patch}"
    
    @property
    def is_sunset(self) -> bool:
        """Sürüm kullanım süresi doldu mu."""
        if self.sunset_date is None:
            return False
        return date.today() >= self.sunset_date
    
    def __str__(self) -> str:
        return self.full_version
    
    def __repr__(self) -> str:
        sunset_str = f", sunset_date={self.sunset_date}" if self.sunset_date else ""
        deprecated_str = ", deprecated=True" if self.deprecated else ""
        return f"APIVersion({self.major}, {self.minor}, {self.patch}{sunset_str}{deprecated_str})"
    
    def __eq__(self, other):
        if isinstance(other, APIVersion):
            return (self.major, self.minor, self.patch) == (other.major, other.minor, other.patch)
        return False
    
    def __lt__(self, other):
        if isinstance(other, APIVersion):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
        return NotImplemented
    
    def __le__(self, other):
        if isinstance(other, APIVersion):
            return (self.major, self.minor, self.patch) <= (other.major, other.minor, other.patch)
        return NotImplemented
    
    def __gt__(self, other):
        if isinstance(other, APIVersion):
            return (self.major, self.minor, self.patch) > (other.major, other.minor, other.patch)
        return NotImplemented
    
    def __ge__(self, other):
        if isinstance(other, APIVersion):
            return (self.major, self.minor, self.patch) >= (other.major, other.minor, other.patch)
        return NotImplemented
    
    @classmethod
    def parse(cls, version_str: str) -> 'APIVersion':
        """
        Sürüm stringini parse eder.
        
        Args:
            version_str: Sürüm stringi (örn. "1.0.0", "2", "3.1")
            
        Returns:
            APIVersion: Sürüm nesnesi
        """
        pattern = r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?$'
        match = re.match(pattern, version_str)
        
        if not match:
            raise ValueError(f"Geçersiz sürüm formatı: {version_str}")
        
        major = int(match.group(1))
        minor = int(match.group(2) or 0)
        patch = int(match.group(3) or 0)
        
        return cls(major, minor, patch)

class VersionManager:
    """
    API sürüm yönetimi için merkezi sınıf.
    Sürüm bilgilerini ve uyumluluk kurallarını tutar.
    """
    
    def __init__(self, mode: VersioningMode = VersioningMode.PATH, 
                 default_version: Union[str, APIVersion] = "1.0.0",
                 header_name: str = "X-API-Version",
                 param_name: str = "version"):
        """
        Args:
            mode: Sürüm belirleme modu
            default_version: Hiçbir sürüm belirtilmezse kullanılacak varsayılan sürüm
            header_name: Header modu için başlık adı
            param_name: Param modu için sorgu parametresi adı
        """
        self.mode = mode
        self.header_name = header_name
        self.param_name = param_name
        
        # Varsayılan sürümü ayarla
        if isinstance(default_version, str):
            self.default_version = APIVersion.parse(default_version)
        else:
            self.default_version = default_version
        
        # Kayıtlı tüm sürümler
        self.versions: Dict[str, APIVersion] = {
            self.default_version.full_version: self.default_version
        }
        
        # Endpoint için sürüm haritaları
        self.endpoint_versions: Dict[str, Dict[str, Callable]] = {}
        
        # Şema dönüşümleri
        self.schema_transforms: Dict[str, Dict[Type, Dict[str, Type]]] = {}
    
    def register_version(self, version: Union[str, APIVersion], 
                         sunset_date: Optional[date] = None,
                         deprecated: bool = False) -> APIVersion:
        """
        Yeni bir API sürümü kaydeder.
        
        Args:
            version: Sürüm stringi veya APIVersion nesnesi
            sunset_date: Bu sürümün kullanımdan kaldırılacağı tarih
            deprecated: Bu sürüm kullanımdan kaldırıldı mı
            
        Returns:
            APIVersion: Kaydedilen sürüm nesnesi
        """
        if isinstance(version, str):
            version_obj = APIVersion.parse(version)
            version_obj.sunset_date = sunset_date
            version_obj.deprecated = deprecated
        else:
            version_obj = version
        
        self.versions[version_obj.full_version] = version_obj
        return version_obj
    
    def extract_version(self, request: Request) -> APIVersion:
        """
        İstekten API sürümünü çıkarır.
        
        Args:
            request: FastAPI istek nesnesi
            
        Returns:
            APIVersion: İstenen API sürümü
        """
        version_str = None
        
        # Sürüm belirleme moduna göre sürümü çıkar
        if self.mode in (VersioningMode.PATH, VersioningMode.MIXED):
            # Path'den sürümü çıkar (/v1/users, /v2/users)
            path = request.url.path
            match = re.match(r'^/v(\d+)(?:\.(\d+))?(?:\.(\d+))?/?', path)
            if match:
                major = match.group(1)
                minor = match.group(2) or "0"
                patch = match.group(3) or "0"
                version_str = f"{major}.{minor}.{patch}"
        
        if not version_str and self.mode in (VersioningMode.HEADER, VersioningMode.MIXED):
            # Header'dan sürümü çıkar
            version_str = request.headers.get(self.header_name)
        
        if not version_str and self.mode in (VersioningMode.PARAM, VersioningMode.MIXED):
            # Sorgu parametresinden sürümü çıkar
            version_str = request.query_params.get(self.param_name)
        
        # Sürüm bulunamadıysa varsayılanı kullan
        if not version_str:
            return self.default_version
        
        # Sürüm stringini parse et
        try:
            version = APIVersion.parse(version_str)
            
            # Kayıtlı sürüm değilse, en yakın olanı bul
            if version.full_version not in self.versions:
                # Aynı major sürüm içinde en yüksek minor sürümü bul
                candidates = [v for v in self.versions.values() if v.major == version.major]
                if candidates:
                    closest = max(candidates)
                    return closest
                    
            # Kayıtlı sürümlerden tam eşleşme varsa onu kullan
            if version.full_version in self.versions:
                return self.versions[version.full_version]
            
            # Hiçbir uygun sürüm bulunamazsa varsayılanı kullan
            return self.default_version
            
        except ValueError:
            # Geçersiz sürüm formatı, varsayılanı kullan
            return self.default_version
    
    def version_dependency(self) -> Callable:
        """
        İstekten sürümü çıkaran ve dependency olarak sunan fonksiyon.
        
        Returns:
            Callable: FastAPI dependency fonksiyonu
        """
        def get_api_version(request: Request) -> APIVersion:
            version = self.extract_version(request)
            
            # Sürüm kullanımdan kaldırıldıysa uyarı header'ı ekle
            if version.deprecated:
                headers = getattr(request.state, "headers", {})
                headers["X-API-Deprecated"] = "true"
                request.state.headers = headers
                
                # Kullanım süresi dolduysa hata fırlat
                if version.is_sunset:
                    raise HTTPException(
                        status_code=status.HTTP_410_GONE,
                        detail=f"API v{version} kullanımdan kaldırılmıştır. Lütfen daha yeni bir sürüm kullanın."
                    )
            
            return version
        
        return get_api_version
    
    def version_response_middleware(self) -> Callable:
        """
        Yanıta sürüm bilgilerini ekleyen middleware.
        
        Returns:
            Callable: FastAPI middleware fonksiyonu
        """
        async def api_version_middleware(request: Request, call_next):
            # İsteği işle
            response = await call_next(request)
            
            # Yanıta sürüm header'ı ekle
            version = self.extract_version(request)
            response.headers["X-API-Version"] = version.full_version
            
            # Sürüm kullanımdan kaldırıldıysa sunset header'ı ekle
            if version.deprecated:
                response.headers["X-API-Deprecated"] = "true"
                if version.sunset_date:
                    response.headers["X-API-Sunset-Date"] = version.sunset_date.isoformat()
            
            # İstek state'inden gelen header'ları ekle
            if hasattr(request.state, "headers"):
                for key, value in request.state.headers.items():
                    response.headers[key] = value
            
            return response
        
        return api_version_middleware
    
    def register_endpoint_version(self, endpoint_name: str, version: Union[str, APIVersion], 
                                   handler: Callable) -> None:
        """
        Belirli bir endpoint için sürüm işleyicisini kaydeder.
        
        Args:
            endpoint_name: Endpoint benzersiz adı
            version: Sürüm
            handler: İşleyici fonksiyon
        """
        if isinstance(version, str):
            version = APIVersion.parse(version)
        
        if endpoint_name not in self.endpoint_versions:
            self.endpoint_versions[endpoint_name] = {}
        
        self.endpoint_versions[endpoint_name][version.full_version] = handler
    
    def get_endpoint_handler(self, endpoint_name: str, version: APIVersion) -> Optional[Callable]:
        """
        Belirli bir endpoint için uygun sürüm işleyicisini bulur.
        
        Args:
            endpoint_name: Endpoint benzersiz adı
            version: İstenen sürüm
            
        Returns:
            Optional[Callable]: İşleyici fonksiyon veya None
        """
        if endpoint_name not in self.endpoint_versions:
            return None
        
        handlers = self.endpoint_versions[endpoint_name]
        
        # Tam sürüm eşleşmesi
        if version.full_version in handlers:
            return handlers[version.full_version]
        
        # Ana sürüm eşleşmesi için elverişli sürümleri bul
        compatible_versions = [
            v for v in handlers.keys() 
            if APIVersion.parse(v).major == version.major and APIVersion.parse(v) <= version
        ]
        
        if compatible_versions:
            # En yüksek uyumlu sürümü kullan
            best_match = max(compatible_versions, key=lambda v: APIVersion.parse(v))
            return handlers[best_match]
        
        return None

    def register_schema_transform(self, model_type: Type[BaseModel], 
                                  from_version: Union[str, APIVersion],
                                  to_version: Union[str, APIVersion],
                                  field_transforms: Dict[str, Any]) -> None:
        """
        Sürümler arası şema dönüşümü kaydeder.
        
        Args:
            model_type: Dönüştürülecek model tipi
            from_version: Kaynak sürüm
            to_version: Hedef sürüm
            field_transforms: Alan dönüşüm kuralları
        """
        if isinstance(from_version, str):
            from_version = APIVersion.parse(from_version)
        
        if isinstance(to_version, str):
            to_version = APIVersion.parse(to_version)
        
        # Dönüşüm mapini oluştur
        transform_key = f"{from_version.full_version}->{to_version.full_version}"
        
        if transform_key not in self.schema_transforms:
            self.schema_transforms[transform_key] = {}
        
        self.schema_transforms[transform_key][model_type] = field_transforms
    
    def transform_model(self, data: Dict[str, Any], model_type: Type[BaseModel],
                       from_version: APIVersion, to_version: APIVersion) -> Dict[str, Any]:
        """
        Model verilerini sürümler arası dönüştürür.
        
        Args:
            data: Dönüştürülecek model verileri
            model_type: Model tipi
            from_version: Kaynak sürüm
            to_version: Hedef sürüm
            
        Returns:
            Dict[str, Any]: Dönüştürülmüş veriler
        """
        transform_key = f"{from_version.full_version}->{to_version.full_version}"
        reverse_key = f"{to_version.full_version}->{from_version.full_version}"
        
        # İleri dönüşüm kuralları
        if transform_key in self.schema_transforms and model_type in self.schema_transforms[transform_key]:
            transforms = self.schema_transforms[transform_key][model_type]
            result = self._apply_transforms(data, transforms)
            return result
            
        # Geri dönüşüm kuralları (ters çevrilmiş)
        elif reverse_key in self.schema_transforms and model_type in self.schema_transforms[reverse_key]:
            # TODO: Otomatik ters dönüşüm mantığı eklenebilir
            # Şimdilik doğrudan veriyi döndür
            return data
            
        # Dönüşüm kuralı yoksa, veriyi olduğu gibi döndür
        return data
    
    def _apply_transforms(self, data: Dict[str, Any], transforms: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dönüşüm kurallarını uygular.
        
        Args:
            data: Dönüştürülecek veriler
            transforms: Dönüşüm kuralları
            
        Returns:
            Dict[str, Any]: Dönüştürülmüş veriler
        """
        result = dict(data)
        
        for field, transform in transforms.items():
            if callable(transform):
                # Fonksiyon dönüşümü
                if field in result:
                    result[field] = transform(result[field])
            elif isinstance(transform, dict) and "rename" in transform:
                # Alan yeniden adlandırma
                if field in result:
                    result[transform["rename"]] = result.pop(field)
            elif isinstance(transform, dict) and "default" in transform:
                # Eksik alan için varsayılan değer
                if field not in result:
                    result[field] = transform["default"]
        
        return result

# API sürüm dekoratörü
def versioned_api_route(endpoint_name: str, versions: Dict[Union[str, APIVersion], Callable],
                        version_manager: VersionManager):
    """
    Sürümlü API endpoint'i oluşturan dekoratör.
    
    Args:
        endpoint_name: Endpoint benzersiz adı
        versions: Sürüm -> işleyici fonksiyonu haritası
        version_manager: VersionManager örneği
        
    Returns:
        Callable: Endpoint işleyici fonksiyonu
    """
    def decorator(func):
        # Her sürümü kaydet
        for version, handler in versions.items():
            version_manager.register_endpoint_version(endpoint_name, version, handler)
        
        # Ana işleyici fonksiyonu
        async def endpoint_handler(
            api_version: APIVersion = Depends(version_manager.version_dependency()),
            *args, **kwargs
        ):
            # Endpoint'in bu sürüm için uygun işleyicisini bul
            handler = version_manager.get_endpoint_handler(endpoint_name, api_version)
            
            if handler:
                # Uygun işleyici bulunduysa çağır
                return await handler(*args, **kwargs)
            else:
                # İşleyici bulunamazsa orijinal fonksiyonu kullan
                return await func(*args, **kwargs)
        
        # Dekoratörü tanıtıcı bilgileri kopyala
        from functools import wraps
        return wraps(func)(endpoint_handler)
    
    return decorator