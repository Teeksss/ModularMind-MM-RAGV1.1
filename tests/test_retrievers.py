import pytest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock

from app.services.retrievers.dense_retriever import DenseRetriever
from app.services.retrievers.sparse_retriever import SparseRetriever
from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.services.retrievers.reranker import Reranker
from app.models.model_manager import get_model_manager


@pytest.fixture
def mock_embedding_model():
    """Mock embedding model for testing."""
    model = MagicMock()
    model.encode.return_value = np.random.randn(1, 384)
    return model


@pytest.fixture
def mock_model_manager():
    """Mock model manager for testing."""
    manager = MagicMock()
    manager.get_embedding_model.return_value = mock_embedding_model()
    return manager


@pytest.fixture
def mock_faiss_index():
    """Mock FAISS index for testing."""
    index = MagicMock()
    index.search.return_value = (
        np.array([[0.8, 0.7, 0.6]]),  # Similarity scores
        np.array([[0, 1, 2]])         # Document IDs
    )
    return index


@pytest.fixture
def mock_document_store():
    """Mock document store for testing."""
    store = MagicMock()
    store.get_documents_by_ids.return_value = [
        {"id": "0", "text": "Test document 1", "metadata": {"source": "test"}},
        {"id": "1", "text": "Test document 2", "metadata": {"source": "test"}},
        {"id": "2", "text": "Test document 3", "metadata": {"source": "test"}}
    ]
    return store


@pytest.mark.asyncio
async def test_dense_retriever_search(mock_model_manager, mock_faiss_index, mock_document_store):
    """Test DenseRetriever search functionality."""
    with patch("app.models.model_manager.get_model_manager", return_value=mock_model_manager):
        dense_retriever = DenseRetriever()
        dense_retriever.index = mock_faiss_index
        dense_retriever.document_store = mock_document_store
        
        results = await dense_retriever.search("test query", k=3)
        
        # Verify results
        assert len(results) == 3
        assert results[0].score == 0.8
        assert results[0].text == "Test document 1"
        assert results[1].score == 0.7
        assert results[2].score == 0.6


@pytest.mark.asyncio
async def test_sparse_retriever_search(mock_document_store):
    """Test SparseRetriever search functionality."""
    # Mock BM25 index
    bm25_results = [
        {"id": "2", "score": 0.9},
        {"id": "0", "score": 0.8},
        {"id": "1", "score": 0.6}
    ]
    
    with patch("app.services.retrievers.sparse_retriever.BM25Index") as mock_bm25:
        mock_bm25_instance = MagicMock()
        mock_bm25_instance.search.return_value = bm25_results
        mock_bm25.return_value = mock_bm25_instance
        
        sparse_retriever = SparseRetriever()
        sparse_retriever.document_store = mock_document_store
        sparse_retriever.initialize()
        
        results = await sparse_retriever.search("test query", k=3)
        
        # Verify results
        assert len(results) == 3
        assert results[0].score == 0.9
        assert results[0].text == "Test document 3"
        assert results[1].score == 0.8
        assert results[2].score == 0.6


@pytest.mark.asyncio
async def test_hybrid_retriever_search():
    """Test HybridRetriever search functionality."""
    # Mock dense and sparse retrievers
    dense_results = [
        {"id": "0", "text": "Dense document 1", "score": 0.9, "metadata": {}},
        {"id": "1", "text": "Dense document 2", "score": 0.8, "metadata": {}},
    ]
    
    sparse_results = [
        {"id": "2", "text": "Sparse document 1", "score": 0.85, "metadata": {}},
        {"id": "0", "text": "Dense document 1", "score": 0.7, "metadata": {}},
    ]
    
    dense_retriever = MagicMock()
    sparse_retriever = MagicMock()
    
    dense_retriever.search.return_value = dense_results
    sparse_retriever.search.return_value = sparse_results
    
    hybrid_retriever = HybridRetriever(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever,
        dense_weight=0.6,
        sparse_weight=0.4
    )
    
    results = await hybrid_retriever.search("test query", k=3)
    
    # Verify results
    assert len(results) == 3
    # Document ID 0 should be first as it appears in both result sets
    assert results[0].id == "0"
    # Check that dense_weight and sparse_weight are applied correctly
    assert results[0].score > results[1].score


@pytest.mark.asyncio
async def test_reranker():
    """Test Reranker functionality."""
    # Mock retriever and cross-encoder model
    retriever = MagicMock()
    cross_encoder = MagicMock()
    
    initial_results = [
        {"id": "0", "text": "Document 1", "score": 0.8, "metadata": {}},
        {"id": "1", "text": "Document 2", "score": 0.7, "metadata": {}},
        {"id": "2", "text": "Document 3", "score": 0.6, "metadata": {}}
    ]
    
    # Cross-encoder gives different scores, changing the ranking
    cross_encoder.predict.return_value = [0.6, 0.9, 0.7]
    
    retriever.search.return_value = initial_results
    
    reranker = Reranker(
        base_retriever=retriever,
        cross_encoder=cross_encoder
    )
    
    results = await reranker.rerank("test query", initial_results)
    
    # Verify results are reranked according to cross-encoder scores
    assert len(results) == 3
    assert results[0].id == "1"  # Highest cross-encoder score
    assert results[1].id == "2"
    assert results[2].id == "0"  # Lowest cross-encoder score


@pytest.mark.asyncio
async def test_hybrid_retriever_with_reranker():
    """Test integration of HybridRetriever with Reranker."""
    # This is more of an integration test
    # Setup mocks for all components
    dense_retriever = MagicMock()
    sparse_retriever = MagicMock()
    cross_encoder = MagicMock()
    
    dense_results = [
        {"id": "0", "text": "Document A", "score": 0.9, "metadata": {}},
        {"id": "1", "text": "Document B", "score": 0.8, "metadata": {}},
    ]
    
    sparse_results = [
        {"id": "2", "text": "Document C", "score": 0.85, "metadata": {}},
        {"id": "0", "text": "Document A", "score": 0.7, "metadata": {}},
    ]
    
    dense_retriever.search.return_value = dense_results
    sparse_retriever.search.return_value = sparse_results
    
    # Cross-encoder ranks document C highest
    cross_encoder.predict.return_value = [0.7, 0.6, 0.9]
    
    # Create hybrid retriever
    hybrid_retriever = HybridRetriever(
        dense_retriever=dense_retriever,
        sparse_retriever=sparse_retriever
    )
    
    # Create reranker with hybrid retriever
    reranker = Reranker(
        base_retriever=hybrid_retriever,
        cross_encoder=cross_encoder
    )
    
    # Perform search with reranking
    results = await reranker.search("test query", k=3)
    
    # Verify final results
    assert len(results) == 3
    assert results[0].id == "2"  # Document C should be ranked highest by cross-encoder