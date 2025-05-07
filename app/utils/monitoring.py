import time
import logging
from functools import wraps
from typing import Dict, List, Any, Optional, Callable
import contextlib

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import multiprocess, CollectorRegistry
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

# Define metrics
REQUEST_COUNT = Counter(
    "mm_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "mm_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 25.0, 50.0, 75.0, 100.0, float("inf"))
)

RETRIEVER_LATENCY = Histogram(
    "mm_retriever_latency_seconds",
    "Retriever latency in seconds",
    ["retriever_type", "operation"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, float("inf"))
)

EMBEDDING_LATENCY = Histogram(
    "mm_embedding_latency_seconds",
    "Embedding generation latency in seconds",
    ["model_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf"))
)

LLM_LATENCY = Histogram(
    "mm_llm_latency_seconds",
    "LLM processing latency in seconds",
    ["model_name", "operation"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf"))
)

ACTIVE_REQUESTS = Gauge(
    "mm_active_requests",
    "Number of active HTTP requests",
    ["method"]
)

DOCUMENT_PROCESSED = Counter(
    "mm_documents_processed_total",
    "Total number of documents processed",
    ["status", "type"]
)

FEEDBACK_COUNT = Counter(
    "mm_feedback_total",
    "Total number of feedback entries",
    ["rating", "helpful"]
)

FINE_TUNING_JOBS = Counter(
    "mm_fine_tuning_jobs_total",
    "Total number of fine-tuning jobs",
    ["status"]
)

WEBSOCKET_CONNECTIONS = Gauge(
    "mm_websocket_connections",
    "Number of active WebSocket connections"
)

MODEL_INFO = Info(
    "mm_model_info",
    "Information about loaded models"
)

CACHE_HITS = Counter(
    "mm_cache_hits_total",
    "Total number of cache hits",
    ["cache_type"]
)

CACHE_MISSES = Counter(
    "mm_cache_misses_total",
    "Total number of cache misses",
    ["cache_type"]
)

RATE_LIMIT_HITS = Counter(
    "mm_rate_limit_hits_total",
    "Total number of rate limit hits",
    ["endpoint", "user_type"]
)

LLM_TOKENS_USED = Counter(
    "mm_llm_tokens_total",
    "Total number of tokens used in LLM calls",
    ["model_name", "token_type"]  # token_type can be "prompt", "completion"
)

LLM_CONTEXT_WINDOW_SIZE = Histogram(
    "mm_llm_context_window_size",
    "Size of context window in LLM calls",
    ["model_name"],
    buckets=(100, 500, 1000, 2000, 4000, 8000, 16000, 32000, float("inf"))
)

TASK_QUEUE_SIZE = Gauge(
    "mm_task_queue_size",
    "Size of the task queue",
    ["queue_name", "priority"]
)

TASK_EXECUTION_TIME = Histogram(
    "mm_task_execution_time_seconds",
    "Execution time of background tasks",
    ["task_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, float("inf"))
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to record Prometheus metrics for each request."""
    
    def __init__(self, app: ASGIApp, exclude_paths: List[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/favicon.ico"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        method = request.method
        path = request.url.path
        
        # Increment active request gauge
        ACTIVE_REQUESTS.labels(method=method).inc()
        
        # Time the request
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status_code = response.status_code
            REQUEST_LATENCY.labels(method=method, endpoint=path).observe(time.time() - start_time)
            REQUEST_COUNT.labels(method=method, endpoint=path, status=status_code).inc()
            return response
        except Exception as e:
            # Record 500 error metrics
            REQUEST_COUNT.labels(method=method, endpoint=path, status=500).inc()
            # Re-raise the exception
            raise e
        finally:
            # Decrement active request gauge
            ACTIVE_REQUESTS.labels(method=method).dec()


def setup_monitoring(app: FastAPI):
    """Set up Prometheus monitoring for the application."""
    # Add Prometheus middleware
    app.add_middleware(PrometheusMiddleware)
    
    # Set up multiprocess mode for Prometheus
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    
    # Log that monitoring is set up
    logger.info("Prometheus monitoring set up successfully")


@contextlib.contextmanager
def track_retriever_latency(retriever_type: str, operation: str):
    """Context manager to track retriever latency."""
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        RETRIEVER_LATENCY.labels(retriever_type=retriever_type, operation=operation).observe(latency)


@contextlib.contextmanager
def track_embedding_latency(model_name: str):
    """Context manager to track embedding latency."""
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        EMBEDDING_LATENCY.labels(model_name=model_name).observe(latency)


@contextlib.contextmanager
def track_llm_latency(model_name: str, operation: str):
    """Context manager to track LLM latency."""
    start_time = time.time()
    try:
        yield
    finally:
        latency = time.time() - start_time
        LLM_LATENCY.labels(model_name=model_name, operation=operation).observe(latency)


def log_tokens_used(model_name: str, prompt_tokens: int, completion_tokens: int):
    """Log tokens used in an LLM call."""
    LLM_TOKENS_USED.labels(model_name=model_name, token_type="prompt").inc(prompt_tokens)
    LLM_TOKENS_USED.labels(model_name=model_name, token_type="completion").inc(completion_tokens)


def log_document_processed(status: str, doc_type: str):
    """Log document processing event."""
    DOCUMENT_PROCESSED.labels(status=status, type=doc_type).inc()


def log_feedback(rating: int, helpful: bool):
    """Log user feedback."""
    FEEDBACK_COUNT.labels(rating=rating, helpful=helpful).inc()


def log_fine_tuning_job(status: str):
    """Log fine-tuning job status change."""
    FINE_TUNING_JOBS.labels(status=status).inc()


def update_model_info(models_info: Dict[str, Any]):
    """Update information about loaded models."""
    MODEL_INFO.info(models_info)


def track_websocket_connection(connected: bool = True):
    """Track WebSocket connection events."""
    if connected:
        WEBSOCKET_CONNECTIONS.inc()
    else:
        WEBSOCKET_CONNECTIONS.dec()


def track_cache(hit: bool, cache_type: str):
    """Track cache hit or miss."""
    if hit:
        CACHE_HITS.labels(cache_type=cache_type).inc()
    else:
        CACHE_MISSES.labels(cache_type=cache_type).inc()


def log_rate_limit_hit(endpoint: str, user_type: str):
    """Log rate limit hit event."""
    RATE_LIMIT_HITS.labels(endpoint=endpoint, user_type=user_type).inc()


def update_task_queue_size(queue_name: str, priority: str, size: int):
    """Update the size of a task queue."""
    TASK_QUEUE_SIZE.labels(queue_name=queue_name, priority=priority).set(size)


@contextlib.contextmanager
def track_task_execution(task_type: str):
    """Context manager to track task execution time."""
    start_time = time.time()
    try:
        yield
    finally:
        execution_time = time.time() - start_time
        TASK_EXECUTION_TIME.labels(task_type=task_type).observe(execution_time)


def monitor_embedding(func):
    """Decorator to monitor embedding function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        model_name = kwargs.get("model_name", "default")
        with track_embedding_latency(model_name):
            return await func(*args, **kwargs)
    return wrapper


def monitor_retriever(func):
    """Decorator to monitor retriever function performance."""
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        retriever_type = self.__class__.__name__
        operation = func.__name__
        with track_retriever_latency(retriever_type, operation):
            return await func(self, *args, **kwargs)
    return wrapper


def monitor_llm(func):
    """Decorator to monitor LLM function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        model_name = kwargs.get("model_name", args[0].model_name if args else "default")
        operation = func.__name__
        with track_llm_latency(model_name, operation):
            result = await func(*args, **kwargs)
            
            # Log token usage if available
            if hasattr(result, "usage") and hasattr(result.usage, "prompt_tokens"):
                log_tokens_used(
                    model_name,
                    result.usage.prompt_tokens,
                    result.usage.completion_tokens
                )
            
            return result
    return wrapper