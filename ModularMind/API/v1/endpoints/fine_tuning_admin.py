from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status, Body, Path

from ModularMind.API.core.auth import get_current_active_user
from ModularMind.API.models.user import User, UserRole
from ModularMind.API.models.fine_tuning import (
    FineTuningJob,
    FineTuningStatus,
    FineTuningModelType,
    FineTunedModel,
    ValidationResult
)
from ModularMind.API.services.fine_tuning_service import FineTuningService

router = APIRouter(prefix="/fine-tuning", tags=["fine-tuning"])

def check_admin_access(current_user: User = Depends(get_current_active_user)):
    """Admin erişimi kontrol eden bağımlılık."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint için admin erişimi gereklidir"
        )
    return current_user

@router.post("/jobs")
async def create_fine_tuning_job(
    name: str = Body(...),
    model_id: str = Body(...),
    model_type: FineTuningModelType = Body(...),
    training_file_ids: List[str] = Body(...),
    validation_file_id: Optional[str] = Body(None),
    description: Optional[str] = Body(None),
    hyperparameters: Optional[Dict[str, Any]] = Body(None),
    tags: Optional[List[str]] = Body(None),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Yeni bir fine-tuning işi oluşturur.
    """
    # Fine-tuning servisi oluştur
    fine_tuning_service = FineTuningService()
    
    # İş verilerini oluştur
    job_data = {
        "user_id": current_user.id,
        "name": name,
        "model_id": model_id,
        "model_type": model_type,
        "training_file_ids": training_file_ids,
        "validation_file_id": validation_file_id,
        "description": description,
        "hyperparameters": hyperparameters or {},
        "tags": tags or []
    }
    
    # İşi oluştur
    job_id = fine_tuning_service.create_job(job_data)
    
    return {
        "job_id": job_id,
        "message": "Fine-tuning işi başarıyla oluşturuldu"
    }

@router.get("/jobs/{job_id}")
async def get_fine_tuning_job(
    job_id: str = Path(...),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Belirli bir fine-tuning işinin detaylarını getirir.
    """
    fine_tuning_service = FineTuningService()
    
    # İşi getir
    job = fine_tuning_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuning işi bulunamadı"
        )
    
    # Erişim kontrolü
    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu fine-tuning işine erişim izniniz yok"
        )
    
    return job.dict()

@router.get("/jobs")
async def list_fine_tuning_jobs(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Kullanıcının fine-tuning işlerini listeler.
    """
    fine_tuning_service = FineTuningService()
    
    # Durum filtresi
    status_filter = None
    if status:
        try:
            status_filter = FineTuningStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz durum: {status}"
            )
    
    # İşleri getir
    jobs = fine_tuning_service.list_jobs(
        user_id=current_user.id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    
    # Toplam sayıyı al
    total_count = fine_tuning_service.count_jobs(
        user_id=current_user.id,
        status=status_filter
    )
    
    # Yanıtı oluştur
    job_dicts = [job.dict() for job in jobs]
    
    return {
        "jobs": job_dicts,
        "total_count": total_count,
        "page": skip // limit + 1,
        "page_size": limit
    }

@router.post("/jobs/{job_id}/cancel")
async def cancel_fine_tuning_job(
    job_id: str = Path(...),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Bir fine-tuning işini iptal eder.
    """
    fine_tuning_service = FineTuningService()
    
    # İşi getir
    job = fine_tuning_service.get_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuning işi bulunamadı"
        )
    
    # Erişim kontrolü
    if job.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu fine-tuning işini iptal etme izniniz yok"
        )
    
    # İşi iptal et
    success = fine_tuning_service.cancel_job(job_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fine-tuning işi iptal edilemedi"
        )
    
    return {
        "message": "Fine-tuning işi başarıyla iptal edildi"
    }

@router.get("/models")
async def list_fine_tuned_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Kullanıcının fine-tuned modellerini listeler.
    """
    fine_tuning_service = FineTuningService()
    
    # Modelleri getir
    models = fine_tuning_service.list_fine_tuned_models(
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    
    # Yanıtı oluştur
    model_dicts = [model.dict() for model in models]
    
    return {
        "models": model_dicts,
        "total_count": len(model_dicts),
        "page": skip // limit + 1,
        "page_size": limit
    }

@router.get("/models/{model_id}")
async def get_fine_tuned_model(
    model_id: str = Path(...),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Belirli bir fine-tuned modelin detaylarını getirir.
    """
    fine_tuning_service = FineTuningService()
    
    # Modeli getir
    model = fine_tuning_service.get_fine_tuned_model(model_id)
    
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine-tuned model bulunamadı"
        )
    
    # Erişim kontrolü
    if model.user_id != current_user.id and current_user.role != UserRole.ADMIN and not model.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu fine-tuned modele erişim izniniz yok"
        )
    
    return model.dict()

@router.get("/admin/all-jobs", dependencies=[Depends(check_admin_access)])
async def admin_list_all_jobs(
    user_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Tüm fine-tuning işlerini listeler (sadece admin).
    """
    fine_tuning_service = FineTuningService()
    
    # Durum filtresi
    status_filter = None
    if status:
        try:
            status_filter = FineTuningStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz durum: {status}"
            )
    
    # İşleri getir
    jobs = fine_tuning_service.list_jobs(
        user_id=user_id or current_user.id,
        status=status_filter,
        skip=skip,
        limit=limit
    )
    
    # Toplam sayıyı al
    total_count = fine_tuning_service.count_jobs(
        user_id=user_id or current_user.id,
        status=status_filter
    )
    
    # Yanıtı oluştur
    job_dicts = [job.dict() for job in jobs]
    
    return {
        "jobs": job_dicts,
        "total_count": total_count,
        "page": skip // limit + 1,
        "page_size": limit
    }