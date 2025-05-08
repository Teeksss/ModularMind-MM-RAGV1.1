"""
ModularMind API için fine-tuning endpointleri.
Model ince ayarı (fine-tuning) işlerinin oluşturulması, izlenmesi ve yönetilmesi için API'ler sağlar.
"""

import os
import time
import logging
import uuid
import json
from typing import List, Dict, Any, Optional, Union
from fastapi import APIRouter, Depends, File, Form, UploadFile, Query, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, validator

from ModularMind.API.models.user import User, UserRole
from ModularMind.API.core.auth import get_current_active_user
from ModularMind.config import config
from ModularMind.API.core.resource_manager import resource_aware
from ModularMind.API.services.fine_tuning_service import FineTuningService, FineTuningJobStatus, ModelType

router = APIRouter(prefix="/fine-tuning", tags=["fine-tuning"])

# Modeller
class FineTuningHyperparameters(BaseModel):
    """Fine-tuning hiperparametreleri."""
    learning_rate: Optional[float] = 0.001
    batch_size: Optional[int] = 4
    num_epochs: Optional[int] = 3
    warmup_steps: Optional[int] = 0
    weight_decay: Optional[float] = 0.01
    max_grad_norm: Optional[float] = 1.0

class CreateJobRequest(BaseModel):
    """Fine-tuning işi oluşturma isteği."""
    name: str
    model_id: str
    model_type: ModelType
    training_file_ids: List[str]
    validation_file_id: Optional[str] = None
    description: Optional[str] = None
    hyperparameters: Optional[FineTuningHyperparameters] = None
    tags: Optional[List[str]] = None
    
    @validator('name')
    def name_must_be_valid(cls, v):
        if not v or len(v) < 3:
            raise ValueError('İş adı en az 3 karakter olmalıdır')
        if len(v) > 64:
            raise ValueError('İş adı en fazla 64 karakter olmalıdır')
        return v
    
    @validator('training_file_ids')
    def must_have_training_files(cls, v):
        if not v or len(v) == 0:
            raise ValueError('En az bir eğitim dosyası gereklidir')
        return v

class JobResponse(BaseModel):
    """Fine-tuning işi yanıtı."""
    job_id: str
    message: str

class FineTuningJob(BaseModel):
    """Fine-tuning işi modeli."""
    id: str
    name: str
    description: Optional[str] = None
    model_id: str
    model_type: str
    status: str
    training_file_ids: List[str]
    validation_file_id: Optional[str] = None
    hyperparameters: Dict[str, Any]
    result_model_id: Optional[str] = None
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    validation_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    progress: int = 0
    tags: List[str] = []
    user_id: str

class FineTunedModel(BaseModel):
    """İnce ayarlanmış (fine-tuned) model modeli."""
    id: str
    user_id: str
    job_id: str
    name: str
    description: Optional[str] = None
    base_model_id: str
    model_type: str
    status: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    tags: List[str] = []
    is_public: bool = False
    usage_count: int = 0
    last_used_at: Optional[str] = None

# Fine-tuning API endpointleri
@router.post("/jobs", response_model=JobResponse)
@resource_aware(throttle_on_high_load=True)
async def create_fine_tuning_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user)
):
    """
    Yeni bir fine-tuning işi oluşturur.
    
    Args:
        request: Fine-tuning işi oluşturma isteği
        
    Returns:
        JobResponse: İşlem başarılı olursa yanıt
    """
    service = FineTuningService()
    
    # Kullanıcının aktif fine-tuning işlerinin sayısını kontrol et
    active_jobs = service.count_active_jobs(current_user.id)
    
    if active_jobs >= config.fine_tuning.max_jobs_per_user:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Maksimum aktif iş sayısına ulaştınız ({config.fine_tuning.max_jobs_per_user})"
        )
    
    # Eğitim dosyalarının varlığını kontrol et
    for file_id in request.training_file_ids:
        if not service.check_file_exists(file_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Eğitim dosyası bulunamadı: {file_id}"
            )
    
    # Doğrulama dosyasının varlığını kontrol et (varsa)
    if request.validation_file_id and not service.check_file_exists(request.validation_file_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doğrulama dosyası bulunamadı: {request.validation_file_id}"
        )
    
    # İşi oluştur
    try:
        # Hiperparametreleri hazırla
        hyperparameters = request.hyperparameters.dict() if request.hyperparameters else {}
        
        # Yeni iş oluştur
        job_id = service.create_job(
            name=request.name,
            model_id=request.model_id,
            model_type=request.model_type,
            training_file_ids=request.training_file_ids,
            validation_file_id=request.validation_file_id,
            description=request.description,
            hyperparameters=hyperparameters,
            tags=request.tags,
            user_id=current_user.id
        )
        
        # Arka planda işi başlat
        background_tasks.add_task(
            service.start_job_pipeline,
            job_id=job_id
        )
        
        return {
            "job_id": job_id,
            "message": "Fine-tuning işi başarıyla oluşturuldu ve başlatıldı"
        }
    
    except Exception as e:
        logging.error(f"Fine-tuning işi oluşturma hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fine-tuning işi oluşturulurken bir hata oluştu: {str(e)}"
        )

@router.get("/jobs", response_model=Dict[str, Any])
async def list_jobs(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının fine-tuning işlerini listeler.
    
    Args:
        status: Filtrelenecek durum (opsiyonel)
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Fine-tuning işlerinin listesi ve meta veriler
    """
    service = FineTuningService()
    
    # Status değerini doğrula
    if status:
        try:
            FineTuningJobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz durum değeri: {status}. Geçerli değerler: {[s.value for s in FineTuningJobStatus]}"
            )
    
    # İşleri getir
    jobs, total_count = service.list_jobs(
        user_id=current_user.id,
        status=status,
        page=page,
        page_size=page_size
    )
    
    return {
        "jobs": jobs,
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }

@router.get("/jobs/{job_id}", response_model=FineTuningJob)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir fine-tuning işinin detaylarını getirir.
    
    Args:
        job_id: Fine-tuning işi ID'si
        
    Returns:
        FineTuningJob: Fine-tuning işi detayları
    """
    service = FineTuningService()
    
    # İşi getir
    job = service.get_job(job_id)
    
    # İş bulunamadıysa
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuning işi bulunamadı"
        )
    
    # Erişim kontrolü
    if job.get("user_id") != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu fine-tuning işine erişim izniniz yok"
        )
    
    return job

@router.post("/jobs/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir fine-tuning işini iptal eder.
    
    Args:
        job_id: Fine-tuning işi ID'si
        
    Returns:
        Dict[str, str]: İşlem başarılı olursa yanıt
    """
    service = FineTuningService()
    
    # İşi getir
    job = service.get_job(job_id)
    
    # İş bulunamadıysa
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuning işi bulunamadı"
        )
    
    # Erişim kontrolü
    if job.get("user_id") != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu fine-tuning işini iptal etme izniniz yok"
        )
    
    # İşin iptal edilebilir durumda olup olmadığını kontrol et
    cancellable_statuses = [
        FineTuningJobStatus.PENDING.value,
        FineTuningJobStatus.PREPARING.value,
        FineTuningJobStatus.TRAINING.value
    ]
    
    if job.get("status") not in cancellable_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bu iş iptal edilemez. Mevcut durum: {job.get('status')}"
        )
    
    # İşi iptal et
    success = service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fine-tuning işi iptal edilirken bir hata oluştu"
        )
    
    return {"message": "Fine-tuning işi başarıyla iptal edildi"}

@router.get("/models", response_model=Dict[str, Any])
async def list_models(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının fine-tuned modellerini listeler.
    
    Args:
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Fine-tuned modellerin listesi ve meta veriler
    """
    service = FineTuningService()
    
    # Modelleri getir
    models, total_count = service.list_models(
        user_id=current_user.id,
        page=page,
        page_size=page_size
    )
    
    return {
        "models": models,
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }

@router.get("/models/{model_id}", response_model=FineTunedModel)
async def get_model(
    model_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir fine-tuned modelin detaylarını getirir.
    
    Args:
        model_id: Fine-tuned model ID'si
        
    Returns:
        FineTunedModel: Fine-tuned model detayları
    """
    service = FineTuningService()
    
    # Modeli getir
    model = service.get_model(model_id)
    
    # Model bulunamadıysa
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuned model bulunamadı"
        )
    
    # Erişim kontrolü
    if not model.get("is_public"):
        if model.get("user_id") != current_user.id and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu fine-tuned modele erişim izniniz yok"
            )
    
    return model

@router.post("/upload-file")
@resource_aware(throttle_on_high_load=True)
async def upload_training_file(
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    purpose: str = Form(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Fine-tuning için eğitim veya doğrulama dosyası yükler.
    
    Args:
        file: Yüklenecek dosya
        description: Dosya açıklaması (opsiyonel)
        purpose: Dosya amacı ("training" veya "validation")
        
    Returns:
        Dict[str, Any]: Yükleme işlemi başarılı olursa yanıt
    """
    service = FineTuningService()
    
    # Dosya formatını kontrol et
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya adı belirtilmemiş"
        )
    
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    
    if ext not in config.fine_tuning.supported_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Desteklenmeyen dosya formatı: {ext}. Desteklenen formatlar: {config.fine_tuning.supported_formats}"
        )
    
    # Dosya amacını kontrol et
    if purpose not in ["training", "validation"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya amacı 'training' veya 'validation' olmalıdır"
        )
    
    # Dosya boyutunu kontrol et
    file.file.seek(0, os.SEEK_END)
    file_size_mb = file.file.tell() / (1024 * 1024)
    file.file.seek(0)
    
    if file_size_mb > config.fine_tuning.max_dataset_size_mb:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dosya çok büyük. Maksimum: {config.fine_tuning.max_dataset_size_mb}MB"
        )
    
    try:
        # Dosya içeriğini yükle
        file_content = await file.read()
        
        # Dosya formatını doğrula
        valid, error_message = service.validate_file_format(file_content, ext)
        
        if not valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz dosya formatı: {error_message}"
            )
        
        # Dosyayı kaydet
        file_id = service.save_file(
            filename=file.filename,
            content=file_content,
            purpose=purpose,
            user_id=current_user.id,
            description=description
        )
        
        return {
            "file_id": file_id,
            "filename": file.filename,
            "purpose": purpose,
            "size_mb": file_size_mb,
            "message": "Dosya başarıyla yüklendi"
        }
    
    except Exception as e:
        logging.error(f"Fine-tuning dosya yükleme hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dosya yüklenirken bir hata oluştu: {str(e)}"
        )

@router.get("/files", response_model=Dict[str, Any])
async def list_files(
    purpose: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Kullanıcının fine-tuning dosyalarını listeler.
    
    Args:
        purpose: Filtrelenecek dosya amacı (opsiyonel)
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Dosyaların listesi ve meta veriler
    """
    service = FineTuningService()
    
    # Amacı doğrula
    if purpose and purpose not in ["training", "validation"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dosya amacı 'training' veya 'validation' olmalıdır"
        )
    
    # Dosyaları getir
    files, total_count = service.list_files(
        user_id=current_user.id,
        purpose=purpose,
        page=page,
        page_size=page_size
    )
    
    return {
        "files": files,
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }

@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Belirli bir fine-tuning dosyasını siler.
    
    Args:
        file_id: Dosya ID'si
        
    Returns:
        Dict[str, str]: İşlem başarılı olursa yanıt
    """
    service = FineTuningService()
    
    # Dosyanın mevcut olup olmadığını kontrol et
    file = service.get_file(file_id)
    
    # Dosya bulunamadıysa
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dosya bulunamadı"
        )
    
    # Erişim kontrolü
    if file.get("user_id") != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu dosyayı silme izniniz yok"
        )
    
    # Dosyayı sil
    success = service.delete_file(file_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Dosya silinirken bir hata oluştu"
        )
    
    return {"message": "Dosya başarıyla silindi"}

# Admin endpoints
@router.get("/admin/all-jobs", response_model=Dict[str, Any])
async def admin_list_all_jobs(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
):
    """
    Tüm fine-tuning işlerini listeler (yalnızca admin kullanıcılar için).
    
    Args:
        user_id: Filtrelenecek kullanıcı ID'si (opsiyonel)
        status: Filtrelenecek durum (opsiyonel)
        page: Sayfa numarası
        page_size: Sayfa başına öğe sayısı
        
    Returns:
        Dict[str, Any]: Fine-tuning işlerinin listesi ve meta veriler
    """
    # Admin yetkisi kontrolü
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint'e erişim için admin yetkisi gereklidir"
        )
    
    service = FineTuningService()
    
    # Status değerini doğrula
    if status:
        try:
            FineTuningJobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz durum değeri: {status}. Geçerli değerler: {[s.value for s in FineTuningJobStatus]}"
            )
    
    # İşleri getir
    jobs, total_count = service.list_jobs(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
        admin_mode=True
    )
    
    return {
        "jobs": jobs,
        "total_count": total_count,
        "page": page,
        "page_size": page_size
    }