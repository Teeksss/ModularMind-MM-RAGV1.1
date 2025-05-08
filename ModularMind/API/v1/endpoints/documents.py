from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from pydantic import BaseModel

from ModularMind.API.core.auth import get_current_active_user
from ModularMind.API.models.user import User
from ModularMind.API.models.document import Document, DocumentMetadata
from ModularMind.API.services.document_processor import DocumentProcessor, UnsupportedFormatError
from ModularMind.API.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

class DocumentResponse(BaseModel):
    id: str
    filename: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    chunk_count: int

class DocumentListResponse(BaseModel):
    documents: List[DocumentResponse]
    total_count: int
    page: int
    page_size: int

class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    message: str

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
) -> DocumentUploadResponse:
    """
    Belge yükler ve işler.
    """
    # Belge işleyici ve servisi oluştur
    document_processor = DocumentProcessor()
    document_service = DocumentService()
    
    # Kullanıcı tarafından sağlanan metadata
    metadata = {}
    if title:
        metadata["title"] = title
    if description:
        metadata["description"] = description
    if tags:
        metadata["tags"] = [tag.strip() for tag in tags.split(",")]
    
    try:
        # Belgeyi işle
        document = document_processor.process_document(
            file.file,
            file.filename,
            current_user.id,
            metadata
        )
        
        # Belgeyi veritabanına kaydet
        document_id = document_service.save_document(document)
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            message="Belge başarıyla yüklendi ve işlendi"
        )
        
    except UnsupportedFormatError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Belge işleme hatası: {str(e)}"
        )

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, gt=0),
    page_size: int = Query(10, gt=0, le=100),
    search: Optional[str] = None,
    tags: Optional[str] = None,
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    current_user: User = Depends(get_current_active_user)
) -> DocumentListResponse:
    """
    Kullanıcının belgelerini listeler.
    """
    document_service = DocumentService()
    
    # Filtre parametreleri
    filters = {
        "user_id": current_user.id
    }
    
    if search:
        filters["search"] = search
    
    if tags:
        filters["tags"] = [tag.strip() for tag in tags.split(",")]
    
    # Belgeleri getir
    documents = document_service.list_documents(
        page=page,
        page_size=page_size,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order
    )
    
    # Toplam belge sayısı
    total_count = document_service.count_documents(filters)
    
    # Yanıt formatına dönüştür
    document_responses = []
    for doc in documents:
        document_responses.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            metadata=doc.metadata.dict(),
            created_at=doc.created_at.isoformat(),
            updated_at=doc.updated_at.isoformat(),
            chunk_count=len(doc.chunks)
        ))
    
    return DocumentListResponse(
        documents=document_responses,
        total_count=total_count,
        page=page,
        page_size=page_size
    )

@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Belge detaylarını getirir.
    """
    document_service = DocumentService()
    
    # Belgeyi getir
    document = document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Belge bulunamadı"
        )
    
    # Erişim kontrolü
    if document.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu belgeye erişim izniniz yok"
        )
    
    # Belge yanıtını oluştur
    response = {
        "id": document.id,
        "filename": document.filename,
        "content": document.content[:1000] + "..." if len(document.content) > 1000 else document.content,
        "metadata": document.metadata.dict(),
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
        "user_id": document.user_id,
        "chunk_count": len(document.chunks)
    }
    
    return response

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, str]:
    """
    Belgeyi siler.
    """
    document_service = DocumentService()
    
    # Belgeyi getir
    document = document_service.get_document(document_id)
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Belge bulunamadı"
        )
    
    # Erişim kontrolü
    if document.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu belgeyi silme izniniz yok"
        )
    
    # Belgeyi sil
    success = document_service.delete_document(document_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Belge silinirken bir hata oluştu"
        )
    
    return {"message": "Belge başarıyla silindi"}