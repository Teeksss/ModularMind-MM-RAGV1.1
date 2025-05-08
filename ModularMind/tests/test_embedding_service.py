"""
Unit tests for embedding service
"""
import unittest
import json
import os
from unittest.mock import patch, MagicMock
import numpy as np

from ModularMind.API.services.embedding import EmbeddingService
from ModularMind.API.services.embedding.cache import EmbeddingCache
from ModularMind.API.services.embedding.model_router import ModelRouter

class TestEmbeddingService(unittest.TestCase):
    """Test embedding service functionality"""
    
    def setUp(self):
        # Create a temp config file
        self.config_path = "temp_embedding_test_config.json"
        self.test_config = {
            "models": [
                {
                    "id": "test-model",
                    "name": "Test Model",
                    "provider": "local",
                    "model_id": "sentence-transformers/all-MiniLM-L6-v2",
                    "dimensions": 384,
                    "options": {"device": "cpu"}
                }
            ],
            "default_model": "test-model",
            "cache": {
                "enabled": True,
                "max_size": 100,
                "ttl": 3600,
                "persistent": False
            },
            "model_router": {
                "enable_auto_routing": False
            }
        }
        
        with open(self.config_path, "w") as f:
            json.dump(self.test_config, f)
            
        # Create the service with mocked components
        self.service = EmbeddingService(self.config_path)
        
    def tearDown(self):
        # Clean up temp config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    @patch('ModularMind.API.services.embedding.models.LocalModel.generate_embedding')
    def test_create_embedding(self, mock_generate):
        """Test creating embeddings with default model"""
        # Mock the model's generate_embedding method
        mock_generate.return_value = np.random.rand(384).tolist()
        
        # Test creating an embedding
        text = "This is a test text"
        embedding = self.service.create_embedding(text)
        
        # Verify
        self.assertIsNotNone(embedding)
        self.assertEqual(len(embedding), 384)
        mock_generate.assert_called_once_with(text)
    
    @patch('ModularMind.API.services.embedding.cache.EmbeddingCache.get')
    @patch('ModularMind.API.services.embedding.cache.EmbeddingCache.set')
    @patch('ModularMind.API.services.embedding.models.LocalModel.generate_embedding')
    def test_embedding_caching(self, mock_generate, mock_cache_set, mock_cache_get):
        """Test that embeddings are cached and retrieved from cache"""
        # Set up the mocks
        test_text = "This is a test for caching"
        test_embedding = np.random.rand(384).tolist()
        mock_generate.return_value = test_embedding
        mock_cache_get.return_value = None  # First call to cache returns miss
        
        # First embedding call should generate and cache
        embedding1 = self.service.create_embedding(test_text)
        self.assertEqual(embedding1, test_embedding)
        mock_generate.assert_called_once()
        mock_cache_set.assert_called_once()
        
        # Set up for second call, returns from cache
        mock_cache_get.return_value = test_embedding
        
        # Second call with same text should use cache
        embedding2 = self.service.create_embedding(test_text)
        self.assertEqual(embedding2, test_embedding)
        # generate_embedding should still have only been called once
        mock_generate.assert_called_once()
        
    @patch('ModularMind.API.services.embedding.models.OpenAIModel.generate_embedding')
    def test_model_selection(self, mock_generate):
        """Test selecting specific model for embedding"""
        # Mock OpenAI model
        mock_generate.return_value = np.random.rand(1536).tolist()
        
        # Add a mock OpenAI model to the service
        self.service.models["openai-test"] = MagicMock()
        self.service.models["openai-test"].generate_embedding = mock_generate
        
        # Test creating with specific model
        text = "Test text for model selection"
        embedding = self.service.create_embedding(text, "openai-test")
        
        # Verify correct model was used
        mock_generate.assert_called_once_with(text)
        self.assertIsNotNone(embedding)

    def test_batch_embeddings(self):
        """Test creating batch embeddings"""
        # Create a spy for the create_embedding method
        with patch.object(self.service, 'create_embedding') as mock_create:
            mock_create.side_effect = lambda text, model_id=None: np.random.rand(384).tolist()
            
            # Test batch embedding
            texts = ["Text 1", "Text 2", "Text 3"]
            embeddings = self.service.create_batch_embeddings(texts)
            
            # Verify
            self.assertEqual(len(embeddings), 3)
            self.assertEqual(len(embeddings[0]), 384)
            self.assertEqual(mock_create.call_count, 3)

if __name__ == '__main__':
    unittest.main()