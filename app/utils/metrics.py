from prometheus_client import Counter, Histogram, Gauge, Info, multiprocess
import time
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize metrics
model_usage_counter = Counter(
    'embedding_model_usage_total', 
    'Number of times each model has been used',
    ['model_name']
)

encoding_latency = Histogram(
    'embedding_encoding_latency_seconds',
    'Time taken to encode texts',
    ['model_name'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
)

batch_size_histogram = Histogram(
    'embedding_batch_size',
    'Distribution of batch sizes',
    buckets=(1, 2, 4, 8, 16, 32, 64, 128, 256, 512)
)

model_load_time = Histogram(
    'embedding_model_load_time_seconds',
    'Time taken to load a model',
    ['model_name', 'device'],
    buckets=(0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)
)

gpu_memory_usage = Gauge(
    'embedding_gpu_memory_usage_gb',
    'GPU memory usage in gigabytes',
    ['model_name', 'device']
)

api_requests_counter = Counter(
    'embedding_api_requests_total',
    'Number of API requests',
    ['endpoint', 'method', 'status']
)

api_request_latency = Histogram(
    'embedding_api_request_latency_seconds',
    'API request latency in seconds',
    ['endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60)
)

concurrent_requests = Gauge(
    'embedding_concurrent_requests',
    'Number of concurrent API requests'
)

class MetricsMiddleware:
    """Middleware for tracking API metrics."""
    
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        
        # Record request
        path = scope["path"]
        method = scope["method"]
        
        # Increase concurrent requests count
        concurrent_requests.inc()
        
        # Track request time
        start_time = time.time()
        
        # Create a new send function to capture the status code
        original_send = send
        
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Record API request with status
                status = message["status"]
                api_requests_counter.labels(
                    endpoint=path,
                    method=method,
                    status=status
                ).inc()
                
                # Record latency
                latency = time.time() - start_time
                api_request_latency.labels(endpoint=path).observe(latency)
            
            return await original_send(message)
        
        try:
            # Process the request
            await self.app(scope, receive, send_wrapper)
        finally:
            # Decrease concurrent requests count
            concurrent_requests.dec()

def setup_metrics_endpoint(app):
    """Set up the metrics endpoint."""
    from fastapi import APIRouter
    from starlette.responses import Response
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    
    metrics_router = APIRouter()
    
    @metrics_router.get("/metrics")
    async def metrics():
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST
        )
    
    app.include_router(metrics_router)
    
    logger.info("Metrics endpoint set up at /metrics")