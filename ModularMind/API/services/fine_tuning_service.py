"""
Model fine-tuning servisi.
LLM modellerinin özel veri setleri ile fine-tuning işlemlerini yönetir.
"""

import os
import time
import logging
import json
import uuid
import shutil
import asyncio
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union, BinaryIO
import traceback
import threading

logger = logging.getLogger(__name__)

class ModelType(str, Enum):
    """Model türleri."""
    BASE_LLM = "base_llm"
    CHAT = "chat"
    INSTRUCTION = "instruction"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"

class FineTuningJobStatus(str, Enum):
    """Fine-tuning iş durumları."""
    PENDING = "pending"          # İş oluşturuldu, henüz başlatılmadı
    PREPARING = "preparing"      # Veriler hazırlanıyor
    VALIDATING = "validating"    # Veriler doğrulanıyor
    TRAINING = "training"        # Eğitim sürüyor
    EVALUATING = "evaluating"    # Model değerlendiriliyor
    COMPLETED = "completed"      # İş başarıyla tamamlandı
    CANCELLED = "cancelled"      # İş kullanıcı tarafından iptal edildi
    FAILED = "failed"            # İş başarısız oldu
    STOPPED = "stopped"          # İş sistem tarafından durduruldu

class FineTuningService:
    """
    Model fine-tuning servis sınıfı.
    """
    
    def __init__(self, db_manager=None):
        """
        Initialize the fine-tuning service.
        
        Args:
            db_manager: Veritabanı yöneticisi (opsiyonel)
        """
        # Veritabanı bağlantısı
        if db_manager:
            self.db_manager = db_manager
        else:
            # Varsayılan veritabanı bağlantısını kullan
            from ModularMind.API.db.base import DatabaseManager
            self.db_manager = DatabaseManager()
        
        self.db = self.db_manager.get_database()
        
        # Koleksiyonlar
        self.jobs_collection = self.db["fine_tuning_jobs"]
        self.models_collection = self.db["fine_tuned_models"]
        self.files_collection = self.db["fine_tuning_files"]
        
        # Depolama yolları
        self.storage_root = os.getenv("FINETUNE_STORAGE_PATH", "finetune_data")
        self.dataset_dir = os.path.join(self.storage_root, "datasets")
        self.model_dir = os.path.join(self.storage_root, "models")
        
        # Dizinleri oluştur
        os.makedirs(self.dataset_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        
        # Aktif iş sayısı
        self.active_jobs_count = 0
        self.active_jobs_lock = threading.Lock()
        
        # İndeksler oluştur
        self._create_indexes()
        
        # Model servisi (lazily loaded)
        self._model_service = None
    
    def _create_indexes(self):
        """Veritabanı indekslerini oluştur."""
        try:
            # İş koleksiyonu indeksleri
            self.jobs_collection.create_index("user_id")
            self.jobs_collection.create_index("status")
            self.jobs_collection.create_index([("user_id", 1), ("status", 1)])
            self.jobs_collection.create_index("created_at")
            
            # Model koleksiyonu indeksleri
            self.models_collection.create_index("user_id")
            self.models_collection.create_index("job_id")
            self.models_collection.create_index([("user_id", 1), ("model_type", 1)])
            
            # Dosya koleksiyonu indeksleri
            self.files_collection.create_index("user_id")
            self.files_collection.create_index([("user_id", 1), ("purpose", 1)])
            
            logger.info("Fine-tuning veritabanı indeksleri başarıyla oluşturuldu")
        except Exception as e:
            logger.error(f"Veritabanı indeksleri oluşturulurken hata: {str(e)}")
    
    def _get_model_service(self):
        """
        Model servisine lazy erişim.
        
        Returns:
            Model servisi
        """
        if not self._model_service:
            # Circular import'u önlemek için lazy import
            from ModularMind.API.services.model_service import ModelService
            self._model_service = ModelService()
        
        return self._model_service
    
    def create_job(self, name: str, model_id: str, model_type: ModelType, 
                  training_file_ids: List[str], user_id: str,
                  validation_file_id: Optional[str] = None, 
                  description: Optional[str] = None,
                  hyperparameters: Optional[Dict[str, Any]] = None,
                  tags: Optional[List[str]] = None) -> str:
        """
        Yeni bir fine-tuning işi oluşturur.
        
        Args:
            name: İş adı
            model_id: Temel model ID'si
            model_type: Model türü
            training_file_ids: Eğitim dosyası ID'leri
            user_id: Kullanıcı ID'si
            validation_file_id: Doğrulama dosyası ID'si (opsiyonel)
            description: İş açıklaması (opsiyonel)
            hyperparameters: Hiperparametreler (opsiyonel)
            tags: Etiketler (opsiyonel)
            
        Returns:
            str: İş ID'si
        """
        # İş ID'si oluştur
        job_id = str(uuid.uuid4())
        
        # Hiperparametreleri varsayılan değerlerle doldur
        default_hyperparameters = {
            "learning_rate": 0.001,
            "batch_size": 4,
            "num_epochs": 3,
            "warmup_steps": 0,
            "weight_decay": 0.01,
            "max_grad_norm": 1.0
        }
        
        if hyperparameters:
            default_hyperparameters.update(hyperparameters)
        
        # Oluşturma zamanı
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # İş verilerini oluştur
        job_data = {
            "id": job_id,
            "name": name,
            "description": description,
            "model_id": model_id,
            "model_type": model_type if isinstance(model_type, str) else model_type.value,
            "status": FineTuningJobStatus.PENDING.value,
            "training_file_ids": training_file_ids,
            "validation_file_id": validation_file_id,
            "hyperparameters": default_hyperparameters,
            "result_model_id": None,
            "created_at": current_time,
            "updated_at": current_time,
            "started_at": None,
            "finished_at": None,
            "validation_result": None,
            "error_message": None,
            "progress": 0,
            "tags": tags or [],
            "user_id": user_id
        }
        
        # İşi veritabanına kaydet
        self.jobs_collection.insert_one(job_data)
        logger.info(f"Fine-tuning işi oluşturuldu: {job_id}")
        
        return job_id
    
    def count_active_jobs(self, user_id: str) -> int:
        """
        Kullanıcının aktif iş sayısını döndürür.
        
        Args:
            user_id: Kullanıcı ID'si
            
        Returns:
            int: Aktif iş sayısı
        """
        # Aktif statüler
        active_statuses = [
            FineTuningJobStatus.PENDING.value,
            FineTuningJobStatus.PREPARING.value,
            FineTuningJobStatus.VALIDATING.value,
            FineTuningJobStatus.TRAINING.value,
            FineTuningJobStatus.EVALUATING.value
        ]
        
        # Aktif iş sayısını sorgula
        count = self.jobs_collection.count_documents({
            "user_id": user_id,
            "status": {"$in": active_statuses}
        })
        
        return count
    
    async def start_job_pipeline(self, job_id: str) -> bool:
        """
        Fine-tuning iş pipeline'ını başlatır.
        
        Args:
            job_id: İş ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        try:
            # İşi al
            job = self.get_job(job_id)
            
            if not job:
                logger.error(f"İş bulunamadı: {job_id}")
                return False
            
            # İşi başlat
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            self.jobs_collection.update_one(
                {"id": job_id},
                {"$set": {
                    "status": FineTuningJobStatus.PREPARING.value,
                    "updated_at": current_time,
                    "started_at": current_time
                }}
            )
            
            # Aktif iş sayısını kontrol et
            with self.active_jobs_lock:
                # Maksimum aktif iş sayısını aşmışsa bekle
                from ModularMind.config import config
                max_concurrent_jobs = config.fine_tuning.max_concurrent_jobs
                
                if self.active_jobs_count >= max_concurrent_jobs:
                    logger.info(f"Maksimum aktif iş sayısına ulaşıldı ({max_concurrent_jobs}). İş beklemede: {job_id}")
                    
                    # İşi beklemede olarak işaretle
                    self.jobs_collection.update_one(
                        {"id": job_id},
                        {"$set": {
                            "status": FineTuningJobStatus.PENDING.value,
                            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }}
                    )
                    
                    return True
                
                # Aktif iş sayısını artır
                self.active_jobs_count += 1
            
            # İş pipeline adımlarını çalıştır
            try:
                # 1. Verileri hazırla
                await self._prepare_data(job_id)
                
                # 2. Verileri doğrula
                await self._validate_data(job_id)
                
                # 3. Modeli eğit
                await self._train_model(job_id)
                
                # 4. Modeli değerlendir
                await self._evaluate_model(job_id)
                
                # 5. İşi tamamla
                await self._complete_job(job_id)
                
                return True
            
            except asyncio.CancelledError:
                # İş iptal edildi
                logger.warning(f"İş iptal edildi: {job_id}")
                await self._fail_job(job_id, "İş kullanıcı tarafından iptal edildi", cancelled=True)
                return False
            
            except Exception as e:
                # İş başarısız oldu
                logger.error(f"İş pipeline hatası: {job_id}, {str(e)}", exc_info=True)
                await self._fail_job(job_id, f"Pipeline hatası: {str(e)}")
                return False
            
            finally:
                # Aktif iş sayısını azalt
                with self.active_jobs_lock:
                    self.active_jobs_count -= 1
                    
                # Bekleyen diğer işleri kontrol et ve başlat
                self._start_pending_job()
        
        except Exception as e:
            logger.error(f"İş başlatma hatası: {str(e)}", exc_info=True)
            await self._fail_job(job_id, f"İş başlatma hatası: {str(e)}")
            return False
    
    def _start_pending_job(self):
        """
        Bekleyen işlerden birini başlat.
        """
        try:
            # Bekleyen ilk işi al
            pending_job = self.jobs_collection.find_one({
                "status": FineTuningJobStatus.PENDING.value
            }, sort=[("created_at", 1)])
            
            if pending_job:
                job_id = pending_job["id"]
                logger.info(f"Bekleyen iş başlatılıyor: {job_id}")
                
                # İş pipeline'ını asenkron olarak başlat
                asyncio.create_task(self.start_job_pipeline(job_id))
        
        except Exception as e:
            logger.error(f"Bekleyen iş başlatma hatası: {str(e)}")
    
    async def _prepare_data(self, job_id: str):
        """
        Fine-tuning için verileri hazırla.
        
        Args:
            job_id: İş ID'si
        """
        logger.info(f"Veriler hazırlanıyor: {job_id}")
        
        # İş durumunu güncelle
        self._update_job_status(job_id, FineTuningJobStatus.PREPARING, progress=10)
        
        # İşi al
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"İş bulunamadı: {job_id}")
        
        # Eğitim dosyalarını kontrol et
        training_files = []
        for file_id in job["training_file_ids"]:
            file_data = self._get_file_data(file_id)
            if not file_data:
                raise ValueError(f"Eğitim dosyası bulunamadı: {file_id}")
            training_files.append(file_data)
        
        # Doğrulama dosyasını kontrol et (varsa)
        validation_file = None
        if job.get("validation_file_id"):
            validation_file = self._get_file_data(job["validation_file_id"])
            if not validation_file:
                raise ValueError(f"Doğrulama dosyası bulunamadı: {job.get('validation_file_id')}")
        
        # İş dizinini oluştur
        job_dir = os.path.join(self.dataset_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        # İlerlemeyi güncelle
        await asyncio.sleep(1)  # Gerçek uygulamada işlem süresi daha uzun olacaktır
        self._update_job_status(job_id, FineTuningJobStatus.PREPARING, progress=30)
    
    async def _validate_data(self, job_id: str):
        """
        Fine-tuning verilerini doğrula.
        
        Args:
            job_id: İş ID'si
        """
        logger.info(f"Veriler doğrulanıyor: {job_id}")
        
        # İş durumunu güncelle
        self._update_job_status(job_id, FineTuningJobStatus.VALIDATING, progress=40)
        
        # Gerçek validasyon işlemini burada yapın
        # Bu örnek implementasyonda sadece bekleme yapıyoruz
        await asyncio.sleep(2)  # Gerçek uygulamada veri doğrulama süresi
        
        # İlerlemeyi güncelle
        self._update_job_status(job_id, FineTuningJobStatus.VALIDATING, progress=50)
    
    async def _train_model(self, job_id: str):
        """
        Modeli eğit.
        
        Args:
            job_id: İş ID'si
        """
        logger.info(f"Model eğitiliyor: {job_id}")
        
        # İş durumunu güncelle
        self._update_job_status(job_id, FineTuningJobStatus.TRAINING, progress=60)
        
        # İşi al
        job = self.get_job(job_id)
        
        # Eğitim işlemi başlatılır
        # Bu örnek implementasyonda sadece bekleme yapıyoruz
        total_epochs = job["hyperparameters"].get("num_epochs", 3)
        
        for epoch in range(total_epochs):
            # İptal kontrolü
            updated_job = self.get_job(job_id)
            if updated_job["status"] == FineTuningJobStatus.CANCELLED.value:
                raise asyncio.CancelledError("İş iptal edildi")
            
            # Eğitim epoch'u
            logger.info(f"Epoch {epoch+1}/{total_epochs} eğitiliyor: {job_id}")
            await asyncio.sleep(3)  # Gerçek uygulamada eğitim süresi daha uzun olacaktır
            
            # Her epoch sonunda ilerlemeyi güncelle
            progress = 60 + (epoch + 1) * (20 / total_epochs)
            self._update_job_status(job_id, FineTuningJobStatus.TRAINING, progress=int(progress))
    
    async def _evaluate_model(self, job_id: str):
        """
        Eğitilmiş modeli değerlendir.
        
        Args:
            job_id: İş ID'si
        """
        logger.info(f"Model değerlendiriliyor: {job_id}")
        
        # İş durumunu güncelle
        self._update_job_status(job_id, FineTuningJobStatus.EVALUATING, progress=85)
        
        # Değerlendirme işlemi
        # Bu örnek implementasyonda sadece bekleme yapıyoruz
        await asyncio.sleep(2)  # Gerçek uygulamada değerlendirme süresi daha uzun olacaktır
        
        # Örnek değerlendirme sonuçları
        validation_result = {
            "loss": 0.234,
            "accuracy": 0.892,
            "perplexity": 1.45,
            "samples_per_second": 24.5
        }
        
        # Değerlendirme sonuçlarını kaydet
        self.jobs_collection.update_one(
            {"id": job_id},
            {"$set": {
                "validation_result": validation_result,
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "progress": 95
            }}
        )
    
    async def _complete_job(self, job_id: str):
        """
        İşi tamamla ve sonuç modelini kaydet.
        
        Args:
            job_id: İş ID'si
        """
        logger.info(f"İş tamamlanıyor: {job_id}")
        
        # İşi al
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"İş bulunamadı: {job_id}")
        
        # Model ID'si oluştur
        model_id = str(uuid.uuid4())
        
        # Model verilerini oluştur
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        model_data = {
            "id": model_id,
            "user_id": job["user_id"],
            "job_id": job_id,
            "name": f"{job['name']} - {current_time}",
            "description": job.get("description"),
            "base_model_id": job["model_id"],
            "model_type": job["model_type"],
            "status": "ready",  # ready, archived
            "created_at": current_time,
            "updated_at": current_time,
            "metadata": {
                "training_file_count": len(job["training_file_ids"]),
                "hyperparameters": job["hyperparameters"]
            },
            "performance_metrics": job.get("validation_result", {}),
            "tags": job.get("tags", []),
            "is_public": False,
            "usage_count": 0,
            "last_used_at": None
        }
        
        # Modeli veritabanına kaydet
        self.models_collection.insert_one(model_data)
        
        # İşi güncelle
        self.jobs_collection.update_one(
            {"id": job_id},
            {"$set": {
                "status": FineTuningJobStatus.COMPLETED.value,
                "result_model_id": model_id,
                "finished_at": current_time,
                "updated_at": current_time,
                "progress": 100
            }}
        )
        
        logger.info(f"İş başarıyla tamamlandı: {job_id}, Model ID: {model_id}")
    
    async def _fail_job(self, job_id: str, error_message: str, cancelled: bool = False):
        """
        İşi başarısız olarak işaretle.
        
        Args:
            job_id: İş ID'si
            error_message: Hata mesajı
            cancelled: İptal edildi mi
        """
        status = FineTuningJobStatus.CANCELLED.value if cancelled else FineTuningJobStatus.FAILED.value
        
        self.jobs_collection.update_one(
            {"id": job_id},
            {"$set": {
                "status": status,
                "error_message": error_message,
                "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }}
        )
        
        if cancelled:
            logger.info(f"İş iptal edildi: {job_id}")
        else:
            logger.error(f"İş başarısız oldu: {job_id}, Hata: {error_message}")
    
    def _update_job_status(self, job_id: str, status: FineTuningJobStatus, progress: int = None):
        """
        İş durumunu güncelle.
        
        Args:
            job_id: İş ID'si
            status: Yeni durum
            progress: İlerleme yüzdesi (opsiyonel)
        """
        update_data = {
            "status": status.value,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        if progress is not None:
            update_data["progress"] = progress
        
        self.jobs_collection.update_one(
            {"id": job_id},
            {"$set": update_data}
        )
    
    def _get_file_data(self, file_id: str):
        """
        Dosya verilerini getir.
        
        Args:
            file_id: Dosya ID'si
        
        Returns:
            dict or None: Dosya verileri
        """
        file_data = self.files_collection.find_one({"id": file_id})
        if file_data and "_id" in file_data:
            del file_data["_id"]
        return file_data
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        İş detaylarını getir.
        
        Args:
            job_id: İş ID'si
            
        Returns:
            Optional[Dict[str, Any]]: İş detayları
        """
        job = self.jobs_collection.find_one({"id": job_id})
        if job and "_id" in job:
            del job["_id"]
        return job
    
    def list_jobs(self, user_id: Optional[str] = None, status: Optional[str] = None, 
                 page: int = 1, page_size: int = 20, admin_mode: bool = False) -> Tuple[List[Dict[str, Any]], int]:
        """
        Kullanıcının işlerini listele.
        
        Args:
            user_id: Kullanıcı ID'si
            status: Filtrelenecek durum (opsiyonel)
            page: Sayfa numarası
            page_size: Sayfa başına öğe sayısı
            admin_mode: Admin olarak tüm kullanıcıların işleri
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: İş listesi ve toplam sayısı
        """
        # Filtre oluştur
        filters = {}
        
        # Admin modunda ve user_id belirtilmemişse tüm işleri listele
        if not admin_mode or user_id:
            filters["user_id"] = user_id
        
        if status:
            filters["status"] = status
        
        # Toplam sayıyı al
        total_count = self.jobs_collection.count_documents(filters)
        
        # Sayfalama
        skip = (page - 1) * page_size
        
        # İşleri al
        cursor = self.jobs_collection.find(
            filters,
            sort=[("created_at", -1)],
            skip=skip,
            limit=page_size
        )
        
        # MongoDB _id alanını kaldır
        jobs = []
        for job in cursor:
            if "_id" in job:
                del job["_id"]
            jobs.append(job)
        
        return jobs, total_count
    
    def cancel_job(self, job_id: str) -> bool:
        """
        İşi iptal et.
        
        Args:
            job_id: İş ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        # İşi al
        job = self.get_job(job_id)
        
        if not job:
            logger.error(f"İptal edilecek iş bulunamadı: {job_id}")
            return False
        
        # İptal edilebilir durumları kontrol et
        cancellable_statuses = [
            FineTuningJobStatus.PENDING.value,
            FineTuningJobStatus.PREPARING.value,
            FineTuningJobStatus.VALIDATING.value,
            FineTuningJobStatus.TRAINING.value
        ]
        
        if job["status"] not in cancellable_statuses:
            logger.error(f"İş iptal edilemez, durum uygun değil: {job_id}, {job['status']}")
            return False
        
        # İşi iptal et
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        result = self.jobs_collection.update_one(
            {"id": job_id},
            {"$set": {
                "status": FineTuningJobStatus.CANCELLED.value,
                "updated_at": current_time,
                "finished_at": current_time
            }}
        )
        
        return result.modified_count > 0
    
    def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Model detaylarını getir.
        
        Args:
            model_id: Model ID'si
            
        Returns:
            Optional[Dict[str, Any]]: Model detayları
        """
        model = self.models_collection.find_one({"id": model_id})
        
        if model and "_id" in model:
            del model["_id"]
            
        return model
    
    def list_models(self, user_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        """
        Kullanıcının modellerini listele.
        
        Args:
            user_id: Kullanıcı ID'si
            page: Sayfa numarası
            page_size: Sayfa başına öğe sayısı
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: Model listesi ve toplam sayısı
        """
        # Filtreleme
        filters = {"user_id": user_id}
        
        # Toplam sayı
        total_count = self.models_collection.count_documents(filters)
        
        # Sayfalama
        skip = (page - 1) * page_size
        
        # Modelleri al
        cursor = self.models_collection.find(
            filters,
            sort=[("created_at", -1)],
            skip=skip,
            limit=page_size
        )
        
        # MongoDB _id alanını kaldır
        models = []
        for model in cursor:
            if "_id" in model:
                del model["_id"]
            models.append(model)
        
        return models, total_count
    
    def check_file_exists(self, file_id: str) -> bool:
        """
        Dosyanın var olup olmadığını kontrol et.
        
        Args:
            file_id: Dosya ID'si
            
        Returns:
            bool: Dosya varsa True, yoksa False
        """
        return self.files_collection.count_documents({"id": file_id}) > 0
    
    def validate_file_format(self, file_content: bytes, file_ext: str) -> Tuple[bool, str]:
        """
        Dosya formatını doğrula.
        
        Args:
            file_content: Dosya içeriği
            file_ext: Dosya uzantısı
            
        Returns:
            Tuple[bool, str]: Geçerli mi ve hata mesajı
        """
        try:
            if file_ext == "jsonl":
                # JSONL doğrulama
                lines = file_content.decode('utf-8').strip().split('\n')
                for i, line in enumerate(lines, 1):
                    try:
                        json_obj = json.loads(line)
                        
                        # Gerekli alanları kontrol et
                        if "prompt" not in json_obj or "completion" not in json_obj:
                            return False, f"Satır {i}: 'prompt' ve 'completion' alanları gereklidir"
                    except json.JSONDecodeError:
                        return False, f"Satır {i}: Geçersiz JSON formatı"
                
                return True, ""
                
            elif file_ext == "csv":
                # CSV doğrulama
                lines = file_content.decode('utf-8').strip().split('\n')
                
                # Başlık satırını kontrol et
                if not lines:
                    return False, "Dosya boş"
                
                header = lines[0].split(',')
                if "prompt" not in header or "completion" not in header:
                    return False, "CSV başlığı 'prompt' ve 'completion' sütunlarını içermelidir"
                
                return True, ""
                
            elif file_ext == "txt":
                # TXT doğrulama - basit kontrol
                content = file_content.decode('utf-8').strip()
                if not content:
                    return False, "Dosya boş"
                
                return True, ""
                
            else:
                return False, f"Desteklenmeyen dosya uzantısı: {file_ext}"
                
        except Exception as e:
            return False, f"Dosya doğrulama hatası: {str(e)}"
    
    def save_file(self, filename: str, content: bytes, purpose: str, user_id: str, 
                 description: Optional[str] = None) -> str:
        """
        Fine-tuning dosyasını kaydet.
        
        Args:
            filename: Dosya adı
            content: Dosya içeriği
            purpose: Dosya amacı ("training" veya "validation")
            user_id: Kullanıcı ID'si
            description: Dosya açıklaması (opsiyonel)
            
        Returns:
            str: Dosya ID'si
        """
        # Dosya ID'si oluştur
        file_id = str(uuid.uuid4())
        
        # Uzantıyı al
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        # Hedef dosya yolunu oluştur
        unique_filename = f"{file_id}.{ext}"
        file_path = os.path.join(self.dataset_dir, unique_filename)
        
        # Dosyayı kaydet
        with open(file_path, 'wb') as f:
            f.write(content)
        
        # Dosya boyutunu al
        file_size = len(content)
        
        # Dosya meta verilerini oluştur
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        file_data = {
            "id": file_id,
            "user_id": user_id,
            "filename": filename,
            "storage_path": file_path,
            "purpose": purpose,
            "size_bytes": file_size,
            "description": description,
            "created_at": current_time,
            "format": ext
        }
        
        # Veritabanına kaydet
        self.files_collection.insert_one(file_data)
        
        logger.info(f"Fine-tuning dosyası kaydedildi: {file_id}")
        
        return file_id
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Dosya detaylarını getir.
        
        Args:
            file_id: Dosya ID'si
            
        Returns:
            Optional[Dict[str, Any]]: Dosya detayları
        """
        file_data = self.files_collection.find_one({"id": file_id})
        
        if file_data and "_id" in file_data:
            del file_data["_id"]
            
        return file_data
    
    def list_files(self, user_id: str, purpose: Optional[str] = None, 
                  page: int = 1, page_size: int = 20) -> Tuple[List[Dict[str, Any]], int]:
        """
        Kullanıcının dosyalarını listele.
        
        Args:
            user_id: Kullanıcı ID'si
            purpose: Filtrelenecek dosya amacı (opsiyonel)
            page: Sayfa numarası
            page_size: Sayfa başına öğe sayısı
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: Dosya listesi ve toplam sayısı
        """
        # Filtreleme
        filters = {"user_id": user_id}
        
        if purpose:
            filters["purpose"] = purpose
        
        # Toplam sayı
        total_count = self.files_collection.count_documents(filters)
        
        # Sayfalama
        skip = (page - 1) * page_size
        
        # Dosyaları al
        cursor = self.files_collection.find(
            filters,
            sort=[("created_at", -1)],
            skip=skip,
            limit=page_size
        )
        
        # MongoDB _id alanını kaldır
        files = []
        for file_data in cursor:
            if "_id" in file_data:
                del file_data["_id"]
            files.append(file_data)
        
        return files, total_count
    
    def delete_file(self, file_id: str) -> bool:
        """
        Dosyayı sil.
        
        Args:
            file_id: Dosya ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        # Dosya bilgilerini al
        file_data = self.get_file(file_id)
        
        if not file_data:
            logger.error(f"Silinecek dosya bulunamadı: {file_id}")
            return False
        
        # Dosyayı fiziksel olarak sil
        storage_path = file_data.get("storage_path")
        if storage_path and os.path.exists(storage_path):
            try:
                os.remove(storage_path)
            except Exception as e:
                logger.error(f"Dosya silme hatası: {storage_path}, {str(e)}")
        
        # Veritabanından kaydı sil
        result = self.files_collection.delete_one({"id": file_id})
        
        return result.deleted_count > 0
    
    def use_model(self, model_id: str) -> bool:
        """
        Modelin kullanım sayısını artır.
        
        Args:
            model_id: Model ID'si
            
        Returns:
            bool: Başarılı ise True
        """
        # Modeli getir
        model = self.get_model(model_id)
        
        if not model:
            logger.error(f"Model bulunamadı: {model_id}")
            return False
        
        # Kullanım sayısını artır
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        result = self.models_collection.update_one(
            {"id": model_id},
            {"$inc": {"usage_count": 1}, "$set": {"last_used_at": current_time}}
        )
        
        return result.modified_count > 0