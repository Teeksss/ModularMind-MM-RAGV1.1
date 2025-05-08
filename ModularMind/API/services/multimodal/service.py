"""
MultiModal servisi - farklı veri tiplerini (metin, görüntü, ses) işleme.
"""

import os
import logging
import json
from typing import Dict, List, Any, Optional, Union, Tuple

from .config import MultiModalConfig
from .text.processor import TextProcessor
from .image.processor import ImageProcessor
from .audio.processor import AudioProcessor
from .fusion.embeddings import MultiModalEmbedding

logger = logging.getLogger(__name__)

class MultiModalService:
    """
    Farklı veri tiplerini işleyen servis.
    
    Bu servis, metin, görüntü ve ses gibi farklı veri tiplerini işleyerek
    birleşik bir temsil oluşturma yetenekleri sağlar.
    """
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Singleton instance getter"""
        if cls._instance is None:
            raise ValueError("MultiModalService henüz başlatılmamış")
        return cls._instance
    
    def __init__(self, config_path: Optional[str] = None):
        """
        MultiModal servisini başlatır
        
        Args:
            config_path: Yapılandırma dosyası yolu
        """
        # Alt işleyiciler
        self.text_processor = TextProcessor()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.embedder = MultiModalEmbedding()
        
        # Yapılandırma
        self.config = MultiModalConfig()
        
        # Singleton instance
        MultiModalService._instance = self
        
        # Yapılandırma yükle
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
    
    def load_config(self, config_path: str) -> bool:
        """
        Yapılandırmayı dosyadan yükler
        
        Args:
            config_path: Yapılandırma dosyası yolu
            
        Returns:
            bool: Yükleme başarılı mı
        """
        try:
            with open(config_path, "r") as f:
                config_data = json.load(f)
            
            # Ana yapılandırmayı ayarla
            self.config = MultiModalConfig.from_dict(config_data)
            
            # Alt modülleri yapılandır
            if "text" in config_data:
                self.text_processor.configure(config_data["text"])
            
            if "image" in config_data:
                self.image_processor.configure(config_data["image"])
            
            if "audio" in config_data:
                self.audio_processor.configure(config_data["audio"])
            
            if "embedding" in config_data:
                self.embedder.configure(config_data["embedding"])
            
            logger.info(f"MultiModal yapılandırması yüklendi: {config_path}")
            return True
        except Exception as e:
            logger.error(f"MultiModal yapılandırması yükleme hatası: {str(e)}")
            return False
    
    def process_text(self, text: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Metin işler ve özellikler çıkarır
        
        Args:
            text: İşlenecek metin
            options: İşleme seçenekleri
            
        Returns:
            Dict[str, Any]: İşleme sonuçları
        """
        return self.text_processor.process(text, options)
    
    def process_image(self, image_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Görüntü işler ve özellikler çıkarır
        
        Args:
            image_path: Görüntü dosyası yolu
            options: İşleme seçenekleri
            
        Returns:
            Dict[str, Any]: İşleme sonuçları
        """
        return self.image_processor.process(image_path, options)
    
    def process_audio(self, audio_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ses işler ve özellikler çıkarır
        
        Args:
            audio_path: Ses dosyası yolu
            options: İşleme seçenekleri
            
        Returns:
            Dict[str, Any]: İşleme sonuçları
        """
        return self.audio_processor.process(audio_path, options)
    
    def create_multimodal_embedding(
        self,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[List[float]]:
        """
        Çoklu model (multimodal) embedding oluşturur
        
        Args:
            text: Metin (opsiyonel)
            image_path: Görüntü dosyası yolu (opsiyonel)
            audio_path: Ses dosyası yolu (opsiyonel)
            options: Embedding oluşturma seçenekleri
            
        Returns:
            Optional[List[float]]: Multimodal embedding vektörü
        """
        # En az bir veri türü gerekli
        if text is None and image_path is None and audio_path is None:
            logger.error("En az bir veri türü (metin, görüntü veya ses) gerekli")
            return None
        
        options = options or {}
        
        # Veri tipleri için işlemcilerden özellikler al
        features = {}
        
        if text:
            text_result = self.text_processor.extract_features(text, options.get("text_options"))
            features["text"] = text_result.get("features")
        
        if image_path:
            image_result = self.image_processor.extract_features(image_path, options.get("image_options"))
            features["image"] = image_result.get("features")
        
        if audio_path:
            audio_result = self.audio_processor.extract_features(audio_path, options.get("audio_options"))
            features["audio"] = audio_result.get("features")
        
        # Özellikleri birleştir ve multimodal embedding oluştur
        return self.embedder.create_embedding(features, options)
    
    def create_multimodal_batch_embeddings(
        self,
        texts: Optional[List[str]] = None,
        image_paths: Optional[List[str]] = None,
        audio_paths: Optional[List[str]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[List[List[float]]]:
        """
        Çoklu belgeler için multimodal embeddingler oluşturur
        
        Args:
            texts: Metinler listesi (opsiyonel)
            image_paths: Görüntü dosyaları listesi (opsiyonel)
            audio_paths: Ses dosyaları listesi (opsiyonel)
            options: Embedding oluşturma seçenekleri
            
        Returns:
            Optional[List[List[float]]]: Multimodal embedding vektörleri listesi
        """
        options = options or {}
        
        # Veri tip sayılarını kontrol et
        count = max(
            len(texts) if texts else 0,
            len(image_paths) if image_paths else 0,
            len(audio_paths) if audio_paths else 0
        )
        
        if count == 0:
            logger.error("En az bir veri listesi (metin, görüntü veya ses) gerekli")
            return None
        
        # Her öğe için embedding oluştur
        embeddings = []
        
        for i in range(count):
            text = texts[i] if texts and i < len(texts) else None
            image_path = image_paths[i] if image_paths and i < len(image_paths) else None
            audio_path = audio_paths[i] if audio_paths and i < len(audio_paths) else None
            
            embedding = self.create_multimodal_embedding(
                text=text,
                image_path=image_path,
                audio_path=audio_path,
                options=options
            )
            
            if embedding:
                embeddings.append(embedding)
        
        return embeddings
    
    def image_to_text(self, image_path: str, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Görüntüden metin çıkarır (görüntü başlıklandırma)
        
        Args:
            image_path: Görüntü dosyası yolu
            options: İşleme seçenekleri
            
        Returns:
            Optional[str]: Oluşturulan metin başlık
        """
        return self.image_processor.caption_image(image_path, options)
    
    def audio_to_text(self, audio_path: str, options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Sesten metin çıkarır (konuşma tanıma)
        
        Args:
            audio_path: Ses dosyası yolu
            options: İşleme seçenekleri
            
        Returns:
            Optional[str]: Transkripsiyon metni
        """
        return self.audio_processor.transcribe(audio_path, options)