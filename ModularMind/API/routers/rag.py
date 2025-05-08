"""
RAG API rotaları - Çoklu Embedding desteği ile.
"""

import logging
import json
import asyncio
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body, File, UploadFile, Form
from pydantic import BaseModel, Field

# API doğrulama
from ModularMind.API.main import validate_token
from ModularMind.API.services.retrieval.service import SearchOptions, RetrievalResult

logger = logging.getLogger(__name__)

# Router
router = APIRouter(dependencies=[Depends(validate_token)])

# Modeller
class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    source: Optional[str] = None
    source_type: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    url: Optional[str] = None
    language: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_metadata: Optional[Dict[str, Any]] = None

class DocumentChunkResponse(BaseModel):
    id: str
    text: str
    document_id: str
    metadata: Optional[DocumentMetadata] = None
    models: Optional[List[str]] = None

class DocumentResponse(BaseModel):
    id: str
    text: str
    metadata: Optional[DocumentMetadata] = None
    chunks: Optional[List[DocumentChunkResponse]] = None

class DocumentsListResponse(BaseModel):
    documents: List[DocumentResponse]
    count: int
    total: int

class SearchResultResponse(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    metadata: Optional[Dict[str, Any]] = None
    score: float
    source: str
    model_id: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResultResponse]
    count: int
    query: str
    search_type: str
    models_used: List[str]

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    filter_metadata: Optional[Dict[str, Any]] = None
    include_metadata: Optional[bool] = True
    min_score_threshold: Optional[float] = None
    embedding_model: Optional[str] = None
    search_type: Optional[str] = "hybrid"
    use_multi_model: Optional[bool] = False
    models_to_use: Optional[List[str]] = None

class QuerySource(BaseModel):
    chunk_id: str
    document_id: str
    metadata: Optional[Dict[str, Any]] = None
    score: float
    text_snippet: str
    model_id: Optional[str] = None

class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[QuerySource]] = None
    llm_model: str
    embedding_models: List[str]

class QueryRequest(BaseModel):
    query: str
    context_limit: Optional[int] = 5
    filter_metadata: Optional[Dict[str, Any]] = None
    include_sources: Optional[bool] = True
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    system_message: Optional[str] = None
    use_multi_model: Optional[bool] = False
    models_to_use: Optional[List[str]] = None
    use_auto_routing: Optional[bool] = True

class DocumentAddRequest(BaseModel):
    document: Dict[str, Any]
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 50
    metadata: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = None
    embedding_models: Optional[List[str]] = None

class DocumentAddResponse(BaseModel):
    document_id: str
    chunks_count: int
    models_used: List[str]

class DocumentDeleteResponse(BaseModel):
    document_id: str
    success: bool

class StatsResponse(BaseModel):
    stats: Dict[str, Any]

class ModelResponse(BaseModel):
    id: str
    name: Optional[str] = None
    dimensions: int
    embedding_count: int
    is_default: bool
    provider: Optional[str] = None

class ModelsListResponse(BaseModel):
    models: List[ModelResponse]

class ModelCoverageResponse(BaseModel):
    coverage: Dict[str, Dict[str, Any]]

# Rotalar
@router.post("/documents", response_model=DocumentAddResponse)
async def add_document(request: Request, doc_request: DocumentAddRequest):
    """
    Yeni bir belge ekler.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Belge ekle
        options = {
            "chunk_size": doc_request.chunk_size,
            "chunk_overlap": doc_request.chunk_overlap,
            "metadata": doc_request.metadata
        }
        
        # Tek model mi çok model mi belirleme
        if doc_request.embedding_models:
            options["embedding_models"] = doc_request.embedding_models
        elif doc_request.embedding_model:
            options["embedding_model"] = doc_request.embedding_model
        
        document_id = retrieval_service.add_document(doc_request.document, options)
        
        if not document_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Belge eklenemedi")
        
        # Belge parçalarını al
        document = retrieval_service.get_document(document_id)
        chunks_count = len(document.get("chunks", [])) if document else 0
        
        # Kullanılan modelleri belirle
        models_used = []
        if document and "chunks" in document and document["chunks"]:
            for model in document["chunks"][0].get("models", []):
                if model not in models_used:
                    models_used.append(model)
        
        return {"document_id": document_id, "chunks_count": chunks_count, "models_used": models_used}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Belge ekleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    chunk_size: Optional[int] = Form(500),
    chunk_overlap: Optional[int] = Form(50),
    embedding_model: Optional[str] = Form(None),
    embedding_models: Optional[str] = Form(None),
    tag: Optional[str] = Form(None)
):
    """
    Dosya yükler ve belge olarak ekler.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Dosya içeriğini oku
        content = await file.read()
        
        # Dosya içeriğini metne dönüştür
        text = content.decode("utf-8", errors="ignore")
        
        # Dosya metadata'sı oluştur
        metadata = {
            "title": file.filename,
            "source": "upload",
            "source_type": "file",
            "file_type": file.content_type
        }
        
        # Tag eklenirse onu da metadata'ya ekle
        if tag:
            if "tags" not in metadata:
                metadata["tags"] = []
            metadata["tags"].append(tag)
        
        # Belge oluştur
        document = {
            "text": text,
            "metadata": metadata
        }
        
        # Belge ekle
        options = {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        }
        
        # Embedding modelleri
        if embedding_models:
            try:
                models_list = json.loads(embedding_models)
                if isinstance(models_list, list):
                    options["embedding_models"] = models_list
            except json.JSONDecodeError:
                # JSON listesi değilse virgülle ayrılmış string olabilir
                options["embedding_models"] = [model.strip() for model in embedding_models.split(',')]
        elif embedding_model:
            options["embedding_model"] = embedding_model
        
        document_id = retrieval_service.add_document(document, options)
        
        if not document_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Belge eklenemedi")
        
        # Belge parçalarını al
        document_info = retrieval_service.get_document(document_id)
        chunks_count = len(document_info.get("chunks", [])) if document_info else 0
        
        # Kullanılan modelleri belirle
        models_used = []
        if document_info and "chunks" in document_info and document_info["chunks"]:
            for model in document_info["chunks"][0].get("models", []):
                if model not in models_used:
                    models_used.append(model)
        
        return {
            "document_id": document_id, 
            "chunks_count": chunks_count, 
            "filename": file.filename,
            "models_used": models_used
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Dosya yükleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(request: Request, document_id: str):
    """
    Belge ID'sine göre belge döndürür.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        document = retrieval_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Belge bulunamadı: {document_id}")
        
        return document
    except Exception as e:
        logger.error(f"Belge alma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/documents", response_model=DocumentsListResponse)
async def list_documents(
    request: Request,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    filter_metadata: Optional[str] = None
):
    """
    Belgeleri listeler.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Metadata filtresini parse et
        metadata_filter = None
        if filter_metadata:
            try:
                metadata_filter = json.loads(filter_metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Geçersiz filter_metadata format")
        
        # Belgeleri listele
        documents = retrieval_service.list_documents(limit, offset, metadata_filter)
        
        return documents
    except Exception as e:
        logger.error(f"Belge listeleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(request: Request, document_id: str):
    """
    Belge siler.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        success = retrieval_service.delete_document(document_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Belge silinemedi: {document_id}")
        
        return {"document_id": document_id, "success": True}
    except Exception as e:
        logger.error(f"Belge silme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/search", response_model=SearchResponse)
async def search(request: Request, search_request: SearchRequest):
    """
    Belgelerde arama yapar.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        # Arama seçenekleri oluştur
        options = SearchOptions(
            limit=search_request.limit,
            min_score_threshold=search_request.min_score_threshold,
            filter_metadata=search_request.filter_metadata,
            include_metadata=search_request.include_metadata,
            embedding_model=search_request.embedding_model,
            search_type=search_request.search_type,
            use_multi_model=search_request.use_multi_model,
            models_to_use=search_request.models_to_use
        )
        
        # Arama yap
        results = retrieval_service.search(search_request.query, options)
        
        # Sonuçları dönüştür
        search_results = [
            SearchResultResponse(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                text=result.text,
                metadata=result.metadata,
                score=result.score,
                source=result.source,
                model_id=result.model_id
            )
            for result in results
        ]
        
        # Kullanılan modelleri belirle
        models_used = []
        for result in results:
            if result.model_id and result.model_id not in models_used:
                models_used.append(result.model_id)
        
        return {
            "results": search_results,
            "count": len(search_results),
            "query": search_request.query,
            "search_type": search_request.search_type,
            "models_used": models_used
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Arama hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/query", response_model=QueryResponse)
async def query(request: Request, query_request: QueryRequest):
    """
    RAG sorgusu yapar.
    """
    retrieval_service = request.app.state.retrieval_service
    llm_service = request.app.state.llm_service
    model_router = getattr(request.app.state, "model_router", None)
    
    try:
        # Model router kullanılacak mı?
        if model_router and query_request.use_auto_routing:
            # Akıllı model router'ı kullan
            result = await model_router.query(
                query=query_request.query,
                context_limit=query_request.context_limit,
                filter_metadata=query_request.filter_metadata,
                llm_model=query_request.llm_model,
                system_message=query_request.system_message
            )
            
            return {
                "answer": result["answer"],
                "sources": [
                    QuerySource(
                        chunk_id=source["chunk_id"],
                        document_id=source["document_id"],
                        metadata=source["metadata"],
                        score=source["score"],
                        text_snippet=source["text"],
                        model_id=source.get("model_id")
                    ) 
                    for source in result.get("sources", [])
                ],
                "llm_model": query_request.llm_model or "default",
                "embedding_models": result.get("embedding_models", [])
            }
        
        # Arama seçenekleri oluştur
        options = SearchOptions(
            limit=query_request.context_limit,
            filter_metadata=query_request.filter_metadata,
            embedding_model=query_request.embedding_model,
            search_type="hybrid",
            use_multi_model=query_request.use_multi_model,
            models_to_use=query_request.models_to_use
        )
        
        # Arama yap
        search_results = retrieval_service.search(query_request.query, options)
        
        # Kullanılan modelleri belirle
        embedding_models = []
        for result in search_results:
            if result.model_id and result.model_id not in embedding_models:
                embedding_models.append(result.model_id)
        
        if not search_results:
            # Sonuç bulunamadı, LLM'yi direkt kullan
            answer = llm_service.generate_text(
                f"Soru: {query_request.query}\n\nCevap:",
                query_request.llm_model,
                system_message=query_request.system_message or "Sen yardımcı bir asistansın."
            )
        else:
            # Bağlam oluştur
            contexts = []
            for i, result in enumerate(search_results):
                context_text = f"[Belge {i+1}]: {result.text}"
                contexts.append(context_text)
            
            context_str = "\n\n".join(contexts)
            
            # Sistem mesajı
            system_msg = query_request.system_message or "Verilen belgelerden bilgi alarak soruları cevapla. Belgelerde bulunmayan bilgiler için bunu belirt."
            
            # Prompt oluştur
            prompt = f"""Aşağıdaki belgeleri kullanarak soruyu cevapla:

{context_str}

Soru: {query_request.query}

Cevap:"""
            
            # LLM ile yanıt oluştur
            answer = llm_service.generate_text(
                prompt,
                query_request.llm_model,
                system_message=system_msg
            )
        
        # LLM model ID'sini al
        llm_model_id = query_request.llm_model
        if not llm_model_id:
            model_ids = llm_service.model_manager.get_model_ids()
            llm_model_id = model_ids[0] if model_ids else "unknown"
        
        # Kaynak belgeleri ekle
        sources = None
        if query_request.include_sources and search_results:
            sources = [
                QuerySource(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    metadata=result.metadata,
                    score=result.score,
                    text_snippet=result.text,
                    model_id=result.model_id
                )
                for result in search_results
            ]
        
        return {
            "answer": answer,
            "sources": sources,
            "llm_model": llm_model_id,
            "embedding_models": embedding_models
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"RAG sorgu hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/models", response_model=ModelsListResponse)
async def list_models(request: Request):
    """
    Kullanılabilir embedding modellerini listeler.
    """
    retrieval_service = request.app.state.retrieval_service
    embedding_service = request.app.state.embedding_service
    
    try:
        # Vector store'dan istatistikleri al
        models = retrieval_service.get_available_models()
        
        # Embedding servisinden ek bilgileri al
        embedding_models = embedding_service.get_models()
        
        # Modelleri birleştir
        model_responses = []
        for model in models:
            # Embedding servisinden ek bilgileri bul
            embedding_model = next((m for m in embedding_models if m["id"] == model["id"]), None)
            
            model_responses.append(ModelResponse(
                id=model["id"],
                name=embedding_model.get("name") if embedding_model else model["id"],
                dimensions=model["dimensions"],
                embedding_count=model["embedding_count"],
                is_default=model["is_default"],
                provider=embedding_model.get("provider") if embedding_model else None
            ))
        
        return {"models": model_responses}
    except Exception as e:
        logger.error(f"Model listeleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/embedding-coverage", response_model=ModelCoverageResponse)
async def get_embedding_coverage(request: Request):
    """
    Belgelerin her model için embedding kapsamını döndürür.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        coverage = retrieval_service.get_embedding_coverage()
        return {"coverage": coverage}
    except Exception as e:
        logger.error(f"Embedding kapsamı alma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/stats", response_model=StatsResponse)
async def get_stats(request: Request):
    """
    Vector store istatistiklerini döndürür.
    """
    retrieval_service = request.app.state.retrieval_service
    
    try:
        stats = retrieval_service.get_stats()
        
        return {"stats": stats}
    except Exception as e:
        logger.error(f"İstatistik alma hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))