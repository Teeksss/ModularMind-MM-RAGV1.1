"""
MultiModal servisi.

Bu modül, metin, görüntü ve ses verilerini işlemek için gereken tüm bileşenleri sağlar.
"""

from .service import MultiModalService
from .config import MultiModalConfig
from .text.processor import TextProcessor
from .image.processor import ImageProcessor
from .audio.processor import AudioProcessor
from .fusion.embeddings import MultiModalEmbedding

__all__ = [
    'MultiModalService',
    'MultiModalConfig',
    'TextProcessor',
    'ImageProcessor',
    'AudioProcessor',
    'MultiModalEmbedding'
]

# Geriye dönük uyumluluk katmanı
import sys
from types import ModuleType

class MultiModalCompat(ModuleType):
    """Geriye dönük uyumluluk modülü"""
    
    def __init__(self):
        super().__init__("ModularMind.API.services.multimodal_service")
        
        # Yeni modül yapısından importlar
        from .service import MultiModalService
        from .config import MultiModalConfig
        
        # Bu modülün adres alanına ekle
        self.MultiModalService = MultiModalService
        self.MultiModalConfig = MultiModalConfig

# Bu modülü uyumluluk modülüyle değiştir
sys.modules["ModularMind.API.services.multimodal_service"] = MultiModalCompat()