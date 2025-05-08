#!/usr/bin/env python
"""
Model Loader Script

This script automates the downloading and initialization of models used
by the ModularMind platform. It handles both embedding and LLM models.

Usage:
    python model_loader.py [--models MODEL_ID [MODEL_ID ...]] [--force] [--cache-dir DIR]

Options:
    --models MODEL_ID     Specific model IDs to load (default: all configured models)
    --force               Force re-download even if model exists in cache
    --cache-dir DIR       Custom cache directory for models
    --provider PROVIDER   Filter models by provider (e.g., 'openai', 'huggingface')
    --type TYPE           Filter models by type (e.g., 'embedding', 'llm')
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import importlib
from typing import List, Dict, Any, Optional, Union
import torch
from tqdm import tqdm

# Add parent directory to path to allow importing from ModularMind
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from ModularMind.API.config import Config
from ModularMind.API.services.embedding.models.base import EmbeddingModel
from ModularMind.API.services.embedding.models.local import LocalModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("model_loader")

class ModelLoader:
    """Automates loading and initialization of models"""
    
    def __init__(
        self, 
        config_path: Optional[str] = None,
        cache_dir: Optional[str] = None,
        force_download: bool = False
    ):
        self.config_path = config_path or os.environ.get(
            "MODULARMIND_CONFIG", 
            os.path.join(parent_dir, "config", "config.json")
        )
        self.cache_dir = cache_dir
        self.force_download = force_download
        self.config = self._load_config()
        
        # Set cache directory if specified
        if self.cache_dir:
            os.environ["TRANSFORMERS_CACHE"] = self.cache_dir
            os.environ["HF_HOME"] = self.cache_dir
            logger.info(f"Using custom cache directory: {self.cache_dir}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")
            sys.exit(1)
    
    def get_embedding_models(self) -> List[Dict[str, Any]]:
        """Get list of embedding models from config"""
        embedding_config_path = self.config.get("embedding_service", {}).get("config_path")
        
        if not embedding_config_path:
            logger.error("Embedding service config path not found in main config")
            return []
        
        # Resolve path - it could be relative to main config
        if not os.path.isabs(embedding_config_path):
            config_dir = os.path.dirname(self.config_path)
            embedding_config_path = os.path.join(config_dir, embedding_config_path)
        
        try:
            with open(embedding_config_path, 'r') as f:
                embedding_config = json.load(f)
            return embedding_config.get("models", [])
        except Exception as e:
            logger.error(f"Failed to load embedding config from {embedding_config_path}: {e}")
            return []
    
    def get_llm_models(self) -> List[Dict[str, Any]]:
        """Get list of LLM models from config"""
        llm_config_path = self.config.get("llm_service", {}).get("config_path")
        
        if not llm_config_path:
            logger.warning("LLM service config path not found in main config")
            return []
        
        # Resolve path - it could be relative to main config
        if not os.path.isabs(llm_config_path):
            config_dir = os.path.dirname(self.config_path)
            llm_config_path = os.path.join(config_dir, llm_config_path)
        
        try:
            with open(llm_config_path, 'r') as f:
                llm_config = json.load(f)
            return llm_config.get("models", [])
        except Exception as e:
            logger.error(f"Failed to load LLM config from {llm_config_path}: {e}")
            return []
    
    def load_local_embedding_model(self, model_config: Dict[str, Any]) -> None:
        """Load a local embedding model"""
        model_id = model_config.get("model_id")
        provider = model_config.get("provider")
        
        if provider != "local" or not model_id:
            return
        
        logger.info(f"Loading local embedding model: {model_id}")
        
        try:
            # Initialize model to trigger download
            model = LocalModel(
                model_id=model_id,
                device=model_config.get("options", {}).get("device", "cpu"),
                normalize_embeddings=model_config.get("options", {}).get("normalize_embeddings", True)
            )
            
            # Test the model with a simple input
            _ = model.generate_embedding("Test input for model initialization")
            logger.info(f"Successfully loaded embedding model: {model_id}")
            
            # Free memory
            if hasattr(model, "_model"):
                del model._model
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Failed to load embedding model {model_id}: {e}")
    
    def load_local_llm_model(self, model_config: Dict[str, Any]) -> None:
        """Load a local LLM model"""
        model_id = model_config.get("model_id")
        provider = model_config.get("provider")
        
        if provider != "local" or not model_id:
            return
        
        logger.info(f"Loading local LLM model: {model_id}")
        
        try:
            # Import the appropriate model class
            module_path = model_config.get("module_path", "ModularMind.API.services.llm.models.local")
            class_name = model_config.get("class_name", "LocalLLM")
            
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)
            
            # Initialize model to trigger download
            model = model_class(
                model_id=model_id,
                **model_config.get("options", {})
            )
            
            # Test the model with a simple input (implementation depends on the model)
            if hasattr(model, "initialize"):
                model.initialize()
            logger.info(f"Successfully loaded LLM model: {model_id}")
            
            # Free memory
            if hasattr(model, "_model"):
                del model._model
            torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Failed to load LLM model {model_id}: {e}")
    
    def filter_models(
        self, 
        models: List[Dict[str, Any]], 
        model_ids: Optional[List[str]] = None,
        provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Filter models by ID and/or provider"""
        filtered = models
        
        if model_ids:
            filtered = [m for m in filtered if m.get("id") in model_ids or m.get("model_id") in model_ids]
        
        if provider:
            filtered = [m for m in filtered if m.get("provider") == provider]
            
        return filtered
    
    def load_models(
        self, 
        model_ids: Optional[List[str]] = None,
        provider: Optional[str] = None,
        model_type: Optional[str] = None
    ) -> None:
        """Load specified models or all models if none specified"""
        models_to_load = []
        
        # Get embedding models if type matches
        if not model_type or model_type.lower() == "embedding":
            embedding_models = self.get_embedding_models()
            embedding_models = self.filter_models(embedding_models, model_ids, provider)
            models_to_load.extend([{"type": "embedding", "config": m} for m in embedding_models])
        
        # Get LLM models if type matches
        if not model_type or model_type.lower() == "llm":
            llm_models = self.get_llm_models()
            llm_models = self.filter_models(llm_models, model_ids, provider)
            models_to_load.extend([{"type": "llm", "config": m} for m in llm_models])
        
        logger.info(f"Found {len(models_to_load)} models to load")
        
        for item in tqdm(models_to_load, desc="Loading models"):
            model_type = item["type"]
            model_config = item["config"]
            
            if model_type == "embedding":
                self.load_local_embedding_model(model_config)
            elif model_type == "llm":
                self.load_local_llm_model(model_config)

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Load and initialize models for ModularMind")
    parser.add_argument("--models", nargs="+", help="Specific model IDs to load")
    parser.add_argument("--force", action="store_true", help="Force re-download even if model exists in cache")
    parser.add_argument("--cache-dir", help="Custom cache directory for models")
    parser.add_argument("--config", help="Path to main configuration file")
    parser.add_argument("--provider", help="Filter models by provider (e.g., 'openai', 'huggingface')")
    parser.add_argument("--type", help="Filter models by type (e.g., 'embedding', 'llm')")
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    loader = ModelLoader(
        config_path=args.config,
        cache_dir=args.cache_dir,
        force_download=args.force
    )
    
    loader.load_models(
        model_ids=args.models,
        provider=args.provider,
        model_type=args.type
    )
    
    logger.info("Model loading complete")

if __name__ == "__main__":
    main()