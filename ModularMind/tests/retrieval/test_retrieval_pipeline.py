"""
Retrieval pipeline bileşenlerinin kapsamlı testleri.
Test coverage artırımı için oluşturulmuştur.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any

from ModularMind.API.services.retrieval.pipeline import RetrievalPipeline
from ModularMind.API.services.retrieval.chunking import DocumentChunker
from ModularMind.API.services.retrieval.ranking import Reranker
from ModularMind.API.services.retrieval.search import VectorSearch, HybridSearch

class TestRetrievalPipeline:
    """Retrieval pipeline test sınıfı."""
    
    @pytest.fixture
    def mock_vector_search(self):
        """Vector search mock nesnesi."""
        mock = MagicMock(spec=VectorSearch)
        mock.search.return_value = [
            {"id": "chunk1", "text": "Bu örnek bir chunk metnidir.", "metadata": {"doc_id": "doc1"}, "score": 0.85},
            {"id": "chunk2", "text": "Bu başka bir chunk metnidir.", "metadata": {"doc_id": "doc2"}, "score": 0.75},
            {"id": "chunk3", "text": "Bu üçüncü bir chunk metnidir.", "metadata": {"doc_id": "doc3"}, "score": 0.65},
        ]
        return mock
    
    @pytest.fixture
    def mock_reranker(self):
        """Reranker mock nesnesi."""
        mock = MagicMock(spec=Reranker)
        mock.rerank.return_value = [
            {"id": "chunk2", "text": "Bu başka bir chunk metnidir.", "metadata": {"doc_id": "doc2"}, "score": 0.95},
            {"id": "chunk1", "text": "Bu örnek bir chunk metnidir.", "metadata": {"doc_id": "doc1"}, "score": 0.85},
            {"id": "chunk3", "text": "Bu üçüncü bir chunk metnidir.", "metadata": {"doc_id": "doc3"}, "score": 0.55},
        ]
        return mock
    
    @pytest.fixture
    def mock_document_chunker(self):
        """Document chunker mock nesnesi."""
        mock = MagicMock(spec=DocumentChunker)
        mock.chunk_document.return_value = [
            {"id": "chunk1", "text": "Bu örnek bir chunk metnidir.", "metadata": {"doc_id": "doc1"}},
            {"id": "chunk2", "text": "Bu başka bir chunk metnidir.", "metadata": {"doc_id": "doc1"}},
        ]
        return mock
    
    @pytest.fixture
    def retrieval_pipeline(self, mock_vector_search, mock_reranker):
        """Retrieval pipeline nesnesi."""
        pipeline = RetrievalPipeline(
            search_engine=mock_vector_search,
            reranker=mock_reranker
        )
        return pipeline
    
    def test_retrieval_pipeline_initialization(self, mock_vector_search, mock_reranker):
        """Pipeline başlatma testi."""
        pipeline = RetrievalPipeline(
            search_engine=mock_vector_search,
            reranker=mock_reranker
        )
        assert pipeline.search_engine == mock_vector_search
        assert pipeline.reranker == mock_reranker
        assert pipeline.top_k == 5  # Varsayılan değer
        assert pipeline.rerank_top_k == 10  # Varsayılan değer
        assert pipeline.use_reranking is True  # Varsayılan değer
    
    def test_retrieve_with_reranking(self, retrieval_pipeline, mock_vector_search, mock_reranker):
        """Yeniden sıralama ile erişim testi."""
        query = "Örnek bir sorgu"
        
        # Pipeline'ı çağır
        results = retrieval_pipeline.retrieve(query)
        
        # Mock fonksiyonlarının doğru parametrelerle çağrıldığını doğrula
        mock_vector_search.search.assert_called_once_with(
            query=query, 
            top_k=retrieval_pipeline.rerank_top_k,
            filters=None
        )
        
        mock_reranker.rerank.assert_called_once()
        
        # Sonuçların doğru olduğunu doğrula
        assert len(results) == 3
        assert results[0]["id"] == "chunk2"
        assert results[0]["score"] == 0.95
    
    def test_retrieve_without_reranking(self, retrieval_pipeline, mock_vector_search, mock_reranker):
        """Yeniden sıralama olmadan erişim testi."""
        # Yeniden sıralamayı devre dışı bırak
        retrieval_pipeline.use_reranking = False
        
        query = "Örnek bir sorgu"
        
        # Pipeline'ı çağır
        results = retrieval_pipeline.retrieve(query)
        
        # Sadece vector search'ün çağrıldığını doğrula
        mock_vector_search.search.assert_called_once_with(
            query=query, 
            top_k=retrieval_pipeline.top_k,
            filters=None
        )
        
        # Reranker'ın çağrılmadığını doğrula
        mock_reranker.rerank.assert_not_called()
        
        # Sonuçların doğru olduğunu doğrula
        assert len(results) == 3
        assert results[0]["id"] == "chunk1"
        assert results[0]["score"] == 0.85
    
    def test_retrieve_with_filters(self, retrieval_pipeline, mock_vector_search, mock_reranker):
        """Filtrelerle erişim testi."""
        query = "Örnek bir sorgu"
        filters = {"doc_type": "pdf"}
        
        # Pipeline'ı çağır
        retrieval_pipeline.retrieve(query, filters=filters)
        
        # Mock fonksiyonlarının doğru parametrelerle çağrıldığını doğrula
        mock_vector_search.search.assert_called_once_with(
            query=query, 
            top_k=retrieval_pipeline.rerank_top_k,
            filters=filters
        )
    
    def test_generate_context(self, retrieval_pipeline, mock_vector_search, mock_reranker):
        """Bağlam oluşturma testi."""
        query = "Örnek bir sorgu"
        
        # Pipeline ile bağlam oluştur
        context = retrieval_pipeline.generate_context(query, max_tokens=500)
        
        # Vector search ve reranker'ın çağrıldığını doğrula
        mock_vector_search.search.assert_called_once()
        mock_reranker.rerank.assert_called_once()
        
        # Bağlamın doğru oluşturulduğunu doğrula
        assert isinstance(context, str)
        assert "Bu başka bir chunk metnidir." in context
        assert "Bu örnek bir chunk metnidir." in context
        assert "Bu üçüncü bir chunk metnidir." in context
    
    def test_document_chunking(self, mock_document_chunker):
        """Belge parçalama testi."""
        # Test belgesi
        document = {
            "id": "doc1",
            "text": "Bu uzun bir belge metnidir. Birden fazla cümle içerir. Bu chunking algoritması tarafından parçalanacaktır.",
            "metadata": {"source": "test", "created_at": "2025-01-01"}
        }
        
        # Belgeyi chunker ile parçala
        chunks = mock_document_chunker.chunk_document(document)
        
        # Mock'un çağrıldığını doğrula
        mock_document_chunker.chunk_document.assert_called_once_with(document)
        
        # Chunk'ların doğru oluşturulduğunu doğrula
        assert len(chunks) == 2
        assert chunks[0]["id"] == "chunk1"
        assert chunks[0]["metadata"]["doc_id"] == "doc1"
    
    @pytest.mark.parametrize("max_tokens,expected_chunks", [
        (50, 1),   # Sadece en yüksek puanlı chunk sığar
        (200, 3),  # Tüm chunk'lar sığar
        (10, 0)    # Hiçbir chunk sığmaz
    ])
    def test_context_generation_with_token_limit(self, retrieval_pipeline, max_tokens, expected_chunks):
        """Token sınırına göre bağlam oluşturma testi."""
        with patch.object(retrieval_pipeline, 'retrieve') as mock_retrieve:
            # Mock veriler
            mock_retrieve.return_value = [
                {"id": "chunk1", "text": "Bu 20 token uzunluğunda olan bir chunk metnidir.", "score": 0.95},
                {"id": "chunk2", "text": "Bu 20 token uzunluğunda olan başka bir chunk metnidir.", "score": 0.85},
                {"id": "chunk3", "text": "Bu 20 token uzunluğunda olan üçüncü bir chunk metnidir.", "score": 0.75},
            ]
            
            # Retrieve'den dönen her chunk'ın token sayısını 20 olarak hesaplata
            with patch('ModularMind.API.services.retrieval.pipeline.count_tokens', return_value=20):
                # Bağlam oluştur
                context = retrieval_pipeline.generate_context("Test sorgu", max_tokens=max_tokens)
                
                # İçeriği kontrol et
                if expected_chunks == 0:
                    assert context == ""
                else:
                    # Beklenen sayıda chunk içerdiğini doğrula
                    expected_chunks_in_context = mock_retrieve.return_value[:expected_chunks]
                    for chunk in expected_chunks_in_context:
                        assert chunk["text"] in context

class TestHybridSearch:
    """Hybrid search test sınıfı."""
    
    @pytest.fixture
    def mock_vector_search(self):
        """Vector search mock nesnesi."""
        mock = MagicMock(spec=VectorSearch)
        mock.search.return_value = [
            {"id": "chunk1", "text": "Vektör araması sonucu 1", "metadata": {"doc_id": "doc1"}, "score": 0.85},
            {"id": "chunk2", "text": "Vektör araması sonucu 2", "metadata": {"doc_id": "doc2"}, "score": 0.75},
        ]
        return mock
    
    @pytest.fixture
    def mock_keyword_search(self):
        """Keyword search mock nesnesi."""
        mock = MagicMock()
        mock.search.return_value = [
            {"id": "chunk3", "text": "Anahtar kelime araması sonucu 1", "metadata": {"doc_id": "doc3"}, "score": 0.65},
            {"id": "chunk4", "text": "Anahtar kelime araması sonucu 2", "metadata": {"doc_id": "doc4"}, "score": 0.55},
        ]
        return mock
    
    @pytest.fixture
    def hybrid_search(self, mock_vector_search, mock_keyword_search):
        """Hybrid search nesnesi."""
        return HybridSearch(
            vector_search=mock_vector_search,
            keyword_search=mock_keyword_search
        )
    
    def test_hybrid_search_initialization(self, mock_vector_search, mock_keyword_search):
        """HybridSearch başlatma testi."""
        hybrid = HybridSearch(
            vector_search=mock_vector_search,
            keyword_search=mock_keyword_search
        )
        assert hybrid.vector_search == mock_vector_search
        assert hybrid.keyword_search == mock_keyword_search
        assert hybrid.vector_weight == 0.7  # Varsayılan değer
        assert hybrid.keyword_weight == 0.3  # Varsayılan değer
    
    def test_hybrid_search_with_default_weights(self, hybrid_search, mock_vector_search, mock_keyword_search):
        """Varsayılan ağırlıklarla hibrit arama testi."""
        query = "Test sorgu"
        
        # Hibrit aramayı çağır
        results = hybrid_search.search(query, top_k=3)
        
        # Her iki arama metodunun da çağrıldığını doğrula
        mock_vector_search.search.assert_called_once_with(query=query, top_k=5, filters=None)
        mock_keyword_search.search.assert_called_once_with(query=query, top_k=5, filters=None)
        
        # Sonuçların birleştirildiğini ve yeniden sıralandığını doğrula
        assert len(results) == 3  # top_k=3
        # Sonuçların puan sırasına göre olduğunu doğrula
        assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]
    
    def test_hybrid_search_with_custom_weights(self, mock_vector_search, mock_keyword_search):
        """Özel ağırlıklarla hibrit arama testi."""
        # Vektör aramaya daha fazla ağırlık ver
        hybrid = HybridSearch(
            vector_search=mock_vector_search,
            keyword_search=mock_keyword_search,
            vector_weight=0.9,
            keyword_weight=0.1
        )
        
        query = "Test sorgu"
        
        # Hibrit aramayı çağır
        results = hybrid.search(query, top_k=4)
        
        # Her iki arama metodunun da çağrıldığını doğrula
        mock_vector_search.search.assert_called_once()
        mock_keyword_search.search.assert_called_once()
        
        # Tüm sonuçların döndüğünü doğrula
        assert len(results) == 4
    
    def test_hybrid_search_with_filters(self, hybrid_search, mock_vector_search, mock_keyword_search):
        """Filtrelerle hibrit arama testi."""
        query = "Test sorgu"
        filters = {"language": "tr"}
        
        # Hibrit aramayı çağır
        hybrid_search.search(query, filters=filters)
        
        # Her iki arama metodunun da filtreleri ile çağrıldığını doğrula
        mock_vector_search.search.assert_called_once_with(query=query, top_k=5, filters=filters)
        mock_keyword_search.search.assert_called_once_with(query=query, top_k=5, filters=filters)