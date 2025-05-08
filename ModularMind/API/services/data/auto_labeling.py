"""
Otomatik Veri Etiketleme Servisi.
Belgeleri otomatik olarak sınıflandırma ve etiketleme işlevleri sağlar.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Set
import time
import json
from enum import Enum
import numpy as np

from ModularMind.API.services.retrieval.models import Document
from ModularMind.API.services.llm_service import LLMService
from ModularMind.API.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class LabelingMethod(str, Enum):
    """Etiketleme metotları."""
    RULE_BASED = "rule_based"
    LLM_BASED = "llm_based"
    EMBEDDING_BASED = "embedding_based"
    HYBRID = "hybrid"

class AutoLabeler:
    """
    Belgeleri otomatik olarak etiketleme ana sınıfı.
    """
    
    def __init__(
        self, 
        llm_service: Optional[LLMService] = None,
        embedding_service: Optional[EmbeddingService] = None
    ):
        """
        Args:
            llm_service: LLM servisi
            embedding_service: Gömme servisi
        """
        self.llm_service = llm_service
        self.embedding_service = embedding_service
        
        # Etiketleme kuralları ve şemalar
        self.labeling_schemas = {}
        self.rule_based_labels = {}
        
        # Etiketleme istatistikleri
        self.stats = {
            "total_documents": 0,
            "labeled_documents": 0,
            "schema_stats": {}
        }
    
    def register_labeling_schema(
        self, 
        schema_id: str, 
        schema: Dict[str, Any]
    ) -> None:
        """
        Etiketleme şeması kaydeder.
        
        Args:
            schema_id: Şema tanımlayıcısı
            schema: Etiketleme şeması
        """
        self.labeling_schemas[schema_id] = schema
        
        # Şema istatistiklerini başlat
        self.stats["schema_stats"][schema_id] = {
            "total": 0,
            "success": 0,
            "method_stats": {
                "rule_based": 0,
                "llm_based": 0,
                "embedding_based": 0,
                "hybrid": 0
            },
            "label_distribution": {}
        }
        
        # Kural tabanlı etiketleri hazırla
        self.rule_based_labels[schema_id] = self._prepare_rule_based_labels(schema)
    
    def label_document(
        self, 
        document: Document, 
        schema_id: str,
        method: LabelingMethod = LabelingMethod.HYBRID,
        confidence_threshold: float = 0.7
    ) -> Document:
        """
        Belgeyi etiketler.
        
        Args:
            document: Etiketlenecek belge
            schema_id: Kullanılacak etiketleme şeması ID'si
            method: Etiketleme metodu
            confidence_threshold: Güven eşiği
            
        Returns:
            Document: Etiketlenmiş belge
        """
        if schema_id not in self.labeling_schemas:
            logger.warning(f"Etiketleme şeması bulunamadı: {schema_id}")
            return document
        
        # Mevcut metadatayı kopyala
        metadata = document.metadata.copy() if document.metadata else {}
        
        # Şemayı al
        schema = self.labeling_schemas[schema_id]
        
        try:
            # İstatistikleri güncelle
            self.stats["total_documents"] += 1
            self.stats["schema_stats"][schema_id]["total"] += 1
            
            # Etiketleme metoduna göre işlem yap
            if method == LabelingMethod.RULE_BASED:
                labels, confidence = self._label_rule_based(document, schema_id)
                
            elif method == LabelingMethod.LLM_BASED:
                labels, confidence = self._label_llm_based(document, schema)
                
            elif method == LabelingMethod.EMBEDDING_BASED:
                labels, confidence = self._label_embedding_based(document, schema)
                
            elif method == LabelingMethod.HYBRID:
                # Önce kural tabanlı dene
                rule_labels, rule_confidence = self._label_rule_based(document, schema_id)
                
                # Güven eşiğini geçtiyse kural tabanlı sonuçları kullan
                if rule_confidence >= confidence_threshold:
                    labels, confidence = rule_labels, rule_confidence
                    method = LabelingMethod.RULE_BASED  # İstatistikler için metodu güncelle
                    
                # Geçmediyse LLM tabanlı dene
                elif self.llm_service:
                    llm_labels, llm_confidence = self._label_llm_based(document, schema)
                    
                    if llm_confidence >= confidence_threshold:
                        labels, confidence = llm_labels, llm_confidence
                        method = LabelingMethod.LLM_BASED  # İstatistikler için metodu güncelle
                        
                    # LLM de yeterli değilse gömme tabanlı dene
                    elif self.embedding_service:
                        emb_labels, emb_confidence = self._label_embedding_based(document, schema)
                        labels, confidence = emb_labels, emb_confidence
                        method = LabelingMethod.EMBEDDING_BASED  # İstatistikler için metodu güncelle
                        
                    else:
                        # Yeterince güvenli bir etiketleme yapılamadı
                        return document
                        
                # LLM yoksa ve kural tabanlı yeterli değilse gömme tabanlı dene
                elif self.embedding_service:
                    emb_labels, emb_confidence = self._label_embedding_based(document, schema)
                    labels, confidence = emb_labels, emb_confidence
                    method = LabelingMethod.EMBEDDING_BASED  # İstatistikler için metodu güncelle
                    
                else:
                    # Hiçbir yöntem kullanılamıyor veya güvenilir değil
                    return document
            
            else:
                logger.warning(f"Desteklenmeyen etiketleme metodu: {method}")
                return document
            
            # Eşik kontrolü
            if confidence < confidence_threshold:
                return document
                
            # Etiketleri metadataya ekle
            metadata["labels"] = labels
            metadata["labeling"] = {
                "schema_id": schema_id,
                "method": method,
                "confidence": confidence,
                "timestamp": time.time()
            }
            
            # İstatistikleri güncelle
            self.stats["labeled_documents"] += 1
            self.stats["schema_stats"][schema_id]["success"] += 1
            self.stats["schema_stats"][schema_id]["method_stats"][method.value] += 1
            
            # Etiket dağılımı istatistiklerini güncelle
            for label in labels:
                if label not in self.stats["schema_stats"][schema_id]["label_distribution"]:
                    self.stats["schema_stats"][schema_id]["label_distribution"][label] = 0
                self.stats["schema_stats"][schema_id]["label_distribution"][label] += 1
            
            # Etiketlenmiş belgeyi döndür
            return Document(
                id=document.id,
                text=document.text,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Etiketleme hatası: {str(e)}")
            return document
    
    def batch_label_documents(
        self, 
        documents: List[Document], 
        schema_id: str,
        method: LabelingMethod = LabelingMethod.HYBRID,
        confidence_threshold: float = 0.7
    ) -> List[Document]:
        """
        Belge listesini etiketler.
        
        Args:
            documents: Etiketlenecek belgeler
            schema_id: Kullanılacak etiketleme şeması ID'si
            method: Etiketleme metodu
            confidence_threshold: Güven eşiği
            
        Returns:
            List[Document]: Etiketlenmiş belgeler
        """
        labeled_documents = []
        
        for document in documents:
            labeled_document = self.label_document(
                document, 
                schema_id, 
                method, 
                confidence_threshold
            )
            labeled_documents.append(labeled_document)
        
        return labeled_documents
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Etiketleme istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        return self.stats
    
    def _prepare_rule_based_labels(self, schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Kural tabanlı etiketleri hazırlar.
        
        Args:
            schema: Etiketleme şeması
            
        Returns:
            Dict[str, Dict[str, Any]]: Hazırlanan kurallar
        """
        rules = {}
        
        # Etiketleri al
        labels = schema.get("labels", [])
        
        # Her etiket için kuralları oluştur
        for label_info in labels:
            label = label_info["name"]
            
            # Anahtar kelime kurallarını derle
            if "keywords" in label_info:
                keyword_patterns = []
                
                for keyword in label_info["keywords"]:
                    # Basit kelime eşleşmesi için düzenli ifade oluştur
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    try:
                        regex = re.compile(pattern)
                        keyword_patterns.append(regex)
                    except Exception as e:
                        logger.warning(f"Geçersiz anahtar kelime paterni: {keyword}, {str(e)}")
                
                rules[label] = {
                    "patterns": keyword_patterns,
                    "weight": label_info.get("weight", 1.0)
                }
        
        return rules
    
    def _label_rule_based(self, document: Document, schema_id: str) -> Tuple[List[str], float]:
        """
        Kural tabanlı etiketleme yapar.
        
        Args:
            document: Etiketlenecek belge
            schema_id: Etiketleme şeması ID'si
            
        Returns:
            Tuple[List[str], float]: Etiketler ve güven skoru
        """
        import re
        
        # Şema kurallarını al
        rules = self.rule_based_labels.get(schema_id, {})
        
        if not rules:
            return [], 0.0
        
        # Metin içeriği küçük harfe çevir
        text = document.text.lower()
        
        # Her etiket için eşleşme puanlarını hesapla
        scores = {}
        total_weight = 0
        
        for label, rule_info in rules.items():
            patterns = rule_info["patterns"]
            weight = rule_info["weight"]
            total_weight += weight
            
            # Eşleşmeleri say
            match_count = 0
            
            for pattern in patterns:
                matches = pattern.findall(text)
                match_count += len(matches)
            
            # Puanı hesapla (eşleşme sayısı * ağırlık)
            scores[label] = match_count * weight
        
        # En yüksek puanlı etiketleri seç
        if not scores:
            return [], 0.0
            
        # Toplam puanı hesapla ve normalleştir
        total_score = sum(scores.values())
        
        if total_score == 0:
            return [], 0.0
            
        # Puanları normalleştir
        normalized_scores = {label: score / total_score for label, score in scores.items()}
        
        # En yüksek puanlı etiketleri seç (0.3'ten büyük olanlar)
        threshold = 0.3
        selected_labels = [label for label, score in normalized_scores.items() if score >= threshold]
        
        # Güven skorunu hesapla - en yüksek puanı al
        confidence = max(normalized_scores.values()) if normalized_scores else 0.0
        
        return selected_labels, confidence
    
    def _label_llm_based(self, document: Document, schema: Dict[str, Any]) -> Tuple[List[str], float]:
        """
        LLM tabanlı etiketleme yapar.
        
        Args:
            document: Etiketlenecek belge
            schema: Etiketleme şeması
            
        Returns:
            Tuple[List[str], float]: Etiketler ve güven skoru
        """
        if not self.llm_service:
            logger.warning("LLM servisi tanımlanmamış, LLM tabanlı etiketleme yapılamıyor.")
            return [], 0.