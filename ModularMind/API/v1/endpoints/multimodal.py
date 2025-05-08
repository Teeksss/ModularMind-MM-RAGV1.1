"""
ModularMind API için multimodal işleme endpointleri.
Görüntü, video ve ses dosyalarının yüklenmesi, analizi ve aranması için API'ler sağlar.
"""

import os
import time
import logging
import shutil
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field

from ModularMind.API.models.user import User
from ModularMind.API.core.auth import get_current_active_user
from ModularMind.config import config
from ModularMind.API.core.resource_manager import resource_aware, limit_cpu
from ModularMind.API.services.multimodal_service import MultimodalProcessor, ContentType

router = APIRouter(prefix="/multimodal", tags=["multimodal"])

# Modeller
class UploadResponse(BaseModel):
    """Dosya yükleme yanıtı."""
    content_id: str
    content_type: str
    filename: str
    caption: Optional[str] = None
    metadata: Dict[str, Any]
    message: str

class MultimodalContent(BaseModel):
    """Multimodal içerik modeli."""
    id: str
    content_type: str
    filename: str
    caption: Optional[str] = None
    preview: Optional[str] = None
    metadata: Dict[str, Any]
    created_at: str
    user_id: str

class MultimodalSearchQuery(BaseModel):
    """Multimodal arama sorgusu."""
    query_text: Optional[str] = None
    query_image: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    limit: Optional[int] = 20

class SearchResult(BaseModel):
    """Arama sonucu."""
    id: str
    content_type: str
    filename: str
    caption: str
    preview: Optional[str] = None
    similarity: float
    metadata: Dict[str, Any]
    created_at: str

# Yardımcı fonksiyonlar
def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Dosya uzantısının izin verilen uzantılar listesinde olup olmadığını kontrol eder.
    
    Args:
        filename: Dosya adı
        allowed_extensions: İzin verilen uzantılar listesi
        
    Returns:
        bool: Uzantı geçerliyse True, değilse False
    """
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    return ext in allowed_extensions

def get_content_type(filename: str) -> ContentType:
    """
    Dosya adından içerik türünü belirler.
    
    Args:
        filename: Dosya adı
        
    Returns:
        ContentType: İçerik türü
    """
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if ext in config.multimodal.supported_image_formats:
        return ContentType.IMAGE
    elif ext in config.multimodal.supported_video_formats:
        return ContentType.VIDEO
    elif ext in config.multimodal.supported_audio_formats:
        return ContentType.AUDIO
    else:
        raise ValueError(f"Desteklenmeyen dosya formatı: {ext}")

def save_uploaded_file(file: UploadFile, content_type: ContentType) -> str:
    """
    Yüklenen dosyayı kaydeder.
    
    Args:
        file: Yüklenen dosya
        content_type: İçerik türü
        
    Returns:
        str: Kaydedilen dosyanın yolu
    """
    # Dosya adını normalize et ve benzersiz hale getir
    original_filename = file.filename or "unknown"
    ext = original_filename.split('.')[-1].lower() if '.' in original_filename else ''
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # İçerik türüne göre alt dizin
    sub_dir = content_type.value.lower() + 's'  # images, videos, audios
    
    # Dizin yapısını oluştur
    save_dir = os.path.join(config.multimodal.storage_path, sub_dir)
    os.makedirs(save_dir, exist_ok=True)
    
    # Tam dosya yolu
    file_path = os.path.join(save_dir, unique_filename)
    
    # Dosyayı kaydet
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return file_path

# Endpoints
@router.post("/upload", response_model=UploadResponse)
@resource_aware(throttle_on_high_load=True)
async def upload_multimodal_content(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    current_user: User = Depends(get_current_active_user)
):
    """
    Multimodal içerik (görüntü, video, ses) yükler.
    
    Args:
        file: Yüklenecek dosya
        title: İçerik başlığı (opsiyonel)
        description: İçerik açıklaması (opsiyonel)
        tags: Virgülle ayrılmış etiketler (opsiyonel)
        
    Returns:
        UploadResponse: Yükleme işlemi başarılı olursa yanıt
    """
    try:
        # Dosya boyutunu kontrol et
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dosya adı belirtilmemiş"
            )
        
        # İçerik türünü belirle ve kontrol et
        try:
            content_type = get_content_type(file.filename)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        
        # Dosya boyutunu kontrol et
        file_size_mb = 0
        file.file.seek(0, os.SEEK_END)
        file_size_mb = file.file.tell() / (1024 * 1024)
        file.file.seek(0)
        
        # İçerik türüne göre boyut sınırını kontrol et
        max_size_mb = 0
        if content_type == ContentType.IMAGE:
            max_size_mb = config.multimodal.max_image_size_mb
        elif content_type == ContentType.VIDEO:
            max_size_mb = config.multimodal.max_video_size_mb
        elif content_type == ContentType.AUDIO:
            max_size_mb = config.multimodal.max_audio_size_mb
        
        if file_size_mb > max_size_mb:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{content_type.value} dosyası çok büyük. Maksimum: {max_size_mb}MB"
            )
        
        # Dosyayı kaydet
        file_path = save_uploaded_file(file, content_type)
        
        # Multimodal işleyiciyi başlat
        processor = MultimodalProcessor()
        
        # Metadata oluştur
        metadata = {
            "title": title or file.filename,
            "description": description or "",
            "tags": tags.split(',') if tags else [],
            "original_filename": file.filename,
            "file_size_mb": file_size_mb,
            "upload_date": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # İçeriği işle ve veritabanına kaydet
        content_id = processor.process_and_store(
            file_path=file_path,
            content_type=content_type,
            user_id=current_user.id,
            metadata=metadata
        )
        
        # Arka planda analiz et
        background_tasks.add_task(
            processor.analyze_content,
            content_id=content_id,
            content_type=content_type
        )
        
        return {
            "content_id": content_id,
            "content_type": content_type.value,
            "filename": file.filename,
            "metadata": metadata,
            "message": f"{content_type.value} başarıyla yüklendi ve işleniyor."
        }
        
    except Exception as e:
        logging.error(f"Multimodal içerik yükleme hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"İçerik yüklenirken bir hata oluştu: {str(e)}"
        )

@router.get("/images", response_model=Dict[str, Any])
async def list_images(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının yüklediği görüntüleri listeler.
    
    Args:
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Görüntü listesi ve meta veriler
    """
    processor = MultimodalProcessor()
    
    result = processor.list_contents(
        content_type=ContentType.IMAGE,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    return result

@router.get("/videos", response_model=Dict[str, Any])
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının yüklediği videoları listeler.
    
    Args:
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Video listesi ve meta veriler
    """
    processor = MultimodalProcessor()
    
    result = processor.list_contents(
        content_type=ContentType.VIDEO,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    return result

@router.get("/audios", response_model=Dict[str, Any])
async def list_audios(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının yüklediği ses dosyalarını listeler.
    
    Args:
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Ses dosyası listesi ve meta veriler
    """
    processor = MultimodalProcessor()
    
    result = processor.list_contents(
        content_type=ContentType.AUDIO,
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    return result

@router.get("/{content_id}", response_model=MultimodalContent)
async def get_content(
    content_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir multimodal içeriğin detaylarını getirir.
    
    Args:
        content_id: İçerik ID'si
        
    Returns:
        MultimodalContent: İçerik detayları
    """
    processor = MultimodalProcessor()
    
    content = processor.get_content(content_id)
    
    # İçerik bulunamadıysa
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İçerik bulunamadı"
        )
    
    # Erişim kontrolü
    if content.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu içeriğe erişim izniniz yok"
        )
    
    return content

@router.delete("/{content_id}")
async def delete_content(
    content_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir multimodal içeriği siler.
    
    Args:
        content_id: İçerik ID'si
        
    Returns:
        Dict[str, str]: Silme işlemi başarılı olursa yanıt
    """
    processor = MultimodalProcessor()
    
    # İçeriğin mevcut olup olmadığını kontrol et
    content = processor.get_content(content_id)
    
    # İçerik bulunamadıysa
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İçerik bulunamadı"
        )
    
    # Erişim kontrolü
    if content.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu içeriği silme izniniz yok"
        )
    
    # İçeriği sil
    result = processor.delete_content(content_id)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="İçerik silinirken bir hata oluştu"
        )
    
    return {"message": "İçerik başarıyla silindi"}

@router.post("/search", response_model=Dict[str, Any])
@limit_cpu(max_processes=6)
@resource_aware()
async def search_multimodal(
    query: MultimodalSearchQuery,
    current_user: User = Depends(get_current_active_user)
):
    """
    Multimodal içeriklerde arama yapar.
    Metin veya görüntü tabanlı arama desteklenir.
    
    Args:
        query: Arama sorgusu
        
    Returns:
        Dict[str, Any]: Arama sonuçları
    """
    # En az bir sorgu türü gerekli
    if not query.query_text and not query.query_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Metin veya görüntü sorgusu gereklidir"
        )
    
    processor = MultimodalProcessor()
    
    # Metin tabanlı arama
    if query.query_text:
        results = processor.search_by_text(
            query_text=query.query_text,
            user_id=current_user.id,
            limit=query.limit or 20,
            filter_dict=query.filter
        )
    # Görüntü tabanlı arama
    elif query.query_image:
        results = processor.search_by_image(
            image_id=query.query_image,
            user_id=current_user.id,
            limit=query.limit or 20,
            filter_dict=query.filter
        )
    
    return {
        "results": results,
        "count": len(results)
    }

@router.post("/{content_id}/analyze")
@limit_cpu(max_processes=2)
async def analyze_content(
    content_id: str,
    force: bool = Query(False),
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir multimodal içeriğin yeniden analiz edilmesini sağlar.
    
    Args:
        content_id: İçerik ID'si
        force: Mevcut analiz sonuçlarını geçersiz kılarak zorla yeniden analiz yapar
        
    Returns:
        Dict[str, str]: Analiz işlemi başarılı olursa yanıt
    """
    processor = MultimodalProcessor()
    
    # İçeriğin mevcut olup olmadığını kontrol et
    content = processor.get_content(content_id)
    
    # İçerik bulunamadıysa
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="İçerik bulunamadı"
        )
    
    # Erişim kontrolü
    if content.get("user_id") != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu içeriği analiz etme izniniz yok"
        )
    
    # İçeriği analiz et
    try:
        content_type = ContentType(content.get("content_type", "unknown"))
        result = processor.analyze_content(
            content_id=content_id,
            content_type=content_type,
            force=force
        )
        
        return {"message": "İçerik analizi başarıyla tamamlandı", "result": result}
    except Exception as e:
        logging.error(f"İçerik analiz hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"İçerik analiz edilirken bir hata oluştu: {str(e)}"
        )