"""
Unit tests for retrieval service
"""
import unittest
import json
import os
from unittest.mock import patch, MagicMock
import numpy as np

from ModularMind.API.services.retrieval.service import RetrievalService
from ModularMind.API.services.embedding import EmbeddingService

class TestRetrievalService(unittest.TestCase):
    """Test retrieval service functionality"""
    
    def setUp(self):
        # Create a temp config file
        self.retrieval_config_path = "temp_retrieval_test_config.json"
        self.test_retrieval_config = {
            "vector_store": {
                "store_type": "memory",
                "dimensions": {"default": 384},
                "metric": "cosine",
                "default_embedding_model": "test-model"
            },
            "hybrid_search": {
                "vector_weight": 0.7,
                "keyword_weight": 0.3,
                "enable_reranking": False
            },
            "chunking": {
                "default_chunk_size": 500,
                "default_chunk_overlap": 50,
                "default_strategy": "recursive"
            },
            "cache_search_results": True,
            "search_result_cache_ttl": 3600
        }
        
        with open(self.retrieval_config_path, "w") as f:
            json.dump(self.test_retrieval_config, f)
        
        # Mock the embedding service
        self.mock_embedding_service = MagicMock(spec=EmbeddingService)
        self.mock_embedding_service.create_embedding.return_value = np.random.rand(384).tolist()
        self.mock_embedding_service.default_model_id = "test-model"
        
        # Create retrieval service with patched embedding service
        with patch('ModularMind.API.services.retrieval.service.EmbeddingService', return_value=self.mock_embedding_service):
            self.service = RetrievalService(self.retrieval_config_path)
        
    def tearDown(self):
        # Clean up temp config files
        if os.path.exists(self.retrieval_config_path):
            os.remove(self.retrieval_config_path)
    
    def test_add_document(self):
        """Test adding a document to the retrieval service"""
        # Mock the vector store add_document method
        self.service.vector_store.add_document = MagicMock(return_value="doc123")
        
        # Test document
        document = {
            "text": "This is a test document for retrieval service",
            "metadata": {"source": "test", "author": "unit test"}
        }
        
        # Add document
        doc_id = self.service.add_document(document)
        
        # Verify
        self.assertEqual(doc_id, "doc123")
        self.service.vector_store.add_document.assert_called_once()
    
    def test_search(self):
        """Test search functionality"""
        # Mock search results
        mock_results = [
            MagicMock(document_id="doc1", text="Result 1", score=0.95, metadata={"source": "test"}),
            MagicMock(document_id="doc2", text="Result 2", score=0.85, metadata={"source": "test"})
        ]
        
        # Mock vector store search
        self.service.vector_store.search = MagicMock(return_value=mock_results)
        
        # Perform search
        query = "test query"
        results = self.service.search(query)
        
        # Verify
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].document_id, "doc1")
        self.assertEqual(results[1].document_id, "doc2")
        self.mock_embedding_service.create_embedding.assert_called_once_with(query, None)
    
    def test_hybrid_search(self):
        """Test hybrid search (vector + keyword)"""
        # Mock vector and keyword search results
        mock_vector_results = [
            MagicMock(document_id="doc1", text="Vector Result 1", score=0.95),
            MagicMock(document_id="doc3", text="Vector Result 3", score=0.75)
        ]
        
        mock_keyword_results = [
            MagicMock(document_id="doc1", text="Keyword Result 1", score=0.90),
            MagicMock(document_id="doc2", text="Keyword Result 2", score=0.80)
        ]
        
        # Mock the search methods
        self.service.vector_store.search = MagicMock(return_value=mock_vector_results)
        self.service.keyword_search = MagicMock(return_value=mock_keyword_results)
        
        # Mock the hybrid_search_blend method to use our direct implementation
        def blend_mock(vector_results, keyword_results, vector_weight=0.7, keyword_weight=0.3):
            # Simple implementation for testing
            result_map = {}
            
            # Process vector results
            for result in vector_results:
                result_map[result.document_id] = {
                    "document_id": result.document_id,
                    "text": result.text,
                    "score": result.score * vector_weight,
                    "metadata": getattr(result, "metadata", {})
                }
            
            # Process keyword results
            for result in keyword_results:
                if result.document_id in result_map:
                    result_map[result.document_id]["score"] += result.score * keyword_weight
                else:
                    result_map[result.document_id] = {
                        "document_id": result.document_id,
                        "text": result.text,
                        "score": result.score * keyword_weight,
                        "metadata": getattr(result, "metadata", {})
                    }
            
            # Convert to list and sort by score
            blended_results = list(result_map.values())
            blended_results.sort(key=lambda x: x["score"], reverse=True)
            
            # Convert to result objects
            return [MagicMock(**item) for item in blended_results]
        
        self.service._blend_search_results = MagicMock(side_effect=blend_mock)
        
        # Perform hybrid search
        query = "hybrid test query"
        search_type = "hybrid"
        results = self.service.search(query, {"search_type": search_type})
        
        # Verify
        self.service.vector_store.search.assert_called_once()
        self.service.keyword_search.assert_called_once()
        self.service._blend_search_results.assert_called_once()
        
        # We should have results for doc1, doc2, and doc3 with blended scores
        self.assertEqual(len(results), 3)
    
    def test_delete_document(self):
        """Test deleting a document"""
        # Mock vector store delete method
        self.service.vector_store.delete_document = MagicMock(return_value=True)
        
        # Delete document
        doc_id = "doc_to_delete"
        result = self.service.delete_document(doc_id)
        
        # Verify
        self.assertTrue(result)
        self.service.vector_store.delete_document.assert_called_once_with(doc_id)

if __name__ == '__main__':
    unittest.main()