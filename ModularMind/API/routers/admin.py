"""
Admin API rotaları.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from pydantic import BaseModel, Field

# API doğrulama
from ModularMind.API.main import validate_token

logger = logging.getLogger(__name__)

# Router
router = APIRouter(dependencies=[Depends(validate_token)])

# Modeller
class StatsResponse(BaseModel):
    stats: Dict[str, Any]

class RebuildIndicesRequest(BaseModel):
    model_id: Optional[str] = None

class RebuildIndicesResponse(BaseModel):
    success: bool

class ModelRebuildRequest(BaseModel):
    model_id: str

class ModelRebuildResponse(BaseModel):
    success: bool
    model_id: str

class AuthCheckResponse(BaseModel):
    authenticated: bool

# Rotalar
@router.get("/stats", response_model=StatsResponse)
async def get_system_stats(request: Request):
    """
    Sistem istatistiklerini döndürür.
    """
    try:
        # Retrieval servisi istatistikleri
        retrieval_stats = {}
        if hasattr(request.app.state, "retrieval_service"):
            retrieval_stats = request.app.state.retrieval_service.get_stats()
        
        # LLM modelleri
        llm_models = []
        if hasattr(request.app.state, "llm_service"):
            llm_models = request.app.state.llm_service.get_models()
        
        # Embedding modelleri
        embedding_models = []
        if hasattr(request.app.state, "embedding_service"):
            embedding_models = request.app.state.embedding_service.get_models()
        
        # İstatistikleri birleştir
        stats = {
            "retrieval": retrieval_stats,
            "llm_models_count": len(llm_models),
            "embedding_models_count": len(embedding_models)
        }
        
        return {"stats": stats}
    except Exception as e:
        logger.error(f"İstatistik alma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/rebuild_indices", response_model=RebuildIndicesResponse)
async def rebuild_indices(request: Request, rebuild_request: Optional[RebuildIndicesRequest] = None):
    """
    Vector indekslerini yeniden oluşturur.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Model ID belirtilmişse sadece o model için indeksi oluştur
        if rebuild_request and rebuild_request.model_id:
            success = retrieval_service.vector_store.rebuild_index(rebuild_request.model_id)
        else:
            # Tüm indeksleri yeniden oluştur
            success = retrieval_service.vector_store.rebuild_index()
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="İndeksler yeniden oluşturulamadı")
        
        # Değişiklikleri kaydet
        retrieval_service.vector_store.save()
        
        return {"success": True}
    except Exception as e:
        logger.error(f"İndeks yenileme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/rebuild-model-index", response_model=ModelRebuildResponse)
async def rebuild_model_index(request: Request, rebuild_request: ModelRebuildRequest):
    """
    Belirli bir model için indeksi yeniden oluşturur.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Sadece belirtilen model için indeksi yeniden oluştur
        success = retrieval_service.vector_store.rebuild_index(rebuild_request.model_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail=f"'{rebuild_request.model_id}' için indeks yeniden oluşturulamadı"
            )
        
        # Değişiklikleri kaydet
        retrieval_service.vector_store.save()
        
        return {"success": True, "model_id": rebuild_request.model_id}
    except Exception as e:
        logger.error(f"Model indeksi yenileme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/check_auth", response_model=AuthCheckResponse)
async def check_auth(request: Request):
    """
    Kimlik doğrulamasını kontrol eder.
    """
    return {"authenticated": True}