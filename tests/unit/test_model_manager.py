import pytest
import os
import sys
import torch
import numpy as np
from unittest.mock import patch, MagicMock

# Add root directory to path to make imports work in tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from app.models.model_manager import ModelManager, ModelInfo, ModelType


class TestModelManager:
    """Test the ModelManager class."""
    
    def test_register_model(self):
        """Test registering a model."""
        manager = ModelManager()
        
        # Create a model info
        model_info = ModelInfo(
            name="test-model",
            model_type=ModelType.SENTENCE_TRANSFORMER,
            model_id="test/model",
            dimension=384
        )
        
        # Register the model
        manager.register_model(model_info)
        
        # Check if model is registered
        assert "test-model" in manager.models
        assert manager.models["test-model"] == model_info
    
    def test_get_model_not_found(self):
        """Test getting a model that doesn't exist."""
        manager = ModelManager()
        
        # Try to get a non-existent model
        model = manager.get_model("non-existent-model")
        
        # Check if None is returned
        assert model is None
    
    @patch('app.models.model_manager.SentenceTransformer')
    def test_load_model_sentence_transformer(self, mock_transformer):
        """Test loading a sentence transformer model."""
        manager = ModelManager()
        
        # Create a mock model
        mock_model = MagicMock()
        mock_transformer.return_value = mock_model
        
        # Create model info
        model_info = ModelInfo(
            name="test-model",
            model_type=ModelType.SENTENCE_TRANSFORMER,
            model_id="test/model",
            dimension=384,
            device="cpu"
        )
        
        # Register the model
        manager.register_model(model_info)
        
        # Load the model
        success = manager.load_model("test-model")
        
        # Check if model was loaded
        assert success
        assert manager.models["test-model"].is_loaded
        mock_transformer.assert_called_once_with("test/model", device="cpu")
    
    @pytest.mark.asyncio
    @patch('app.models.model_manager.SentenceTransformer')
    async def test_encode_text(self, mock_transformer):
        """Test encoding text with a model."""
        manager = ModelManager()
        
        # Create a mock model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3, 0.4]])
        mock_transformer.return_value = mock_model
        
        # Create model info
        model_info = ModelInfo(
            name="test-model",
            model_type=ModelType.SENTENCE_TRANSFORMER,
            model_id="test/model",
            dimension=4,
            device="cpu"
        )
        
        # Register and "load" the model
        manager.register_model(model_info)
        manager.models["test-model"].model = mock_model
        manager.models["test-model"].is_loaded = True
        
        # Encode text
        result = await manager.encode("test text", "test-model")
        
        # Check the result
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 4)
        mock_model.encode.assert_called_once()
    
    def test_model_not_loaded_error(self):
        """Test error when model is not loaded."""
        manager = ModelManager()
        
        # Create model info but don't load it
        model_info = ModelInfo(
            name="test-model",
            model_type=ModelType.SENTENCE_TRANSFORMER,
            model_id="test/model",
            dimension=384,
            device="cpu"
        )
        
        # Register the model
        manager.register_model(model_info)
        
        # Try to use the unloaded model
        with patch.object(manager, 'load_model', return_value=False):
            with pytest.raises(ValueError):
                manager.get_model("test-model")
    
    def test_list_models(self):
        """Test listing all models."""
        manager = ModelManager()
        
        # Create and register multiple models
        for i in range(3):
            model_info = ModelInfo(
                name=f"test-model-{i}",
                model_type=ModelType.SENTENCE_TRANSFORMER,
                model_id=f"test/model-{i}",
                dimension=384,
                device="cpu"
            )
            manager.register_model(model_info)
        
        # Set a default model
        manager.default_model_name = "test-model-1"
        
        # List models
        models_list = manager.list_models()
        
        # Check the list
        assert len(models_list) == 3
        assert any(m["name"] == "test-model-0" for m in models_list)
        assert any(m["name"] == "test-model-1" and m["is_default"] for m in models_list)
        assert any(m["name"] == "test-model-2" for m in models_list)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])