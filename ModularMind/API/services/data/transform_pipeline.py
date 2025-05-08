"""
Veri Transformasyon Pipeline.
Belgeler üzerinde sıralı transformasyonlar uygular.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
import time
from enum import Enum

from ModularMind.API.services.retrieval.models import Document
from ModularMind.API.services.data.metadata_extractor import MetadataExtractor, MetadataField, EntityExtractor, TopicExtractor, SentimentAnalyzer
from ModularMind.API.services.llm_service import LLMService
from ModularMind.API.services.retrieval.advanced_chunking import SemanticChunker

logger = logging.getLogger(__name__)

class TransformStage(str, Enum):
    """Transformasyon aşaması türleri."""
    METADATA_EXTRACTION = "metadata_extraction"
    ENTITY_EXTRACTION = "entity_extraction"
    TOPIC_EXTRACTION = "topic_extraction"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    SEMANTIC_CHUNKING = "semantic_chunking"
    TEXT_CLEANING = "text_cleaning"
    CUSTOM = "custom"

@dataclass
class TransformStageConfig:
    """Transformasyon aşaması yapılandırması."""
    stage_type: TransformStage
    name: str
    enabled: bool = True
    options: Dict[str, Any] = field(default_factory=dict)

class TransformPipeline:
    """
    Belgeleri işlemek için transformasyon pipeline'ı.
    """
    
    def __init__(
        self, 
        stages: List[TransformStageConfig], 
        llm_service: Optional[LLMService] = None
    ):
        """
        Args:
            stages: Transformasyon aşamaları
            llm_service: LLM servisi
        """
        self.stages = stages
        self.llm_service = llm_service
        
        # Servisler
        self.metadata_extractor = MetadataExtractor(llm_service)
        self.entity_extractor = EntityExtractor(llm_service)
        self.topic_extractor = TopicExtractor(llm_service) if llm_service else None
        self.sentiment_analyzer = SentimentAnalyzer(llm_service)
        self.semantic_chunker = SemanticChunker(llm_service) if llm_service else None
        
        # Özel transformasyonlar
        self.custom_transforms = {}
        
        # Performans metrikleri
        self.metrics = {
            "documents_processed": 0,
            "stage_timing": {},
            "errors": {}
        }
    
    def register_custom_transform(self, name: str, transform_func: Callable[[Document], Document]):
        """
        Özel transformasyon kaydeder.
        
        Args:
            name: Transformasyon adı
            transform_func: Transformasyon işlevi
        """
        self.custom_transforms[name] = transform_func
    
    def process_document(self, document: Document) -> Document:
        """
        Belgeye transformasyon aşamalarını uygular.
        
        Args:
            document: İşlenecek belge
            
        Returns:
            Document: İşlenmiş belge
        """
        processed_doc = document
        
        # Her aşama için
        for stage in self.stages:
            if not stage.enabled:
                continue
                
            try:
                # Aşama başlangıç zamanı
                start_time = time.time()
                
                # Aşama türüne göre işlemi uygula
                if stage.stage_type == TransformStage.METADATA_EXTRACTION:
                    processed_doc = self._apply_metadata_extraction(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.ENTITY_EXTRACTION:
                    processed_doc = self._apply_entity_extraction(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.TOPIC_EXTRACTION:
                    processed_doc = self._apply_topic_extraction(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.SENTIMENT_ANALYSIS:
                    processed_doc = self._apply_sentiment_analysis(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.SEMANTIC_CHUNKING:
                    processed_doc = self._apply_semantic_chunking(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.TEXT_CLEANING:
                    processed_doc = self._apply_text_cleaning(processed_doc, stage)
                    
                elif stage.stage_type == TransformStage.CUSTOM:
                    processed_doc = self._apply_custom_transform(processed_doc, stage)
                
                # Aşama süresini ölç
                elapsed = time.time() - start_time
                self._update_stage_timing(stage.name, elapsed)
                
            except Exception as e:
                logger.error(f"Transformasyon hatası - {stage.name}: {str(e)}")
                self._update_error_count(stage.name)
        
        # İşlenen belge sayısını güncelle
        self.metrics["documents_processed"] += 1
        
        return processed_doc
    
    def process_documents(self, documents: List[Document]) -> List[Document]:
        """
        Belge listesine transformasyon aşamalarını uygular.
        
        Args:
            documents: İşlenecek belgeler
            
        Returns:
            List[Document]: İşlenmiş belgeler
        """
        processed_docs = []
        
        for document in documents:
            processed_doc = self.process_document(document)
            processed_docs.append(processed_doc)
        
        return processed_docs
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Pipeline metriklerini döndürür.
        
        Returns:
            Dict[str, Any]: Metrikler
        """
        return self.metrics
    
    def _apply_metadata_extraction(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Metadata çıkarma aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        fields = stage.options.get("fields", [])
        
        # MetadataField nesnelerine dönüştür
        metadata_fields = []
        for field_config in fields:
            field = MetadataField(
                name=field_config["name"],
                field_type=field_config["field_type"],
                description=field_config.get("description", ""),
                is_required=field_config.get("is_required", False),
                extraction_method=field_config.get("extraction_method", "regex"),
                regex_pattern=field_config.get("regex_pattern"),
                default_value=field_config.get("default_value"),
                normalizer=field_config.get("normalizer"),
                indexed=field_config.get("indexed", True)
            )
            metadata_fields.append(field)
        
        context = stage.options.get("context", {})
        
        # Metadata çıkar
        return self.metadata_extractor.extract_metadata(document, metadata_fields, context)
    
    def _apply_entity_extraction(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Varlık (entity) çıkarma aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        return self.entity_extractor.extract_entities(document)
    
    def _apply_topic_extraction(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Konu (topic) çıkarma aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        if not self.topic_extractor:
            logger.warning("Konu çıkarıcı başlatılmamış, LLM servisi gereklidir.")
            return document
            
        num_topics = stage.options.get("num_topics", 5)
        return self.topic_extractor.extract_topics(document, num_topics)
    
    def _apply_sentiment_analysis(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Duygu analizi aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        return self.sentiment_analyzer.analyze_sentiment(document)
    
    def _apply_semantic_chunking(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Semantik parçalama aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge (chunk metadatasıyla)
        """
        if not self.semantic_chunker:
            logger.warning("Semantik chunker başlatılmamış, LLM servisi gereklidir.")
            return document
            
        # Chunking yapılandırması
        chunk_size = stage.options.get("chunk_size", 500)
        chunk_overlap = stage.options.get("chunk_overlap", 50)
        
        # Chunking'i uygula
        chunks = self.semantic_chunker.create_chunks(
            document.text, 
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap,
            metadata=document.metadata
        )
        
        # Chunk bilgilerini metaverilere ekle
        metadata = document.metadata.copy() if document.metadata else {}
        metadata["chunks"] = [
            {
                "id": chunk.id,
                "text": chunk.text[:100] + "..." if len(chunk.text) > 100 else chunk.text,
                "size": len(chunk.text)
            }
            for chunk in chunks
        ]
        metadata["chunk_count"] = len(chunks)
        
        return Document(
            id=document.id,
            text=document.text,
            metadata=metadata
        )
    
    def _apply_text_cleaning(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Metin temizleme aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        import re
        
        text = document.text
        
        # Temizleme seçenekleri
        remove_html = stage.options.get("remove_html", True)
        remove_urls = stage.options.get("remove_urls", False)
        remove_emails = stage.options.get("remove_emails", False)
        normalize_whitespace = stage.options.get("normalize_whitespace", True)
        
        # HTML etiketlerini kaldır
        if remove_html:
            text = re.sub(r'<[^>]+>', ' ', text)
        
        # URL'leri kaldır
        if remove_urls:
            text = re.sub(r'https?://\S+', '[URL]', text)
        
        # E-postaları kaldır
        if remove_emails:
            text = re.sub(r'\S+@\S+', '[EMAIL]', text)
        
        # Boşlukları normalize et
        if normalize_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()
        
        return Document(
            id=document.id,
            text=text,
            metadata=document.metadata
        )
    
    def _apply_custom_transform(self, document: Document, stage: TransformStageConfig) -> Document:
        """
        Özel transformasyon aşamasını uygular.
        
        Args:
            document: İşlenecek belge
            stage: Aşama yapılandırması
            
        Returns:
            Document: İşlenmiş belge
        """
        transform_name = stage.options.get("transform_name")
        
        if not transform_name or transform_name not in self.custom_transforms:
            logger.warning(f"Özel transformasyon bulunamadı: {transform_name}")
            return document
        
        # Özel transformasyonu uygula
        transform_func = self.custom_transforms[transform_name]
        return transform_func(document)
    
    def _update_stage_timing(self, stage_name: str, elapsed: float) -> None:
        """
        Aşama süresini günceller.
        
        Args:
            stage_name: Aşama adı
            elapsed: Geçen süre (saniye)
        """
        if stage_name not in self.metrics["stage_timing"]:
            self.metrics["stage_timing"][stage_name] = {
                "total_time": 0,
                "count": 0,
                "avg_time": 0
            }
        
        self.metrics["stage_timing"][stage_name]["total_time"] += elapsed
        self.metrics["stage_timing"][stage_name]["count"] += 1
        self.metrics["stage_timing"][stage_name]["avg_time"] = (
            self.metrics["stage_timing"][stage_name]["total_time"] / 
            self.metrics["stage_timing"][stage_name]["count"]
        )
    
    def _update_error_count(self, stage_name: str) -> None:
        """
        Hata sayısını günceller.
        
        Args:
            stage_name: Aşama adı
        """
        if stage_name not in self.metrics["errors"]:
            self.metrics["errors"][stage_name] = 0
        
        self.metrics["errors"][stage_name] += 1