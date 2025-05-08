"""
Embedding API rotaları.
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
class ModelInfo(BaseModel):
    id: str
    name: Optional[str] = None
    provider: str
    model_id: str
    dimensions: int
    api_base_url: Optional[str] = None
    options: Optional[Dict[str, Any]] = {}
    is_default: Optional[bool] = False

class ModelsResponse(BaseModel):
    models: List[ModelInfo]
    default_model: Optional[str] = None

class EmbeddingRequest(BaseModel):
    text: str
    model: Optional[str] = None

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model: str
    dimensions: int

class BatchEmbeddingRequest(BaseModel):
    texts: List[str]
    model: Optional[str] = None

class BatchEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimensions: int

class SimilarityRequest(BaseModel):
    text1: str
    text2: str
    model: Optional[str] = None

class SimilarityResponse(BaseModel):
    similarity: float
    model: str

class ModelConfigUpdateRequest(BaseModel):
    model_config: ModelInfo
    set_as_default: Optional[bool] = False

class ModelConfigUpdateResponse(BaseModel):
    success: bool
    model: str
    is_default: bool

class SetDefaultModelRequest(BaseModel):
    model_id: str

class SetDefaultModelResponse(BaseModel):
    success: bool
    model_id: str

# Rotalar
@router.get("/models", response_model=ModelsResponse)
async def get_models(request: Request):
    """
    Kullanılabilir embedding modellerini listeler.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        models = embedding_service.get_models()
        
        # API yanıtı için modelleri dönüştür
        model_infos = []
        for model in models:
            model_infos.append(
                ModelInfo(
                    id=model["id"],
                    name=model.get("name"),
                    provider=model["provider"],
                    model_id=model["model_id"],
                    dimensions=model["dimensions"],
                    api_base_url=model.get("api_base_url"),
                    options=model.get("options", {}),
                    is_default=model["id"] == embedding_service.default_model_id
                )
            )
        
        return {
            "models": model_infos,
            "default_model": embedding_service.default_model_id
        }
    except Exception as e:
        logger.error(f"Model listeleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/create", response_model=EmbeddingResponse)
async def create_embedding(request: Request, embedding_request: EmbeddingRequest):
    """
    Metin için embedding oluşturur.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        # Embedding oluştur
        embedding = embedding_service.create_embedding(
            embedding_request.text,
            embedding_request.model
        )
        
        if embedding is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embedding oluşturulamadı")
        
        # Model bilgisini al
        model_id = embedding_request.model or embedding_service.default_model_id
        model_config = embedding_service.get_model_config(model_id)
        
        return {
            "embedding": embedding,
            "model": model_id,
            "dimensions": len(embedding)
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Embedding oluşturma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/batch", response_model=BatchEmbeddingResponse)
async def create_batch_embeddings(request: Request, batch_request: BatchEmbeddingRequest):
    """
    Metinler için toplu embedding oluşturur.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        # Batch embedding oluştur
        embeddings = embedding_service.create_batch_embeddings(
            batch_request.texts,
            batch_request.model
        )
        
        if embeddings is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Embeddingler oluşturulamadı")
        
        # Model bilgisini al
        model_id = batch_request.model or embedding_service.default_model_id
        model_config = embedding_service.get_model_config(model_id)
        
        return {
            "embeddings": embeddings,
            "model": model_id,
            "dimensions": len(embeddings[0]) if embeddings else 0
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Batch embedding oluşturma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/similarity", response_model=SimilarityResponse)
async def calculate_similarity(request: Request, similarity_request: SimilarityRequest):
    """
    İki metin arasındaki benzerliği hesaplar.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        # Benzerlik hesapla
        similarity = embedding_service.calculate_similarity(
            similarity_request.text1,
            similarity_request.text2,
            similarity_request.model
        )
        
        if similarity is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Benzerlik hesaplanamadı")
        
        # Model bilgisini al
        model_id = similarity_request.model or embedding_service.default_model_id
        
        return {
            "similarity": similarity,
            "model": model_id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Benzerlik hesaplama hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/set-default-model", response_model=SetDefaultModelResponse)
async def set_default_model(request: Request, req: SetDefaultModelRequest):
    """
    Varsayılan embedding modelini ayarlar.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        # Varsayılan modeli ayarla
        success = embedding_service.set_default_model(req.model_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Model bulunamadı: {req.model_id}")
        
        # Yapılandırmayı kaydet
        config_dir = os.environ.get("CONFIG_DIR", "./config")
        config_path = os.path.join(config_dir, "embedding_models.json")
        
        embedding_service.save_config(config_path)
        
        # Vector store yapılandırmasını da güncelle
        try:
            # Vector store yapılandırma dosyasını aç
            vector_store_config_path = os.path.join(config_dir, "vector_store.json")
            
            if os.path.exists(vector_store_config_path):
                with open(vector_store_config_path, "r") as f:
                    vs_config = json.load(f)
                
                # Varsayılan modeli güncelle
                vs_config["default_embedding_model"] = req.model_id
                
                # Yapılandırmayı kaydet
                with open(vector_store_config_path, "w") as f:
                    json.dump(vs_config, f, indent=2)
        except Exception as vs_e:
            logger.error(f"Vector store yapılandırması güncelleme hatası: {str(vs_e)}")
        
        return {
            "success": True,
            "model_id": req.model_id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Varsayılan model ayarlama hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/update-model", response_model=ModelConfigUpdateResponse)
async def update_model_config(request: Request, update_request: ModelConfigUpdateRequest):
    """
    Model yapılandırmasını günceller veya yeni model ekler.
    """
    embedding_service = request.app.state.embedding_service
    
    try:
        from ModularMind.API.services.embedding.service import EmbeddingModelConfig
        
        # ModelInfo'yu EmbeddingModelConfig'e dönüştür
        model_config = EmbeddingModelConfig(
            id=update_request.model_config.id,
            name=update_request.model_config.name,
            provider=update_request.model_config.provider,
            model_id=update_request.model_config.model_id,
            dimensions=update_request.model_config.dimensions,
            api_base_url=update_request.model_config.api_base_url,
            options=update_request.model_config.options
        )
        
        # Modeli ekle/güncelle
        success = embedding_service.add_model(model_config)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Model güncellenemedi")
        
        # Varsayılan olarak ayarla
        is_default = update_request.set_as_default
        if is_default:
            embedding_service.set_default_model(model_config.id)
        
        # Yapılandırmayı kaydet
        config_dir = os.environ.get("CONFIG_DIR", "./config")
        config_path = os.path.join(config_dir, "embedding_models.json")
        
        embedding_service.save_config(config_path)
        
        return {
            "success": True,
            "model": model_config.id,
            "is_default": is_default or embedding_service.default_model_id == model_config.id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Model güncelleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))