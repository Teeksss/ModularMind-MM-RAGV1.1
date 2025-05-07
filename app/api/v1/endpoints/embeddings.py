from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Body
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.models.model_manager import get_model_manager
from app.utils.metrics import batch_size_histogram, encoding_latency

import time
import logging
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter()


class EmbeddingRequest(BaseModel):
    """Request model for generating embeddings."""
    texts: Union[str, List[str]]
    model: Optional[str] = None
    normalize: bool = True
    truncate: bool = True


class EmbeddingResponse(BaseModel):
    """Response model for embeddings."""
    model: str
    embeddings: List[List[float]]
    dimensions: int
    texts_count: int
    processing_time: float


@router.post(
    "/", 
    response_model=EmbeddingResponse, 
    summary="Generate embeddings"
)
async def create_embeddings(
    request: EmbeddingRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate embeddings for text."""
    model_manager = get_model_manager()
    start_time = time.time()
    
    try:
        # Track batch size in metrics
        texts = request.texts
        if isinstance(texts, str):
            texts = [texts]
            
        batch_size = len(texts)
        batch_size_histogram.observe(batch_size)
        
        # Call model manager to generate embeddings
        embeddings = await model_manager.encode(
            texts=texts,
            model_name=request.model,
            normalize=request.normalize,
            truncate=request.truncate
        )
        
        # Get the model info for response
        model_info = model_manager.get_model(request.model)
        model_name = model_info.name  # Get actual model name used
        
        # Record latency
        processing_time = time.time() - start_time
        encoding_latency.labels(model_name=model_name).observe(processing_time)
        
        # Prepare response
        return EmbeddingResponse(
            model=model_name,
            embeddings=embeddings.tolist(),
            dimensions=model_info.dimension,
            texts_count=batch_size,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error generating embeddings: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error generating embeddings: {str(e)}"
        )


class SimilarityRequest(BaseModel):
    """Request model for computing similarity."""
    texts1: List[str]
    texts2: List[str]
    model: Optional[str] = None


class SimilarityResponse(BaseModel):
    """Response model for similarity."""
    model: str
    similarities: List[float]
    processing_time: float


@router.post(
    "/similarity", 
    response_model=SimilarityResponse, 
    summary="Compute similarity between texts"
)
async def compute_similarity(
    request: SimilarityRequest,
    current_user: User = Depends(get_current_user)
):
    """Compute cosine similarity between pairs of texts."""
    model_manager = get_model_manager()
    start_time = time.time()
    
    # Validate input
    if len(request.texts1) != len(request.texts2):
        raise HTTPException(
            status_code=400,
            detail="texts1 and texts2 must have the same length"
        )
    
    try:
        # Generate embeddings for both sets of texts
        model_info = model_manager.get_model(request.model)
        model_name = model_info.name
        
        embeddings1 = await model_manager.encode(
            texts=request.texts1,
            model_name=model_name,
            normalize=True  # Normalize for cosine similarity
        )
        
        embeddings2 = await model_manager.encode(
            texts=request.texts2,
            model_name=model_name,
            normalize=True  # Normalize for cosine similarity
        )
        
        # Compute similarities
        similarities = np.sum(embeddings1 * embeddings2, axis=1).tolist()
        
        # Record processing time
        processing_time = time.time() - start_time
        
        return SimilarityResponse(
            model=model_name,
            similarities=similarities,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error computing similarity: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error computing similarity: {str(e)}"
        )


class DocumentEmbeddingRequest(BaseModel):
    """Request for embedding and storing document embeddings."""
    document_ids: List[str]
    model: Optional[str] = None
    force_recompute: bool = False


@router.post(
    "/documents",
    summary="Generate and store embeddings for documents"
)
async def create_document_embeddings(
    request: DocumentEmbeddingRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Generate and store embeddings for documents (runs in background)."""
    from app.core.tasks import get_task_queue
    
    # Schedule background task to generate embeddings
    task_queue = get_task_queue()
    
    # Import here to avoid circular imports
    from app.services.document_embedder import embed_documents
    
    task = await task_queue.enqueue(
        embed_documents,
        name="document_embedding",
        metadata={
            "user_id": current_user.id,
            "document_count": len(request.document_ids)
        },
        document_ids=request.document_ids,
        model_name=request.model,
        force_recompute=request.force_recompute,
        user_id=current_user.id
    )
    
    return {
        "message": f"Embedding generation started for {len(request.document_ids)} documents",
        "task_id": task.id,
        "status": task.status
    }