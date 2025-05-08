from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
from typing import Optional
import jwt
from app.core.settings import get_settings

settings = get_settings()

class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: ASGIApp,
        secret_key: str = settings.SECRET_KEY,
        allowed_hosts: list = settings.ALLOWED_HOSTS
    ):
        super().__init__(app)
        self.secret_key = secret_key
        self.allowed_hosts = allowed_hosts
        
    async def dispatch(self, request: Request, call_next) -> Response:
        # Host validation
        if not self._is_valid_host(request.headers.get("host")):
            return Response(
                content="Invalid host",
                status_code=400
            )
            
        # Add security headers
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = self._get_csp_policy()
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response
        
    def _is_valid_host(self, host: Optional[str]) -> bool:
        if not host:
            return False
        
        host = host.split(":")[0]
        return host in self.allowed_hosts
        
    def _get_csp_policy(self) -> str:
        return "; ".join([
            "default-src 'self'",
            "img-src 'self' data: https:",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'"
        ])