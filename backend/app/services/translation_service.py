from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
from enum import Enum

from app.core.settings import get_settings
from app.services.llm_service import get_llm_service

settings = get_settings()
logger = logging.getLogger(__name__)


class TranslationProvider(str, Enum):
    LLM = "llm"               # Use configured LLM for translation
    HUGGINGFACE = "huggingface"  # Use HuggingFace models
    CUSTOM = "custom"         # Use custom translation service/model


class TranslationService:
    """
    Service for translating text between languages.
    
    Supports multiple translation providers and languages.
    """
    
    def __init__(self):
        """Initialize the translation service."""
        self.provider = TranslationProvider(settings.multilingual.translation_provider 
                                          if hasattr(settings.multilingual, 'translation_provider') 
                                          else "llm")
        self.default_language = settings.multilingual.default_language
        self.supported_languages = settings.multilingual.supported_languages
        self.llm_service = get_llm_service()
        
        # HuggingFace models (if enabled)
        self.hf_models = {}
        
        # Load translation models if needed
        if settings.multilingual.translation_enabled:
            self._initialize_translation()
    
    def _initialize_translation(self):
        """Initialize translation models or services."""
        if self.provider == TranslationProvider.HUGGINGFACE:
            try:
                # Only import if needed
                from transformers import MarianMTModel, MarianTokenizer
                
                # Load models for each language pair as needed
                for lang in self.supported_languages:
                    if lang == self.default_language:
                        continue
                        
                    # Define model name
                    if self.default_language == "en" and lang != "en":
                        model_name = f"Helsinki-NLP/opus-mt-en-{lang}"
                    elif self.default_language != "en" and lang == "en":
                        model_name = f"Helsinki-NLP/opus-mt-{self.default_language}-en"
                    else:
                        # For non-English language pairs, we'll use English as a pivot
                        continue
                        
                    try:
                        # Load tokenizer and model
                        tokenizer = MarianTokenizer.from_pretrained(model_name)
                        model = MarianMTModel.from_pretrained(model_name)
                        
                        # Store model and tokenizer
                        self.hf_models[f"{self.default_language}-{lang}"] = {
                            "tokenizer": tokenizer,
                            "model": model
                        }
                        
                        logger.info(f"Loaded translation model for {self.default_language} -> {lang}")
                    except Exception as e:
                        logger.error(f"Failed to load translation model {model_name}: {str(e)}")
            
            except ImportError:
                logger.error("Failed to import transformers. HuggingFace translation unavailable.")
                # Fall back to LLM
                self.provider = TranslationProvider.LLM
    
    def get_language_name(self, lang_code: str) -> str:
        """Get the name of a language from its code."""
        language_names = {
            "en": "English",
            "tr": "Turkish",
            "de": "German",
            "fr": "French",
            "es": "Spanish",
            "it": "Italian",
            "nl": "Dutch",
            "pt": "Portuguese",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
        }
        
        return language_names.get(lang_code, lang_code)
    
    async def is_language_supported(self, lang_code: str) -> bool:
        """Check if a language is supported."""
        return lang_code in self.supported_languages
    
    async def translate_with_llm(
        self,
        text: str,
        source_lang: str,
        target_lang: str
    ) -> str:
        """Translate text using LLM."""
        if source_lang == target_lang:
            return text
            
        source_name = self.get_language_name(source_lang)
        target_name = self.get_language_name(target_lang)
        
        prompt = f"""
        Translate the following {source_name} text to {target_name}.
        Preserve the formatting, and translate as accurately as possible.
        
        Text to translate:
        {text}
        
        {target_name} translation:
        """
        
        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.1  # Lower temperature for more