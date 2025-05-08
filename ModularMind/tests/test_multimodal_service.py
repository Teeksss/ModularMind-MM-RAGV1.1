"""
Unit tests for multimodal service
"""
import unittest
import json
import os
from unittest.mock import patch, MagicMock, mock_open
import numpy as np
import io

from ModularMind.API.services.multimodal.service import MultimodalService
from ModularMind.API.services.embedding import EmbeddingService

class TestMultimodalService(unittest.TestCase):
    """Test multimodal service functionality"""
    
    def setUp(self):
        # Create a temp config file
        self.config_path = "temp_multimodal_test_config.json"
        self.test_config = {
            "models": {
                "image": {
                    "provider": "openai",
                    "model_id": "clip",
                    "options": {}
                },
                "image_caption": {
                    "provider": "local",
                    "model_id": "blip-image-captioning-base",
                    "options": {"device": "cpu"}
                },
                "audio": {
                    "provider": "openai",
                    "model_id": "whisper-1",
                    "options": {}
                }
            },
            "fusion": {
                "method": "vector_concat",
                "weights": {
                    "text": 1.0,
                    "image": 0.7,
                    "audio": 0.5
                }
            },
            "embedding_service": {
                "config_path": "embedding_service_config.json"
            }
        }
        
        with open(self.config_path, "w") as f:
            json.dump(self.test_config, f)
            
        # Create the service with mocked components
        with patch('ModularMind.API.services.embedding.EmbeddingService') as mock_embedding_service:
            self.mock_embedding = mock_embedding_service.return_value
            self.mock_embedding.create_embedding.return_value = np.random.rand(384).tolist()
            self.service = MultimodalService(self.config_path)
        
    def tearDown(self):
        # Clean up temp config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    @patch('ModularMind.API.services.multimodal.image_processor.ImageProcessor.process_image')
    def test_process_image(self, mock_process_image):
        """Test processing an image"""
        # Mock image processing results
        mock_result = {
            "embedding": np.random.rand(512).tolist(),
            "features": {"objects": ["car", "person"]},
            "caption": "A person standing next to a car"
        }
        mock_process_image.return_value = mock_result
        
        # Create test image data
        test_image = io.BytesIO(b"fake image data")
        
        # Process the image
        result = self.service.process_image(test_image)
        
        # Verify
        self.assertEqual(result["embedding"], mock_result["embedding"])
        self.assertEqual(result["features"], mock_result["features"])
        self.assertEqual(result["caption"], mock_result["caption"])
        mock_process_image.assert_called_once()
    
    @patch('ModularMind.API.services.multimodal.audio_processor.AudioProcessor.process_audio')
    def test_process_audio(self, mock_process_audio):
        """Test processing audio"""
        # Mock audio processing results
        mock_result = {
            "embedding": np.random.rand(256).tolist(),
            "features": {"duration": 10.5},
            "transcript": "This is a test transcript"
        }
        mock_process_audio.return_value = mock_result
        
        # Create test audio data
        test_audio = io.BytesIO(b"fake audio data")
        
        # Process the audio
        result = self.service.process_audio(test_audio)
        
        # Verify
        self.assertEqual(result["embedding"], mock_result["embedding"])
        self.assertEqual(result["features"], mock_result["features"])
        self.assertEqual(result["transcript"], mock_result["transcript"])
        mock_process_audio.assert_called_once()
    
    @patch('ModularMind.API.services.multimodal.image_processor.ImageProcessor.process_image')
    @patch('ModularMind.API.services.multimodal.audio_processor.AudioProcessor.process_audio')
    def test_process_multimodal(self, mock_process_audio, mock_process_image):
        """Test processing multiple modalities together"""
        # Mock processing results
        mock_image_result = {
            "embedding": np.random.rand(512).tolist(),
            "features": {"objects": ["car", "person"]},
            "caption": "A person standing next to a car"
        }
        mock_process_image.return_value = mock_image_result
        
        mock_audio_result = {
            "embedding": np.random.rand(256).tolist(),
            "features": {"duration": 10.5},
            "transcript": "This is a test transcript"
        }
        mock_process_audio.return_value = mock_audio_result
        
        # Create test data
        test_text = "This is a test query"
        test_image = io.BytesIO(b"fake image data")
        test_audio = io.BytesIO(b"fake audio data")
        
        # Process multimodal input
        result = self.service.process_multimodal(
            text=test_text,
            image=test_image,
            audio=test_audio
        )
        
        # Verify
        self.assertIn("text_result", result)
        self.assertIn("image_result", result)
        self.assertIn("audio_result", result)
        self.assertIn("combined_embedding", result)
        
        # Text should have been processed with embedding service
        self.mock_embedding.create_embedding.assert_called_once_with(test_text)
        
        # Image and audio should have been processed with respective processors
        mock_process_image.assert_called_once()
        mock_process_audio.assert_called_once()
    
    def test_process_text_only(self):
        """Test processing text only"""
        # Create test data
        test_text = "This is a test text"
        
        # Process text
        result = self.service.process_multimodal(text=test_text)
        
        # Verify
        self.assertIn("text_result", result)
        self.assertNotIn("image_result", result)
        self.assertNotIn("audio_result", result)
        self.assertIn("combined_embedding", result)
        
        # Text should have been processed with embedding service
        self.mock_embedding.create_embedding.assert_called_once_with(test_text)

if __name__ == '__main__':
    unittest.main()