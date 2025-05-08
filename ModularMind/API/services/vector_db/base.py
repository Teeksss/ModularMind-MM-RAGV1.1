"""
Vektör veritabanı yöneticileri için temel sınıflar.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple

class BaseIndexManager(ABC):
    """
    Vektör indeks yöneticileri için temel sınıf.
    
    Bu sınıf, farklı vektör veritabanları için standart bir arayüz sağlar.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        İndeksi başlatır
        
        Returns:
            bool: Başlatma başarılı mı
        """
        pass
    
    @abstractmethod
    def add_item(self, vector: List[float], doc_id: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Vektörü indekse ekler
        
        Args:
            vector: Eklenecek vektör
            doc_id: Belge kimliği
            metadata: Meta veriler
            
        Returns:
            bool: Ekleme başarılı mı
        """
        pass
    
    @abstractmethod
    def add_items_batch(self, vectors: List[List[float]], doc_ids: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Vektörleri toplu olarak indekse ekler
        
        Args:
            vectors: Eklenecek vektörler
            doc_ids: Belge kimlikleri
            metadatas: Meta veriler listesi
            
        Returns:
            bool: Ekleme başarılı mı
        """
        pass
    
    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 10, min_score: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Vektöre en benzer öğeleri arar
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Döndürülecek sonuç sayısı
            min_score: Minimum benzerlik skoru
            
        Returns:
            List[Tuple[str, float]]: (doc_id, score) çiftleri listesi
        """
        pass
    
    @abstractmethod
    def delete_item(self, doc_id: str) -> bool:
        """
        Belge kimliği ile vektörü siler
        
        Args:
            doc_id: Silinecek belge kimliği
            
        Returns:
            bool: Silme başarılı mı
        """
        pass
    
    @abstractmethod
    def save(self, path: str) -> bool:
        """
        İndeksi diske kaydeder
        
        Args:
            path: Kayıt yolu
            
        Returns:
            bool: Kaydetme başarılı mı
        """
        pass
    
    @abstractmethod
    def load(self, path: str) -> bool:
        """
        İndeksi diskten yükler
        
        Args:
            path: Yükleme yolu
            
        Returns:
            bool: Yükleme başarılı mı
        """
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini alır
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        return {}
    
    def optimize(self) -> bool:
        """
        İndeksi optimize eder (Opsiyonel)
        
        Returns:
            bool: Optimizasyon başarılı mı
        """
        return True