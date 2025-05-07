import pytest
import os
import sys
import asyncio
import numpy as np
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add root directory to path to make imports work in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.main import app
from app.models.model_manager import get_model_manager, ModelInfo, ModelType


# Create a test client
client = TestClient(app)


class TestEmbeddingAPI:
    """Test the embedding API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_model_manager(self):
        """Set up a mock model manager for tests."""
        # Create a model manager with a test model
        model_manager = get_model_manager()
        
        # Clear any existing models
        model_manager.models = {}
        
        # Create a test model
        model_info = ModelInfo(
            name="test-model",
            model_type=ModelType.SENTENCE_TRANSFORMER,
            model_id="test/model",
            dimension=4,
            device="cpu"
        )
        
        # Register the model
        model_manager.register_model(model_info)
        model_manager.default_model_name = "test-model"
        
        # Create a mock for the encode method
        async def mock_encode(texts, model_name=None, **kwargs):
            """Mock encode method that returns dummy embeddings."""
            if isinstance(texts, str):
                texts = [texts]
            
            # Create dummy embeddings
            return np.array([[0.1, 0.2, 0.3, 0.4] for _ in texts])
        
        # Patch the encode method
        with patch.object(model_manager, 'encode', side_effect=mock_encode):
            # Mark model as loaded
            model_manager.models["test-model"].is_loaded = True
            model_manager.models["test-model"].model = MagicMock()
            
            yield
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        assert "name" in response.json()
        assert "default_model" in response.json()
    
    def test_embed_endpoint(self):
        """Test the embed endpoint."""
        # Test with a single text
        response = client.post(
            "/api/v1/embeddings/embed",
            json={"texts": "This is a test."}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert "model" in data
        assert data["model"] == "test-model"
        assert len(data["embeddings"]) == 1
        assert len(data["embeddings"][0]) == 4
    
    def test_embed_endpoint_with_batch(self):
        """Test the embed endpoint with a batch of texts."""
        # Test with multiple texts
        response = client.post(
            "/api/v1/embeddings/embed",
            json={"texts": ["Text 1", "Text 2", "Text 3"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "embeddings" in data
        assert len(data["embeddings"]) == 3
        assert data["texts_count"] == 3
    
    def test_similarity_endpoint(self):
        """Test the similarity endpoint."""
        # Test similarity computation
        response = client.post(
            "/api/v1/embeddings/similarity",
            json={
                "texts1": ["Text 1", "Text 2"],
                "texts2": ["Text A", "Text B"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "similarities" in data
        assert len(data["similarities"]) == 2
    
    def test_batch_embed_endpoint(self):
        """Test the batch-embed endpoint."""
        # Test batch embedding
        response = client.post(
            "/api/v1/embeddings/batch-embed",
            json={
                "batch": [
                    {"texts": "Single text"},
                    {"texts": ["Multiple", "texts"]}
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 2
        assert data["results"][0]["success"]
        assert data["results"][1]["success"]
        assert len(data["results"][1]["embeddings"]) == 2
    
    def test_models_list_endpoint(self):
        """Test the models listing endpoint."""
        response = client.get("/api/v1/models/")
        
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        assert "default_model" in data
        assert data["default_model"] == "test-model"
        assert len(data["models"]) == 1
        assert data["models"][0]["name"] == "test-model"
    
    def test_health_endpoint(self):
        """Test the health endpoint."""
        response = client.get("/api/v1/health/")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        assert "models" in data


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])