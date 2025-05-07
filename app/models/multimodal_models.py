import os
import logging
import torch
from typing import Dict, List, Optional, Union, Any, Tuple
import numpy as np
from enum import Enum
from PIL import Image
import io
import base64

# CLIP ve diğer multimodal modeller için gerekli kütüphaneler
from transformers import CLIPProcessor, CLIPModel, CLIPTokenizerFast
from transformers import ViTFeatureExtractor, ViTModel
from transformers import AutoProcessor, AutoModel

from app.core.config import settings
from app.utils.metrics import model_load_time, model_usage_counter, gpu_memory_usage

logger = logging.getLogger(__name__)

class MultiModalType(str, Enum):
    """Multi-modal model türleri."""
    CLIP = "clip"
    VIT = "vit"
    FLAVA = "flava"
    BLIP = "blip"
    CUSTOM = "custom"


class MultiModalModelInfo:
    """Multimodal model bilgilerini saklayan sınıf."""
    def __init__(
        self, 
        name: str, 
        model_type: MultiModalType,
        model_id: str,
        image_dimension: int,
        text_dimension: Optional[int] = None,
        device: str = None,
        max_sequence_length: int = 77,  # CLIP için varsayılan
        max_image_size: Tuple[int, int] = (224, 224),  # Çoğu model için varsayılan
        metadata: Dict[str, Any] = None
    ):
        self.name = name
        self.model_type = model_type
        self.model_id = model_id
        self.image_dimension = image_dimension
        self.text_dimension = text_dimension or image_dimension
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.max_sequence_length = max_sequence_length
        self.max_image_size = max_image_size
        self.metadata = metadata or {}
        
        # Runtime attributes
        self.model = None
        self.processor = None
        self.tokenizer = None
        self.is_loaded = False
        self.last_used = None
        self.load_time = None
        self.error = None


class MultiModalManager:
    """
    Multimodal modelleri yöneten sınıf.
    
    Farklı multimodal modelleri (CLIP, ViT, FLAVA vb.) yükleme, boşaltma ve kullanma
    işlemlerini yönetir. Hem metinlerin hem de görüntülerin embedding'lerini oluşturabilir.
    """
    
    def __init__(self):
        """Initialize the multimodal manager."""
        self.models: Dict[str, MultiModalModelInfo] = {}
        self.default_model_name = None
        
        logger.info("Initializing MultiModalManager")
        
        # Register models from config
        self._register_models_from_config()
    
    def _register_models_from_config(self):
        """Register models defined in configuration."""
        models_config = settings.multimodal_models
        
        if not models_config:
            logger.warning("No multimodal models defined in configuration")
            return
        
        for model_config in models_config:
            try:
                model_info = MultiModalModelInfo(
                    name=model_config.name,
                    model_type=model_config.model_type,
                    model_id=model_config.model_id,
                    image_dimension=model_config.image_dimension,
                    text_dimension=model_config.text_dimension,
                    device=model_config.device,
                    max_sequence_length=model_config.max_sequence_length,
                    max_image_size=model_config.max_image_size,
                    metadata={
                        "description": model_config.description,
                        "version": model_config.version
                    }
                )
                
                self.register_model(model_info)
                
                # Set as default if specified
                if model_config.is_default:
                    self.default_model_name = model_info.name
                    logger.info(f"Set {model_info.name} as default multimodal model")
                
            except Exception as e:
                logger.error(f"Error registering multimodal model {model_config.name}: {str(e)}")
        
        # Set first model as default if none specified
        if not self.default_model_name and self.models:
            self.default_model_name = next(iter(self.models))
            logger.info(f"No default multimodal model specified, using {self.default_model_name}")
    
    def register_model(self, model_info: MultiModalModelInfo) -> None:
        """Register a new multimodal model."""
        if model_info.name in self.models:
            logger.warning(f"Multimodal model {model_info.name} already registered, overwriting")
        
        self.models[model_info.name] = model_info
        logger.info(f"Registered multimodal model {model_info.name} ({model_info.model_id})")
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a multimodal model into memory.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            bool: True if model was loaded successfully, False otherwise
        """
        if model_name not in self.models:
            logger.error(f"Multimodal model {model_name} not found")
            return False
        
        model_info = self.models[model_name]
        
        # Skip if already loaded
        if model_info.is_loaded and model_info.model is not None:
            logger.debug(f"Multimodal model {model_name} already loaded")
            return True
        
        try:
            import torch
            
            start_time = time.time()
            
            # Load the model based on type
            if model_info.model_type == MultiModalType.CLIP:
                # Load CLIP model and processor
                model_info.model = CLIPModel.from_pretrained(model_info.model_id).to(model_info.device)
                model_info.processor = CLIPProcessor.from_pretrained(model_info.model_id)
                
            elif model_info.model_type == MultiModalType.VIT:
                # Load ViT model and feature extractor
                model_info.model = ViTModel.from_pretrained(model_info.model_id).to(model_info.device)
                model_info.processor = ViTFeatureExtractor.from_pretrained(model_info.model_id)
                
            elif model_info.model_type == MultiModalType.FLAVA:
                # Load FLAVA model and processor
                model_info.model = AutoModel.from_pretrained(model_info.model_id).to(model_info.device)
                model_info.processor = AutoProcessor.from_pretrained(model_info.model_id)
                
            elif model_info.model_type == MultiModalType.BLIP:
                # Load BLIP model and processor
                model_info.model = AutoModel.from_pretrained(model_info.model_id).to(model_info.device)
                model_info.processor = AutoProcessor.from_pretrained(model_info.model_id)
                
            else:
                raise ValueError(f"Unsupported multimodal model type: {model_info.model_type}")
            
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
                logger.info(f"Multimodal model {model_name} loaded on {model_info.device}, using {mem_allocated:.2f} GB GPU memory")
            else:
                logger.info(f"Multimodal model {model_name} loaded on {model_info.device} in {model_info.load_time:.2f}s")
            
            return True
            
        except Exception as e:
            model_info.is_loaded = False
            model_info.error = str(e)
            logger.error(f"Error loading multimodal model {model_name}: {str(e)}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """
        Unload a multimodal model from memory.
        
        Args:
            model_name: Name of the model to unload
            
        Returns:
            bool: True if model was unloaded successfully, False otherwise
        """
        if model_name not in self.models:
            logger.error(f"Multimodal model {model_name} not found")
            return False
        
        model_info = self.models[model_name]
        
        # Skip if not loaded
        if not model_info.is_loaded or model_info.model is None:
            logger.debug(f"Multimodal model {model_name} not loaded")
            return True
        
        try:
            # Clear model and processor
            del model_info.model
            if model_info.processor:
                del model_info.processor
            
            # Clear CUDA cache if using CUDA
            if model_info.device.startswith("cuda") and torch.cuda.is_available():
                with torch.cuda.device(torch.device(model_info.device)):
                    torch.cuda.empty_cache()
            
            # Update model information
            model_info.model = None
            model_info.processor = None
            model_info.is_loaded = False
            
            logger.info(f"Multimodal model {model_name} unloaded from {model_info.device}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading multimodal model {model_name}: {str(e)}")
            return False
    
    def get_model(self, model_name: Optional[str] = None) -> Optional[MultiModalModelInfo]:
        """
        Get a multimodal model by name, or the default model if no name provided.
        
        Args:
            model_name: Name of the model to get, or None for default
            
        Returns:
            MultiModalModelInfo or None if model not found
        """
        name = model_name or self.default_model_name
        
        if not name:
            logger.error("No multimodal model name provided and no default model set")
            return None
        
        if name not in self.models:
            logger.error(f"Multimodal model {name} not found")
            return None
        
        model_info = self.models[name]
        
        # Load model if not loaded
        if not model_info.is_loaded:
            success = self.load_model(name)
            if not success:
                logger.error(f"Failed to load multimodal model {name}")
                return None
        
        # Update last used timestamp
        model_info.last_used = time.time()
        
        return model_info
    
    async def encode_image(
        self,
        image: Union[str, bytes, Image.Image],
        model_name: Optional[str] = None,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Encode an image to an embedding vector.
        
        Args:
            image: Image to encode (PIL Image, base64 string, or bytes)
            model_name: Name of the model to use, or None for default
            normalize: Whether to normalize the embedding
            
        Returns:
            numpy.ndarray: Image embedding
        """
        # Get model
        model_info = self.get_model(model_name)
        if not model_info:
            raise ValueError(f"Multimodal model not found: {model_name or 'default'}")
        
        # Process the image
        pil_image = self._process_image_input(image)
        
        # Record metrics
        model_usage_counter.labels(model_name=model_info.name).inc()
        
        try:
            # Process image based on model type
            if model_info.model_type == MultiModalType.CLIP:
                # Process image with CLIP processor
                inputs = model_info.processor(
                    images=pil_image,
                    return_tensors="pt"
                ).to(model_info.device)
                
                # Get image embeddings
                with torch.no_grad():
                    image_features = model_info.model.get_image_features(**inputs)
                    
                    if normalize:
                        image_features = image_features / image_features.norm(dim=1, keepdim=True)
                    
                    # Move to CPU and convert to numpy
                    embedding = image_features.cpu().numpy()
                
            elif model_info.model_type in [MultiModalType.VIT, MultiModalType.FLAVA, MultiModalType.BLIP]:
                # Process image with appropriate processor
                inputs = model_info.processor(
                    images=pil_image,
                    return_tensors="pt"
                ).to(model_info.device)
                
                # Get image embeddings
                with torch.no_grad():
                    outputs = model_info.model(**inputs)
                    image_features = outputs.pooler_output  # Most models use this
                    
                    if normalize:
                        image_features = image_features / image_features.norm(dim=1, keepdim=True)
                    
                    # Move to CPU and convert to numpy
                    embedding = image_features.cpu().numpy()
            
            else:
                raise ValueError(f"Unsupported multimodal model type: {model_info.model_type}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error encoding image with model {model_info.name}: {str(e)}")
            raise
    
    async def encode_text(
        self,
        text: Union[str, List[str]],
        model_name: Optional[str] = None,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Encode text to an embedding vector using multimodal model.
        
        Args:
            text: Text to encode
            model_name: Name of the model to use, or None for default
            normalize: Whether to normalize the embedding
            
        Returns:
            numpy.ndarray: Text embedding
        """
        # Get model
        model_info = self.get_model(model_name)
        if not model_info:
            raise ValueError(f"Multimodal model not found: {model_name or 'default'}")
        
        # Ensure text is a list
        if isinstance(text, str):
            text = [text]
        
        # Record metrics
        model_usage_counter.labels(model_name=model_info.name).inc()
        
        try:
            # Process text based on model type
            if model_info.model_type == MultiModalType.CLIP:
                # Process text with CLIP processor
                inputs = model_info.processor(
                    text=text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=model_info.max_sequence_length
                ).to(model_info.device)
                
                # Get text embeddings
                with torch.no_grad():
                    text_features = model_info.model.get_text_features(**inputs)
                    
                    if normalize:
                        text_features = text_features / text_features.norm(dim=1, keepdim=True)
                    
                    # Move to CPU and convert to numpy
                    embedding = text_features.cpu().numpy()
                
            elif model_info.model_type in [MultiModalType.FLAVA, MultiModalType.BLIP]:
                # Process text with appropriate processor
                inputs = model_info.processor(
                    text=text,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=model_info.max_sequence_length
                ).to(model_info.device)
                
                # Get text embeddings
                with torch.no_grad():
                    outputs = model_info.model(**inputs)
                    text_features = outputs.text_embeds  # or appropriate field
                    
                    if normalize:
                        text_features = text_features / text_features.norm(dim=1, keepdim=True)
                    
                    # Move to CPU and convert to numpy
                    embedding = text_features.cpu().numpy()
            
            else:
                raise ValueError(f"Model type {model_info.model_type} does not support text encoding")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error encoding text with model {model_info.name}: {str(e)}")
            raise
    
    async def compute_similarity(
        self,
        image: Union[str, bytes, Image.Image],
        text: Union[str, List[str]],
        model_name: Optional[str] = None
    ) -> Union[float, List[float]]:
        """
        Compute similarity between an image and text(s).
        
        Args:
            image: Image to compare
            text: Text or list of texts to compare
            model_name: Name of the model to use, or None for default
            
        Returns:
            float or List[float]: Similarity score(s) between 0 and 1
        """
        # Get model
        model_info = self.get_model(model_name)
        if not model_info:
            raise ValueError(f"Multimodal model not found: {model_name or 'default'}")
        
        # Ensure text is a list
        is_single_text = isinstance(text, str)
        if is_single_text:
            text = [text]
        
        # Process the image
        pil_image = self._process_image_input(image)
        
        # Record metrics
        model_usage_counter.labels(model_name=model_info.name).inc()
        
        try:
            # Compute similarity based on model type
            if model_info.model_type == MultiModalType.CLIP:
                # Process inputs with CLIP processor
                inputs = model_info.processor(
                    text=text,
                    images=pil_image,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=model_info.max_sequence_length
                ).to(model_info.device)
                
                # Compute similarity scores
                with torch.no_grad():
                    outputs = model_info.model(**inputs)
                    logits_per_image = outputs.logits_per_image
                    probs = logits_per_image.softmax(dim=1)
                    
                    # Move to CPU and convert to numpy
                    similarities = probs.cpu().numpy()
                
            elif model_info.model_type in [MultiModalType.FLAVA, MultiModalType.BLIP]:
                # For other models, we compute embeddings separately and then calculate similarity
                image_embedding = await self.encode_image(
                    image=pil_image,
                    model_name=model_name,
                    normalize=True
                )
                
                text_embeddings = await self.encode_text(
                    text=text,
                    model_name=model_name,
                    normalize=True
                )
                
                # Compute cosine similarity
                similarities = np.matmul(text_embeddings, image_embedding.T)
                similarities = similarities.flatten()
            
            else:
                raise ValueError(f"Unsupported multimodal model type: {model_info.model_type}")
            
            # Return single value if input was a single text
            if is_single_text:
                return float(similarities[0])
            
            return similarities.tolist()
            
        except Exception as e:
            logger.error(f"Error computing similarity with model {model_info.name}: {str(e)}")
            raise
    
    def _process_image_input(self, image: Union[str, bytes, Image.Image]) -> Image.Image:
        """
        Process different image input formats to PIL Image.
        
        Args:
            image: Image in various formats (PIL Image, base64 string, or bytes)
            
        Returns:
            PIL.Image.Image: Processed PIL Image
        """
        if isinstance(image, Image.Image):
            return image
        
        if isinstance(image, str):
            # Check if it's a base64 string
            if image.startswith('data:image'):
                # Extract the base64 part
                image = image.split(',')[1]
            
            # Decode base64
            try:
                image_data = base64.b64decode(image)
                return Image.open(io.BytesIO(image_data))
            except Exception as e:
                # Not a valid base64 string, try as a file path
                try:
                    return Image.open(image)
                except Exception:
                    raise ValueError(f"Invalid image string format: {str(e)}")
        
        if isinstance(image, bytes):
            return Image.open(io.BytesIO(image))
        
        raise ValueError(f"Unsupported image type: {type(image)}")
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all registered multimodal models with their information.
        
        Returns:
            List of dictionaries with model information
        """
        models_info = []
        
        for name, model_info in self.models.items():
            info = {
                "name": name,
                "type": model_info.model_type,
                "model_id": model_info.model_id,
                "image_dimension": model_info.image_dimension,
                "text_dimension": model_info.text_dimension,
                "device": model_info.device,
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


# Create a singleton instance
_multimodal_manager = None

def get_multimodal_manager() -> MultiModalManager:
    """Get the multimodal manager singleton instance."""
    global _multimodal_manager
    if _multimodal_manager is None:
        _multimodal_manager = MultiModalManager()
    return _multimodal_manager