"""
DocumentChunker modülü için test dosyası.
Test coverage artırımı için oluşturulmuştur.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from ModularMind.API.services.retrieval.chunking import DocumentChunker, ChunkingStrategy

class TestDocumentChunker:
    """DocumentChunker test sınıfı."""
    
    @pytest.fixture
    def sample_document(self):
        """Örnek belge."""
        return {
            "id": "doc1",
            "text": "Bu bir örnek belgedir. Birçok cümle içerir. Bu chunking algoritması tarafından parçalanacaktır. " +
                    "Her chunk belirli bir boyutta olacaktır. Örtüşme miktarı da ayarlanabilir.",
            "metadata": {
                "source": "test",
                "language": "tr",
                "created_at": "2025-01-01"
            }
        }
    
    @pytest.fixture
    def chunker(self):
        """DocumentChunker nesnesi."""
        return DocumentChunker(
            chunk_size=40,
            chunk_overlap=5,
            strategy=ChunkingStrategy.PARAGRAPH
        )
    
    def test_chunker_initialization(self):
        """Başlatma testi."""
        chunker = DocumentChunker(
            chunk_size=50,
            chunk_overlap=10,
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        assert chunker.chunk_size == 50
        assert chunker.chunk_overlap == 10
        assert chunker.strategy == ChunkingStrategy.FIXED_SIZE
    
    def test_chunker_with_default_values(self):
        """Varsayılan değerlerle başlatma testi."""
        chunker = DocumentChunker()
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 50
        assert chunker.strategy == ChunkingStrategy.PARAGRAPH
    
    def test_fixed_size_chunking(self, sample_document):
        """Sabit boyut parçalama testi."""
        chunker = DocumentChunker(
            chunk_size=40,
            chunk_overlap=5,
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        
        chunks = chunker.chunk_document(sample_document)
        
        # Doğru sayıda chunk oluşturulduğunu doğrula
        assert len(chunks) > 1
        
        # Chunk'ların doğru boyutta olduğunu doğrula
        for chunk in chunks:
            # İlk ve son chunk dışındakiler için sınıra yakın olmalı
            if chunk != chunks[0] and chunk != chunks[-1]:
                assert len(chunk["text"]) <= 40
    
    def test_paragraph_chunking(self, sample_document):
        """Paragraf parçalama testi."""
        chunker = DocumentChunker(
            chunk_size=200,  # Tüm metni tek bir chunk yapacak kadar büyük
            chunk_overlap=5,
            strategy=ChunkingStrategy.PARAGRAPH
        )
        
        # Paragraf ayırıcıları ekle
        sample_document["text"] = "Birinci paragraf.\n\nİkinci paragraf.\n\nÜçüncü paragraf."
        
        chunks = chunker.chunk_document(sample_document)
        
        # Paragraf sayısına göre chunk oluşturulduğunu doğrula
        assert len(chunks) == 3
        assert "Birinci paragraf" in chunks[0]["text"]
        assert "İkinci paragraf" in chunks[1]["text"]
        assert "Üçüncü paragraf" in chunks[2]["text"]
    
    def test_sentence_chunking(self, sample_document):
        """Cümle parçalama testi."""
        chunker = DocumentChunker(
            chunk_size=100,  # Tek bir chunk için fazla büyük
            chunk_overlap=5,
            strategy=ChunkingStrategy.SENTENCE
        )
        
        chunks = chunker.chunk_document(sample_document)
        
        # Birden fazla chunk oluşturulduğunu doğrula
        assert len(chunks) > 1
        
        # Her chunk'ın tam cümle(ler) içerdiğini doğrula
        for chunk in chunks:
            # Her chunk'ın sonunda nokta, soru işareti veya ünlem olmalı
            text = chunk["text"].strip()
            assert text[-1] in ['.', '?', '!']
    
    def test_metadata_preservation(self, sample_document, chunker):
        """Metadata korunması testi."""
        chunks = chunker.chunk_document(sample_document)
        
        # Her chunk'ın orijinal belgenin metadata bilgisini içerdiğini doğrula
        for chunk in chunks:
            assert "metadata" in chunk
            assert "doc_id" in chunk["metadata"]
            assert chunk["metadata"]["doc_id"] == sample_document["id"]
            
            # Orijinal metadatanın korunduğunu doğrula
            for key, value in sample_document["metadata"].items():
                assert chunk["metadata"][key] == value
    
    def test_chunk_ids_generation(self, sample_document, chunker):
        """Chunk ID'leri oluşturma testi."""
        chunks = chunker.chunk_document(sample_document)
        
        # Her chunk'ın benzersiz bir ID'si olduğunu doğrula
        chunk_ids = [chunk["id"] for chunk in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))  # Benzersiz ID'ler
        
        # Her chunk ID'sinin belge ID'si ile başladığını doğrula
        for chunk_id in chunk_ids:
            assert chunk_id.startswith(sample_document["id"])
    
    def test_empty_document_handling(self, chunker):
        """Boş belge işleme testi."""
        empty_doc = {
            "id": "empty_doc",
            "text": "",
            "metadata": {"source": "test"}
        }
        
        chunks = chunker.chunk_document(empty_doc)
        
        # Boş belge için boş chunk listesi döndüğünü doğrula
        assert len(chunks) == 0
    
    def test_large_chunk_size_handling(self, sample_document, chunker):
        """Büyük chunk boyutu işleme testi."""
        # Belgenin boyutundan daha büyük chunk boyutu
        large_chunker = DocumentChunker(
            chunk_size=1000,  # Belgenin tamamından daha büyük
            chunk_overlap=5,
            strategy=ChunkingStrategy.FIXED_SIZE
        )
        
        chunks = large_chunker.chunk_document(sample_document)
        
        # Tüm belgenin tek bir chunk olduğunu doğrula
        assert len(chunks) == 1
        assert chunks[0]["text"] == sample_document["text"]
    
    def test_custom_separator_chunking(self, sample_document):
        """Özel ayırıcı ile parçalama testi."""
        # Özel ayırıcıyı belirle
        with patch('ModularMind.API.services.retrieval.chunking.ChunkingStrategy') as mock_strategy:
            # CUSTOM stratejisi için özel bir değer oluştur
            mock_strategy.CUSTOM = "custom"
            
            # Chunker'ı özel ayırıcı ile başlat
            chunker = DocumentChunker(
                chunk_size=100,
                chunk_overlap=5,
                strategy="custom",
                separator="##"
            )
            
            # Test belgesi
            sample_document["text"] = "İlk bölüm##İkinci bölüm##Üçüncü bölüm"
            
            # Parçalama işlemi
            chunks = chunker.chunk_document(sample_document)
            
            # Doğru parçalandığını doğrula
            assert len(chunks) == 3
            assert chunks[0]["text"] == "İlk bölüm"
            assert chunks[1]["text"] == "İkinci bölüm"
            assert chunks[2]["text"] == "Üçüncü bölüm"