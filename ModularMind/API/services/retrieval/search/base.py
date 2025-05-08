"""
Retrieval ve arama operasyonları için temel bileşenler.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

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