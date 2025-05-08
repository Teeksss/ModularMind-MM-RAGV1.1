"""
Reranker modülü için test dosyası.
Test coverage artırımı için oluşturulmuştur.
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from ModularMind.API.services.retrieval.ranking import Reranker, CrossEncoderReranker

class TestReranker:
    """Reranker test sınıfı."""
    
    @pytest.fixture
    def sample_chunks(self):
        """Örnek chunk'lar."""
        return [
            {"id": "chunk1", "text": "Bu örnek bir chunk metnidir.", "metadata": {"doc_id": "doc1"}, "score": 0.85},
            {"id": "chunk2", "text": "Bu başka bir chunk metnidir.", "metadata": {"doc_id": "doc2"}, "score": 0.75},
            {"id": "chunk3", "text": "Bu üçüncü bir chunk metnidir.", "metadata": {"doc_id": "doc3"}, "score": 0.65},
        ]
    
    @pytest.fixture
    def mock_cross_encoder(self):
        """Mock cross encoder modeli."""
        mock = MagicMock()
        # Sorgu ve metinlerin çiftleri için puanlar döndür
        mock.predict.return_value = [0.9, 0.7, 0.8]
        return mock
    
    @pytest.fixture
    def reranker(self, mock_cross_encoder):
        """Reranker nesnesi."""
        with patch('ModularMind.API.services.retrieval.ranking.CrossEncoder', return_value=mock_cross_encoder):
            return CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
    
    def test_reranker_initialization(self):
        """Başlatma testi."""
        with patch('ModularMind.API.services.retrieval.ranking.CrossEncoder'):
            reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")
            assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def test_reranker_rerank(self, reranker, sample_chunks, mock_cross_encoder):
        """Yeniden sıralama testi."""
        query = "Örnek sorgu"
        
        # Yeniden sırala
        results = reranker.rerank(query, sample_chunks)
        
        # Cross encoder'ın çağrıldığını doğrula
        mock_cross_encoder.predict.assert_called_once()
        
        # Sonuçların doğru sıralandığını doğrula
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"  # En yüksek puan (0.9)
        assert results[1]["id"] == "chunk3"  # İkinci en yüksek puan (0.8)
        assert results[2]["id"] == "chunk2"  # En düşük puan (0.7)
        
        # Yeni puanların atandığını doğrula
        assert results[0]["score"] == 0.9
        assert results[1]["score"] == 0.8
        assert results[2]["score"] == 0.7
    
    def test_reranker_with_empty_chunks(self, reranker, mock_cross_encoder):
        """Boş chunk listesi testi."""
        query = "Örnek sorgu"
        
        # Boş liste ile çağır
        results = reranker.rerank(query, [])
        
        # Cross encoder'ın çağrılmadığını doğrula
        mock_cross_encoder.predict.assert_not_called()
        
        # Boş liste döndüğünü doğrula
        assert results == []
    
    def test_reranker_with_single_chunk(self, reranker, mock_cross_encoder):
        """Tek chunk testi."""
        query = "Örnek sorgu"
        chunks = [{"id": "chunk1", "text": "Bu örnek bir chunk metnidir.", "metadata": {"doc_id": "doc1"}, "score": 0.85}]
        
        # Tek bir chunk için yeniden puan döndür
        mock_cross_encoder.predict.return_value = [0.95]
        
        # Yeniden sırala
        results = reranker.rerank(query, chunks)
        
        # Cross encoder'ın çağrıldığını doğrula
        mock_cross_encoder.predict.assert_called_once()
        
        # Sonucun doğru olduğunu doğrula
        assert len(results) == 1
        assert results[0]["id"] == "chunk1"
        assert results[0]["score"] == 0.95
    
    @patch('ModularMind.API.services.retrieval.ranking.logger')
    def test_reranker_error_handling(self, mock_logger, reranker, sample_chunks, mock_cross_encoder):
        """Hata işleme testi."""
        query = "Örnek sorgu"
        
        # Hata fırlatması için mock'u ayarla
        mock_cross_encoder.predict.side_effect = Exception("Reranking error")
        
        # Yeniden sıralamayı çağır (hata yakalanmalı ve orijinal sıralama döndürülmeli)
        results = reranker.rerank(query, sample_chunks)
        
        # Hatanın loglandığını doğrula
        mock_logger.error.assert_called_once()
        
        # Orijinal chunk'ların döndüğünü ve sıralamalarının korunduğunu doğrula
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"
        assert results[1]["id"] == "chunk2"
        assert results[2]["id"] == "chunk3"
        assert results[0]["score"] == 0.85
    
    def test_reranker_with_threshold_filter(self, reranker, sample_chunks, mock_cross_encoder):
        """Eşik filtresi testi."""
        query = "Örnek sorgu"
        
        # Yeni puanlar ayarla
        mock_cross_encoder.predict.return_value = [0.9, 0.3, 0.7]
        
        # 0.5 eşik değeriyle yeniden sırala
        results = reranker.rerank(query, sample_chunks, threshold=0.5)
        
        # Eşik altındaki chunk'ların filtrelendiğini doğrula
        assert len(results) == 2
        assert results[0]["id"] == "chunk1"  # 0.9
        assert results[1]["id"] == "chunk3"  # 0.7
        # chunk2 (0.3) eşik değerin altında olduğu için filtrelenmeli
    
    def test_reranker_with_custom_batch_size(self):
        """Özel batch_size testi."""
        with patch('ModularMind.API.services.retrieval.ranking.CrossEncoder') as mock_cross_encoder_cls:
            # Özel batch_size ile reranker oluştur
            reranker = CrossEncoderReranker(
                model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
                batch_size=16
            )
            
            # CrossEncoder'ın doğru batch_size ile çağrıldığını doğrula
            mock_cross_encoder_cls.assert_called_once_with(
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                device=None,
                max_length=512
            )
            assert reranker.batch_size == 16