from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, Form, Body
from pydantic import BaseModel, Field
import base64
from PIL import Image
import io
import time
import logging
import numpy as np

from app.models.multimodal_models import get_multimodal_manager
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.utils.metrics import batch_size_histogram, encoding_latency

logger = logging.getLogger(__name__)

router = APIRouter()


class ImageEmbeddingRequest(BaseModel):
    """Request model for generating image embeddings."""
    image_data: str  # Base64 encoded image data
    model: Optional[str] = None
    normalize: bool = True


class TextEmbeddingRequest(BaseModel):
    """Request model for generating text embeddings with multimodal models."""
    texts: Union[str, List[str]]
    model: Optional[str] = None
    normalize: bool = True


class EmbeddingResponse(BaseModel):
    """Response model for embeddings."""
    model: str
    embeddings: List[List[float]]
    dimensions: int
    processing_time: float


class ImageTextSimilarityRequest(BaseModel):
    """Request model for computing similarity between image and text."""
    image_data: str  # Base64 encoded image data
    texts: Union[str, List[str]]
    model: Optional[str] = None


class SimilarityResponse(BaseModel):
    """Response model for similarity scores."""
    model: str
    similarities: List[float]
    processing_time: float


@router.post(
    "/image-embedding",
    response_model=EmbeddingResponse,
    summary="Generate embeddings for images"
)
async def create_image_embedding(
    request: ImageEmbeddingRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate embeddings for an image."""
    multimodal_manager = get_multimodal_manager()
    start_time = time.time()
    
    try:
        # Call multimodal manager to generate embeddings
        embedding = await multimodal_manager.encode_image(
            image=request.image_data,
            model_name=request.model,
            normalize=request.normalize
        )
        
        # Get the model info for response
        model_info = multimodal_manager.get_model(request.model)
        model_name = model_info.name  # Get actual model name used
        
        # Record latency
        processing_time = time.time() - start_time
        encoding_latency.labels(model_name=model_name).observe(processing_time)
        
        # Prepare response
        return EmbeddingResponse(
            model=model_name,
            embeddings=[embedding[0].tolist()],  # Single image, wrapped in list
            dimensions=model_info.image_dimension,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating image embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating image embedding: {str(e)}"
        )


@router.post(
    "/image-upload",
    response_model=EmbeddingResponse,
    summary="Generate embeddings for uploaded image"
)
async def upload_image_embedding(
    file: UploadFile = File(...),
    model: Optional[str] = Form(None),
    normalize: bool = Form(True),
    current_user: User = Depends(get_current_user)
):
    """Generate embeddings for an uploaded image file."""
    multimodal_manager = get_multimodal_manager()
    start_time = time.time()
    
    try:
        # Read image file
        image_data = await file.read()
        
        # Call multimodal manager to generate embeddings
        embedding = await multimodal_manager.encode_image(
            image=image_data,
            model_name=model,
            normalize=normalize
        )
        
        # Get the model info for response
        model_info = multimodal_manager.get_model(model)
        model_name = model_info.name  # Get actual model name used
        
        # Record latency
        processing_time = time.time() - start_time
        encoding_latency.labels(model_name=model_name).observe(processing_time)
        
        # Prepare response
        return EmbeddingResponse(
            model=model_name,
            embeddings=[embedding[0].tolist()],  # Single image, wrapped in list
            dimensions=model_info.image_dimension,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating image embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating image embedding: {str(e)}"
        )


@router.post(
    "/text-embedding",
    response_model=EmbeddingResponse,
    summary="Generate text embeddings with multimodal models"
)
async def create_text_embedding(
    request: TextEmbeddingRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate text embeddings using multimodal models."""
    multimodal_manager = get_multimodal_manager()
    start_time = time.time()
    
    try:
        # Track batch size in metrics
        texts = request.texts
        if isinstance(texts, str):
            texts = [texts]
            
        batch_size = len(texts)
        batch_size_histogram.observe(batch_size)
        
        # Call multimodal manager to generate embeddings
        embeddings = await multimodal_manager.encode_text(
            text=texts,
            model_name=request.model,
            normalize=request.normalize
        )
        
        # Get the model info for response
        model_info = multimodal_manager.get_model(request.model)
        model_name = model_info.name  # Get actual model name used
        
        # Record latency
        processing_time = time.time() - start_time
        encoding_latency.labels(model_name=model_name).observe(processing_time)
        
        # Prepare response
        return EmbeddingResponse(
            model=model_name,
            embeddings=embeddings.tolist(),
            dimensions=model_info.text_dimension,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating text embedding: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating text embedding: {str(e)}"
        )


@router.post(
    "/similarity",
    response_model=SimilarityResponse,
    summary="Compute similarity between an image and text"
)
async def compute_image_text_similarity(
    request: ImageTextSimilarityRequest,
    current_user: User = Depends(get_current_user)
):
    """Compute similarity between an image and text."""
    multimodal_manager = get_multimodal_manager()
    start_time = time.time()
    
    try:
        # Call multimodal manager to compute similarity
        similarities = await multimodal_manager.compute_similarity(
            image=request.image_data,
            text=request.texts,
            model_name=request.model
        )
        
        # Get the model info for response
        model_info = multimodal_manager.get_model(request.model)
        model_name = model_info.name  # Get actual model name used
        
        # Convert to list if not already
        if not isinstance(similarities, list):
            similarities = [similarities]
        
        # Record latency
        processing_time = time.time() - start_time
        encoding_latency.labels(model_name=model_name).observe(processing_time)
        
        # Prepare response
        return SimilarityResponse(
            model=model_name,
            similarities=similarities,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error computing image-text similarity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error computing image-text similarity: {str(e)}"
        )


@router.get(
    "/models",
    summary="List all available multimodal models"
)
async def list_multimodal_models(
    current_user: User = Depends(get_current_user)
):
    """List all available multimodal models."""
    multimodal_manager = get_multimodal_manager()
    models_info = multimodal_manager.list_models()
    
    return {
        "models": models_info,
        "default_model": multimodal_manager.default_model_name,
        "total": len(models_info)
    }