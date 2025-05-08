"""
Prometheus ve diğer izleme sistemleri için metrics toplama modülü.
"""

import time
import os
from typing import Callable, Dict, List, Optional
from fastapi import FastAPI, Request, Response
from fastapi.routing import APIRoute
from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

# Metrics için registry
REGISTRY = CollectorRegistry()

# HTTP istekleri için metrikler
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests count",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    registry=REGISTRY
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method"],
    registry=REGISTRY
)

# Uygulama metrikleri
app_info = Gauge(
    "app_info",
    "Application information",
    ["version", "environment"],
    registry=REGISTRY
)

# LLM istekleri için metrikler
llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests count",
    ["model", "type"],
    registry=REGISTRY
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM API request duration in seconds",
    ["model", "type"],
    registry=REGISTRY
)

# Vektör veritabanı metrikleri
vector_db_queries_total = Counter(
    "vector_db_queries_total",
    "Total vector database queries count",
    ["operation_type"],
    registry=REGISTRY
)

vector_db_query_duration_seconds = Histogram(
    "vector_db_query_duration_seconds",
    "Vector database query duration in seconds",
    ["operation_type"],
    registry=REGISTRY
)

# Bellek ve CPU kullanımı
memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "Application memory usage in bytes",
    registry=REGISTRY
)

cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "Application CPU usage in percent",
    registry=REGISTRY
)

class PrometheusMiddleware:
    """
    HTTP istekleri için Prometheus metrik toplayan middleware.
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
        
        # Uygulama bilgileri metrikleri
        app_version = os.getenv("APP_VERSION", "unknown")
        environment = os.getenv("ENVIRONMENT", "development")
        app_info.labels(
            version=app_version,
            environment=environment
        ).set(1)
    
    async def __call__(self, request: Request, call_next):
        # İsteğin başlangıç zamanı
        start_time = time.time()
        
        # İlerleme sayacını artır
        method = request.method
        http_requests_in_progress.labels(method=method).inc()
        
        # İsteği işle
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Hata durumunda 500 olarak işaretle
            status_code = 500
            raise e
        finally:
            # İstek süresini hesapla
            duration = time.time() - start_time
            
            # Endpoint yolunu al
            endpoint = request.url.path
            route = request.scope.get("route")
            if route:
                endpoint = route.path
            
            # Metrikleri güncelle
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=status_code
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
            # İlerleme sayacını azalt
            http_requests_in_progress.labels(method=method).dec()
        
        return response

def setup_metrics(app: FastAPI):
    """
    FastAPI uygulaması için metrics yapılandırması.
    
    Args:
        app: FastAPI uygulaması
    """
    # Prometheus middleware ekle
    app.add_middleware(PrometheusMiddleware)
    
    # Metrics endpoint'i
    @app.get("/metrics", include_in_schema=False)
    async def metrics():
        # Sistem metriklerini güncelle
        try:
            import psutil
            
            # Bellek kullanımını güncelle
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_usage_bytes.set(memory_info.rss)
            
            # CPU kullanımını güncelle
            cpu_percent = process.cpu_percent(interval=0.1)
            cpu_usage_percent.set(cpu_percent)
        except ImportError:
            # psutil yoksa devam et
            pass
            
        # Prometheus formatında metrik yanıtı oluştur
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )