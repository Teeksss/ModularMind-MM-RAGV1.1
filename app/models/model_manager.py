import os
import logging
import torch
from typing import Dict, List, Optional, Union, Any
import threading
import time
from enum import Enum
import numpy as np

from sentence_transformers import SentenceTransformer
from transformers import AutoModel, AutoTokenizer

from app.core.config import settings
from app.utils.metrics import model_load_time, model_usage_counter, gpu_memory_usage

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Enum for supported model types."""
    SENTENCE_TRANSFORMER = "sentence_transformer"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


class ModelInfo:
    """Class to store information about a model."""
    def __init__(
        self, 
        name: str, 
        model_type: ModelType,
        model_id: str,
        dimension: int,
        device: str = None,
        max_sequence_length: int = 512,
        tokenizer_name: Optional[str] = None,
        pooling_strategy: str = "mean",
        normalize_embeddings: bool = True,
        metadata: Dict[str, Any] = None
    ):
        self.name = name
        self.model_type = model_type
        self.model_id = model_id
        self.dimension = dimension
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_sequence_length = max_sequence_length
        self.tokenizer_name = tokenizer_name or model_id
        self.pooling_strategy = pooling_strategy
        self.normalize_embeddings = normalize_embeddings
        self.metadata = metadata or {}
        
        # Runtime attributes
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.last_used = None
        self.load_time = None
        self.error = None


class ModelManager:
    """
    Manager for embedding models.
    
    Handles loading, unloading, and accessing embedding models.
    Supports multiple model types and dynamic model selection.
    """
    
    def __init__(self):
        """Initialize the model manager."""
        self.models: Dict[str, ModelInfo] = {}
        self.default_model_name = None
        self._lock = threading.RLock()
        
        logger.info("Initializing ModelManager")
        
        # Register models from config
        self._register_models_from_config()
    
    def _register_models_from_config(self):
        """Register models defined in configuration."""
        models_config = settings.embedding_models
        
        if not models_config:
            logger.warning("No embedding models defined in configuration")
            return
        
        # Process each model definition
        for model_config in models_config:
            try:
                model_info = ModelInfo(
                    name=model_config.name,
                    model_type=model_config.model_type,
                    model_id=model_config.model_id,
                    dimension=model_config.dimension,
                    device=model_config.device,
                    max_sequence_length=model_config.max_sequence_length,
                    tokenizer_name=model_config.tokenizer_name,
                    pooling_strategy=model_config.pooling_strategy,
                    normalize_embeddings=model_config.normalize_embeddings,
                    metadata={
                        "description": model_config.description,
                        "language": model_config.language,
                        "version": model_config.version
                    }
                )
                
                self.register_model(model_info)
                
                # Set as default if specified
                if model_config.is_default:
                    self.default_model_name = model_info.name
                    logger.info(f"Set {model_info.name} as default model")
                
            except Exception as e:
                logger.error(f"Error registering model {model_config.name}: {str(e)}")
        
        # Set first model as default if none specified
        if not self.default_model_name and self.models:
            self.default_model_name = next(iter(self.models))
            logger.info(f"No default model specified, using {self.default_model_name}")
    
    def register_model(self, model_info: ModelInfo) -> None:
        """Register a new model."""
        with self._lock:
            if model_info.name in self.models:
                logger.warning(f"Model {model_info.name} already registered, overwriting")
            
            self.models[model_info.name] = model_info
            logger.info(f"Registered model {model_info.name} ({model_info.model_id})")
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model into memory.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        with self._lock:
            if model_name not in self.models:
                logger.error(f"Model {model_name} not found")
                return False
            
            model_info = self.models[model_name]
            
            # Skip if already loaded
            if model_info.is_loaded and model_info.model is not None:
                logger.debug(f"Model {model_name} already loaded")
                return True
            
            try:
                start_time = time.time()
                
                # Load the model based on type
                if model_info.model_type == ModelType.SENTENCE_TRANSFORMER:
                    model_info.model = SentenceTransformer(
                        model_info.model_id, 
                        device=model_info.device
                    )
                
                elif model_info.model_type == ModelType.HUGGINGFACE:
                    # Load tokenizer and model
                    model_info.tokenizer = AutoTokenizer.from_pretrained(model_info.tokenizer_name)
                    model_info.model = AutoModel.from_pretrained(model_info.model_id)
                    
                    # Move model to appropriate device
                    model_info.model.to(model_info.device)
                
                elif model_info.model_type == ModelType.CUSTOM:
                    # For custom models, we need to implement a specific loading mechanism
                    # This is just a placeholder for custom model loading logic
                    raise NotImplementedError(f"Custom model loading not implemented for {model_name}")
                
                else:
                    raise ValueError(f"Unsupported model type: {model_info.model_type}")
                
                # Update model information
                model_info.is_loaded = True
                model_info.error = None
                model_info.load_time = time.time() - start_time
                
                # Record metrics
                model_load_time.labels(model_name=model_name, device=model_info.device).observe(model_info.load_time)
                
                # Log GPU memory usage if using CUDA
                if model_info.device.startswith("cuda") and torch.cuda.is_available():
                    mem_allocated = torch.cuda.memory_allocated(torch.device(model_info.device)) / (1024 ** 3)  # GB
                    gpu_memory_usage.labels(model_name=model_name, device=model_info.device).set(mem_allocated)
                    logger.info(f"Model {model_name} loaded on {model_info.device}, using {mem_allocated:.2f} GB GPU memory")
                else:
                    logger.info(f"Model {model_name} loaded on {model_info.device} in {model_info.load_time:.2f}s")
                
                return True
                
            except Exception as e:
                model_info.is_loaded = False
                model_info.error = str(e)
                logger.error(f"Error loading model {model_name}: {str(e)}")
                return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model from memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            bool: True if model was unloaded successfully, False otherwise
        """
        with self._lock:
            if model_name not in self.models:
                logger.error(f"Model {model_name} not found")
                return False
            
            model_info = self.models[model_name]
            
            # Skip if not loaded
            if not model_info.is_loaded or model_info.model is None:
                logger.debug(f"Model {model_name} not loaded")
                return True
            
            try:
                # Clear model and tokenizer
                del model_info.model
                if model_info.tokenizer:
                    del model_info.tokenizer
                
                # Clear CUDA cache if using CUDA
                if model_info.device.startswith("cuda") and torch.cuda.is_available():
                    with torch.cuda.device(torch.device(model_info.device)):
                        torch.cuda.empty_cache()
                
                # Update model information
                model_info.model = None
                model_info.tokenizer = None
                model_info.is_loaded = False
                
                logger.info(f"Model {model_name} unloaded from {model_info.device}")
                return True
                
            except Exception as e:
                logger.error(f"Error unloading model {model_name}: {str(e)}")
                return False
    
    def get_model(self, model_name: Optional[str] = None) -> Optional[ModelInfo]:
        """
        Get a model by name, or the default model if no name provided.
        
        Args:
            model_name: Name of the model to get, or None for default
            
        Returns:
            ModelInfo or None if model not found
        """
        name = model_name or self.default_model_name
        
        if not name:
            logger.error("No model name provided and no default model set")
            return None
        
        with self._lock:
            if name not in self.models:
                logger.error(f"Model {name} not found")
                return None
            
            model_info = self.models[name]
            
            # Load model if not loaded
            if not model_info.is_loaded:
                success = self.load_model(name)
                if not success:
                    logger.error(f"Failed to load model {name}")
                    return None
            
            # Update last used timestamp
            model_info.last_used = time.time()
            
            return model_info
    
    async def encode(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        batch_size: int = 32,
        **kwargs
    ) -> np.ndarray:
        """
        Encode texts to embeddings using the specified model.
        
        Args:
            texts: Text or list of texts to encode
            model_name: Name of the model to use, or None for default
            batch_size: Batch size for encoding
            **kwargs: Additional parameters for encoding
            
        Returns:
            numpy.ndarray: Array of embeddings
        """
        # Get model
        model_info = self.get_model(model_name)
        if not model_info:
            raise ValueError(f"Model not found: {model_name or 'default'}")
        
        # Ensure texts is a list
        if isinstance(texts, str):
            texts = [texts]
        
        # Record metrics
        model_usage_counter.labels(model_name=model_info.name).inc()
        
        try:
            # Encode based on model type
            if model_info.model_type == ModelType.SENTENCE_TRANSFORMER:
                # SentenceTransformer has built-in batching
                embeddings = model_info.model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=model_info.normalize_embeddings
                )
                
            elif model_info.model_type == ModelType.HUGGINGFACE:
                # Manual batching for Hugging Face models
                embeddings = await self._encode_with_huggingface(
                    model_info, texts, batch_size, **kwargs
                )
                
            else:
                raise NotImplementedError(f"Encoding not implemented for model type: {model_info.model_type}")
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error encoding with model {model_info.name}: {str(e)}")
            raise
    
    async def _encode_with_huggingface(
        self,
        model_info: ModelInfo,
        texts: List[str],
        batch_size: int,
        **kwargs
    ) -> np.ndarray:
        """
        Encode texts using a Hugging Face model.
        
        Args:
            model_info: ModelInfo for the model
            texts: List of texts to encode
            batch_size: Batch size for encoding
            **kwargs: Additional parameters for encoding
            
        Returns:
            numpy.ndarray: Array of embeddings
        """
        # Determine pooling strategy
        pooling = kwargs.get("pooling", model_info.pooling_strategy)
        
        # Prepare result array
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # Tokenize
            inputs = model_info.tokenizer(
                batch_texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=model_info.max_sequence_length
            )
            
            # Move inputs to device
            inputs = {k: v.to(model_info.device) for k, v in inputs.items()}
            
            # Forward pass
            with torch.no_grad():
                outputs = model_info.model(**inputs)
                
                # Get embeddings based on pooling strategy
                if pooling == "cls":
                    # Use CLS token embedding
                    embeddings = outputs.last_hidden_state[:, 0]
                elif pooling == "mean":
                    # Mean pooling
                    attention_mask = inputs["attention_mask"]
                    token_embeddings = outputs.last_hidden_state
                    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
                    embeddings = torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)
                else:
                    raise ValueError(f"Unsupported pooling strategy: {pooling}")
                
                # Normalize if requested
                if model_info.normalize_embeddings:
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                
                # Move to CPU and convert to numpy
                embeddings = embeddings.cpu().numpy()
                
            all_embeddings.append(embeddings)
        
        # Combine batches
        return np.vstack(all_embeddings)
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all registered models with their information.
        
        Returns:
            List of dictionaries with model information
        """
        models_info = []
        
        with self._lock:
            for name, model_info in self.models.items():
                info = {
                    "name": name,
                    "type": model_info.model_type,
                    "model_id": model_info.model_id,
                    "dimension": model_info.dimension,
                    "device": model_info.device,
                    "max_sequence_length": model_info.max_sequence_length,
                    "is_loaded": model_info.is_loaded,
                    "is_default": name == self.default_model_name,
                    "metadata": model_info.metadata
                }
                
                # Add additional runtime information if available
                if model_info.is_loaded:
                    info["load_time"] = model_info.load_time
                    info["last_used"] = model_info.last_used
                elif model_info.error:
                    info["error"] = model_info.error
                
                models_info.append(info)
        
        return models_info
    
    def preload_models(self) -> Dict[str, bool]:
        """
        Preload all models marked for preloading in the config.
        
        Returns:
            Dictionary mapping model names to loading success status
        """
        results = {}
        preload_models = settings.preload_models or []
        
        if not preload_models and self.default_model_name:
            # Preload at least the default model if no models specified
            preload_models = [self.default_model_name]
            logger.info(f"No models specified for preloading, loading default model: {self.default_model_name}")
        
        logger.info(f"Preloading {len(preload_models)} models: {', '.join(preload_models)}")
        
        for model_name in preload_models:
            try:
                if model_name in self.models:
                    logger.info(f"Preloading model: {model_name}")
                    success = self.load_model(model_name)
                    results[model_name] = success
                else:
                    logger.warning(f"Cannot preload unknown model: {model_name}")
                    results[model_name] = False
            except Exception as e:
                logger.error(f"Error preloading model {model_name}: {str(e)}")
                results[model_name] = False
        
        return results
    
    def get_model_status(self, model_name: str) -> Dict[str, Any]:
        """
        Get detailed status information for a specific model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            Dictionary with model status information
        """
        with self._lock:
            if model_name not in self.models:
                return {"name": model_name, "status": "not_found"}
            
            model_info = self.models[model_name]
            
            status = {
                "name": model_name,
                "status": "loaded" if model_info.is_loaded else "not_loaded",
                "type": model_info.model_type,
                "model_id": model_info.model_id,
                "dimension": model_info.dimension,
                "device": model_info.device,
                "is_default": model_name == self.default_model_name
            }
            
            # Add runtime information if available
            if model_info.is_loaded:
                status["load_time"] = model_info.load_time
                status["last_used"] = model_info.last_used
                
                # Add memory usage if on CUDA
                if model_info.device.startswith("cuda") and torch.cuda.is_available():
                    with torch.cuda.device(torch.device(model_info.device)):
                        mem_allocated = torch.cuda.memory_allocated() / (1024 ** 3)  # GB
                        status["gpu_memory_usage"] = f"{mem_allocated:.2f} GB"
            elif model_info.error:
                status["error"] = model_info.error
            
            return status


# Create a singleton instance
_model_manager = None

def get_model_manager() -> ModelManager:
    """Get the model manager singleton instance."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager