"""
Metadata Ekstraksiyon ve Zenginleştirme Modülü.
Belgelerden üst veri çıkarma ve zenginleştirme işlevleri sağlar.
"""

import logging
import re
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import datetime
import hashlib

from ModularMind.API.services.retrieval.models import Document
from ModularMind.API.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class MetadataFieldType(str, Enum):
    """Metadata alan türleri."""
    TEXT = "text"
    DATE = "date"
    NUMBER = "number"
    CATEGORY = "category"
    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    CUSTOM = "custom"

@dataclass
class MetadataField:
    """Metadata alanı tanımı."""
    name: str
    field_type: MetadataFieldType
    description: str
    is_required: bool = False
    extraction_method: str = "regex"  # regex, llm, or custom
    regex_pattern: Optional[str] = None
    default_value: Optional[Any] = None
    normalizer: Optional[str] = None
    indexed: bool = True

class MetadataExtractor:
    """
    Metadata çıkarma ve zenginleştirme ana sınıfı.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Args:
            llm_service: LLM servisi (LLM tabanlı ekstraksiyon için)
        """
        self.llm_service = llm_service
        
        # Ekstrakte edilen alan bilgilerini sakla
        self.extracted_fields_stats = {}
        
        # Önceden derlenen regex'ler
        self.compiled_regexes = {}
        
        # Varsayılan ekstraktörleri yükle
        self.default_extractors = self._load_default_extractors()
    
    def extract_metadata(
        self, 
        document: Document, 
        fields: List[MetadataField],
        context: Optional[Dict[str, Any]] = None
    ) -> Document:
        """
        Belgeden metadata çıkarır ve zenginleştirir.
        
        Args:
            document: İşlenecek belge
            fields: Çıkarılacak metadata alanları
            context: Ekstraksiyon bağlamı (isteğe bağlı)
            
        Returns:
            Document: Metadata ile zenginleştirilmiş belge
        """
        # Mevcut metadatayı kopyala
        metadata = document.metadata.copy() if document.metadata else {}
        
        # Her alan için ekstraksiyon yap
        for field in fields:
            try:
                # Alan zaten varsa ve override değilse atla
                if field.name in metadata and not field.is_required:
                    continue
                
                # Ekstraksiyon yöntemine göre metadata değerini çıkar
                if field.extraction_method == "regex" and field.regex_pattern:
                    value = self._extract_by_regex(document.text, field)
                elif field.extraction_method == "llm" and self.llm_service:
                    value = self._extract_by_llm(document.text, field, context)
                elif field.extraction_method == "custom":
                    value = self._extract_by_custom_method(document.text, field, context)
                else:
                    # Varsayılan ekstraktörleri kullan
                    value = self._extract_by_default_method(document.text, field)
                
                # Değer varsa normalize et ve metadataya ekle
                if value is not None:
                    # Normalizasyon işlemi
                    if field.normalizer:
                        value = self._normalize_value(value, field)
                    
                    # Metadataya ekle
                    metadata[field.name] = value
                    
                    # İstatistikleri güncelle
                    self._update_stats(field.name, "success")
                
                elif field.is_required and field.default_value is not None:
                    # Zorunlu alan için değer bulunamadıysa varsayılan değeri kullan
                    metadata[field.name] = field.default_value
                    self._update_stats(field.name, "default")
                
                else:
                    # İstatistikleri güncelle
                    self._update_stats(field.name, "missed")
                
            except Exception as e:
                logger.error(f"Metadata çıkarma hatası - {field.name}: {str(e)}")
                self._update_stats(field.name, "error")
        
        # Zenginleştirilmiş belgeyi döndür
        return Document(
            id=document.id,
            text=document.text,
            metadata=metadata
        )
    
    def batch_extract_metadata(
        self, 
        documents: List[Document], 
        fields: List[MetadataField],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Belge listesinden toplu metadata çıkarır ve zenginleştirir.
        
        Args:
            documents: İşlenecek belgeler
            fields: Çıkarılacak metadata alanları
            context: Ekstraksiyon bağlamı (isteğe bağlı)
            
        Returns:
            List[Document]: Metadata ile zenginleştirilmiş belgeler
        """
        enriched_documents = []
        
        for document in documents:
            enriched_document = self.extract_metadata(document, fields, context)
            enriched_documents.append(enriched_document)
        
        return enriched_documents
    
    def get_extraction_stats(self) -> Dict[str, Dict[str, int]]:
        """
        Metadata çıkarma istatistiklerini döndürür.
        
        Returns:
            Dict[str, Dict[str, int]]: İstatistikler
        """
        return self.extracted_fields_stats
    
    def _extract_by_regex(self, text: str, field: MetadataField) -> Optional[Any]:
        """
        Regex ile metadata değeri çıkarır.
        
        Args:
            text: Kaynak metin
            field: Metadata alanı
            
        Returns:
            Optional[Any]: Çıkarılan değer
        """
        if not field.regex_pattern:
            return None
        
        # Regex'i derle (önbellekte yoksa)
        if field.regex_pattern not in self.compiled_regexes:
            self.compiled_regexes[field.regex_pattern] = re.compile(field.regex_pattern, re.DOTALL | re.MULTILINE)
        
        regex = self.compiled_regexes[field.regex_pattern]
        
        # Eşleşmeyi bul
        match = regex.search(text)
        
        if not match:
            return None
        
        # Grupları al
        if match.groups():
            value = match.group(1)  # İlk grup
        else:
            value = match.group(0)  # Tüm eşleşme
        
        # Alan türüne göre değeri dönüştür
        return self._convert_value_by_type(value, field.field_type)
    
    def _extract_by_llm(
        self, 
        text: str, 
        field: MetadataField, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        LLM ile metadata değeri çıkarır.
        
        Args:
            text: Kaynak metin
            field: Metadata alanı
            context: Ekstraksiyon bağlamı
            
        Returns:
            Optional[Any]: Çıkarılan değer
        """
        if not self.llm_service:
            logger.warning("LLM servisi tanımlanmamış, LLM tabanlı ekstraksiyon yapılamıyor.")
            return None
        
        # Metnin uzunluğunu kontrol et ve kısalt
        max_text_length = 10000  # 10k karakter (yaklaşık 2.5k token)
        if len(text) > max_text_length:
            # Metni kısalt - baştan ve sondan biraz al
            truncated_text = text[:max_text_length//2] + "...[TRUNCATED]..." + text[-max_text_length//2:]
        else:
            truncated_text = text
        
        # Prompt oluştur
        prompt = f"""
        Verilen metin içinden '{field.name}' alanına karşılık gelen değeri çıkar.
        
        Alan Türü: {field.field_type.value}
        Alan Açıklaması: {field.description}
        
        Metin:
        -----------
        {truncated_text}
        -----------
        
        Yanıtını yalnızca çıkarılan değer olarak ver, herhangi bir açıklama ekleme. 
        Eğer değer bulunamazsa sadece 'NULL' döndür.
        """
        
        try:
            # LLM'den yanıt al
            response = self.llm_service.generate_text(prompt, max_tokens=100)
            
            # Yanıtı işle
            if not response or response.strip().upper() == "NULL":
                return None
            
            # Alan türüne göre değeri dönüştür
            return self._convert_value_by_type(response.strip(), field.field_type)
            
        except Exception as e:
            logger.error(f"LLM ekstraksiyon hatası - {field.name}: {str(e)}")
            return None
    
    def _extract_by_custom_method(
        self, 
        text: str, 
        field: MetadataField, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """
        Özel metot ile metadata değeri çıkarır.
        
        Args:
            text: Kaynak metin
            field: Metadata alanı
            context: Ekstraksiyon bağlamı
            
        Returns:
            Optional[Any]: Çıkarılan değer
        """
        # Özel ekstraktör adını belirle
        extractor_name = f"_extract_{field.name}"
        
        # Metodun mevcut olup olmadığını kontrol et
        if hasattr(self, extractor_name) and callable(getattr(self, extractor_name)):
            extractor_method = getattr(self, extractor_name)
            return extractor_method(text, field, context)
        
        logger.warning(f"Özel ekstraktör bulunamadı: {extractor_name}")
        return None
    
    def _extract_by_default_method(self, text: str, field: MetadataField) -> Optional[Any]:
        """
        Varsayılan metot ile metadata değeri çıkarır.
        
        Args:
            text: Kaynak metin
            field: Metadata alanı
            
        Returns:
            Optional[Any]: Çıkarılan değer
        """
        # Alan türü için varsayılan ekstraktörü al
        if field.field_type.value in self.default_extractors:
            extractor_info = self.default_extractors[field.field_type.value]
            
            regex_pattern = extractor_info.get("regex")
            if regex_pattern:
                # Geçici bir alan oluştur
                temp_field = MetadataField(
                    name=field.name,
                    field_type=field.field_type,
                    description=field.description,
                    extraction_method="regex",
                    regex_pattern=regex_pattern
                )
                return self._extract_by_regex(text, temp_field)
        
        return None
    
    def _convert_value_by_type(self, value: str, field_type: MetadataFieldType) -> Any:
        """
        Değeri alan türüne göre dönüştürür.
        
        Args:
            value: Dönüştürülecek değer
            field_type: Alan türü
            
        Returns:
            Any: Dönüştürülmüş değer
        """
        if not value:
            return None
        
        try:
            if field_type == MetadataFieldType.NUMBER:
                # Sayılar için nokta ve virgül kontrolü
                value = value.replace(',', '.')
                try:
                    return int(value)
                except ValueError:
                    return float(value)
                
            elif field_type == MetadataFieldType.DATE:
                # Tarih formatını algılamaya çalış
                import dateutil.parser
                return dateutil.parser.parse(value).isoformat()
                
            elif field_type in [MetadataFieldType.CATEGORY, MetadataFieldType.PERSON, 
                             MetadataFieldType.ORGANIZATION, MetadataFieldType.LOCATION]:
                # Kategori temizleme
                return value.strip()
                
            else:
                # Diğer türler için string olarak döndür
                return value.strip()
                
        except Exception as e:
            logger.error(f"Değer dönüştürme hatası ({field_type.value}): {str(e)}")
            return value
    
    def _normalize_value(self, value: Any, field: MetadataField) -> Any:
        """
        Değeri normalize eder.
        
        Args:
            value: Normalize edilecek değer
            field: Metadata alanı
            
        Returns:
            Any: Normalize edilmiş değer
        """
        if value is None:
            return None
        
        normalizer_name = field.normalizer
        
        # Normalizer metodunu çağır
        if hasattr(self, f"_normalize_{normalizer_name}") and callable(getattr(self, f"_normalize_{normalizer_name}")):
            normalizer = getattr(self, f"_normalize_{normalizer_name}")
            return normalizer(value, field)
        
        # Yerleşik normalizer'lar
        if normalizer_name == "lowercase":
            return value.lower() if isinstance(value, str) else value
            
        elif normalizer_name == "uppercase":
            return value.upper() if isinstance(value, str) else value
            
        elif normalizer_name == "strip":
            return value.strip() if isinstance(value, str) else value
            
        elif normalizer_name == "capitalize":
            return value.capitalize() if isinstance(value, str) else value
            
        elif normalizer_name == "title":
            return value.title() if isinstance(value, str) else value
            
        return value
    
    def _update_stats(self, field_name: str, status: str) -> None:
        """
        Ekstraksiyon istatistiklerini günceller.
        
        Args:
            field_name: Alan adı
            status: Durum (success, missed, error, default)
        """
        if field_name not in self.extracted_fields_stats:
            self.extracted_fields_stats[field_name] = {
                "success": 0,
                "missed": 0,
                "error": 0,
                "default": 0,
                "total": 0
            }
        
        self.extracted_fields_stats[field_name][status] += 1
        self.extracted_fields_stats[field_name]["total"] += 1
    
    def _load_default_extractors(self) -> Dict[str, Dict[str, Any]]:
        """
        Varsayılan ekstraktörleri yükler.
        
        Returns:
            Dict[str, Dict[str, Any]]: Ekstraktörler
        """
        return {
            "date": {
                "regex": r'(?:(?:\d{4}-\d{2}-\d{2})|(?:\d{2}/\d{2}/\d{4})|(?:\d{2}\.\d{2}\.\d{4}))'
            },
            "email": {
                "regex": r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
            },
            "url": {
                "regex": r'(https?://[^\s]+)'
            },
            "phone": {
                "regex": r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            },
            "person": {
                "regex": None  # LLM kullanımı daha uygun
            },
            "organization": {
                "regex": None  # LLM kullanımı daha uygun
            },
            "location": {
                "regex": None  # LLM kullanımı daha uygun
            }
        }

class EntityExtractor(MetadataExtractor):
    """
    NER (Named Entity Recognition) tabanlı metadata çıkarıcı.
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """
        Args:
            llm_service: LLM servisi (LLM tabanlı ekstraksiyon için)
        """
        super().__init__(llm_service)
        self.ner_model = None
        
        # NER modeli yüklemeyi dene
        try:
            import spacy
            self.ner_model = spacy.load("en_core_web_sm")
            logger.info("NER modeli başarıyla yüklendi (spaCy)")
        except Exception as e:
            logger.warning(f"NER modeli yüklenemedi: {str(e)}")
    
    def extract_entities(self, document: Document) -> Document:
        """
        Belgeden NER'ler çıkarır.
        
        Args:
            document: İşlenecek belge
            
        Returns:
            Document: Varlıklarla zenginleştirilmiş belge
        """
        # Mevcut metadatayı kopyala
        metadata = document.metadata.copy() if document.metadata else {}
        
        try:
            if self.ner_model:
                # spaCy NER kullan
                entities = self._extract_with_spacy(document.text)
                metadata.update(entities)
            else:
                # LLM ile NER çıkarımı yap
                entities = self._extract_with_llm(document.text)
                metadata.update(entities)
                
            return Document(
                id=document.id,
                text=document.text,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Varlık çıkarma hatası: {str(e)}")
            return document
    
    def _extract_with_spacy(self, text: str) -> Dict[str, List[str]]:
        """
        spaCy ile varlıkları çıkarır.
        
        Args:
            text: Kaynak metin
            
        Returns:
            Dict[str, List[str]]: Çıkarılan varlıklar
        """
        # Metni işle
        doc = self.ner_model(text)
        
        # Varlıkları kategorize et
        entities = {
            "people":