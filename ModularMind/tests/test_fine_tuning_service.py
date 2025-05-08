"""
Unit tests for fine-tuning service
"""
import unittest
import json
import os
from unittest.mock import patch, MagicMock
import numpy as np

from ModularMind.API.services.fine_tuning.service import FineTuningService

class TestFineTuningService(unittest.TestCase):
    """Test fine-tuning service functionality"""
    
    def setUp(self):
        # Create a temp config file
        self.config_path = "temp_fine_tuning_test_config.json"
        self.test_config = {
            "providers": {
                "openai": {
                    "enabled": True,
                    "api_key_env": "OPENAI_API_KEY",
                    "default_models": {
                        "chat": "gpt-3.5-turbo",
                        "embedding": "text-embedding-3-small"
                    }
                },
                "hugging_face": {
                    "enabled": True,
                    "api_key_env": "HF_API_KEY",
                    "default_models": {
                        "text-generation": "gpt2"
                    }
                }
            },
            "storage": {
                "type": "file",
                "path": "data/fine_tuning"
            },
            "default_training_params": {
                "openai": {
                    "n_epochs": 3,
                    "batch_size": 2,
                    "learning_rate_multiplier": 1.0
                },
                "hugging_face": {
                    "num_train_epochs": 3,
                    "per_device_train_batch_size": 8,
                    "learning_rate": 5e-5
                }
            }
        }
        
        with open(self.config_path, "w") as f:
            json.dump(self.test_config, f)
            
        # Set environment variables for testing
        os.environ["OPENAI_API_KEY"] = "test-openai-key"
        os.environ["HF_API_KEY"] = "test-hf-key"
        
        # Create service
        self.service = FineTuningService(self.config_path)
        
    def tearDown(self):
        # Clean up temp config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    @patch('ModularMind.API.services.fine_tuning.providers.openai_provider.OpenAIProvider.create_fine_tuning_job')
    def test_create_openai_fine_tuning_job(self, mock_create_job):
        """Test creating an OpenAI fine-tuning job"""
        # Mock job creation result
        mock_job = {
            "job_id": "ft-job-123",
            "model_id": "gpt-3.5-turbo",
            "status": "created",
            "created_at": "2025-05-07T14:00:00Z"
        }
        mock_create_job.return_value = mock_job
        
        # Create test training data
        training_data = [
            {"messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Hello, how are you?"},
                {"role": "assistant", "content": "I'm doing well, thank you!"}
            ]}
        ]
        
        # Create fine-tuning job
        result = self.service.create_fine_tuning_job(
            provider="openai",
            model_id="gpt-3.5-turbo",
            training_data=training_data,
            validation_data=None,
            options={"n_epochs": 5}
        )
        
        # Verify
        self.assertEqual(result["job_id"], mock_job["job_id"])
        self.assertEqual(result["status"], mock_job["status"])
        
        # Verify provider was called with correct parameters
        mock_create_job.assert_called_once_with(
            model_id="gpt-3.5-turbo",
            training_data=training_data,
            validation_data=None,
            hyperparameters={"n_epochs": 5}
        )
    
    @patch('ModularMind.API.services.fine_tuning.providers.hugging_face_provider.HuggingFaceProvider.create_fine_tuning_job')
    def test_create_huggingface_fine_tuning_job(self, mock_create_job):
        """Test creating a HuggingFace fine-tuning job"""
        # Mock job creation result
        mock_job = {
            "job_id": "hf-job-456",
            "model_id": "gpt2",
            "status": "running",
            "created_at": "2025-05-07T14:05:00Z"
        }
        mock_create_job.return_value = mock_job
        
        # Create test training data
        training_data = {
            "train": [
                {"text": "Example training text 1"},
                {"text": "Example training text 2"}
            ]
        }
        
        # Create fine-tuning job
        result = self.service.create_fine_tuning_job(
            provider="hugging_face",
            model_id="gpt2",
            training_data=training_data,
            validation_data=None,
            options={"num_train_epochs": 2}
        )
        
        # Verify
        self.assertEqual(result["job_id"], mock_job["job_id"])
        self.assertEqual(result["status"], mock_job["status"])
        
        # Verify provider was called with correct parameters
        mock_create_job.assert_called_once_with(
            model_id="gpt2",
            training_data=training_data,
            validation_data=None,
            hyperparameters={"num_train_epochs": 2}
        )
    
    @patch('ModularMind.API.services.fine_tuning.providers.openai_provider.OpenAIProvider.get_fine_tuning_job')
    def test_get_fine_tuning_job(self, mock_get_job):
        """Test getting a fine-tuning job status"""
        # Mock job status
        mock_job = {
            "job_id": "ft-job-123",
            "model_id": "gpt-3.5-turbo",
            "status": "succeeded",
            "created_at": "2025-05-07T14:00:00Z",
            "finished_at": "2025-05-07T14:30:00Z",
            "fine_tuned_model": "ft:gpt-3.5-turbo:org-123:custom-name:789"
        }
        mock_get_job.return_value = mock_job
        
        # Get job status
        result = self.service.get_fine_tuning_job("openai", "ft-job-123")
        
        # Verify
        self.assertEqual(result["job_id"], mock_job["job_id"])
        self.assertEqual(result["status"], mock_job["status"])
        self.assertEqual(result["fine_tuned_model"], mock_job["fine_tuned_model"])
        
        # Verify provider was called with correct parameters
        mock_get_job.assert_called_once_with("ft-job-123")
    
    @patch('ModularMind.API.services.fine_tuning.providers.openai_provider.OpenAIProvider.list_fine_tuned_models')
    def test_list_fine_tuned_models(self, mock_list_models):
        """Test listing fine-tuned models"""
        # Mock models list
        mock_models = [
            {
                "model_id": "ft:gpt-3.5-turbo:org-123:custom-name:789",
                "base_model": "gpt-3.5-turbo",
                "created_at": "2025-05-01T10:00:00Z",
                "status": "ready"
            },
            {
                "model_id": "ft:gpt-3.5-turbo:org-123:another-model:456",
                "base_model": "gpt-3.5-turbo",
                "created_at": "2025-05-05T14:30:00Z",
                "status": "ready"
            }
        ]
        mock_list_models.return_value = mock_models
        
        # List models
        result = self.service.list_fine_tuned_models("openai")
        
        # Verify
        self.assertEqual(len(result), len(mock_models))
        self.assertEqual(result[0]["model_id"], mock_models[0]["model_id"])
        self.assertEqual(result[1]["model_id"], mock_models[1]["model_id"])
        
        # Verify provider was called
        mock_list_models.assert_called_once()

if __name__ == '__main__':
    unittest.main()