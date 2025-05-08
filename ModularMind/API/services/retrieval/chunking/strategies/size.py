"""
Boyut tabanlı bölümleme stratejileri.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Tuple

from ..base import BaseChunker, Document, Chunk, ChunkingError

logger = logging.getLogger(__name__)

class CharacterTextSplitter(BaseChunker):
    """Karaktere göre metin bölümleme"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Karakter tabanlı bölümleyici başlatır
        
        Args:
            chunk_size: Parça boyutu (karakter sayısı)
            chunk_overlap: Parça örtüşme boyutu (karakter sayısı)
            config: Ek yapılandırma
        """
        super().__init__(config)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split(self, document: Document) -> List[Chunk]:
        """
        Belgeyi sabit boyutlu parçalara böler
        
        Args:
            document: Bölünecek belge
            
        Returns:
            List[Chunk]: Parçalar listesi
        """
        text = document.text
        
        if not text:
            return []
        
        chunks = []
        start = 0
        
        # Metin uzunluğu boyunca kaydırarak parçala
        while start < len(text):
            # Parça bitişini belirle
            end = min(start + self.chunk_size, len(text))
            
            # Tam kelimenin sonunda bölmeye çalış (eğer bu parçanın sonu değilse)
            if end < len(text):
                # Sonraki boşluğu veya noktalama işaretini bul
                while end > start and end < len(text) and not text[end].isspace() and text[end] not in ".,;:!?)]}":
                    end -= 1
                
                # Eğer geri giderek boşluk bulamadıysak, ileriye doğru ara
                if end == start:
                    end = start + self.chunk_size
                    while end < len(text) and not text[end].isspace() and text[end] not in ".,;:!?)]}":
                        end += 1
                
                # Hala bulunamadıysa kesme noktasını kullan
                if end >= len(text):
                    end = min(start + self.chunk_size, len(text))
            
            # Parça metnini al
            chunk_text = text[start:end].strip()
            
            # Eğer parça boş değilse ekle
            if chunk_text:
                # Parça meta verileri
                chunk_metadata = {
                    **document.metadata,
                    "chunk_size": len(chunk_text),
                    "chunk_index": len(chunks)
                }
                
                chunk = Chunk(
                    text=chunk_text,
                    metadata=chunk_metadata,
                    doc_id=document.doc_id,
                    index=len(chunks)
                )
                
                chunks.append(chunk)
            
            # Bir sonraki parçanın başlangıcını belirle (örtüşmeyi göz önünde bulundurarak)
            start = min(end, start + self.chunk_size - self.chunk_overlap)
        
        return chunks

class TokenTextSplitter(BaseChunker):
    """Token tabanlı metin bölümleme"""
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        tokenizer: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Token tabanlı bölümleyici başlatır
        
        Args:
            chunk_size: Parça boyutu (token sayısı)
            chunk_overlap: Parça örtüşme boyutu (token sayısı)
            tokenizer: Tokenizer adı (None ise tiktoken kullanılır)
            config: Ek yapılandırma
        """
        super().__init__(config)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer_name = tokenizer or "cl100k_base"  # gpt-4 ve 3.5 için varsayılan
        self.tokenizer = None
    
    def _init_tokenizer(self) -> bool:
        """
        Tokenizer'ı başlatır
        
        Returns:
            bool: Başlatma başarılı mı
        """
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding(self.tokenizer_name)
            return True
        except ImportError:
            logger.error("tiktoken kütüphanesi yüklenmedi. Kurulum: pip install tiktoken")
            return False
        except Exception as e:
            logger.error(f"Tokenizer başlatma hatası: {str(e)}")
            return False
    
    def split(self, document: Document) -> List[Chunk]:
        """
        Belgeyi token sayısına göre parçalara böler
        
        Args:
            document: Bölünecek belge
            
        Returns:
            List[Chunk]: Parçalar listesi
        """
        text = document.text
        
        if not text:
            return []
        
        # Tokenizer'ı başlat
        if not self.tokenizer:
            if not self._init_tokenizer():
                # Başarısız olursa karakter bölümleyiciye geri dön
                logger.warning("Tokenizer başlatılamadı, karakter bölümleyiciye geri dönülüyor")
                fallback = CharacterTextSplitter(
                    chunk_size=self.chunk_size * 4,  # Yaklaşık olarak token -> karakter dönüşümü
                    chunk_overlap=self.chunk_overlap * 4
                )
                return fallback.split(document)
        
        # Metni tokenize et
        tokens = self.tokenizer.encode(text)
        
        chunks = []
        start_idx = 0
        
        # Token listesi boyunca kaydırarak parçala
        while start_idx < len(tokens):
            # Parça bitişini belirle
            end_idx = min(start_idx + self.chunk_size, len(tokens))
            
            # Parça tokenlerini al
            chunk_tokens = tokens[start_idx:end_idx]
            
            # Tokenleri metne çevir
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Parça meta verileri
            chunk_metadata = {
                **document.metadata,
                "token_count": len(chunk_tokens),
                "chunk_index": len(chunks)
            }
            
            chunk = Chunk(
                text=chunk_text,
                metadata=chunk_metadata,
                doc_id=document.doc_id,
                index=len(chunks)
            )
            
            chunks.append(chunk)
            
            # Bir sonraki parçanın başlangıcını belirle (örtüşmeyi göz önünde bulundurarak)
            start_idx = min(end_idx, start_idx + self.chunk_size - self.chunk_overlap)
        
        return chunks

class Recursive