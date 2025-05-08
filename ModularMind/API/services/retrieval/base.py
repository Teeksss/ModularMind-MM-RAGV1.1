"""
Retrieval işlemleri için temel sınıflar ve yapılar.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

class SearchResult:
    """Arama sonucu sınıfı"""
    
    def __init__(
        self,
        chunk_id: str,
        document_id: str,
        text: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "vector",
        model_id: Optional[str] = None
    ):
        """
        Arama sonucunu başlatır
        
        Args:
            chunk_id: Belge parçası kimliği
            document_id: Belge kimliği
            text: Parça metni
            score: Benzerlik skoru
            metadata: Meta veriler
            source: Sonuç kaynağı (vector, keyword, hybrid)
            model_id: Kullanılan model kimliği
        """
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.text = text
        self.score = score
        self.metadata = metadata or {}
        self.source = source
        self.model_id = model_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        result = {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "text": self.text,
            "score": self.score,
            "source": self.source
        }
        
        if self.metadata:
            result["metadata"] = self.metadata
        
        if self.model_id:
            result["model_id"] = self.model_id
        
        return result
    
    def __str__(self) -> str:
        return f"SearchResult(id={self.chunk_id}, score={self.score:.4f}, source={self.source})"

class Document:
    """Belge sınıfı"""
    
    def __init__(
        self,
        id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunks: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Belge nesnesini başlatır
        
        Args:
            id: Belge kimliği
            text: Belge metni
            metadata: Meta veriler
            chunks: Belge parçaları
        """
        self.id = id
        self.text = text
        self.metadata = metadata or {}
        self.chunks = chunks or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e dönüştürür"""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
            "chunks": self.chunks
        }
    
    def __str__(self) -> str:
        return f"Document(id={self.id}, chunks={len(self.chunks)})"

class BaseSearcher(ABC):
    """Arama sınıfları için temel arayüz"""
    
    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Arama yapar
        
        Args:
            query: Arama sorgusu
            limit: Sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            
        Returns:
            List[SearchResult]: Arama sonuçları
        """
        pass

class BaseVectorStore(ABC):
    """Vektör deposu için temel arayüz"""
    
    @abstractmethod
    def add_document(
        self,
        document: Union[Document, Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Belge ekler
        
        Args:
            document: Eklenecek belge
            options: Ekleme seçenekleri
            
        Returns:
            Optional[str]: Belge kimliği veya None
        """
        pass
    
    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Belge getirir
        
        Args:
            document_id: Belge kimliği
            
        Returns:
            Optional[Dict[str, Any]]: Belge veya None
        """
        pass
    
    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """
        Belge siler
        
        Args:
            document_id: Silinecek belge kimliği
            
        Returns:
            bool: Silme başarılı mı
        """
        pass
    
    @abstractmethod
    def search_by_text(
        self,
        query: str,
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Metin sorgusu ile arama yapar
        
        Args:
            query: Arama sorgusu
            limit: Sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        pass
    
    @abstractmethod
    def search_by_vector(
        self,
        query_vector: List[float],
        limit: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True,
        embedding_model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Vektör sorgusu ile arama yapar
        
        Args:
            query_vector: Sorgu vektörü
            limit: Sonuç limiti
            filter_metadata: Meta veri filtresi
            include_metadata: Meta verileri dahil et
            embedding_model: Kullanılacak embedding modeli
            
        Returns:
            List[Dict[str, Any]]: Arama sonuçları
        """
        pass