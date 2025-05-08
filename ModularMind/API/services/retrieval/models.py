"""
Vektör depolama modelleri - Çoklu Embedding desteği ile.
"""

import logging
import os
import json
import pickle
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple, Set, Union

logger = logging.getLogger(__name__)

class IndexType(str, Enum):
    """İndeks tipleri."""
    HNSW = "HNSW"
    FAISS = "FAISS"

@dataclass
class VectorStoreConfig:
    """Vektör deposu yapılandırması."""
    index_type: IndexType = IndexType.HNSW
    dimensions: Dict[str, int] = field(default_factory=lambda: {"default": 1536})
    metric: str = "cosine"  # cosine, l2, dot
    storage_path: Optional[str] = None
    hnsw_params: Dict[str, Any] = field(default_factory=lambda: {
        "M": 16,
        "ef_construction": 200,
        "ef_search": 50
    })
    default_embedding_model: str = "default"
    embedding_models: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Ayarları sözlüğe dönüştürür."""
        return {
            "index_type": self.index_type,
            "dimensions": self.dimensions,
            "metric": self.metric,
            "storage_path": self.storage_path,
            "hnsw_params": self.hnsw_params,
            "default_embedding_model": self.default_embedding_model,
            "embedding_models": self.embedding_models
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VectorStoreConfig':
        """Sözlükten yapılandırma oluşturur."""
        if "index_type" in data and isinstance(data["index_type"], str):
            data["index_type"] = IndexType(data["index_type"])
            
        # Eski format kontrolü - tek boyut uyumluluğu için
        if "dimensions" in data and isinstance(data["dimensions"], int):
            data["dimensions"] = {"default": data["dimensions"]}
            
        return cls(**data)

@dataclass
class DocumentMetadata:
    """Belge metadata'sı."""
    source: Optional[str] = None
    source_id: Optional[str] = None
    source_type: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[str] = None
    author: Optional[str] = None
    title: Optional[str] = None
    language: Optional[str] = None
    mime_type: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DocumentChunk:
    """Belge parçası - çoklu embedding desteği ile."""
    id: str
    text: str
    document_id: str
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    embeddings: Dict[str, List[float]] = field(default_factory=dict)
    
    def get_embedding(self, model_id: str = "default") -> Optional[List[float]]:
        """Belirli model için embedding döndürür."""
        return self.embeddings.get(model_id)
    
    def set_embedding(self, embedding: List[float], model_id: str = "default") -> None:
        """Belirli model için embedding ayarlar."""
        self.embeddings[model_id] = embedding
    
    def has_embedding(self, model_id: str = "default") -> bool:
        """Belirli model için embedding var mı kontrol eder."""
        return model_id in self.embeddings and self.embeddings[model_id] is not None

@dataclass
class Document:
    """Belge."""
    id: str
    text: str
    metadata: DocumentMetadata = field(default_factory=DocumentMetadata)
    chunks: List[DocumentChunk] = field(default_factory=list)

class VectorStore:
    """Vektör deposu sınıfı - Çoklu embedding modellerini destekler."""
    
    def __init__(self, config: VectorStoreConfig):
        self.config = config
        self.documents: Dict[str, Document] = {}
        self.document_chunks: Dict[str, DocumentChunk] = {}
        
        # Model başına indeksleri tut - {model_id: index}
        self.indices: Dict[str, Any] = {}
        
        # Model başına ID eşleştirmeleri - {model_id: {numeric_id: chunk_id}}
        self.id_maps: Dict[str, Dict[int, str]] = {}
    
    def add_document(self, document: Document) -> bool:
        """
        Belge ekler.
        
        Args:
            document: Eklenecek belge
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Belgeyi ekle
            self.documents[document.id] = document
            
            # Belge parçalarını ekle
            for chunk in document.chunks:
                self.document_chunks[chunk.id] = chunk
            
            return True
        except Exception as e:
            logger.error(f"Belge ekleme hatası: {str(e)}")
            return False
    
    def add_documents(self, documents: List[Document]) -> bool:
        """
        Belgeleri toplu ekler.
        
        Args:
            documents: Eklenecek belgeler
            
        Returns:
            bool: Başarı durumu
        """
        try:
            for document in documents:
                self.documents[document.id] = document
                
                for chunk in document.chunks:
                    self.document_chunks[chunk.id] = chunk
            
            return True
        except Exception as e:
            logger.error(f"Toplu belge ekleme hatası: {str(e)}")
            return False
    
    def get_document(self, document_id: str) -> Optional[Document]:
        """
        Belge ID'sine göre belge döndürür.
        
        Args:
            document_id: Belge ID
            
        Returns:
            Optional[Document]: Belge
        """
        return self.documents.get(document_id)
    
    def get_document_chunk(self, chunk_id: str) -> Optional[DocumentChunk]:
        """
        Chunk ID'sine göre belge parçası döndürür.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Optional[DocumentChunk]: Belge parçası
        """
        return self.document_chunks.get(chunk_id)
    
    def delete_document(self, document_id: str) -> bool:
        """
        Belge siler.
        
        Args:
            document_id: Belge ID
            
        Returns:
            bool: Başarı durumu
        """
        try:
            # Belgeyi al
            document = self.documents.get(document_id)
            
            if not document:
                logger.warning(f"Silinecek belge bulunamadı: {document_id}")
                return False
            
            # Belge parçalarını sil
            for chunk in document.chunks:
                if chunk.id in self.document_chunks:
                    del self.document_chunks[chunk.id]
            
            # Belgeyi sil
            del self.documents[document_id]
            
            return True
        except Exception as e:
            logger.error(f"Belge silme hatası: {str(e)}")
            return False
    
    def clear(self) -> bool:
        """
        Tüm verileri temizler.
        
        Returns:
            bool: Başarı durumu
        """
        try:
            self.documents = {}
            self.document_chunks = {}
            self.indices = {}
            self.id_maps = {}
            
            return True
        except Exception as e:
            logger.error(f"Veri temizleme hatası: {str(e)}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        İstatistikleri döndürür.
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        # Model bazında embedding sayıları
        model_stats = {}
        for model_id in self.config.embedding_models:
            count = sum(1 for chunk in self.document_chunks.values() if chunk.has_embedding(model_id))
            model_stats[model_id] = count
        
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.document_chunks),
            "index_type": self.config.index_type,
            "dimensions": self.config.dimensions,
            "metric": self.config.metric,
            "embedding_models": model_stats
        }
    
    def build_index(self, model_id: Optional[str] = None) -> bool:
        """
        Vektör indeksini oluşturur. Tek model veya tüm modeller için.
        
        Args:
            model_id: İndeks oluşturulacak model ID (None ise tüm modeller)
            
        Returns:
            bool: Başarı durumu
        """
        from ModularMind.API.services.retrieval.indices import create_index
        
        # Tek model indeksi
        if model_id:
            return create_index(self, model_id)
        
        # Tüm modeller için indeks
        success = True
        for model in self.config.embedding_models:
            if not create_index(self, model):
                success = False
        
        return success
    
    def load_index(self, model_id: Optional[str] = None) -> bool:
        """
        Vektör indeksini yükler. Tek model veya tüm modeller için.
        
        Args:
            model_id: İndeks yüklenecek model ID (None ise tüm modeller)
            
        Returns:
            bool: Başarı durumu
        """
        from ModularMind.API.services.retrieval.indices import load_index
        
        # Tek model indeksi
        if model_id:
            return load_index(self, model_id)
        
        # Tüm modeller için indeks
        success = True
        for model in self.config.embedding_models:
            if not load_index(self, model):
                success = False
        
        return success
    
    def rebuild_index(self, model_id: Optional[str] = None) -> bool:
        """
        Vektör indeksini yeniden oluşturur. Tek model veya tüm modeller için.
        
        Args:
            model_id: İndeks yeniden oluşturulacak model ID (None ise tüm modeller)
            
        Returns:
            bool: Başarı durumu
        """
        from ModularMind.API.services.retrieval.indices import rebuild_index
        
        # Tek model indeksi
        if model_id:
            return rebuild_index(self, model_id)
        
        # Tüm modeller için indeks
        success = True
        for model in self.config.embedding_models:
            if not rebuild_index(self, model):
                success = False
        
        return success
    
    def search(
        self, 
        query_vector: List[float], 
        model_id: str,
        limit: int = 5, 
        min_score_threshold: Optional[float] = None
    ) -> List[Tuple[str, float]]:
        """
        Vektör araması yapar.
        
        Args:
            query_vector: Sorgu vektörü
            model_id: Embedding model ID'si
            limit: Sonuç limiti
            min_score_threshold: Minimum skor eşiği
            
        Returns:
            List[Tuple[str, float]]: (chunk_id, score) çiftleri
        """
        from ModularMind.API.services.retrieval.indices import search_index
        return search_index(self, query_vector, model_id, limit, min_score_threshold)
    
    def save(self) -> bool:
        """
        Vektör deposunu kaydeder.
        
        Returns:
            bool: Başarı durumu
        """
        if not self.config.storage_path:
            logger.error("Kayıt için storage_path gereklidir")
            return False
        
        try:
            # Depolama dizinini oluştur
            os.makedirs(self.config.storage_path, exist_ok=True)
            
            # Yapılandırmayı kaydet
            config_path = os.path.join(self.config.storage_path, "config.json")
            with open(config_path, "w") as f:
                json.dump(self.config.to_dict(), f, indent=2)
            
            # Belgeleri kaydet
            documents_path = os.path.join(self.config.storage_path, "documents.json")
            
            # Belgeleri JSON uyumlu formata dönüştür
            documents_data = {}
            for doc_id, doc in self.documents.items():
                documents_data[doc_id] = {
                    "id": doc.id,
                    "text": doc.text,
                    "metadata": doc.metadata.__dict__,
                    "chunk_ids": [chunk.id for chunk in doc.chunks]
                }
            
            with open(documents_path, "w") as f:
                json.dump(documents_data, f, indent=2)
            
            # Belge parçalarını kaydet
            chunks_path = os.path.join(self.config.storage_path, "chunks.pkl")
            
            with open(chunks_path, "wb") as f:
                pickle.dump(self.document_chunks, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Vektör deposu kaydetme hatası: {str(e)}")
            return False
    
    def load(self) -> bool:
        """
        Vektör deposunu yükler.
        
        Returns:
            bool: Başarı durumu
        """
        if not self.config.storage_path:
            logger.error("Yükleme için storage_path gereklidir")
            return False
        
        try:
            # Yapılandırma dosyası
            config_path = os.path.join(self.config.storage_path, "config.json")
            
            # Yapılandırmayı yükle
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_data = json.load(f)
                
                self.config = VectorStoreConfig.from_dict(config_data)
            
            # Belgeler
            documents_path = os.path.join(self.config.storage_path, "documents.json")
            
            if os.path.exists(documents_path):
                with open(documents_path, "r") as f:
                    documents_data = json.load(f)
                
                self.documents = {}
                
                # Belge parçalarını önce yükle
                chunks_path = os.path.join(self.config.storage_path, "chunks.pkl")
                
                if os.path.exists(chunks_path):
                    with open(chunks_path, "rb") as f:
                        self.document_chunks = pickle.load(f)
                else:
                    self.document_chunks = {}
                
                # Belgeleri oluştur
                for doc_id, doc_data in documents_data.items():
                    metadata = DocumentMetadata(**doc_data["metadata"])
                    
                    # Belge parçalarını al
                    chunks = []
                    for chunk_id in doc_data["chunk_ids"]:
                        if chunk_id in self.document_chunks:
                            chunks.append(self.document_chunks[chunk_id])
                    
                    # Belge oluştur
                    document = Document(
                        id=doc_data["id"],
                        text=doc_data["text"],
                        metadata=metadata,
                        chunks=chunks
                    )
                    
                    self.documents[doc_id] = document
            else:
                self.documents = {}
                self.document_chunks = {}
            
            # İndeksleri yükle - Her model için ayrı ayrı
            for model_id in self.config.embedding_models:
                self.load_index(model_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Vektör deposu yükleme hatası: {str(e)}")
            return False
    
    def close(self) -> None:
        """Vector store bağlantılarını kapatır."""
        # Şimdilik yapılacak bir şey yok
        pass

def get_unique_document_ids(vector_store: VectorStore) -> Set[str]:
    """
    Vektör deposundaki benzersiz belge ID'lerini döndürür.
    
    Args:
        vector_store: Vektör deposu
        
    Returns:
        Set[str]: Benzersiz belge ID'leri
    """
    return set(vector_store.documents.keys())