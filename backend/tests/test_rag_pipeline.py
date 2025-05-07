import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os
import tempfile

from app.services.retrieval_pipeline import RetrievalPipeline
from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.services.retrievers.bm25_retriever import BM25Retriever
from app.services.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.services.retrievers.base import SearchResult
from app.services.context_optimizer import ContextOptimizer
from app.services.dynamic_retriever import DynamicRetrieverSelector
from app.agents.query_expander import QueryExpanderAgent


# Mock data for tests
@pytest.fixture
def mock_search_results():
    """Create mock search results for testing."""
    results = [
        SearchResult(
            id=f"doc{i}",
            text=f"This is document {i} with some content for testing retrieval.",
            score=1.0 - (i * 0.1),
            metadata={"title": f"Document {i}", "source": "test"}
        )
        for i in range(10)
    ]
    return results


@pytest.fixture
def mock_query():
    """Sample query for testing."""
    return "What is retrieval augmented generation?"


# Mocked retrievers and rerankers
@pytest.fixture
def mock_hybrid_retriever(mock_search_results):
    """Create a mock hybrid retriever."""
    retriever = AsyncMock(spec=HybridRetriever)
    retriever.search.return_value = mock_search_results
    return retriever


@pytest.fixture
def mock_bm25_retriever(mock_search_results):
    """Create a mock BM25 retriever."""
    retriever = AsyncMock(spec=BM25Retriever)
    retriever.search.return_value = mock_search_results
    return retriever


@pytest.fixture
def mock_reranker(mock_search_results):
    """Create a mock reranker."""
    reranker = AsyncMock(spec=CrossEncoderReranker)
    # Sort results differently to simulate reranking
    reranked_results = sorted(mock_search_results, key=lambda x: int(x.id[3:]))
    reranker.rerank.return_value = reranked_results
    return reranker


@pytest.fixture
def mock_query_expander():
    """Create a mock query expander agent."""
    expander = AsyncMock(spec=QueryExpanderAgent)
    expander.execute.return_value = {
        "original_query": "What is retrieval augmented generation?",
        "expanded_queries": [
            "What is retrieval augmented generation?",
            "What is RAG in AI?",
            "retrieval augmented generation explanation"
        ],
        "rewritten_query": "Explain retrieval augmented generation and its applications",
        "query_type": "natural_language"
    }
    return expander


# Test the basic retrieval pipeline functionality
@pytest.mark.asyncio
async def test_retrieval_pipeline_basic(mock_hybrid_retriever, mock_reranker, mock_query):
    """Test basic functionality of the retrieval pipeline."""
    # Create pipeline with mocked components
    pipeline = RetrievalPipeline(
        use_query_expansion=False,
        use_reranking=True,
        first_stage_k=10,
        final_k=5
    )
    
    # Replace real components with mocks
    pipeline.hybrid_retriever = mock_hybrid_retriever
    pipeline.reranker = mock_reranker
    
    # Execute the pipeline
    results = await pipeline.retrieve(query=mock_query)
    
    # Verify results
    assert len(results) == 5  # Should return final_k results
    assert mock_hybrid_retriever.search.called
    assert mock_reranker.rerank.called
    
    # Check that reranker was called with correct parameters
    reranker_call_args = mock_reranker.rerank.call_args[1]
    assert reranker_call_args['query'] == mock_query
    assert len(reranker_call_args['results']) == 10  # first_stage_k


@pytest.mark.asyncio
async def test_retrieval_pipeline_without_reranking(mock_hybrid_retriever, mock_query):
    """Test retrieval pipeline without reranking."""
    pipeline = RetrievalPipeline(
        use_query_expansion=False,
        use_reranking=False,
        first_stage_k=10,
        final_k=5
    )
    
    # Replace real components with mocks
    pipeline.hybrid_retriever = mock_hybrid_retriever
    
    # Execute the pipeline
    results = await pipeline.retrieve(query=mock_query)
    
    # Verify results
    assert len(results) == 5  # Should return final_k results
    assert mock_hybrid_retriever.search.called
    
    # Results should be sorted by score (highest first)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_dynamic_retriever_selector(
    mock_hybrid_retriever, mock_bm25_retriever, mock_query
):
    """Test the dynamic retriever selector."""
    selector = DynamicRetrieverSelector()
    
    # Replace retrievers with mocks
    selector.hybrid_retriever = mock_hybrid_retriever
    selector.bm25_retriever = mock_bm25_retriever
    selector.vector_retriever = AsyncMock()
    selector.vector_retriever.similarity_search.return_value = []
    
    # Test with forced methods
    hybrid_result = await selector.retrieve(query=mock_query, force_method="hybrid")
    assert hybrid_result["retrieval_method"] == "hybrid"
    assert mock_hybrid_retriever.search.called
    
    bm25_result = await selector.retrieve(query=mock_query, force_method="bm25")
    assert bm25_result["retrieval_method"] == "bm25"
    assert mock_bm25_retriever.search.called
    
    # Test pattern-based selection
    keyword_query = "document retrieval examples"
    with patch.object(selector, '_analyze_query', return_value=("bm25", {"query_type": "keyword"})):
        result = await selector.retrieve(query=keyword_query)
        assert result["retrieval_method"] == "bm25"
        
    semantic_query = "How does retrieval-augmented generation work?"
    with patch.object(selector, '_analyze_query', return_value=("vector", {"query_type": "semantic"})):
        result = await selector.retrieve(query=semantic_query)
        assert result["retrieval_method"] == "vector"


@pytest.mark.asyncio
async def test_context_optimizer(mock_search_results):
    """Test the context window optimizer."""
    optimizer = ContextOptimizer(
        max_tokens=1000,
        max_chunks=3,
        overlap_threshold=0.7
    )
    
    # Test greedy strategy
    context_window = await optimizer.optimize(
        results=mock_search_results,
        query="test query",
        strategy="greedy"
    )
    
    assert len(context_window.chunks) <= 3  # Respect max_chunks
    assert context_window.total_tokens <= 1000  # Respect max_tokens
    
    # Test with different strategies
    strategies = ["relevance", "coverage", "diverse"]
    for strategy in strategies:
        context_window = await optimizer.optimize(
            results=mock_search_results,
            query="test query",
            strategy=strategy
        )
        assert len(context_window.chunks) > 0


@pytest.mark.asyncio
async def test_retrieval_metrics_integration():
    """Test integration with retrieval metrics."""
    from app.services.metrics.retrieval_metrics import retrieval_metrics
    
    # Create a simple test function that simulates retrieval
    @retrieval_metrics.track_retrieval(method="test")
    async def test_retrieval():
        await asyncio.sleep(0.1)  # Simulate some work
        return [
            SearchResult(id="1", text="Test document", score=0.9, metadata={})
        ]
    
    # Call the function
    result = await test_retrieval()
    
    assert len(result) == 1
    assert result[0].id == "1"
    
    # Create a test reranking function
    @retrieval_metrics.track_reranking(model="test_model")
    async def test_reranking(results):
        await asyncio.sleep(0.1)  # Simulate some work
        return results
    
    # Call the function
    reranked = await test_reranking(result)
    assert len(reranked) == 1
    assert reranked[0].id == "1"