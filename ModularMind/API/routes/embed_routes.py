"""
Embedding API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ModularMind.API.main import get_embedding_service, verify_token

router = APIRouter()

class EmbedRequest(BaseModel):
    """Embedding isteği modeli."""
    text: str
    model: Optional[str] = None
    normalize: Optional[bool] = None

class BatchEmbedRequest(BaseModel):
    """Toplu embedding isteği modeli."""
    texts: List[str]
    model: Optional[str] = None
    normalize: Optional[bool] = None

class SimilarityRequest(BaseModel):
    """Benzerlik hesaplama isteği modeli."""
    text1: str
    text2: str
    model: Optional[str] = None

class BulkSimilarityRequest(BaseModel):
    """Toplu benzerlik hesaplama isteği modeli."""
    texts: List[str]
    query: str
    model: Optional[str] = None

class EmbedResponse(BaseModel):
    """Embedding yanıtı modeli."""
    embedding: List[float]
    model: str
    dimensions: int

class BatchEmbedResponse(BaseModel):
    """Toplu embedding yanıtı modeli."""
    embeddings: List[List[float]]
    model: str
    dimensions: int
    count: int

class SimilarityResponse(BaseModel):
    """Benzerlik yanıtı modeli."""
    similarity: float
    model: str

class BulkSimilarityResponse(BaseModel):
    """Toplu benzerlik yanıtı modeli."""
    similarities: List[float]
    model: str

class ModelsResponse(BaseModel):
    """Modeller yanıtı modeli."""
    models: List[Dict[str, Any]]

@router.post("/embed", response_model=EmbedResponse, dependencies=[Depends(verify_token)])
async def create_embedding(request: EmbedRequest, embedding_service=Depends(get_embedding_service)):
    """
    Metin için embedding vektörü oluşturur.
    """
    try:
        embedding = embedding_service.get_embedding(
            text=request.text,
            model=request.model,
            normalize=request.normalize
        )
        
        model_used = request.model or embedding_service.default_model
        dimensions = len(embedding)
        
        return {
            "embedding": embedding,
            "model": model_used,
            "dimensions": dimensions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/embed_batch", response_model=BatchEmbedResponse, dependencies=[Depends(verify_token)])
async def create_batch_embedding(request: BatchEmbedRequest, embedding_service=Depends(get_embedding_service)):
    """
    Çoklu metin için embedding vektörleri oluşturur.
    """
    try:
        embeddings = embedding_service.get_embeddings(
            texts=request.texts,
            model=request.model,
            normalize=request.normalize
        )
        
        model_used = request.model or embedding_service.default_model
        dimensions = len(embeddings[0]) if embeddings else 0
        
        return {
            "embeddings": embeddings,
            "model": model_used,
            "dimensions": dimensions,
            "count": len(embeddings)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/similarity", response_model=SimilarityResponse, dependencies=[Depends(verify_token)])
async def calculate_similarity(request: SimilarityRequest, embedding_service=Depends(get_embedding_service)):
    """
    İki metin arasındaki benzerliği hesaplar.
    """
    try:
        similarity = embedding_service.similarity(
            text1=request.text1,
            text2=request.text2,
            model=request.model
        )
        
        model_used = request.model or embedding_service.default_model
        
        return {
            "similarity": similarity,
            "model": model_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bulk_similarity", response_model=BulkSimilarityResponse, dependencies=[Depends(verify_token)])
async def calculate_bulk_similarity(
    request: BulkSimilarityRequest, 
    embedding_service=Depends(get_embedding_service)
):
    """
    Bir sorgu ile çoklu metin arasındaki benzerlikleri hesaplar.
    """
    try:
        similarities = embedding_service.bulk_similarity(
            texts=request.texts,
            query=request.query,
            model=request.model
        )
        
        model_used = request.model or embedding_service.default_model
        
        return {
            "similarities": similarities,
            "model": model_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=ModelsResponse, dependencies=[Depends(verify_token)])
async def get_models(embedding_service=Depends(get_embedding_service)):
    """
    Mevcut embedding modellerini listeler.
    """
    try:
        models = embedding_service.get_available_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))