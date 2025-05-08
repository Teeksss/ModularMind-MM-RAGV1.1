"""
API middleware definitions
"""
from typing import Callable, List
import time
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request, log details, and pass to the next middleware"""
        request_id = request.headers.get("X-Request-ID", "-")
        path = request.url.path
        method = request.method
        
        # Skip logging for health check and metrics endpoints
        if path in ["/health", "/metrics"]:
            return await call_next(request)
        
        # Log request
        logger.info(f"Request {request_id}: {method} {path}")
        
        # Record request processing time
        start_time = time.time()
        
        # Process the request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response {request_id}: {method} {path} - Status: {response.status_code} - "
                f"Completed in {process_time:.4f}s"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = f"{process_time:.4f}"
            return response
            
        except Exception as e:
            # Log exception
            process_time = time.time() - start_time
            logger.error(
                f"Error {request_id}: {method} {path} - {str(e)} - "
                f"Failed after {process_time:.4f}s"
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware for adding security headers to responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to the response"""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), camera=(), geolocation=(), gyroscope=(), "
            "magnetometer=(), microphone=(), payment=(), usb=()"
        )
        
        return response


def setup_middlewares(app: FastAPI, allowed_origins: List[str] = None) -> None:
    """Setup all middleware for the FastAPI application"""
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Request logging
    app.add_middleware(RequestLoggingMiddleware)