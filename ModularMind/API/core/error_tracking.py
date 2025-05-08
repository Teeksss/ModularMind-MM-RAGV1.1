"""
Hata izleme için Sentry entegrasyonu ve diğer araçlar.
"""

import os
import logging
import sys
import traceback
from typing import Dict, Any, Optional, Callable

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration
from sentry_sdk.integrations.excepthook import ExcepthookIntegration
from sentry_sdk.integrations.dedupe import DedupeIntegration
from sentry_sdk.integrations.stdlib import StdlibIntegration
from sentry_sdk.integrations.modules import ModulesIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

def setup_error_tracking(app: Optional[FastAPI] = None):
    """
    Sentry ve diğer hata izleme araçlarını yapılandırır.
    
    Args:
        app: FastAPI uygulaması (isteğe bağlı)
    """
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    
    if not sentry_dsn:
        logger.info("Sentry DSN bulunamadı. Hata izleme devre dışı.")
        return
    
    # Logging entegrasyonunu yapılandır
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Sentry'ye gönderilecek minimum seviye
        event_level=logging.ERROR  # Sentry'de olay olarak işaretlenecek minimum seviye
    )
    
    # Sentry'yi yapılandır
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=os.getenv("APP_VERSION", "1.0.0"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        integrations=[
            logging_integration,
            ThreadingIntegration(propagate_hub=True),
            ExcepthookIntegration(),
            DedupeIntegration(),
            StdlibIntegration(),
            ModulesIntegration(),
            FastApiIntegration(),
        ],
        # Hassas verileri reddet
        default_integrations=False,
        send_default_pii=False,
        # Sentry özelleştirmeleri
        before_send=before_send_event,
    )
    
    logger.info(f"Sentry hata izleme yapılandırıldı: env={environment}")
    
    # Uygulama varsa Sentry middleware'ini ekle
    if app is not None:
        app.add_middleware(SentryMiddleware)

def before_send_event(event: Dict[str, Any], hint: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sentry'ye gönderilmeden önce olayı işle.
    Hassas verileri temizler ve belirli hataları filtreler.
    
    Args:
        event: Sentry olayı
        hint: Orijinal istisna ve diğer ipuçları
        
    Returns:
        Dict[str, Any]: İşlenmiş olay veya None (göndermemek için)
    """
    # Hassas verileri temizle
    if 'request' in event and 'headers' in event['request']:
        # Kimlik doğrulama başlıklarını kaldır
        headers = event['request']['headers']
        if 'Authorization' in headers:
            headers['Authorization'] = '[REDACTED]'
        if 'Cookie' in headers:
            headers['Cookie'] = '[REDACTED]'
    
    # Hassas alanları filtrele
    if 'extra' in event:
        sensitive_fields = ['password', 'token', 'secret', 'key', 'auth', 'credentials']
        for field in sensitive_fields:
            if field in event['extra']:
                event['extra'][field] = '[REDACTED]'
    
    # 404 hatalarını izleme
    if 'exception' in event and 'values' in event['exception']:
        for exc in event['exception']['values']:
            # 404 hatalarını filtrele
            if exc.get('type') == 'HTTPException' and exc.get('value', '').startswith('404'):
                return None
    
    return event

class SentryMiddleware(BaseHTTPMiddleware):
    """
    Sentry için ek bilgiler toplar ve oturum başlatır.
    """
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Her istek için Sentry oturumunu yapılandırır.
        
        Args:
            request: FastAPI istek nesnesi
            call_next: Sonraki middleware
            
        Returns:
            Response: FastAPI yanıt nesnesi
        """
        with sentry_sdk.configure_scope() as scope:
            # İstek bilgilerini ekle
            scope.set_tag("http_method", request.method)
            scope.set_tag("http_route", request.url.path)
            
            # Kullanıcı bilgilerini ekle (varsa)
            if hasattr(request.state, "user"):
                user = request.state.user
                scope.set_user({
                    "id": getattr(user, "id", None),
                    "username": getattr(user, "username", None),
                    "ip_address": request.client.host if request.client else None
                })
            else:
                scope.set_user({
                    "ip_address": request.client.host if request.client else None
                })
            
            # İsteği işle
            try:
                response = await call_next(request)
                return response
            except Exception as e:
                # İstisnaları elle yakala (FastAPI zaten kendi hata işleyicileriyle ele alır)
                # Burada sadece ekstra bilgileri ekleriz
                with sentry_sdk.push_scope() as scope:
                    scope.set_extra("url", str(request.url))
                    scope.set_extra("method", request.method)
                    scope.set_extra("headers", dict(request.headers))
                    scope.set_extra("path_params", request.path_params)
                    scope.set_extra("query_params", dict(request.query_params))
                
                # İstisnayı tekrar fırlat (FastAPI ele alacak)
                raise