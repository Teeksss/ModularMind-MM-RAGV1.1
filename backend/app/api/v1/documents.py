from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
import uuid
from datetime import datetime

from app.models.document import (
    DocumentCreate, 
    DocumentResponse, 
    DocumentList, 
    DocumentMetadata,
    EnrichmentStatus
)
from app.services.document_service import DocumentService, get_document_service
from app.services.enrichment_service import EnrichmentService, get_enrichment_service
from app.api.deps import get_current_user
from app.models.user import User
from app.core.settings import get_settings

settings = get_settings()
router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/", response_model=DocumentResponse)
async def create_document(
    document: DocumentCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """
    Create a new document from text content.
    
    Optionally starts enrichment processes in the background.
    """
    # Create the document
    doc_id = str(uuid.uuid4())
    document_data = {
        "id": doc_id,
        "title": document.title,
        "content": document.content,
        "content_type": document.content_type,
        "source": document.source,
        "owner_id": current_user.id,
        "created_at": datetime.now(),
        "metadata": document.metadata or {},
        "language": document.language or settings.multilingual.default_language,
        "enrichment_status": EnrichmentStatus.PENDING if settings.enrichment.enrichment_enabled else EnrichmentStatus.SKIPPED
    }
    
    # Save to database
    created_doc = await document_service.create_document(document_data)
    
    # Start enrichment process in background if enabled
    if settings.enrichment.enrichment_enabled:
        background_tasks.add_task(
            enrichment_service.enrich_document,
            doc_id=doc_id,
            content=document.content,
            language=document.language or settings.multilingual.default_language,
            content_type=document.content_type
        )
    
    return created_doc


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = None,
    source: Optional[str] = None,
    language: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """
    Upload a document file (PDF, TXT, DOCX, etc.) and create a document.
    
    The file will be processed and the content extracted.
    """
    # Determine content type from file extension
    content_type = None
    if file.filename:
        ext = file.filename.split(".")[-1].lower()
        if ext == "pdf":
            content_type = "application/pdf"
        elif ext == "txt":
            content_type = "text/plain"
        elif ext == "docx":
            content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == "html":
            content_type = "text/html"
        else:
            content_type = "application/octet-stream"
    
    # Read file content
    file_content = await file.read()
    
    # Extract text content from the file
    # In a real implementation, this would use specialized libraries
    # for different file types (PyPDF2, python-docx, etc.)
    text_content = await document_service.extract_text_from_file(
        file_content, 
        content_type=content_type
    )
    
    # Create document
    doc_id = str(uuid.uuid4())
    document_data = {
        "id": doc_id,
        "title": title or file.filename,
        "content": text_content,
        "content_type": content_type,
        "source": source or "file_upload",
        "owner_id": current_user.id,
        "created_at": datetime.now(),
        "metadata": {
            "original_filename": file.filename,
            "file_size": len(file_content)
        },
        "language": language or settings.multilingual.default_language,
        "enrichment_status": EnrichmentStatus.PENDING if settings.enrichment.enrichment_enabled else EnrichmentStatus.SKIPPED
    }
    
    # Save to database
    created_doc = await document_service.create_document(document_data)
    
    # Start enrichment process in background if enabled
    if settings.enrichment.enrichment_enabled:
        background_tasks.add_task(
            enrichment_service.enrich_document,
            doc_id=doc_id,
            content=text_content,
            language=language or settings.multilingual.default_language,
            content_type=content_type
        )
    
    return created_doc


@router.get("/", response_model=DocumentList)
async def get_documents(
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get a list of documents owned by the current user."""
    documents = await document_service.get_documents(
        owner_id=current_user.id,
        skip=skip,
        limit=limit
    )
    total = await document_service.count_documents(owner_id=current_user.id)
    
    return {
        "documents": documents,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get a specific document by ID."""
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check ownership
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    return document


@router.delete("/{document_id}", response_model=Dict[str, Any])
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Delete a document by ID."""
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check ownership
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this document")
    
    # Delete document
    deleted = await document_service.delete_document(document_id)
    
    if not deleted:
        raise HTTPException(status_code=500, detail="Failed to delete document")
    
    return {"status": "success", "message": f"Document {document_id} deleted"}


@router.get("/{document_id}/enrichment", response_model=EnrichmentStatus)
async def get_enrichment_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service)
):
    """Get the enrichment status for a document."""
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check ownership
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this document")
    
    return document.enrichment_status


@router.post("/{document_id}/enrich", response_model=Dict[str, Any])
async def start_enrichment(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    document_service: DocumentService = Depends(get_document_service),
    enrichment_service: EnrichmentService = Depends(get_enrichment_service)
):
    """Start or restart the enrichment process for a document."""
    document = await document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    
    # Check ownership
    if document.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this document")
    
    # Update status to PENDING
    await document_service.update_enrichment_status(
        document_id=document_id,
        status=EnrichmentStatus.PENDING
    )
    
    # Start enrichment in background
    background_tasks.add_task(
        enrichment_service.enrich_document,
        doc_id=document_id,
        content=document.content,
        language=document.language or settings.multilingual.default_language,
        content_type=document.content_type
    )
    
    return {
        "status": "success", 
        "message": f"Enrichment started for document {document_id}"
    }