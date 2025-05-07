import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.services.retrievers.base import SearchResult


@pytest.mark.unit
@pytest.mark.retrieval
class TestCrossEncoderReranker:
    """Test suite for the CrossEncoderReranker class."""
    
    @pytest.fixture
    def mock_results(self):
        """Return mock search results for testing."""
        return [
            SearchResult(
                id="doc1",
                text="This is the first test document",
                score=0.85,
                metadata={"title": "Document 1"}
            ),
            SearchResult(
                id="doc2",
                text="This is the second test document",
                score=0.75,
                metadata={"title": "Document 2"}
            ),
            SearchResult(
                id="doc3",
                text="This is the third test document",
                score=0.65,
                metadata={"title": "Document 3"}
            )
        ]
    
    @pytest.mark.asyncio
    async def test_rerank(self, mock_results):
        """Test the reranking functionality."""
        with patch("app.services.rerankers.cross_encoder_reranker.CrossEncoder") as MockCrossEncoder:
            # Setup mock cross-encoder to return predictable scores
            mock_cross_encoder = MagicMock()
            mock_cross_encoder.predict.return_value = [0.6, 0.9, 0.7]
            MockCrossEncoder.return_value = mock_cross_encoder
            
            reranker = CrossEncoderReranker()
            
            # Call the rerank method
            query = "test query"
            reranked_results = await reranker.rerank(query, mock_results)
            
            # Check that the cross-encoder was called with the correct inputs
            query_doc_pairs = [
                [query, "This is the first test document"],
                [query, "This is the second test document"],
                [query, "This is the third test document"]
            ]
            mock_cross_encoder.predict.assert_called_once_with(query_doc_pairs)
            
            # Check that results are reranked according to cross-encoder scores
            assert len(reranked_results) == 3
            assert reranked_results[0].id == "doc2"  # Highest score 0.9
            assert reranked_results[1].id == "doc3"  # Second highest 0.7
            assert reranked_results[2].id == "doc1"  # Lowest score 0.6
            
            # Check that the original scores are preserved in metadata
            assert reranked_results[0].metadata["original_score"] == 0.75
            assert reranked_results[0].score == 0.9  # New score
    
    @pytest.mark.asyncio
    async def test_rerank_with_top_k(self, mock_results):
        """Test reranking with top_k parameter."""
        with patch("app.services.rerankers.cross_encoder_reranker.CrossEncoder") as MockCrossEncoder:
            # Setup mock
            mock_cross_encoder = MagicMock()
            mock_cross_encoder.predict.return_value = [0.6, 0.9, 0.7]
            MockCrossEncoder.return_value = mock_cross_encoder
            
            reranker = CrossEncoderReranker()
            
            # Call rerank with top_k=2
            reranked_results = await reranker.rerank("test query", mock_results, top_k=2)
            
            # Should only return top 2 results
            assert len(reranked_results) == 2
            assert reranked_results[0].id == "doc2"  # Highest score
            assert reranked_results[1].id == "doc3"  # Second highest
    
    @pytest.mark.asyncio
    async def test_empty_results(self):
        """Test reranking with empty results."""
        reranker = CrossEncoderReranker()
        
        # Call rerank with empty results
        reranked_results = await reranker.rerank("test query", [])
        
        # Should return empty list
        assert reranked_results == []
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test the initialize method."""
        with patch("app.services.rerankers.cross_encoder_reranker.CrossEncoder") as MockCrossEncoder:
            mock_cross_encoder = MagicMock()
            MockCrossEncoder.return_value = mock_cross_encoder
            
            # Create reranker
            reranker = CrossEncoderReranker(model_name="test-model")
            
            # Call initialize
            await reranker.initialize()
            
            # Check that cross-encoder was initialized with the correct model
            MockCrossEncoder.assert_called_once_with("test-model", max_length=512)
            
            # Check that is_initialized is set
            assert reranker.is_initialized