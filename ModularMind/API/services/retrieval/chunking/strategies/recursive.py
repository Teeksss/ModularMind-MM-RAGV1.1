"""
Özyinelemeli bölümleme stratejileri.
"""

import re
import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from ..base import BaseChunker, Document, Chunk, ChunkingError

logger = logging.getLogger(__name__)

class RecursiveTextSplitter(BaseChunker):
    """Metni özyinelemeli olarak bölen sınıf"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: Optional[List[str]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Özyinelemeli bölümleyici başlatır
        
        Args:
            chunk_size: Hedef parça boyutu (karakter sayısı)
            chunk_overlap: Parça örtüşme boyutu (karakter sayısı)
            separators: Bölme ayırıcıları listesi, None ise varsayılan ayırıcılar kullanılır
            config: Ek yapılandırma
        """
        super().__init__(config)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Varsayılan ayırıcılar
        self.separators = separators or [
            "\n\n",      # Paragraf
            "\n",        # Satır sonları
            ". ",        # Cümleler
            "! ",        # Ünlem ile biten cümleler
            "? ",        # Soru ile biten cümleler
            ";",         # Noktalı virgül
            ",",         # Virgül
            " ",         # Kelimeler
            ""           # Karakterler
        ]
    
    def split(self, document: Document) -> List[Chunk]:
        """
        Belgeyi özyinelemeli olarak parçalara böler
        
        Args:
            document: Bölünecek belge
            
        Returns:
            List[Chunk]: Parçalar listesi
        """
        text = document.text
        
        if not text:
            return []
        
        # Metni özyinelemeli olarak böl
        splits = self._split_text(text)
        
        # Parçaları oluştur
        chunks = []
        for i, split_text in enumerate(splits):
            # Parça meta verileri
            chunk_metadata = {
                **document.metadata,
                "chunk_size": len(split_text),
                "chunk_index": i
            }
            
            chunk = Chunk(
                text=split_text,
                metadata=chunk_metadata,
                doc_id=document.doc_id,
                index=i
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _split_text(self, text: str) -> List[str]:
        """
        Metni özyinelemeli olarak böler
        
        Args:
            text: Bölünecek metin
            
        Returns:
            List[str]: Bölünmüş metin parçaları
        """
        # Metin zaten hedef boyuttan küçükse direkt döndür
        if len(text) <= self.chunk_size:
            return [text]
        
        # Her ayırıcı için dene
        for separator in self.separators:
            # Boş ayırıcı en son seçenek
            if separator == "":
                return self._split_by_character(text)
            
            # Ayırıcıya göre böl
            if separator in text:
                splits = self._split_by_separator(text, separator)
                
                # Daha küçük parçalara böl
                final_splits = []
                for split in splits:
                    # Parça hala büyükse özyinelemeli olarak böl
                    if len(split) > self.chunk_size:
                        final_splits.extend(self._split_text(split))
                    else:
                        final_splits.append(split)
                
                # Parçaları birleştirerek hedef boyuta yaklaştır
                return self._merge_splits(final_splits)
        
        # Eğer hiçbir ayırıcı bulunamazsa, karakter bazında böl
        return self._split_by_character(text)
    
    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """
        Metni belirli bir ayırıcıya göre böler
        
        Args:
            text: Bölünecek metin
            separator: Ayırıcı
            
        Returns:
            List[str]: Bölünmüş metin parçaları
        """
        splits = text.split(separator)
        
        # Eğer ayırıcı önemli bir ayırıcıysa (boşluk hariç), ayırıcıyı parçalara dahil et
        if separator != " ":
            for i in range(len(splits) - 1):
                splits[i] += separator
        
        # Boş parçaları filtrele
        return [s for s in splits if s]
    
    def _split_by_character(self, text: str) -> List[str]:
        """
        Metni karakter bazında böler
        
        Args:
            text: Bölünecek metin
            
        Returns:
            List[str]: Bölünmüş metin parçaları
        """
        # Metni karakter bazında bölmek çok küçük parçalar oluşturur
        # Bu nedenle direkt chunk_size kadar parçalara bölelim
        splits = []
        for i in range(0, len(text), self.chunk_size):
            splits.append(text[i:i + self.chunk_size])
        
        return splits
    
    def _merge_splits(self, splits: List[str]) -> List[str]:
        """
        Küçük parçaları birleştirerek hedef boyuta yaklaştırır
        
        Args:
            splits: Birleştirilecek parçalar
            
        Returns:
            List[str]: Birleştirilmiş parçalar
        """
        # Eğer parça yoksa boş liste döndür
        if not splits:
            return []
        
        # Eğer tek parça varsa direkt döndür
        if len(splits) == 1:
            return splits
        
        # Parçaları birleştir
        merged_splits = []
        current_split = splits[0]
        
        for split in splits[1:]:
            # Eğer birleştirilmiş metin hedef boyutu aşmıyorsa birleştir
            if len(current_split) + len(split) <= self.chunk_size:
                current_split += split
            else:
                # Hedef boyutu aşıyorsa yeni parça olarak ekle
                merged_splits.append(current_split)
                current_split = split
        
        # Son parçayı ekle
        if current_split:
            merged_splits.append(current_split)
        
        # Örtüşme ekle
        if self.chunk_overlap > 0 and len(merged_splits) > 1:
            return self._add_overlap(merged_splits)
        
        return merged_splits
    
    def _add_overlap(self, splits: List[str]) -> List[str]:
        """
        Parçalara örtüşme ekler
        
        Args:
            splits: Örtüşme eklenecek parçalar
            
        Returns:
            List[str]: Örtüşme eklenmiş parçalar
        """
        # Örtüşmeli parçalar
        overlapped_splits = []
        
        for i in range(len(splits)):
            # Mevcut parça
            current_split = splits[i]
            
            # Son parça değilse bir sonraki parçadan örtüşme ekle
            if i < len(splits) - 1 and self.chunk_overlap > 0:
                next_split = splits[i + 1]
                overlap_size = min(self.chunk_overlap, len(next_split))
                current_split += next_split[:overlap_size]
            
            overlapped_splits.append(current_split)
        
        return overlapped_splits