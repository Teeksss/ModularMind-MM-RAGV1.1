"""
Semantik bölümleme stratejileri.
"""

import logging
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

from ..base import BaseChunker, Document, Chunk, ChunkingError

logger = logging.getLogger(__name__)

class SemanticTextSplitter(BaseChunker):
    """Metni semantik benzerliğe göre parçalara bölen sınıf"""
    
    def __init__(
        self,
        embedding_func: Callable[[str], List[float]],
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        threshold: float = 0.75,
        initial_splitter: Optional[BaseChunker] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Semantik bölümleyici başlatır
        
        Args:
            embedding_func: Embedding fonksiyonu
            chunk_size: Başlangıç parça boyutu
            chunk_overlap: Parça örtüşme boyutu
            threshold: Benzerlik eşiği (0-1 arası)
            initial_splitter: İlk bölümleme için kullanılacak bölümleyici
            config: Ek yapılandırma
        """
        super().__init__(config)
        self.embedding_func = embedding_func
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.threshold = threshold
        
        # İlk bölümleme için bölümleyici
        if initial_splitter is None:
            from .size import CharacterTextSplitter
            initial_splitter = CharacterTextSplitter(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap
            )
        
        self.initial_splitter = initial_splitter
    
    def split(self, document: Document) -> List[Chunk]:
        """
        Belgeyi semantik benzerliğe göre parçalara böler
        
        Args:
            document: Bölünecek belge
            
        Returns:
            List[Chunk]: Parçalar listesi
        """
        text = document.text
        
        if not text:
            return []
        
        try:
            # İlk olarak temel bölümleyici ile böl
            initial_chunks = self.initial_splitter.split(document)
            
            # Eğer parça sayısı 1 ise direkt döndür
            if len(initial_chunks) <= 1:
                return initial_chunks
            
            # Semantik bölümlemeyi uygula
            return self._semantic_merge(initial_chunks)
        except Exception as e:
            logger.error(f"Semantik bölümleme hatası: {str(e)}")
            # Hata olursa temel bölümleyici ile devam et
            return self.initial_splitter.split(document)
    
    def _semantic_merge(self, chunks: List[Chunk]) -> List[Chunk]:
        """
        Parçaları semantik benzerliğe göre birleştirir
        
        Args:
            chunks: Birleştirilecek parçalar
            
        Returns:
            List[Chunk]: Semantik olarak birleştirilmiş parçalar
        """
        # Parça sayısı 1 ise direkt döndür
        if len(chunks) <= 1:
            return chunks
        
        try:
            # Her parça için embedding hesapla
            embeddings = []
            for chunk in chunks:
                try:
                    embedding = self.embedding_func(chunk.text)
                    embeddings.append(embedding)
                except Exception as e:
                    logger.error(f"Embedding hesaplama hatası: {str(e)}")
                    # Embedding hesaplanamazsa boş bir vektör kullan
                    embedding_size = len(embeddings[0]) if embeddings else 768
                    embeddings.append([0.0] * embedding_size)
            
            # Parçaları birleştir
            merged_chunks = []
            current_chunks = [chunks[0]]
            current_embedding = embeddings[0]
            
            for i in range(1, len(chunks)):
                # Mevcut parçanın embedding'i ve yeni parçanın embedding'i arasındaki benzerliği hesapla
                similarity = self._cosine_similarity(current_embedding, embeddings[i])
                
                # Benzerlik eşiğin üzerindeyse birleştir
                if similarity >= self.threshold:
                    current_chunks.append(chunks[i])
                    # Embedding'leri ortalamasını al
                    current_embedding = self._average_embeddings([current_embedding, embeddings[i]])
                else:
                    # Benzerlik eşiğin altındaysa yeni parça oluştur
                    merged_chunk = self._merge_chunks(current_chunks)
                    merged_chunks.append(merged_chunk)
                    
                    # Yeni parçaya başla
                    current_chunks = [chunks[i]]
                    current_embedding = embeddings[i]
            
            # Son parçayı ekle
            if current_chunks:
                merged_chunk = self._merge_chunks(current_chunks)
                merged_chunks.append(merged_chunk)
            
            return merged_chunks
        except Exception as e:
            logger.error(f"Semantik birleştirme hatası: {str(e)}")
            # Hata olursa orijinal parçaları döndür
            return chunks
    
    def _merge_chunks(self, chunks: List[Chunk]) -> Chunk:
        """
        Parçaları birleştirir
        
        Args:
            chunks: Birleştirilecek parçalar
            
        Returns:
            Chunk: Birleştirilmiş parça
        """
        if not chunks:
            return None
        
        # Tek parça varsa direkt döndür
        if len(chunks) == 1:
            return chunks[0]
        
        # Parçaları birleştir
        merged_text = " ".join([chunk.text for chunk in chunks])
        
        # Birleştirilmiş parça meta verileri
        merged_metadata = {
            **chunks[0].metadata,
            "merged_chunk_count": len(chunks),
            "merged_chunk_indices": [chunk.index for chunk in chunks]
        }
        
        # Yeni parça oluştur
        merged_chunk = Chunk(
            text=merged_text,
            metadata=merged_metadata,
            doc_id=chunks[0].doc_id,
            index=chunks[0].index
        )
        
        return merged_chunk
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        İki vektör arasındaki kosinüs benzerliğini hesaplar
        
        Args:
            vec1: Birinci vektör
            vec2: İkinci vektör
            
        Returns:
            float: Kosinüs benzerliği (0-1 arası)
        """
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        # Sıfır vektörü kontrolü
        if np.all(vec1 == 0) or np.all(vec2 == 0):
            return 0.0
        
        # Kosinüs benzerliği
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        
        # Benzerlik değerini 0-1 aralığına sınırla
        return float(max(0.0, min(1.0, similarity)))
    
    def _average_embeddings(self, embeddings: List[List[float]]) -> List[float]:
        """
        Embedding'lerin ortalamasını alır
        
        Args:
            embeddings: Embedding'ler listesi
            
        Returns:
            List[float]: Ortalama embedding
        """
        if not embeddings:
            return []
        
        # Vektörleri numpy dizisine dönüştür
        np_embeddings = np.array(embeddings)
        
        # Ortalamasını al
        average = np.mean(np_embeddings, axis=0)
        
        # Vektörü normalize et
        norm = np.linalg.norm(average)
        if norm > 0:
            average = average / norm
        
        return average.tolist()