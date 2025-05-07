import pytest
import os
import sys
from unittest.mock import MagicMock, patch
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.context_optimizer import ContextOptimizer, ContextWindow
from app.services.retrievers.base import SearchResult


@pytest.mark.unit
class TestContextOptimizer:
    """Test suite for the ContextOptimizer class."""
    
    @pytest.fixture
    def mock_results(self):
        """Create mock search results for testing."""
        return [
            SearchResult(
                id="doc1",
                text="This is the first document with some important information about the topic.",
                score=0.95,
                metadata={"title": "Document 1", "source": "Test DB"}
            ),
            SearchResult(
                id="doc2",
                text="This is the second document with slightly different information about the same topic.",
                score=0.85,
                metadata={"title": "Document 2", "source": "Test DB"}
            ),
            SearchResult(
                id="doc3",
                text="The third document contains unrelated information that doesn't really help with the query.",
                score=0.75,
                metadata={"title": "Document 3", "source": "Test DB"}
            ),
            SearchResult(
                id="doc4",
                text="Document four has more information that's very helpful for understanding the topic completely.",
                score=0.65,
                metadata={"title": "Document 4", "source": "Test DB"}
            ),
            SearchResult(
                id="doc5",
                text="This document is redundant and just repeats information from document one.",
                score=0.55,
                metadata={"title": "Document 5", "source": "Test DB"}
            )
        ]
    
    @pytest.fixture
    def context_optimizer(self):
        """Create a ContextOptimizer instance for testing."""
        return ContextOptimizer(
            max_tokens=200,  # Small max_tokens for testing
            max_chars=1000,  # Small max_chars for testing
            max_chunks=3,    # Limit chunks for testing
            diversity_weight=0.3
        )
    
    @pytest.mark.asyncio
    async def test_optimize_coverage_strategy(self, context_optimizer, mock_results):
        """Test optimization with 'coverage' strategy."""
        # Mock the token counting function to return predictable values
        with patch.object(context_optimizer, '_count_tokens', return_value=50):
            optimized = await context_optimizer.optimize(
                results=mock_results,
                query="information about the topic",
                strategy="coverage"
            )
            
            # Should return a ContextWindow object
            assert isinstance(optimized, ContextWindow)
            
            # Should have limited chunks due to max_chunks setting
            assert len(optimized.chunks) <= 3
            
            # Should include highest-scoring documents
            doc_ids = [chunk.id for chunk in optimized.chunks]
            assert "doc1" in doc_ids  # Highest score should be included
            
            # Should track sources
            assert len(optimized.sources) > 0
            assert all(source_id in [r.id for r in mock_results] for source_id in optimized.sources)
    
    @pytest.mark.asyncio
    async def test_optimize_diverse_strategy(self, context_optimizer, mock_results):
        """Test optimization with 'diverse' strategy."""
        # Mock embeddings generation
        with patch.object(context_optimizer, '_get_embeddings') as mock_get_embeddings:
            # Return different mock embeddings for query and documents to simulate diversity
            mock_get_embeddings.return_value = np.array([
                [0.1, 0.2, 0.3, 0.4],  # query
                [0.1, 0.2, 0.3, 0.4],  # doc1 - similar to query
                [0.5, 0.6, 0.7, 0.8],  # doc2 - different
                [0.9, 0.8, 0.7, 0.6],  # doc3 - very different
                [0.2, 0.3, 0.4, 0.5],  # doc4 - somewhat similar
                [0.1, 0.2, 0.3, 0.5],  # doc5 - similar to doc1
            ])
            
            # Mock token counting
            with patch.object(context_optimizer, '_count_tokens', return_value=50):
                optimized = await context_optimizer.optimize(
                    results=mock_results,
                    query="information about the topic",
                    strategy="diverse"
                )
                
                # Should prioritize diversity while still respecting relevance
                doc_ids = [chunk.id for chunk in optimized.chunks]
                
                # Should include some diverse documents (we don't know exactly which due to 
                # the MMR algorithm's balance of relevance and diversity)
                assert len(doc_ids) <= 3  # Max chunks constraint
    
    @pytest.mark.asyncio
    async def test_optimize_token_limits(self, context_optimizer, mock_results):
        """Test that optimization respects token limits."""
        # Mock token counting to return increasing values to test limits
        token_counts = {
            "doc1": 100,  # First doc fits
            "doc2": 120,  # Adding this exceeds limit
            "doc3": 90,   # If we added this instead of doc2, it would fit
            "doc4": 80,
            "doc5": 50
        }
        
        def mock_count_tokens(text):
            for doc_id, count in token_counts.items():
                if doc_id in text:
                    return count
            return 30  # Default for query
        
        with patch.object(context_optimizer, '_count_tokens', side_effect=mock_count_tokens):
            # Set max_tokens to only fit one document
            context_optimizer.max_tokens = 110
            
            optimized = await context_optimizer.optimize(
                results=mock_results,
                query="information about the topic",
                strategy="coverage"
            )
            
            # Should only include one document due to token limit
            assert len(optimized.chunks) == 1
            assert optimized.chunks[0].id == "doc1"  # Highest score that fits
            
            # Total tokens should be below limit
            assert optimized.total_tokens <= context_optimizer.max_tokens
    
    @pytest.mark.asyncio
    async def test_compute_similarity_scores(self, context_optimizer):
        """Test similarity score computation."""
        # Create mock embeddings
        query_embedding = np.array([0.1, 0.2, 0.3, 0.4])
        doc_embeddings = np.array([
            [0.1, 0.2, 0.3, 0.4],  # doc1 - identical to query (score 1.0)
            [0.4, 0.3, 0.2, 0.1],  # doc2 - inverse of query (lower score)
            [0.0, 0.0, 0.0, 0.0],  # doc3 - zero vector (lowest score)
        ])
        
        scores = context_optimizer._compute_similarity_scores(query_embedding, doc_embeddings)
        
        # Check that scores have the right shape
        assert scores.shape == (3,)
        
        # First doc should have highest similarity (close to 1)
        assert scores[0] > 0.9
        
        # Zero vector should have very low similarity
        assert scores[2] < 0.1