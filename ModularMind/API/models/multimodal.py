from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

class ImageContent(BaseModel):
    """Görüntü içeriği modeli."""
    id: str
    user_id: str
    filename: str
    file_path: str
    caption: str
    width: int
    height: int
    format: Optional[str] = None
    base64: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VideoContent(BaseModel):
    """Video içeriği modeli."""
    id: str
    user_id: str
    filename: str
    file_path: str
    caption: str
    width: int
    height: int
    duration: float  # saniye cinsinden
    frame_count: int
    frames: List[str] = Field(default_factory=list)  # base64 kodlu kareler
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AudioContent(BaseModel):
    """Ses içeriği modeli."""
    id: str
    user_id: str
    filename: str
    file_path: str
    transcript: str
    duration: float  # saniye cinsinden
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultimodalContent(BaseModel):
    """Multimodal içerik modeli."""
    id: str
    user_id: str
    content_type: str  # "image", "video", "audio"
    image: Optional[ImageContent] = None
    video: Optional[VideoContent] = None
    audio: Optional[AudioContent] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultimodalEmbedding(BaseModel):
    """Multimodal embedding modeli."""
    id: str
    content_id: str
    content_type: str  # "image", "video", "audio"
    embedding: List[float]
    model: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MultimodalProcessingResult(BaseModel):
    """Multimodal işleme sonucu."""
    content: Union[ImageContent, VideoContent, AudioContent]
    embedding: MultimodalEmbedding
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MultimodalSearchQuery(BaseModel):
    """Multimodal arama sorgusu."""
    query_text: Optional[str] = None
    query_image: Optional[str] = None  # base64 kodlu görüntü
    filter: Optional[Dict[str, Any]] = None
    limit: int = 10