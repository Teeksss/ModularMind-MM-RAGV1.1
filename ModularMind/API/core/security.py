"""
API güvenlik yapılandırması.
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import os
from pydantic import BaseModel
from typing import List, Optional, Dict

class SecuritySettings(BaseModel):
    """API güvenlik ayarları."""
    allowed_origins: List[str] = []
    allow_credentials: bool = True
    allow_methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    allow_headers: List[str] = ["Authorization", "Content-Type"]
    trusted_hosts: List[str] = ["localhost", "127.0.0.1"]
    
    @classmethod
    def from_env(cls):
        """Ortam değişkenlerinden güvenlik ayarlarını yapılandırır."""
        environment = os.getenv("ENVIRONMENT", "development")
        
        # İzin verilen originler
        origins_env = os.getenv("ALLOWED_ORIGINS", "")
        origins = origins_env.split(",") if origins_env else []
        
        # Geliştirme ortamında localhost'a izin ver
        if environment == "development" and not origins:
            origins = [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
            ]
        
        # Güvenilen hostlar
        trusted_hosts_env = os.getenv("TRUSTED_HOSTS", "")
        trusted_hosts = trusted_hosts_env.split(",") if trusted_hosts_env else ["localhost", "127.0.0.1"]
        
        return cls(
            allowed_origins=origins,
            trusted_hosts=trusted_hosts
        )

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Güvenlik başlıkları ekleyen middleware."""
    
    def __init__(
        self,
        app,
        csp_directives: Optional[Dict[str, str]] = None,
    ):
        super().__init__(app)
        
        # Content Security Policy direktifleri
        self.csp_directives = csp_directives or {
            "default-src": "'self'",
            "img-src": "'self' data: https:",
            "script-src": "'self' 'unsafe-inline'",
            "style-src": "'self' 'unsafe-inline'",
            "connect-src": "'self' https:",
            "font-src": "'self'",
            "object-src": "'none'",
            "frame-ancestors": "'self'",
            "form-action": "'self'",
            "base-uri": "'self'",
            "frame-src": "'self'"
        }
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # CSP başlığını oluştur
        csp_header = "; ".join([f"{key} {value}" for key, value in self.csp_directives.items()])
        
        # Güvenlik başlıklarını ekle
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = csp_header
        
        # HSTS (sadece HTTPS üzerinde çalışıyorsa)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response

def setup_security(app: FastAPI) -> None:
    """
    API için güvenlik yapılandırmasını ayarlar.
    
    Args:
        app: FastAPI uygulaması
    """
    settings = SecuritySettings.from_env()
    
    # CORS middleware'ini ekle
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=settings.allow_methods,
        allow_headers=settings.allow_headers,
    )
    
    # Trusted Host middleware'ini ekle
    if os.getenv("ENVIRONMENT", "development") == "production":
        app.add_middleware(
            TrustedHostMiddleware, 
            allowed_hosts=settings.trusted_hosts
        )
    
    # Güvenlik başlıkları middleware'ini ekle
    app.add_middleware(SecurityHeadersMiddleware)
    
    print(f"Güvenlik yapılandırması tamamlandı: CORS, güvenlik başlıkları ve trusted hosts.")