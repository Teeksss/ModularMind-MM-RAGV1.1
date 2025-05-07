import logging
import time
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import prometheus_client
from prometheus_client import Counter, Histogram, Gauge, multiprocess, CollectorRegistry
import os

from app.core.settings import get_settings
from app.api.v1.api import api_router
from app.db.init_db import init_db
from app.services.vector_store import init_vector_store
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"/var/log/modularmind/app.log")
    ]
)

logger = logging.getLogger(__name__)

# Set up Prometheus metrics
request_counter = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP Request Duration', ['method', 'endpoint'])
active_requests = Gauge('http_active_requests', 'Number of active HTTP requests')

# Start-up and shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up ModularMind MM-RAG v1.1 API...")
    
    # Initialize multiprocess prometheus metrics if enabled
    if settings.metrics.metrics_enabled:
        logger.info("Initializing Prometheus metrics...")
        if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
            registry = CollectorRegistry()
            multiprocess.MultiProcessCollector(registry)
        else:
            logger.warning("PROMETHEUS_MULTIPROC_DIR not set - metrics may not work correctly in multiprocess environment")
    
    # Initialize database
    logger.info("Initializing database connection...")
    await init_db()
    
    # Initialize vector store
    logger.info("Initializing vector store...")
    init_vector_store()
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ModularMind MM-RAG v1.1 API...")


# Create FastAPI application
app = FastAPI(
    title="ModularMind MM-RAG API",
    description="Modular Retrieval-Augmented Generation API",
    version="1.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.security.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware if enabled
if settings.metrics.metrics_enabled:
    app.add_middleware(
        MetricsMiddleware,
        request_counter=request_counter,
        request_duration=request_duration,
        active_requests=active_requests
    )

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {
        "name": "ModularMind MM-RAG API",
        "version": "1.1.0",
        "status": "active"
    }

# Health check endpoint
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "timestamp": time.time(),
        "version": "1.1.0"
    }

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    if not settings.metrics.metrics_enabled:
        return JSONResponse(
            status_code=404,
            content={"detail": "Metrics not enabled"}
        )
    
    registry = prometheus_client.REGISTRY
    if 'PROMETHEUS_MULTIPROC_DIR' in os.environ:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    
    return Response(
        content=prometheus_client.generate_latest(registry),
        media_type="text/plain"
    )

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.environment == "development"
    )