"""
ModularMind performans metrikleri için Prometheus izleme
"""

import time
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Request, Response
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Prometheus metriklerini toplamak için FastAPI middleware
    """
    
    def __init__(self, app: FastAPI, metrics):
        super().__init__(app)
        self.metrics = metrics
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        response = await call_next(request)
        
        # Süreyi hesapla
        process_time = time.time() - start_time
        
        # Metrikleri kaydet
        status_code = response.status_code
        endpoint = request.url.path
        method = request.method
        
        # HTTP istekleri sayacı
        self.metrics.request_count.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        
        # İstek süresi
        self.metrics.request_duration.labels(
            method=method, endpoint=endpoint
        ).observe(process_time)
        
        # Hata sayacı
        if 400 <= status_code < 600:
            self.metrics.error_count.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
        
        return response

class Metrics:
    """
    ModularMind için Prometheus metrikleri
    """
    
    def __init__(self):
        # Prometheus kayıt defteri
        self.registry = CollectorRegistry()
        
        # HTTP istek sayacı
        self.request_count = Counter(
            "modularmind_request_count_total",
            "Total count of HTTP requests",
            ["method", "endpoint", "status_code"],
            registry=self.registry
        )
        
        # İstek süresi histogramı
        self.request_duration = Histogram(
            "modularmind_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 25.0, 50.0, 75.0, 100.0, float("inf")),
            registry=self.registry
        )
        
        # Hata sayacı
        self.error_count = Counter(
            "modularmind_error_count_total",
            "Total count of HTTP errors",
            ["method", "endpoint", "status_code"],
            registry=self.registry
        )
        
        # Embedding metrikleri
        self.embedding_count = Counter(
            "modularmind_embedding_count_total",
            "Total count of embeddings generated",
            ["model_id"],
            registry=self.registry
        )
        
        self.embedding_duration = Histogram(
            "modularmind_embedding_generation_duration_milliseconds",
            "Embedding generation duration in milliseconds",
            ["model_id"],
            buckets=(1, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000, float("inf")),
            registry=self.registry
        )
        
        # Arama metrikleri
        self.search_count = Counter(
            "modularmind_search_count_total",
            "Total count of search operations",
            ["search_type"],
            registry=self.registry
        )
        
        self.search_duration = Histogram(
            "modularmind_search_duration_milliseconds",
            "Search operation duration in milliseconds",
            ["search_type"],
            buckets=(1, 5, 10, 25, 50, 75, 100, 250, 500, 750, 1000, 2500, 5000, 7500, 10000, float("inf")),
            registry=self.registry
        )
        
        # Cache metrikleri
        self.cache_hit_ratio = Gauge(
            "modularmind_cache_hit_ratio",
            "Cache hit ratio (0-1)",
            ["cache_type"],
            registry=self.registry
        )
        
        # Vektör depo metrikleri
        self.document_count = Gauge(
            "modularmind_vector_store_document_count",
            "Number of documents in vector store",
            registry=self.registry
        )
        
        self.chunk_count = Gauge(
            "modularmind_vector_store_chunk_count",
            "Number of chunks in vector store",
            registry=self.registry
        )
        
        self.embedding_store_count = Gauge(
            "modularmind_vector_store_embedding_count",
            "Number of embeddings in vector store",
            registry=self.registry
        )
        
        self.vector_store_size = Gauge(
            "modularmind_vector_store_size_bytes",
            "Size of vector store in bytes",
            registry=self.registry
        )
        
        self.vector_store_load = Gauge(
            "modularmind_vector_store_load",
            "Vector store load (0-1)",
            registry=self.registry
        )
        
        # Model metrikleri
        self.model_count = Gauge(
            "modularmind_embedding_count_by_model",
            "Number of embeddings by model",
            ["model"],
            registry=self.registry
        )
        
        self.embedding_coverage = Gauge(
            "modularmind_document_embedding_coverage_percent",
            "Percentage of documents with embeddings by model",
            ["model"],
            registry=self.registry
        )
        
        # Arama skorları
        self.avg_search_score = Gauge(
            "modularmind_avg_search_result_score",
            "Average search result score",
            ["model_id"],
            registry=self.registry
        )
        
        self.avg_results = Gauge(
            "modularmind_avg_search_results",
            "Average number of search results returned",
            registry=self.registry
        )
        
        self.avg_relevance = Gauge(
            "modularmind_query_relevance_score",
            "Average relevance score of search results",
            registry=self.registry
        )
    
    def generate(self):
        """Prometheus metrik çıktısı oluşturur"""
        return Response(
            content=generate_latest(self.registry),
            media_type=CONTENT_TYPE_LATEST
        )

def setup_metrics(app: FastAPI) -> Metrics:
    """
    FastAPI uygulaması için metrikleri yapılandırır
    
    Args:
        app: FastAPI uygulaması
        
    Returns:
        Metrics: Metrik nesnesi
    """
    metrics = Metrics()
    app.add_middleware(PrometheusMiddleware, metrics=metrics)
    
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint():
        return metrics.generate()
    
    return metrics