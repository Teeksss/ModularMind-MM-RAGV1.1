import pytest
import os
import sys
import asyncio
from unittest.mock import MagicMock, patch
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.services.retrievers.base import SearchResult


@pytest.mark.unit
@pytest.mark.retrieval
class TestHybridRetriever:
    """Test suite for the HybridRetriever class."""
    
    @pytest.fixture
    def mock_vector_store(self):
        """Create a mock vector store."""
        mock = MagicMock()
        mock.similarity_search.return_value = [
            SearchResult(
                id="doc1",
                text="Vector document 1",
                score=0.9,
                metadata={"source": "vector"}
            ),
            SearchResult(
                id="doc2",
                text="Vector document 2",
                score=0.8,
                metadata={"source": "vector"}
            )
        ]
        return mock
    
    @pytest.fixture
    def mock_bm25_retriever(self):
        """Create a mock BM25 retriever."""
        mock = MagicMock()
        mock.search.return_value = [
            SearchResult(
                id="doc3",
                text="BM25 document 1",
                score=0.85,
                metadata={"source": "bm25"}
            ),
            SearchResult(
                id="doc4",
                text="BM25 document 2",
                score=0.75,
                metadata={"source": "bm25"}
            )
        ]
        return mock
    
    @pytest.mark.asyncio
    async def test_search(self, mock_vector_store, mock_bm25_retriever):
        """Test the search method."""
        # Create the hybrid retriever with mocks
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            sparse_retriever=mock_bm25_retriever,
            alpha=0.7
        )
        
        # Call the search method
        results = await retriever.search("test query", k=3)
        
        # Check that both retrievers were called
        mock_vector_store.similarity_search.assert_called_once_with(
            "test query", k=3, filters=None
        )
        mock_bm25_retriever.search.assert_called_once_with(
            "test query", k=3, filters=None
        )
        
        # Check result count (hybrid retriever should merge and sort)
        assert len(results) == 3
        
        # Check that results are sorted by score
        assert results[0].score >= results[1].score
        assert results[1].score >= results[2].score
    
    @pytest.mark.asyncio
    async def test_custom_alpha(self, mock_vector_store, mock_bm25_retriever):
        """Test with custom alpha value."""
        # Create with custom alpha (higher weight to BM25)
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            sparse_retriever=mock_bm25_retriever,
            alpha=0.3  # More weight to BM25
        )
        
        # Mock normalize_scores to return predictable values
        retriever._normalize_scores = MagicMock(return_value=[0.9, 0.8])
        
        # Call the search method
        results = await retriever.search("test query", k=3)
        
        # Verify BM25 has more influence (0.3 alpha means 70% BM25 weight)
        assert len(results) > 0
        
        # Reset and try with full vector weight
        retriever = HybridRetriever(
            vector_store=mock_vector_store,
            sparse_retriever=mock_bm25_retriever,
            alpha=1.0  # Vector only
        )
        
        # Call the search method
        results = await retriever.search("test query", k=3)
        
        # Verify only vector results
        assert all(r.metadata.get("source") == "vector" for r in results)
    
    @pytest.mark.asyncio
    async def test_normalize_scores(self):
        """Test the score normalization function."""
        retriever = HybridRetriever()
        
        # Test with simple values
        scores = [0.5, 1.0, 0.0, 0.75]
        normalized = retriever._normalize_scores(scores)
        
        # Check normalization (0-1 range)
        assert min(normalized) == 0.0
        assert max(normalized) == 1.0
        assert normalized[1] == 1.0  # Highest should be 1.0
        assert normalized[2] == 0.0  # Lowest should be 0.0
        assert 0.0 < normalized[0] < 1.0  # Middle values should be between 0-1
        
        # Test with all same values
        scores = [0.5, 0.5, 0.5]
        normalized = retriever._normalize_scores(scores)
        assert all(n == 0.0 for n in normalized)  # All normalized to 0 when all same
    
    @pytest.mark.asyncio
    async def test_rerank_results(self):
        """Test the result reranking process."""
        retriever = HybridRetriever(alpha=0.6)  # 60% vector, 40% BM25
        
        # Create some test results
        vector_results = [
            SearchResult(id="v1", text="Vector 1", score=0.9),
            SearchResult(id="v2", text="Vector 2", score=0.8),
            SearchResult(id="v3", text="Vector 3", score=0.7)
        ]
        
        bm25_results = [
            SearchResult(id="b1", text="BM25 1", score=0.95),
            SearchResult(id="v2", text="Vector 2", score=0.85),  # Overlapping doc
            SearchResult(id="b3", text="BM25 3", score=0.75)
        ]
        
        # Mock normalize_scores
        retriever._normalize_scores = MagicMock(side_effect=[
            [1.0, 0.5, 0.0],  # Normalized vector scores
            [1.0, 0.5, 0.0]   # Normalized BM25 scores
        ])
        
        reranked = retriever._rerank_results(vector_results, bm25_results)
        
        # Check count (one is overlapping)
        assert len(reranked) == 5
        
        # Check that overlapping document has combined score
        v2_result = next(r for r in reranked if r.id == "v2")
        assert v2_result is not None
        
        # Verify the boosting field is populated
        assert all("boosting" in r.metadata for r in reranked)