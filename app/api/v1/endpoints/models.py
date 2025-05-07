from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from app.models.model_manager import get_model_manager, ModelType, ModelInfo
from app.core.config import settings
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User

router = APIRouter()


@router.get("/", summary="List all available models")
async def list_models(
    current_user: User = Depends(get_current_user)
):
    """List all available models."""
    model_manager = get_model_manager()
    models_info = model_manager.list_models()
    
    return {
        "models": models_info,
        "default_model": model_manager.default_model_name,
        "total": len(models_info)
    }


@router.get("/{model_name}", summary="Get model details")
async def get_model(
    model_name: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific model."""
    model_manager = get_model_manager()
    
    if model_name not in model_manager.models:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_name}"
        )
    
    model_status = model_manager.get_model_status(model_name)
    return model_status


@router.post("/{model_name}/load", summary="Load a model")
async def load_model(
    model_name: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    current_user: User = Depends(get_current_admin_user)
):
    """Load a model into memory (admin only)."""
    model_manager = get_model_manager()
    
    if model_name not in model_manager.models:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_name}"
        )
    
    # Check if already loaded
    model_info = model_manager.models[model_name]
    if model_info.is_loaded and not force:
        return {"message": f"Model {model_name} is already loaded"}
    
    # Load in background for large models
    if model_info.dimension > 768 or model_name.startswith("large"):
        background_tasks.add_task(model_manager.load_model, model_name)
        return {
            "message": f"Loading model {model_name} in background",
            "status": "loading"
        }
    else:
        success = model_manager.load_model(model_name)
        
        if success:
            return {
                "message": f"Model {model_name} loaded successfully",
                "status": "loaded"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to load model {model_name}: {model_info.error}"
            )


@router.post("/{model_name}/unload", summary="Unload a model")
async def unload_model(
    model_name: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Unload a model from memory (admin only)."""
    model_manager = get_model_manager()
    
    if model_name not in model_manager.models:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_name}"
        )
    
    # Check if default model
    if model_name == model_manager.default_model_name:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot unload default model: {model_name}"
        )
    
    # Unload the model
    success = model_manager.unload_model(model_name)
    
    if success:
        return {
            "message": f"Model {model_name} unloaded successfully",
            "status": "unloaded"
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unload model {model_name}"
        )


@router.post("/register", summary="Register a new model")
async def register_model(
    model_info: Dict[str, Any],
    current_user: User = Depends(get_current_admin_user)
):
    """Register a new model (admin only)."""
    model_manager = get_model_manager()
    
    try:
        # Create model info
        new_model = ModelInfo(
            name=model_info["name"],
            model_type=model_info.get("model_type", ModelType.SENTENCE_TRANSFORMER),
            model_id=model_info["model_id"],
            dimension=model_info["dimension"],
            device=model_info.get("device"),
            max_sequence_length=model_info.get("max_sequence_length", 512),
            tokenizer_name=model_info.get("tokenizer_name"),
            pooling_strategy=model_info.get("pooling_strategy", "mean"),
            normalize_embeddings=model_info.get("normalize_embeddings", True),
            metadata=model_info.get("metadata", {})
        )
        
        # Register the model
        model_manager.register_model(new_model)
        
        return {
            "message": f"Model {new_model.name} registered successfully",
            "model": model_manager.get_model_status(new_model.name)
        }
        
    except KeyError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required field: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register model: {str(e)}"
        )


@router.put("/{model_name}/default", summary="Set default model")
async def set_default_model(
    model_name: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Set a model as the default (admin only)."""
    model_manager = get_model_manager()
    
    if model_name not in model_manager.models:
        raise HTTPException(
            status_code=404,
            detail=f"Model not found: {model_name}"
        )
    
    # Ensure model is loaded
    model_info = model_manager.models[model_name]
    if not model_info.is_loaded:
        # Try to load the model first
        success = model_manager.load_model(model_name)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot set unloaded model as default. Failed to load: {model_info.error}"
            )
    
    # Set as default
    model_manager.default_model_name = model_name
    
    return {
        "message": f"Model {model_name} set as default",
        "default_model": model_name
    }