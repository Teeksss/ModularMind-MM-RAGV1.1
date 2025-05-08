from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class FineTuningStatus(str, Enum):
    """Fine-tuning durumları."""
    PENDING = "pending"
    PREPARING = "preparing"
    TRAINING = "training"
    VALIDATING = "validating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

class FineTuningModelType(str, Enum):
    """Desteklenen fine-tuning model tipleri."""
    COMPLETION = "completion"
    CHAT = "chat"
    MULTILINGUAL = "multilingual"
    EMBEDDINGS = "embeddings"

class TrainingExample(BaseModel):
    """
    Fine-tuning için eğitim örneği.
    Chat modelleri için messages array'i, Completion için prompt-completion çifti.
    """
    id: str
    model_type: FineTuningModelType
    messages: Optional[List[Dict[str, str]]] = None  # Chat modelleri için
    prompt: Optional[str] = None  # Completion modelleri için
    completion: Optional[str] = None  # Completion modelleri için
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ValidationResult(BaseModel):
    """Model fine-tuning doğrulama sonuçları."""
    id: str
    accuracy: float
    loss: float
    examples_evaluated: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metrics: Dict[str, Any] = Field(default_factory=dict)

class FineTuningJob(BaseModel):
    """Fine-tuning iş modeli."""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    model_id: str  # Temel model kimliği
    model_type: FineTuningModelType
    status: FineTuningStatus = FineTuningStatus.PENDING
    training_file_ids: List[str]  # Eğitim veri dosyası kimlikleri
    validation_file_id: Optional[str] = None  # Doğrulama veri dosyası kimliği
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)
    result_model_id: Optional[str] = None  # İnce ayar yapılmış model kimliği
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    progress: int = 0  # 0-100 arası yüzde
    organization_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FineTunedModel(BaseModel):
    """İnce ayar yapılmış model."""
    id: str
    user_id: str
    job_id: str  # Fine-tuning iş kimliği
    name: str
    description: Optional[str] = None
    base_model_id: str  # Temel model kimliği
    model_type: FineTuningModelType
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, Any] = Field(default_factory=dict)
    organization_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_public: bool = False
    usage_count: int = 0
    last_used_at: Optional[datetime] = None