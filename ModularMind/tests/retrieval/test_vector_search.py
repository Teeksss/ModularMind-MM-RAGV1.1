"""
Vektör arama modülü için test dosyası.
Test coverage artırımı için oluşturulmuştur.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from ModularMind.API.services.retrieval.search import VectorSearch
from ModularMind.API.services.retrieval.embedding import EmbeddingService

class TestVectorSearch:
    """VectorSearch test sınıfı."""
    
    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding servisi."""
        mock = MagicMock(spec=EmbeddingService)
        # Herhangi bir metni, sabit bir vektöre dönüştür
        mock.get_embedding.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        return mock
    
    @pytest.fixture
    def mock_vector_db(self):
        """Mock vektör veritabanı."""
        mock = MagicMock()
        mock.query.return_value = [
            {
                "id": "chunk1", 
                "text": "Örnek metin içeriği bir", 
                "metadata": {"source": "doc1"}, 
                "distance": 0.15
            },
            {
                "id": "chunk2", 
                "text": "Örnek metin içeriği iki", 
                "metadata": {"source": "doc2"}, 
                "distance": 0.25
            },
            {
                "id": "chunk3", 
                "text": "Örnek metin içeriği üç", 
                "metadata": {"source": "doc3"}, 
                "distance": 0.35
            }
        ]
        return mock
    
    @pytest.fixture
    def vector_search(self, mock_embedding_service, mock_vector_db):
        """VectorSearch nesnesi."""
        return VectorSearch(
            embedding_service=mock_embedding_service,
            vector_db=mock_vector_db
        )
    
    def test_vector_search_initialization(self, mock_embedding_service, mock_vector_db):
        """Başlatma testi."""
        vector_search = VectorSearch(
            embedding_service=mock_embedding_service,
            vector_db=mock_vector_db
        )
        assert vector_search.embedding_service == mock_embedding_service
        assert vector_search.vector_db == mock_vector_db
    
    def test_search_basic(self, vector_search, mock_embedding_service, mock_vector_db):
        """Temel arama işlevselliği testi."""
        query = "Örnek bir sorgu"
        
        # Aramayı gerçekleştir
        results = vector_search.search(query)
        
        # Embedding servisinin çağrıldığını doğrula
        mock_embedding_service.get_embedding.assert_called_once_with(query)
        
        # Vector DB'nin doğru parametrelerle çağrıldığını doğrula
        mock_vector_db.query.assert_called_once()
        
        # Sonuçların doğru dönüştürüldüğünü doğrula
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"
        assert results[0]["score"] == 0.85  # 1.0 - distance
        assert results[1]["score"] == 0.75  # 1.0 - distance
        assert results[2]["score"] == 0.65  # 1.0 - distance
    
    def test_search_with_top_k(self, vector_search, mock_vector_db):
        """top_k parametresi testi."""
        query = "Örnek bir sorgu"
        
        # Belirli bir top_k ile aramayı gerçekleştir
        vector_search.search(query, top_k=2)
        
        # Vector DB'nin doğru top_k ile çağrıldığını doğrula
        call_kwargs = mock_vector_db.query.call_args[1]
        assert call_kwargs.get('top_k') == 2
    
    def test_search_with_filters(self, vector_search, mock_vector_db):
        """Filtrelerle arama testi."""
        query = "Örnek bir sorgu"
        filters = {"source": "doc1"}
        
        # Filtrelerle aramayı gerçekleştir
        vector_search.search(query, filters=filters)
        
        # Vector DB'nin doğru filtrelerle çağrıldığını doğrula
        call_kwargs = mock_vector_db.query.call_args[1]
        assert call_kwargs.get('filter') == filters
    
    def test_search_empty_results(self, vector_search, mock_vector_db):
        """Boş sonuçlar testi."""
        # Boş sonuç döndürmesi için mock'u ayarla
        mock_vector_db.query.return_value = []
        
        query = "Sonuç bulunamayan sorgu"
        
        # Aramayı gerçekleştir
        results = vector_search.search(query)
        
        # Boş bir liste döndüğünü doğrula
        assert results == []
    
    @pytest.mark.parametrize("distance,expected_score", [
        (0.0, 1.0),   # Tam eşleşme
        (0.5, 0.5),   # Kısmi eşleşme
        (1.0, 0.0)    # Hiç eşleşme yok
    ])
    def test_score_calculation(self, vector_search, mock_embedding_service, distance, expected_score):
        """Puan hesaplama testi."""
        query = "Puan hesaplama sorgusu"
        
        # Belirli bir uzaklık değeri döndürmesi için mock'u ayarla
        mock_vector_db = MagicMock()
        mock_vector_db.query.return_value = [
            {"id": "chunk1", "text": "Test", "metadata": {}, "distance": distance}
        ]
        
        # Mock vector DB'yi kullanarak yeni bir VectorSearch nesnesi oluştur
        vs = VectorSearch(
            embedding_service=mock_embedding_service,
            vector_db=mock_vector_db
        )
        
        # Aramayı gerçekleştir
        results = vs.search(query)
        
        # Puanın doğru hesaplandığını doğrula
        assert len(results) == 1
        assert results[0]["score"] == pytest.approx(expected_score, abs=1e-6)
    
    def test_embedding_service_error_handling(self, vector_search, mock_embedding_service):
        """Embedding servisi hata işleme testi."""
        # Hata fırlatması için mock'u ayarla
        mock_embedding_service.get_embedding.side_effect = Exception("Embedding error")
        
        query = "Hata oluşturacak sorgu"
        
        # Hatanın yakalanıp yeniden fırlatıldığını doğrula
        with pytest.raises(Exception, match="Embedding error"):
            vector_search.search(query)
    
    @patch('ModularMind.API.services.retrieval.search.logger')
    def test_vector_db_error_logging(self, mock_logger, vector_search, mock_embedding_service):
        """VectorDB hatalarının loglanması testi."""
        # VectorDB hatası
        mock_vector_db = MagicMock()
        mock_vector_db.query.side_effect = Exception("VectorDB error")
        
        # Mock vector DB'yi kullanarak yeni bir VectorSearch nesnesi oluştur
        vs = VectorSearch(
            embedding_service=mock_embedding_service,
            vector_db=mock_vector_db
        )
        
        query = "Hata oluşturacak sorgu"
        
        # Hatanın yakalanıp yeniden fırlatıldığını doğrula
        with pytest.raises(Exception):
            vs.search(query)
        
        # Hatanın loglandığını doğrula
        mock_logger.error.assert_called_once()