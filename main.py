"""
ModularMind API ana uygulama modülü.
FastAPI uygulamasını başlatır ve tüm bileşenleri yapılandırır.
"""

import os
import time
import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

# Core modülleri
from ModularMind.API.core.logging import setup_logging
from ModularMind.API.core.docs import setup_docs
from ModularMind.API.core.security import setup_security
from ModularMind.API.core.rate_limiter import AdvancedRateLimiter
from ModularMind.API.core.error_tracking import setup_error_tracking
from ModularMind.API.core.metrics import setup_metrics
from ModularMind.API.core.advanced_cache import AdvancedCacheManager, CacheMiddleware, CacheStrategy
from ModularMind.API.core.resource_manager import ResourceManager
from ModularMind.API.core.versioning import VersionManager, VersioningMode, APIVersion

# API versiyonları ve endpointler
from ModularMind.API.v1.router import api_router as api_router_v1
from ModularMind.API.v2.router import api_router as api_router_v2

# Loglama sistemini kur
setup_logging()
logger = logging.getLogger(__name__)

# Uygulama meta verileri
APP_NAME = os.getenv("APP_NAME", "ModularMind API")
APP_VERSION = os.getenv("APP_VERSION", "1.2.0")
APP_DESCRIPTION = os.getenv("APP_DESCRIPTION", "Retrieval-Augmented Generation Platform")
APP_ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Uygulama oluştur
app = FastAPI(
    title=APP_NAME,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    docs_url=None,  # Özel dokümantasyon için
    redoc_url=None  # Özel dokümantasyon için
)

# API başlangıç zamanı
START_TIME = time.time()

# Statik dosyalar
app.mount("/static", StaticFiles(directory="static"), name="static")

# API sürüm yönetimini yapılandır
version_manager = VersionManager(
    mode=VersioningMode.PATH,
    default_version="1.0.0",
    header_name="X-API-Version",
    param_name="version"
)

# API sürümlerini kaydet
v1 = version_manager.register_version("1.0.0")
v2 = version_manager.register_version("2.0.0")

# Middleware ve güvenlik yapılandırması
@app.on_event("startup")
async def startup_event():
    """Uygulama başlangıcında çalışacak işlemler."""
    logger.info(f"ModularMind API başlatılıyor: versiyon={APP_VERSION}, ortam={APP_ENVIRONMENT}")

    # Hata izleme
    setup_error_tracking(app)
    
    # Güvenlik yapılandırması
    setup_security(app)
    
    # API dokümantasyonu
    setup_docs(app)
    
    # Metrics
    setup_metrics(app)
    
    # Önbellek yöneticisi
    cache_strategy = CacheStrategy.TIERED if APP_ENVIRONMENT == "production" else CacheStrategy.SIMPLE
    cache_manager = AdvancedCacheManager(strategy=cache_strategy)
    
    # Kaynak yöneticisi
    resource_manager = ResourceManager()
    
    # Önbellek middleware
    app.add_middleware(
        CacheMiddleware,
        ttl=60,  # 1 dakika
        exclude_paths=["/api/v1/auth", "/api/v2/auth", "/metrics", "/health"],
        manager=cache_manager
    )
    
    # Rate limiter middleware
    redis_url = os.getenv("REDIS_URL")
    app.add_middleware(
        AdvancedRateLimiter,
        redis_url=redis_url,
        enabled=APP_ENVIRONMENT == "production"
    )
    
    # Sürüm middleware
    app.add_middleware(
        version_manager.version_response_middleware()
    )
    
    logger.info("Tüm servisler başarıyla başlatıldı")

# Sağlık kontrolü endpoint'i
@app.get("/health", include_in_schema=False)
async def health_check():
    """
    API sağlık kontrolü için endpoint.
    """
    uptime = int(time.time() - START_TIME)
    
    # Kaynak kullanım bilgilerini al
    resource_manager = ResourceManager()
    resources = resource_manager.get_system_resources()
    
    # Önbellek istatistiklerini al
    cache_manager = AdvancedCacheManager()
    cache_stats = cache_manager.stats()
    
    return {
        "status": "ok",
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT,
        "uptime_seconds": uptime,
        "resources": resources,
        "cache": cache_stats
    }

# API rotalarını kaydet (v1)
app.include_router(
    api_router_v1,
    prefix="/api/v1"
)

# API rotalarını kaydet (v2)
app.include_router(
    api_router_v2,
    prefix="/api/v2"
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Tüm API için genel hata işleyici."""
    logger.error(f"Global hata: {str(exc)}", exc_info=True)
    
    status_code = getattr(exc, "status_code", 500)
    
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": str(exc),
            "type": exc.__class__.__name__
        }
    )

# Uygulama çalıştığında bilgi logu
logger.info(f"ModularMind API uygulaması hazır: {APP_NAME} v{APP_VERSION}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)