import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import numpy as np
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException
import fasttext
import unicodedata
import os

from app.core.config import settings
from app.utils.cache import get_cache

# Ensure deterministic language detection
DetectorFactory.seed = 0

logger = logging.getLogger(__name__)


class LanguageDetector:
    """
    Language detection service that can identify the language of text.
    
    Supports multiple detection methods (langdetect, fasttext) and caching
    of results for improved performance.
    """
    
    def __init__(self, method: str = "fasttext", cache_ttl: int = 3600):
        """
        Initialize the language detector.
        
        Args:
            method: Detection method to use ("langdetect" or "fasttext")
            cache_ttl: Cache time-to-live in seconds
        """
        self.method = method
        self.cache_ttl = cache_ttl
        self.cache = get_cache()
        self.model = None
        
        # Load fasttext model if needed
        if self.method == "fasttext":
            self._load_fasttext_model()
        
        # Language code to name mapping
        self.language_names = {
            'en': 'English',
            'tr': 'Turkish',
            'de': 'German',
            'fr': 'French',
            'es': 'Spanish',
            'it': 'Italian',
            'pt': 'Portuguese',
            'nl': 'Dutch',
            'pl': 'Polish',
            'ru': 'Russian',
            'ar': 'Arabic',
            'zh': 'Chinese',
            'ja': 'Japanese',
            'ko': 'Korean',
            # Add more languages as needed
        }
    
    def _load_fasttext_model(self):
        """Load the fasttext language detection model."""
        try:
            # Check if model path is set in config
            model_path = getattr(settings, "language_model_path", None)
            
            if not model_path:
                # Use default path or fasttext pretrained model
                model_path = os.path.join(settings.models_dir, "lid.176.bin")
            
            # Download model if it doesn't exist
            if not os.path.exists(model_path):
                logger.info(f"Downloading language detection model to {model_path}")
                import urllib.request
                urllib.request.urlretrieve(
                    "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin",
                    model_path
                )
            
            logger.info(f"Loading language detection model from {model_path}")
            self.model = fasttext.load_model(model_path)
            logger.info("Language detection model loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading fasttext model: {str(e)}")
            logger.warning("Falling back to langdetect method")
            self.method = "langdetect"
    
    async def detect_language(self, text: str) -> str:
        """
        Detect the language of a text.
        
        Args:
            text: The text to detect language for
            
        Returns:
            str: ISO 639-1 language code (en, fr, de, etc.)
        """
        if not text or len(text.strip()) < 20:
            # For very short texts, detection can be unreliable
            return "en"  # Default to English
        
        # Clean and normalize text
        text = self._clean_text(text)
        
        # Check cache first
        cache_key = f"lang_detect:{hash(text[:1000])}"  # Use only first 1000 chars for hash
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            # Detect language
            if self.method == "fasttext":
                language = self._detect_with_fasttext(text)
            else:
                language = self._detect_with_langdetect(text)
            
            # Cache result
            await self.cache.set(cache_key, language, self.cache_ttl)
            
            return language
            
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return "en"  # Default to English on error
    
    def _detect_with_langdetect(self, text: str) -> str:
        """
        Detect language using langdetect library.
        
        Args:
            text: The text to detect
            
        Returns:
            str: ISO 639-1 language code
        """
        try:
            return detect(text)
        except LangDetectException:
            return "en"  # Default to English
    
    def _detect_with_fasttext(self, text: str) -> str:
        """
        Detect language using fasttext model.
        
        Args:
            text: The text to detect
            
        Returns:
            str: ISO 639-1 language code
        """
        if not self.model:
            return self._detect_with_langdetect(text)
        
        # Get predictions
        predictions = self.model.predict(text.replace("\n", " "))
        
        # Extract language code
        language = predictions[0][0].replace("__label__", "")
        
        return language
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text for language detection.
        
        Args:
            text: Text to clean
            
        Returns:
            str: Cleaned text
        """
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize unicode characters
        text = unicodedata.normalize('NFKC', text)
        
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        return text.strip()
    
    def get_language_name(self, language_code: str) -> str:
        """
        Get the human-readable language name from a language code.
        
        Args:
            language_code: ISO 639-1 language code (en, fr, de, etc.)
            
        Returns:
            str: Human-readable language name
        """
        return self.language_names.get(language_code, f"Unknown ({language_code})")


class MultilingualTextPreprocessor:
    """
    Preprocess text in multiple languages for improved retrieval and embedding.
    
    Applies language-specific preprocessing steps to improve retrieval
    across different languages.
    """
    
    def __init__(self):
        """Initialize the multilingual text preprocessor."""
        self.language_detector = LanguageDetector()
        
        # Language-specific stopwords
        self.stopwords = {
            'en': set(['the', 'and', 'is', 'in', 'to', 'of', 'a', 'for', 'with', 'on', 'that', 'by']),
            'tr': set(['ve', 'bir', 'bu', 'ile', 'için', 'de', 'da', 'ki', 'çok', 'daha', 'olarak', 'olan']),
            # Add more languages as needed
        }
    
    async def preprocess(
        self,
        text: str,
        language: Optional[str] = None,
        remove_stopwords: bool = False,
        normalize_chars: bool = True,
        stem: bool = False
    ) -> str:
        """
        Preprocess text for improved retrieval.
        
        Args:
            text: Text to preprocess
            language: ISO 639-1 language code (if None, will be detected)
            remove_stopwords: Whether to remove stopwords
            normalize_chars: Whether to normalize characters
            stem: Whether to apply stemming (language dependent)
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
        
        # Detect language if not provided
        if not language:
            language = await self.language_detector.detect_language(text)
        
        # Normalize characters
        if normalize_chars:
            text = self._normalize_chars(text, language)
        
        # Remove stopwords if requested
        if remove_stopwords:
            text = self._remove_stopwords(text, language)
        
        # Apply stemming if requested
        if stem:
            text = self._apply_stemming(text, language)
        
        return text
    
    def _normalize_chars(self, text: str, language: str) -> str:
        """
        Normalize characters based on language.
        
        Args:
            text: Text to normalize
            language: ISO 639-1 language code
            
        Returns:
            str: Normalized text
        """
        # Apply unicode normalization (NFKC combines compatibility characters)
        text = unicodedata.normalize('NFKC', text)
        
        # Language-specific normalizations
        if language == 'tr':
            # Turkish-specific: normalize İ/I and ı/i
            text = text.replace('İ', 'I').replace('ı', 'i')
        
        return text
    
    def _remove_stopwords(self, text: str, language: str) -> str:
        """
        Remove stopwords based on language.
        
        Args:
            text: Text to process
            language: ISO 639-1 language code
            
        Returns:
            str: Text with stopwords removed
        """
        # Get language-specific stopwords
        language_stopwords = self.stopwords.get(language, set())
        
        if not language_stopwords:
            return text
        
        # Split into words, filter stopwords, and rejoin
        words = text.split()
        filtered_words = [w for w in words if w.lower() not in language_stopwords]
        
        return ' '.join(filtered_words)
    
    def _apply_stemming(self, text: str, language: str) -> str:
        """
        Apply language-specific stemming.
        
        Args:
            text: Text to stem
            language: ISO 639-1 language code
            
        Returns:
            str: Stemmed text
        """
        # TODO: Implement language-specific stemming
        # For now, return unstemmed text
        return text


# Create a singleton instance
_language_detector = None
_text_preprocessor = None

def get_language_detector() -> LanguageDetector:
    """Get the language detector singleton instance."""
    global _language_detector
    if _language_detector is None:
        _language_detector = LanguageDetector()
    return _language_detector

def get_text_preprocessor() -> MultilingualTextPreprocessor:
    """Get the text preprocessor singleton instance."""
    global _text_preprocessor
    if _text_preprocessor is None:
        _text_preprocessor = MultilingualTextPreprocessor()
    return _text_preprocessor