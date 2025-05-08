"""
Model setup and initialization utilities
"""
import os
import logging
import importlib
from typing import Dict, List, Optional, Any, Union, Tuple
import torch
from pathlib import Path
import json
import shutil
import requests
from tqdm import tqdm

# Configure logging
logger = logging.getLogger(__name__)

class ModelSetup:
    """Automates model setup and initialization"""
    
    def __init__(
        self,
        models_dir: str = "models",
        cache_dir: Optional[str] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the model setup utility
        
        Args:
            models_dir: Directory to store models
            cache_dir: Optional custom cache directory for models
            config_path: Path to model configuration file
        """
        self.models_dir = models_dir
        self.cache_dir = cache_dir
        self.config_path = config_path or os.path.join(models_dir, "models_config.json")
        
        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)
        
        # Set environment variables for HuggingFace
        if self.cache_dir:
            os.environ["TRANSFORMERS_CACHE"] = self.cache_dir
            os.environ["HF_HOME"] = self.cache_dir
            logger.info(f"Using custom cache directory: {self.cache_dir}")
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load model configuration
        
        Returns:
            Dict: Model configuration
        """
        try:
            with open(self.config_path, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded model configuration from {self.config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Configuration file not found at {self.config_path}, creating default")
            default_config = {
                "models": {
                    "embedding": [
                        {
                            "name": "default-embedding",
                            "provider": "sentence-transformers",
                            "model_id": "all-MiniLM-L6-v2",
                            "framework": "pytorch",
                            "dimensions": 384,
                            "device": "cpu"
                        }
                    ],
                    "rag": [
                        {
                            "name": "default-rag",
                            "provider": "langchain",
                            "model_id": "gpt2",
                            "framework": "pytorch",
                            "device": "cpu"
                        }
                    ],
                    "multimodal": [
                        {
                            "name": "default-image-caption",
                            "provider": "huggingface",
                            "model_id": "Salesforce/blip-image-captioning-base",
                            "framework": "pytorch",
                            "device": "cpu"
                        }
                    ]
                },
                "default_models": {
                    "embedding": "default-embedding",
                    "rag": "default-rag",
                    "image_caption": "default-image-caption"
                }
            }
            
            # Save default config
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise
    
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Save model configuration
        
        Args:
            config: Model configuration
        """
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved model configuration to {self.config_path}")
    
    def download_model(
        self,
        model_id: str,
        provider: str,
        local_dir: Optional[str] = None,
        force: bool = False
    ) -> str:
        """
        Download a model from a provider
        
        Args:
            model_id: Model identifier
            provider: Model provider (huggingface, openai, etc.)
            local_dir: Local directory to store the model
            force: Force re-download even if model exists
            
        Returns:
            str: Path to downloaded model
        """
        # Determine local directory
        if not local_dir:
            local_dir = os.path.join(self.models_dir, provider, model_id.replace("/", "_"))
        
        # Create local directory if it doesn't exist
        os.makedirs(local_dir, exist_ok=True)
        
        # Check if model already exists
        model_files = os.listdir(local_dir)
        if not force and len(model_files) > 0:
            logger.info(f"Model already exists at {local_dir}")
            return local_dir
        
        logger.info(f"Downloading model {model_id} from {provider}")
        
        if provider == "huggingface" or provider == "sentence-transformers":
            try:
                # Use transformers to download the model
                from transformers import AutoModel, AutoTokenizer
                
                # Download tokenizer
                tokenizer = AutoTokenizer.from_pretrained(model_id, cache_dir=local_dir)
                tokenizer.save_pretrained(local_dir)
                
                # Download model
                model = AutoModel.from_pretrained(model_id, cache_dir=local_dir)
                model.save_pretrained(local_dir)
                
                logger.info(f"Downloaded model {model_id} to {local_dir}")
                return local_dir
            except Exception as e:
                logger.error(f"Error downloading model {model_id}: {e}")
                raise
        elif provider == "openai":
            # OpenAI models are accessed via API, so we just create a placeholder
            logger.info(f"OpenAI model {model_id} will be accessed via API")
            
            # Create a placeholder file
            with open(os.path.join(local_dir, "model_info.json"), "w") as f:
                json.dump({
                    "model_id": model_id,
                    "provider": "openai",
                    "api_access": True
                }, f, indent=2)
            
            return local_dir
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def test_model(
        self,
        model_id: str,
        provider: str,
        model_type: str,
        device: str = "cpu"
    ) -> bool:
        """
        Test if a model can be loaded and used
        
        Args:
            model_id: Model identifier
            provider: Model provider
            model_type: Type of model (embedding, rag, multimodal)
            device: Device to load the model on
            
        Returns:
            bool: True if model can be loaded and used
        """
        logger.info(f"Testing model {model_id} from {provider}")
        
        try:
            if provider == "huggingface" or provider == "sentence-transformers":
                if model_type == "embedding":
                    # Test with sentence-transformers
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer(model_id, device=device)
                    
                    # Generate an embedding
                    test_text = "This is a test sentence for embedding."
                    embedding = model.encode(test_text)
                    
                    # Check if embedding is valid
                    if embedding is None or len(embedding) == 0:
                        logger.error(f"Model {model_id} returned invalid embedding")
                        return False
                    
                    logger.info(f"Successfully tested model {model_id} (embedding size: {len(embedding)})")
                    
                    # Free up memory
                    del model
                    torch.cuda.empty_cache()
                    
                    return True
                    
                elif model_type == "rag" or model_type == "multimodal":
                    # Test with transformers
                    from transformers import AutoModel, AutoTokenizer
                    
                    # Load tokenizer and model
                    tokenizer = AutoTokenizer.from_pretrained(model_id)
                    model = AutoModel.from_pretrained(model_id)
                    
                    # Move to device
                    model = model.to(device)
                    
                    # Test with a sample input
                    test_text = "This is a test sentence for the model."
                    inputs = tokenizer(test_text, return_tensors="pt").to(device)
                    outputs = model(**inputs)
                    
                    # Check if outputs are valid
                    if outputs is None:
                        logger.error(f"Model {model_id} returned invalid outputs")
                        return False
                    
                    logger.info(f"Successfully tested model {model_id}")
                    
                    # Free up memory
                    del model
                    torch.cuda.empty_cache()
                    
                    return True
            
            elif provider == "openai":
                # OpenAI models require API access, so we just check if the API key is set
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("OPENAI_API_KEY environment variable is not set")
                    return False
                
                logger.info(f"OpenAI API key is set, model {model_id} is ready for use")
                return True
            
            else:
                logger.error(f"Unsupported provider: {provider}")
                return False
                
        except Exception as e:
            logger.error(f"Error testing model {model_id}: {e}")
            return False
    
    def preprocess_model(
        self,
        model_id: str,
        provider: str,
        model_type: str,
        device: str = "cpu",
        optimize: bool = True
    ) -> bool:
        """
        Preprocess a model for faster inference
        
        Args:
            model_id: Model identifier
            provider: Model provider
            model_type: Type of model
            device: Device to optimize for
            optimize: Whether to apply optimizations
            
        Returns:
            bool: True if preprocessing succeeded
        """
        if not optimize:
            logger.info(f"Skipping model optimization for {model_id}")
            return True
        
        logger.info(f"Preprocessing model {model_id} for faster inference")
        
        try:
            if provider == "huggingface" or provider == "sentence-transformers":
                if device == "cuda" and torch.cuda.is_available():
                    # For CUDA, we'll try to use torch.jit
                    try:
                        if model_type == "embedding":
                            from sentence_transformers import SentenceTransformer
                            model = SentenceTransformer(model_id, device=device)
                            
                            # Create a traced model
                            local_dir = os.path.join(self.models_dir, provider, model_id.replace("/", "_"))
                            traced_model_path = os.path.join(local_dir, "traced_model.pt")
                            
                            # Create a sample input
                            test_text = "This is a test sentence for the model."
                            
                            # Define a function to trace
                            def encode_fn(text):
                                return model.encode(text)
                            
                            # Trace the model
                            traced_model = torch.jit.trace(encode_fn, [test_text])
                            
                            # Save the traced model
                            torch.jit.save(traced_model, traced_model_path)
                            
                            logger.info(f"Saved traced model to {traced_model_path}")
                            
                            # Free up memory
                            del model
                            torch.cuda.empty_cache()
                            
                            return True
                    except Exception as e:
                        logger.warning(f"Failed to create traced model: {e}")
                        # Continue without tracing
                
                # For CPU, quantize the model if possible
                if device == "cpu" and model_type in ["rag", "multimodal"]:
                    try:
                        from transformers import AutoModelForCausalLM, AutoTokenizer
                        
                        # Load tokenizer and model
                        tokenizer = AutoTokenizer.from_pretrained(model_id)
                        model = AutoModelForCausalLM.from_pretrained(model_id)
                        
                        # Quantize the model
                        model = torch.quantization.quantize_dynamic(
                            model,
                            {torch.nn.Linear},
                            dtype=torch.qint8
                        )
                        
                        # Save the quantized model
                        local_dir = os.path.join(self.models_dir, provider, model_id.replace("/", "_"))
                        quantized_model_path = os.path.join(local_dir, "quantized_model.pt")
                        torch.save(model.state_dict(), quantized_model_path)
                        
                        logger.info(f"Saved quantized model to {quantized_model_path}")
                        
                        # Free up memory
                        del model
                        torch.cuda.empty_cache()
                        
                        return True
                    except Exception as e:
                        logger.warning(f"Failed to quantize model: {e}")
                        # Continue without quantization
            
            # If we got here, no optimizations were applied but that's OK
            logger.info(f"No optimizations applied for model {model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error preprocessing model {model_id}: {e}")
            return False
    
    def setup_all_models(self, force: bool = False, test: bool = True, optimize: bool = True) -> Dict[str, bool]:
        """
        Set up all models from the configuration
        
        Args:
            force: Force re-download even if models exist
            test: Test models after download
            optimize: Apply optimizations
            
        Returns:
            Dict: Status of each model setup
        """
        config = self.load_config()
        results = {}
        
        # Process all model types
        for model_type, models in config["models"].items():
            for model_info in models:
                model_id = model_info["model_id"]
                provider = model_info["provider"]
                device = model_info.get("device", "cpu")
                
                logger.info(f"Setting up {model_type} model: {model_id} (provider: {provider})")
                
                try:
                    # Download model
                    self.download_model(model_id, provider, force=force)
                    
                    # Test model if requested
                    if test:
                        test_result = self.test_model(model_id, provider, model_type, device)
                        if not test_result:
                            logger.error(f"Failed to test model {model_id}")
                            results[model_id] = False
                            continue
                    
                    # Preprocess model if requested
                    if optimize:
                        preprocess_result = self.preprocess_model(
                            model_id,
                            provider,
                            model_type,
                            device,
                            optimize
                        )
                        if not preprocess_result:
                            logger.warning(f"Failed to preprocess model {model_id}")
                    
                    # Mark as successful
                    results[model_id] = True
                    
                except Exception as e:
                    logger.error(f"Error setting up model {model_id}: {e}")
                    results[model_id] = False
        
        # Print summary
        success_count = sum(1 for status in results.values() if status)
        total_count = len(results)
        logger.info(f"Model setup complete: {success_count}/{total_count} models successful")
        
        return results
    
    def get_model_path(self, model_id: str, provider: str) -> str:
        """
        Get the local path to a model
        
        Args:
            model_id: Model identifier
            provider: Model provider
            
        Returns:
            str: Path to the model
        """
        return os.path.join(self.models_dir, provider, model_id.replace("/", "_"))
    
    @staticmethod
    def is_cuda_available() -> bool:
        """
        Check if CUDA is available
        
        Returns:
            bool: True if CUDA is available
        """
        return torch.cuda.is_available()
    
    @staticmethod
    def get_available_memory() -> Dict[str, int]:
        """
        Get available memory information
        
        Returns:
            Dict: Available memory info
        """
        import psutil
        
        # Get system memory
        system_mem = psutil.virtual_memory()
        
        memory_info = {
            "system_total_mb": system_mem.total // (1024 * 1024),
            "system_available_mb": system_mem.available // (1024 * 1024),
            "system_percent": system_mem.percent
        }
        
        # Get GPU memory if available
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                # Get GPU stats in MB
                gpu_stats = torch.cuda.get_device_properties(i)
                reserved_memory = torch.cuda.memory_reserved(i) // (1024 * 1024)
                allocated_memory = torch.cuda.memory_allocated(i) // (1024 * 1024)
                
                memory_info[f"gpu_{i}_total_mb"] = gpu_stats.total_memory // (1024 * 1024)
                memory_info[f"gpu_{i}_reserved_mb"] = reserved_memory
                memory_info[f"gpu_{i}_allocated_mb"] = allocated_memory
                memory_info[f"gpu_{i}_available_mb"] = (
                    gpu_stats.total_memory // (1024 * 1024) - allocated_memory
                )
        
        return memory_info
    
    def generate_status_report(self) -> Dict[str, Any]:
        """
        Generate a status report for all models
        
        Returns:
            Dict: Status report
        """
        config = self.load_config()
        report = {
            "system": {
                "cuda_available": self.is_cuda_available(),
                "memory": self.get_available_memory(),
                "models_dir": os.path.abspath(self.models_dir)
            },
            "models": {}
        }
        
        # Process all model types
        for model_type, models in config["models"].items():
            report["models"][model_type] = []
            
            for model_info in models:
                model_id = model_info["model_id"]
                provider = model_info["provider"]
                
                # Get model path
                model_path = self.get_model_path(model_id, provider)
                
                # Check if model exists
                model_exists = os.path.exists(model_path) and len(os.listdir(model_path)) > 0
                
                # Get model size if it exists
                model_size_mb = 0
                if model_exists:
                    for dirpath, dirnames, filenames in os.walk(model_path):
                        for filename in filenames:
                            filepath = os.path.join(dirpath, filename)
                            model_size_mb += os.path.getsize(filepath) / (1024 * 1024)
                
                # Add to report
                report["models"][model_type].append({
                    "name": model_info.get("name", model_id),
                    "model_id": model_id,
                    "provider": provider,
                    "device": model_info.get("device", "cpu"),
                    "status": "available" if model_exists else "not_downloaded",
                    "path": model_path if model_exists else None,
                    "size_mb": round(model_size_mb, 2) if model_exists else 0
                })
        
        # Add default models
        report["default_models"] = config.get("default_models", {})
        
        return report


def initialize_models(
    models_dir: str = "models",
    cache_dir: Optional[str] = None,
    config_path: Optional[str] = None,
    force: bool = False,
    test: bool = True,
    optimize: bool = True
) -> Dict[str, bool]:
    """
    Initialize all models needed for the application
    
    Args:
        models_dir: Directory to store models
        cache_dir: Optional custom cache directory for models
        config_path: Path to model configuration file
        force: Force re-download even if models exist
        test: Test models after download
        optimize: Apply optimizations
        
    Returns:
        Dict: Status of each model setup
    """
    model_setup = ModelSetup(models_dir, cache_dir, config_path)
    return model_setup.setup_all_models(force, test, optimize)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize models
    initialize_models(force=False, test=True, optimize=True)