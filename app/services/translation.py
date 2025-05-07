import logging
from typing import Dict, List, Optional, Union, Any
import aiohttp
import time
import os
from pydantic import BaseModel

from app.core.config import settings
from app.utils.cache import get_cache

logger = logging.getLogger(__name__)


class TranslationResult(BaseModel):
    """Model for translation results."""
    translated_text: str
    source_language: str
    target_language: str
    confidence: Optional[float] = None
    execution_time: Optional[float] = None


class TranslationService:
    """
    Service for translating text between languages.
    
    Supports multiple translation providers:
    1. Local models (CTranslate2)
    2. External API (optional API key required)
    3. OpenAI translation (via the API)
    """
    
    def __init__(
        self,
        provider: str = "local",
        api_key: Optional[str] = None,
        cache_ttl: int = 86400,
        model_path: Optional[str] = None
    ):
        """
        Initialize the translation service.
        
        Args:
            provider: Translation provider ("local", "external", "openai")
            api_key: API key for external provider
            cache_ttl: Cache time-to-live in seconds
            model_path: Path to local translation model
        """
        self.provider = provider
        self.api_key = api_key
        self.cache_ttl = cache_ttl
        self.model_path = model_path
        self.cache = get_cache()
        self.local_model = None
        
        # Load local model if using local provider
        if self.provider == "local":
            self._load_local_model()
    
    def _load_local_model(self):
        """Load local translation model."""
        try:
            # Attempt to load CTranslate2 (lightweight translation library)
            import ctranslate2
            from transformers import AutoTokenizer
            
            # Default model paths
            model_dir = os.path.join(settings.models_dir, "translation")
            if not self.model_path:
                self.model_path = os.path.join(model_dir, "m2m100")
            
            # Ensure model directory exists
            os.makedirs(model_dir, exist_ok=True)
            
            # Check if model already downloaded
            if not os.path.exists(self.model_path):
                logger.info(f"Translation model not found at {self.model_path}. Will use dynamic loading.")
                return
            
            # Load model and tokenizer
            self.local_model = {
                "translator": ctranslate2.Translator(self.model_path, device="cuda" if settings.use_gpu else "cpu"),
                "tokenizer": AutoTokenizer.from_pretrained("facebook/m2m100_418M")
            }
            
            logger.info(f"Loaded local translation model from {self.model_path}")
            
        except ImportError:
            logger.warning("CTranslate2 not installed. Translation will fall back to external provider.")
            self.provider = "external"
        except Exception as e:
            logger.error(f"Error loading local translation model: {str(e)}")
            self.provider = "external"
    
    async def translate(
        self,
        text: str,
        source_language: Optional[str] = None,
        target_language: str = "en",
        force_refresh: bool = False
    ) -> str:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_language: Source language code (auto-detect if None)
            target_language: Target language code
            force_refresh: Whether to bypass cache
            
        Returns:
            str: Translated text
        """
        if not text:
            return ""
        
        # Skip translation if source and target are the same
        if source_language and source_language == target_language:
            return text
        
        # Check cache first
        cache_key = f"translate:{hash(text)}:{source_language or 'auto'}:{target_language}"
        
        if not force_refresh:
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                return cached_result
        
        start_time = time.time()
        
        try:
            # Translate based on provider
            if self.provider == "local":
                translated_text = await self._translate_local(text, source_language, target_language)
            elif self.provider == "openai":
                translated_text = await self._translate_openai(text, source_language, target_language)
            else:
                translated_text = await self._translate_external(text, source_language, target_language)
            
            # Cache the result
            await self.cache.set(cache_key, translated_text, self.cache_ttl)
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return text  # Return original text on error
    
    async def _translate_local(
        self,
        text: str,
        source_language: Optional[str],
        target_language: str
    ) -> str:
        """
        Translate text using local model.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            str: Translated text
        """
        # Load model if not loaded
        if not self.local_model:
            try:
                self._load_local_model()
            except Exception as e:
                logger.error(f"Error loading local model for translation: {str(e)}")
                # Fall back to external provider
                return await self._translate_external(text, source_language, target_language)
        
        try:
            # Map ISO 639-1 codes to model's expected format
            source_lang = source_language or "en"
            target_lang = target_language
            
            # Tokenize source text
            tokenizer = self.local_model["tokenizer"]
            translator = self.local_model["translator"]
            
            # Set language codes
            tokenizer.src_lang = source_lang
            tokenizer.tgt_lang = target_lang
            
            # Tokenize and translate
            source_tokens = tokenizer.encode(text, return_tensors="pt")
            target_tokens = translator.translate_batch([source_tokens])
            
            # Decode the translated tokens
            translated_text = tokenizer.decode(target_tokens[0].hypotheses[0], skip_special_tokens=True)
            
            return translated_text
            
        except Exception as e:
            logger.error(f"Local translation error: {str(e)}")
            # Fall back to external provider
            return await self._translate_external(text, source_language, target_language)
    
    async def _translate_external(
        self,
        text: str,
        source_language: Optional[str],
        target_language: str
    ) -> str:
        """
        Translate text using external API.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            str: Translated text
        """
        api_url = getattr(settings, "translation_api_url", "https://api.cognitive.microsofttranslator.com/translate")
        api_key = self.api_key or getattr(settings, "translation_api_key", None)
        region = getattr(settings, "translation_api_region", "global")
        
        if not api_key:
            logger.warning("No API key for translation. Returning original text.")
            return text
        
        try:
            # Setup request
            headers = {
                "Ocp-Apim-Subscription-Key": api_key,
                "Ocp-Apim-Subscription-Region": region,
                "Content-type": "application/json"
            }
            
            params = {
                "api-version": "3.0",
                "to": target_language
            }
            
            # Add source language if provided
            if source_language:
                params["from"] = source_language
            
            # Prepare request body
            body = [{"text": text}]
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, headers=headers, params=params, json=body) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and len(data) > 0:
                            translations = data[0].get("translations", [])
                            if translations and len(translations) > 0:
                                return translations[0].get("text", text)
                    else:
                        response_text = await response.text()
                        logger.error(f"Translation API error: {response.status} - {response_text}")
            
            return text  # Return original text on error
            
        except Exception as e:
            logger.error(f"External translation error: {str(e)}")
            return text
    
    async def _translate_openai(
        self,
        text: str,
        source_language: Optional[str],
        target_language: str
    ) -> str:
        """
        Translate text using OpenAI API.
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            str: Translated text
        """
        from app.services.llm_service import get_llm_service
        
        try:
            # Get LLM service
            llm_service = get_llm_service()
            
            # Get language names for better results
            source_name = source_language or "the source language"
            target_name = target_language or "English"
            
            # Create prompt
            prompt = f"""Translate the following text from {source_name} to {target_name}:

Text: {text}

Translation:"""
            
            # Get translation
            translated_text = await llm_service.generate(
                prompt=prompt,
                max_tokens=len(text) * 2,  # Estimate maximum tokens needed
                temperature=0.3,  # Lower temperature for translation
                stop=["\n\n"]  # Stop at empty line
            )
            
            return translated_text.strip()
            
        except Exception as e:
            logger.error(f"OpenAI translation error: {str(e)}")
            # Fall back to external provider
            return await self._translate_external(text, source_language, target_language)


# Create a singleton instance
_translation_service = None

def get_translation_service() -> TranslationService:
    """Get the translation service singleton instance."""
    global _translation_service
    if _translation_service is None:
        # Create service from settings
        provider = getattr(settings, "translation_provider", "local")
        api_key = getattr(settings, "translation_api_key", None)
        model_path = getattr(settings, "translation_model_path", None)
        
        _translation_service = TranslationService(
            provider=provider,
            api_key=api_key,
            model_path=model_path
        )
    return _translation_service