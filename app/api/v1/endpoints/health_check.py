from fastapi import APIRouter, Depends, Response, status
from typing import Dict, List, Any, Optional
import logging
import time
import os
import psutil
from datetime import datetime

from app.core.config import settings
from app.models.model_manager import get_model_manager
from app.db.mongodb import check_db_connection
from app.services.llm_service import get_llm_service
from app.services.retrievers.base import check_vector_store

router = APIRouter()

logger = logging.getLogger(__name__)

class SystemHealth:
    """System health checker."""
    
    @staticmethod
    async def check_db_health() -> Dict[str, Any]:
        """Check database health."""
        start_time = time.time()
        try:
            is_connected = await check_db_connection()
            return {
                "status": "healthy" if is_connected else "unhealthy",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"DB health check error: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    @staticmethod
    async def check_vector_store_health() -> Dict[str, Any]:
        """Check vector store health."""
        start_time = time.time()
        try:
            is_healthy = await check_vector_store()
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Vector store health check error: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    @staticmethod
    async def check_models_health() -> Dict[str, Any]:
        """Check model health."""
        start_time = time.time()
        model_manager = get_model_manager()
        try:
            # Get loaded models info
            loaded_models = model_manager.get_loaded_models()
            
            # Try to get a simple embedding as a test
            test_passed = False
            test_model = None
            
            if loaded_models:
                test_model = loaded_models[0]
                embedding = await model_manager.get_embeddings(
                    texts=["test"],
                    model_name=test_model
                )
                test_passed = embedding is not None and len(embedding) > 0
            
            return {
                "status": "healthy" if test_passed else "degraded",
                "loaded_models": loaded_models,
                "total_models": len(loaded_models),
                "test_model": test_model,
                "test_passed": test_passed,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"Models health check error: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "loaded_models": model_manager.get_loaded_models(),
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    @staticmethod
    async def check_llm_health() -> Dict[str, Any]:
        """Check LLM service health."""
        start_time = time.time()
        try:
            llm_service = get_llm_service()
            # Do a simple test generation
            test_result = await llm_service.generate(
                prompt="Say 'healthy' if you're working.",
                max_tokens=5,
                temperature=0.0
            )
            
            is_healthy = "healthy" in test_result.lower()
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "model": llm_service.model_name,
                "test_result": test_result,
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
        except Exception as e:
            logger.error(f"LLM health check error: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "latency_ms": round((time.time() - start_time) * 1000, 2)
            }
    
    @staticmethod
    def check_system_health() -> Dict[str, Any]:
        """Check system health metrics."""
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        
        # Get process info
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        # Calculate status based on thresholds
        status = "healthy"
        if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
            status = "warning"
        
        return {
            "status": status,
            "cpu": {
                "percent": cpu_percent
            },
            "memory": {
                "total_mb": round(memory.total / (1024 * 1024), 2),
                "available_mb": round(memory.available / (1024 * 1024), 2),
                "percent": memory_percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
                "free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "percent": disk_percent
            },
            "process": {
                "memory_mb": round(process_memory, 2),
                "threads": process.num_threads()
            }
        }


@router.get("/", tags=["Health"], summary="Simple health check")
async def health_check():
    """
    Simple health check endpoint.
    
    Returns:
        A simple status indicating the service is running.
    """
    return {"status": "healthy", "version": settings.version, "timestamp": datetime.utcnow().isoformat()}


@router.get("/readiness", tags=["Health"], summary="Readiness probe")
async def readiness_probe(response: Response):
    """
    Readiness check endpoint.
    
    This checks if the service is ready to receive traffic.
    
    Returns:
        A detailed status of various system components.
    """
    # Check database connection
    db_health = await SystemHealth.check_db_health()
    
    # Build health status
    health_status = {
        "status": "ready" if db_health["status"] == "healthy" else "not_ready",
        "database": db_health,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Set response status code
    if health_status["status"] != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status


@router.get("/liveness", tags=["Health"], summary="Liveness probe")
async def liveness_probe(response: Response):
    """
    Liveness check endpoint.
    
    This checks if the service is running and responsive.
    
    Returns:
        A simple status indicating if the service is alive.
    """
    # Check system health
    system_health = SystemHealth.check_system_health()
    
    # Build health status
    health_status = {
        "status": "alive" if system_health["status"] != "critical" else "not_alive",
        "system": system_health,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # Set response status code
    if health_status["status"] != "alive":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status


@router.get("/detailed", tags=["Health"], summary="Detailed health check")
async def detailed_health_check(response: Response):
    """
    Detailed health check endpoint.
    
    This provides a comprehensive view of all system components.
    
    Returns:
        A detailed health report of all system components.
    """
    # Run health checks in parallel
    db_health = await SystemHealth.check_db_health()
    vector_store_health = await SystemHealth.check_vector_store_health()
    models_health = await SystemHealth.check_models_health()
    llm_health = await SystemHealth.check_llm_health()
    system_health = SystemHealth.check_system_health()
    
    # Determine overall status
    status_values = [
        db_health["status"],
        vector_store_health["status"],
        models_health["status"],
        llm_health["status"],
        system_health["status"]
    ]
    
    if "unhealthy" in status_values:
        overall_status = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif "degraded" in status_values or "warning" in status_values:
        overall_status = "degraded"
        response.status_code = status.HTTP_200_OK
    else:
        overall_status = "healthy"
        response.status_code = status.HTTP_200_OK
    
    # Build health status
    health_status = {
        "status": overall_status,
        "database": db_health,
        "vector_store": vector_store_health,
        "models": models_health,
        "llm": llm_health,
        "system": system_health,
        "environment": settings.environment,
        "version": settings.version,
        "uptime_seconds": time.time() - psutil.boot_time(),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return health_status


@router.get("/models", tags=["Health"], summary="Models health check")
async def models_health_check():
    """
    Check the health of all models.
    
    Returns:
        A detailed report on the status of embedding and LLM models.
    """
    # Get model health
    models_health = await SystemHealth.check_models_health()
    llm_health = await SystemHealth.check_llm_health()
    
    # Get model manager for more details
    model_manager = get_model_manager()
    available_models = model_manager.list_available_models()
    
    # Build response
    return {
        "embedding_models": {
            "status": models_health["status"],
            "loaded_models": models_health["loaded_models"],
            "available_models": available_models,
            "default_model": model_manager.default_model,
        },
        "llm_models": {
            "status": llm_health["status"],
            "current_model": llm_health["model"],
        },
        "test_results": {
            "embedding_test": models_health.get("test_passed", False),
            "llm_test": "healthy" in llm_health.get("test_result", "").lower()
        },
        "latencies_ms": {
            "embedding": models_health["latency_ms"],
            "llm": llm_health["latency_ms"]
        }
    }