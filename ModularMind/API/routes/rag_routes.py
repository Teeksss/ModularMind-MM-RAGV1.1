"""
RAG API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path, File, UploadFile
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ModularMind.API.main import get_vector_store, get_embedding_service, get_llm_service, verify_token
from ModularMind.API.services.retrieval.models import Chunk, Document, SearchResult

router = APIRouter()

class AddDocumentRequest(BaseModel):
    """Belge ekleme isteği modeli."""
    document: Dict[str, Any]
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 50
    metadata: Optional[Dict[str, Any]] = None
    embedding_model: Optional[str] = None

class SearchRequest(BaseModel):
    """Arama isteği modeli."""
    query: str
    limit: Optional[int] = 10
    filter_metadata: Optional[Dict[str, Any]] = None
    include_metadata: Optional[bool] = True
    min_score_threshold: Optional[float] = None
    embedding_model: Optional[str] = None
    search_type: str = "hybrid"  # hybrid, vector, keyword, metadata

class QueryRequest(BaseModel):
    """RAG sorgu isteği modeli."""
    query: str
    context_limit: Optional[int] = 5
    filter_metadata: Optional[Dict[str, Any]] = None
    include_sources: Optional[bool] = True
    llm_model: Optional[str] = None
    embedding_model: Optional[str] = None
    system_message: Optional[str] = None

class DocumentResponse(BaseModel):
    """Belge yanıtı modeli."""
    document_id: str
    chunks_count: int
    metadata: Dict[str, Any]

class SearchResponse(BaseModel):
    """Arama yanıtı modeli."""
    results: List[Dict[str, Any]]
    count: int
    query: str
    search_type: str

class QueryResponse(BaseModel):
    """RAG sorgu yanıtı modeli."""
    answer: str
    sources: Optional[List[Dict[str, Any]]]
    llm_model: str
    embedding_model: str

class StatsResponse(BaseModel):
    """İstatistik yanıtı modeli."""
    stats: Dict[str, Any]

@router.post("/documents", response_model=DocumentResponse, dependencies=[Depends(verify_token)])
async def add_document(request: AddDocumentRequest, vector_store=Depends(get_vector_store), embedding_service=Depends(get_embedding_service)):
    """
    Belge ekler ve vektör deposuna kaydeder.
    """
    try:
        # Belge modelini oluştur
        doc_dict = request.document
        document = Document(
            id=doc_dict.get("id", ""),
            text=doc_dict.get("text", ""),
            metadata=doc_dict.get("metadata", {}) or request.metadata or {}
        )
        
        # Metni parçalara ayır
        from ModularMind.API.services.retrieval.chunking import split_text
        chunks = split_text(
            document.text, 
            chunk_size=request.chunk_size, 
            chunk_overlap=request.chunk_overlap
        )
        
        # Parçaları oluştur
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk = Chunk(
                id=f"{document.id}_{i}",
                text=chunk_text,
                document_id=document.id,
                metadata=document.metadata.copy()
            )
            
            # Embedding hesapla
            if embedding_service:
                chunk.embedding = embedding_service.get_embedding(
                    chunk_text, 
                    model=request.embedding_model
                )
            
            # Parçayı ekle
            chunk_objects.append(chunk)
            document.chunks.append(chunk)
        
        # Vektör deposuna ekle
        vector_store.add_batch(chunk_objects)
        
        return {
            "document_id": document.id,
            "chunks_count": len(document.chunks),
            "metadata": document.metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=SearchResponse, dependencies=[Depends(verify_token)])
async def search_documents(request: SearchRequest, vector_store=Depends(get_vector_store)):
    """
    Belgelerde arama yapar.
    """
    try:
        search_results = []
        
        if request.search_type == "vector":
            search_results = vector_store.search_by_text(
                query_text=request.query,
                limit=request.limit,
                filter_metadata=request.filter_metadata,
                include_metadata=request.include_metadata,
                min_score_threshold=request.min_score_threshold,
                embedding_model=request.embedding_model
            )
        elif request.search_type == "keyword":
            search_results = vector_store.keyword_search(
                query_text=request.query,
                limit=request.limit,
                filter_metadata=request.filter_metadata
            )
        elif request.search_type == "metadata":
            if not request.filter_metadata:
                raise HTTPException(status_code=400, detail="filter_metadata gereklidir")
                
            search_results = vector_store.metadata_search(
                filter_metadata=request.filter_metadata,
                limit=request.limit
            )
        else:  # hybrid
            search_results = vector_store.hybrid_search(
                query_text=request.query,
                limit=request.limit,
                filter_metadata=request.filter_metadata,
                min_score_threshold=request.min_score_threshold,
                embedding_model=request.embedding_model
            )
        
        # Sonuçları sözlüğe dönüştür
        results = []
        for result in search_results:
            results.append({
                "chunk_id": result.chunk.id,
                "document_id": result.chunk.document_id,
                "text": result.chunk.text,
                "metadata": result.chunk.metadata if request.include_metadata else None,
                "score": result.score,
                "source": result.source
            })
        
        return {
            "results": results,
            "count": len(results),
            "query": request.query,
            "search_type": request.search_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=QueryResponse, dependencies=[Depends(verify_token)])
async def query_rag(
    request: QueryRequest, 
    vector_store=Depends(get_vector_store),
    llm_service=Depends(get_llm_service)
):
    """
    RAG sorgusu yapar: Arama + Yanıt Üretme.
    """
    try:
        # İlgili belgeleri ara
        search_results = vector_store.hybrid_search(
            query_text=request.query,
            limit=request.context_limit,
            filter_metadata=request.filter_metadata,
            embedding_model=request.embedding_model
        )
        
        # Bağlam oluştur
        context = ""
        sources = []
        
        for i, result in enumerate(search_results):
            context += f"[{i+1}] {result.chunk.text}\n\n"
            
            if request.include_sources:
                sources.append({
                    "chunk_id": result.chunk.id,
                    "document_id": result.chunk.document_id,
                    "metadata": result.chunk.metadata,
                    "score": result.score,
                    "text_snippet": result.chunk.text[:100] + "..." if len(result.chunk.text) > 100 else result.chunk.text
                })
        
        # Sistem mesajı
        system_message = request.system_message or "Bağlam bilgilerini kullanarak soruyu doğru ve kapsamlı bir şekilde yanıtla."
        
        # Soru-cevap şablonu oluştur
        prompt_template = llm_service.prompt_templates.get("question_answer")
        if prompt_template:
            answer = llm_service.generate_from_template(
                template_id="question_answer",
                variables={
                    "context": context,
                    "question": request.query
                },
                model=request.llm_model,
                temperature=0.3
            )
        else:
            # Şablon yoksa direkt prompt oluştur
            prompt = f"""Aşağıdaki bağlamı kullanarak soruyu cevapla:

Bağlam:
{context}

Soru: {request.query}

Cevap:"""
            
            answer = llm_service.generate_text(
                prompt=prompt,
                model=request.llm_model,
                system_message=system_message,
                temperature=0.3
            )
        
        return {
            "answer": answer,
            "sources": sources if request.include_sources else None,
            "llm_model": request.llm_model or llm_service.default_model,
            "embedding_model": request.embedding_model or "default"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", dependencies=[Depends(verify_token)])
async def get_document(document_id: str, vector_store=Depends(get_vector_store)):
    """
    Belge bilgilerini getirir.
    """
    try:
        documents = vector_store.get_documents(document_id=document_id)
        
        if not documents:
            raise HTTPException(status_code=404, detail="Belge bulunamadı")
            
        return documents[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents", dependencies=[Depends(verify_token)])
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    filter_metadata: Optional[Dict[str, Any]] = None,
    vector_store=Depends(get_vector_store)
):
    """
    Belgeleri listeler.
    """
    try:
        documents = vector_store.get_documents(
            filter_metadata=filter_metadata,
            limit=limit,
            offset=offset
        )
        
        return {
            "documents": documents,
            "count": len(documents),
            "total": vector_store.collection_stats.get("total_documents", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/documents/{document_id}", dependencies=[Depends(verify_token)])
async def delete_document(document_id: str, vector_store=Depends(get_vector_store)):
    """
    Belgeyi siler.
    """
    try:
        # İlgili tüm parçaları bul
        documents = vector_store.get_documents(document_id=document_id)
        
        if not documents:
            raise HTTPException(status_code=404, detail="Belge bulunamadı")
            
        document = documents[0]
        
        # Parçaları sil
        for chunk in document["chunks"]:
            vector_store.delete(chunk["chunk_id"])
        
        return {"status": "success", "document_id": document_id, "deleted_chunks": len(document["chunks"])}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats", response_model=StatsResponse, dependencies=[Depends(verify_token)])
async def get_stats(vector_store=Depends(get_vector_store)):
    """
    Vektör deposu istatistiklerini döndürür.
    """
    try:
        stats = vector_store.get_stats()
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    chunk_size: int = Query(500),
    chunk_overlap: int = Query(50),
    embedding_model: Optional[str] = None,
    vector_store=Depends(get_vector_store),
    embedding_service=Depends(get_embedding_service)
):
    """
    Belge dosyası yükler ve işler.
    """
    try:
        from ModularMind.API.services.retrieval.document_loader import load_document_from_file
        
        # Dosyayı oku ve belge oluştur
        document = await load_document_from_file(file)
        
        # Belge ekleme işlemini gerçekleştir
        request = AddDocumentRequest(
            document=document.to_dict(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model
        )
        
        return await add_document(request, vector_store, embedding_service)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))