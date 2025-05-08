"""
Belge bölümleme için temel sınıflar.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class ChunkingError(Exception):
    """Bölümleme hatası için temel istisna"""
    pass

class Chunk:
    """Bir belge parçasını temsil eder"""
    
    def __init__(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        index: Optional[int] = None
    ):
        """
        Belge parçası başlatır
        
        Args:
            text: Parça metni
            metadata: Parça meta verileri
            doc_id: Belge kimliği
            chunk_id: Parça kimliği
            index: Parça dizini
        """
        self.text = text
        self.metadata = metadata or {}
        self.doc_id = doc_id
        self.chunk_id = chunk_id
        self.index = index
    
    def __str__(self) -> str:
        return f"Chunk(id={self.chunk_id}, len={len(self.text)}, doc_id={self.doc_id})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "chunk_id": self.chunk_id,
            "index": self.index
        }

class Document:
    """Bir belgeyi temsil eder"""
    
    def __init__(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None
    ):
        """
        Belge başlatır
        
        Args:
            text: Belge metni
            metadata: Belge meta verileri
            doc_id: Belge kimliği
        """
        self.text = text
        self.metadata = metadata or {}
        self.doc_id = doc_id
        self.chunks: List[Chunk] = []
    
    def __str__(self) -> str:
        return f"Document(id={self.doc_id}, len={len(self.text)}, chunks={len(self.chunks)})"
    
    def __repr__(self) -> str:
        return self.__str__()
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "text": self.text,
            "metadata": self.metadata,
            "doc_id": self.doc_id,
            "chunks": [chunk.to_dict() for chunk in self.chunks]
        }
    
    def add_chunk(self, chunk: Chunk) -> None:
        """
        Belgeye parça ekler
        
        Args:
            chunk: Eklenecek parça
        """
        if not chunk.doc_id:
            chunk.doc_id = self.doc_id
        
        if not chunk.index:
            chunk.index = len(self.chunks)
        
        self.chunks.append(chunk)

class BaseChunker(ABC):
    """Belge bölümleme için temel sınıf"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Bölümleyici başlatır
        
        Args:
            config: Yapılandırma
        """
        self.config = config or {}
    
    @abstractmethod
    def split(self, document: Document) -> List[Chunk]:
        """
        Belgeyi parçalara böler
        
        Args:
            document: Bölünecek belge
            
        Returns:
            List[Chunk]: Parçalar listesi
        """
        pass
    
    def clean_text(self, text: str) -> str:
        """
        Metni temizler
        
        Args:
            text: Temizlenecek metin
            
        Returns:
            str: Temizlenmiş metin
        """
        # Çoklu boşlukları tekli boşluğa çevirir
        text = ' '.join(text.split())
        
        # Trim yapar
        text = text.strip()
        
        return text
    
    def create_chunk_id(self, doc_id: str, index: int) -> str:
        """
        Parça kimliği oluşturur
        
        Args:
            doc_id: Belge kimliği
            index: Parça dizini
            
        Returns:
            str: Parça kimliği
        """
        return f"{doc_id}_chunk_{index}"
    
    def process_document(self, document: Document) -> Document:
        """
        Belgeyi işler ve parçalara böler
        
        Args:
            document: İşlenecek belge
            
        Returns:
            Document: İşlenmiş belge
        """
        # Metni temizle
        document.text = self.clean_text(document.text)
        
        # Belgeyi parçalara böl
        chunks = self.split(document)
        
        # Parçaları belgeye ekle
        for i, chunk in enumerate(chunks):
            if not chunk.chunk_id:
                chunk.chunk_id = self.create_chunk_id(document.doc_id, i)
            
            chunk.index = i
            document.add_chunk(chunk)
        
        return document