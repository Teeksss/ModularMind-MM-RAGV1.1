from typing import Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import time
import os
import platform
import psutil
import torch

from app.models.model_manager import get_model_manager
from app.core.config import settings

router = APIRouter()


class SystemInfo(BaseModel):
    """Information about the system."""
    cpu_count: int
    memory_total: str
    memory_available: str
    python_version: str
    torch_version: str
    cuda_available: bool
    cuda_version: Optional[str] = None
    gpu_info: Optional[List[Dict[str, Any]]] = None


class ModelStatus(BaseModel):
    """Status of a model."""
    name: str
    is_loaded: bool
    device: str
    error: Optional[str] = None
    memory_usage: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    version: str
    uptime: float
    system: SystemInfo
    models: List[ModelStatus]


@router.get(
    "/",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health of the embedding service and get system information"
)
async def health_check(detailed: bool = False):
    """Check the health of the service."""
    start_time = time.time()
    model_manager = get_model_manager()
    
    # Get system information
    system_info = {
        "cpu_count": os.cpu_count(),
        "memory_total": f"{psutil.virtual_memory().total / (1024 ** 3):.2f} GB",
        "memory_available": f"{psutil.virtual_memory().available / (1024 ** 3):.2f} GB",
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available()
    }
    
    # Add CUDA information if available
    if torch.cuda.is_available():
        system_info["cuda_version"] = torch.version.cuda
        
        # Get GPU information if detailed
        if detailed:
            gpu_info = []
            for i in range(torch.cuda.device_count()):
                gpu_props = torch.cuda.get_device_properties(i)
                gpu_info.append({
                    "name": gpu_props.name,
                    "memory_total": f"{gpu_props.total_memory / (1024 ** 3):.2f} GB",
                    "compute_capability": f"{gpu_props.major}.{gpu_props.minor}"
                })
                
                # Add current memory usage
                if torch.cuda.is_initialized():
                    mem_allocated = torch.cuda.memory_allocated(i) / (1024 ** 3)
                    mem_reserved = torch.cuda.memory_reserved(i) / (1024 ** 3)
                    gpu_info[-1]["memory_allocated"] = f"{mem_allocated:.2f} GB"
                    gpu_info[-1]["memory_reserved"] = f"{mem_reserved:.2f} GB"
            
            system_info["gpu_info"] = gpu_info
    
    # Get model statuses
    model_statuses = []
    for name, model_info in model_manager.models.items():
        status = {
            "name": name,
            "is_loaded": model_info.is_loaded,
            "device": model_info.device
        }
        
        if model_info.error:
            status["error"] = model_info.error
        
        if model_info.is_loaded and model_info.device.startswith("cuda") and torch.cuda.is_available():
            # Try to get memory usage
            try:
                with torch.cuda.device(torch.device(model_info.device)):
                    mem_allocated = torch.cuda.memory_allocated() / (1024 ** 3)
                    status["memory_usage"] = f"{mem_allocated:.2f} GB"
            except Exception:
                pass
        
        model_statuses.append(status)
    
    return {
        "status": "ok",
        "version": "1.0.0",  # Replace with actual version
        "uptime": time.time() - start_time,
        "system": system_info,
        "models": model_statuses
    }


@router.get(
    "/models",
    summary="Models health check",
    description="Check the status of all models"
)
async def models_health():
    """Check the health of all models."""
    model_manager = get_model_manager()
    
    # Get basic status of all models
    models_status = {}
    for name, model_info in model_manager.models.items():
        models_status[name] = {
            "is_loaded": model_info.is_loaded,
            "status": "loaded" if model_info.is_loaded else "not_loaded",
            "device": model_info.device
        }
        
        if model_info.error:
            models_status[name]["error"] = model_info.error
    
    return {
        "models": models_status,
        "default_model": model_manager.default_model_name,
        "count": len(models_status),
        "loaded_count": sum(1 for info in models_status.values() if info["is_loaded"])
    }


@router.get(
    "/model/{model_name}",
    summary="Check specific model health",
    description="Check the health of a specific model"
)
async def model_health(model_name: str):
    """Check the health of a specific model."""
    model_manager = get_model_manager()
    
    # Check if model exists
    if model_name not in model_manager.models:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_name}"
        )
    
    # Get detailed status
    status = model_manager.get_model_status(model_name)
    
    # Test the model with a simple input if it's loaded
    if status.get("status") == "loaded":
        try:
            # Create a simple test input
            test_text = "This is a test."
            
            # Time the encoding
            start_time = time.time()
            embedding = await model_manager.encode(test_text, model_name)
            encoding_time = time.time() - start_time
            
            # Add test results to status
            status["test_result"] = {
                "success": True,
                "encoding_time": encoding_time,
                "embedding_shape": list(embedding.shape)
            }
        except Exception as e:
            status["test_result"] = {
                "success": False,
                "error": str(e)
            }
    
    return status